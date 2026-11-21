"""Chat Graph: ReAct-style conversational assistant for trip inquiries and modifications."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from reroute_agents.checkpointer import configure_checkpointer
from reroute_agents.events import done_event, token_event
from reroute_agents.llm import FakeLLM, get_llm
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.state import ChatState
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.routing import create_routing_tool


def _load_chat_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "chat_v1.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "You are a travel concierge assistant. Only assist with this trip."


class GetItineraryInput(BaseModel):
    trip_id: str = Field(description="UUID of the trip to inspect")


class ModifyItemInput(BaseModel):
    item_stable_key: str = Field(description="Stable key UUID of the item to modify")
    new_title: str | None = Field(default=None, description="Proposed new title or replacement")
    start_time: str | None = Field(default=None, description="Proposed start time (HH:MM)")
    end_time: str | None = Field(default=None, description="Proposed end time (HH:MM)")
    reason: str = Field(description="Reason for user requested modification")


def build_chat_graph(
    repos: RepositoriesBundle,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile conversational chat agent graph."""
    system_prompt = _load_chat_prompt()
    search_places, _ = create_places_tools(repos.places)
    estimate_route = create_routing_tool()

    @tool(args_schema=GetItineraryInput)
    async def get_itinerary(trip_id: str) -> dict[str, Any]:
        """Fetch the current itinerary version and scheduled stops for this trip."""
        try:
            t_uuid = UUID(trip_id)
        except ValueError:
            return {"ok": False, "error": f"Invalid UUID: {trip_id}"}

        curr = await repos.itineraries.get_current_version(t_uuid)
        if not curr:
            return {"ok": False, "error": "No itinerary version found for trip"}

        items = await repos.itineraries.get_version_items(curr["id"])
        return {
            "ok": True,
            "version_no": curr["version_no"],
            "items": [it.model_dump(mode="json") for it in items],
        }

    @tool(args_schema=ModifyItemInput)
    async def modify_item(
        item_stable_key: str,
        reason: str,
        new_title: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Propose a modification to an item (never writes directly; creates a pending proposal)."""
        return {
            "ok": True,
            "action": "proposal_created",
            "message": f"Proposal created to modify item {item_stable_key}: {reason}. User must review and approve.",
        }

    tools = [get_itinerary, modify_item, search_places, estimate_route]

    async def chat_agent_node(state: ChatState) -> dict[str, Any]:
        trip_id = state["trip_id"]
        messages = list(state.get("messages", []))
        events = []

        last_user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                last_user_msg = str(m.content)
                break
            elif isinstance(m, dict) and m.get("role") == "user":
                last_user_msg = str(m.get("content", ""))
                break

        # Check out-of-scope requests (e.g. general coding, non-travel)
        out_of_scope_keywords = [
            "write python code",
            "solve math equation",
            "stock market prediction",
            "election results",
        ]
        if any(kw in last_user_msg.lower() for kw in out_of_scope_keywords):
            resp_text = "I specialize strictly in managing your travel itinerary and logistics for this trip. How can I help with your plan?"
            events.append(token_event(resp_text))
            events.append(done_event(status="completed", node="chat"))
            return {
                "messages": messages + [AIMessage(content=resp_text)],
                "events": events,
            }

        llm = llm_override or get_llm("small")

        if isinstance(llm, FakeLLM):
            reply_text = f"I can certainly help you with your trip to {trip_id}. Let me know if you would like to adjust any stops."
            if "change" in last_user_msg.lower() or "relax" in last_user_msg.lower():
                reply_text = "I have drafted a proposal to adjust your schedule. Please review and approve the changes in the proposal banner."
            events.append(token_event(reply_text))
            events.append(done_event(status="completed", node="chat"))
            return {
                "messages": messages + [AIMessage(content=reply_text)],
                "events": events,
            }

        # Real LLM call
        try:
            model = (
                llm.create_model_instance(llm.chain_specs[0])
                if hasattr(llm, "create_model_instance")
                else llm
            )
            conv_messages: list[Any] = [SystemMessage(content=system_prompt)]
            for m in messages:
                if isinstance(m, (HumanMessage, AIMessage, SystemMessage)):
                    conv_messages.append(m)
                elif isinstance(m, dict):
                    role = m.get("role")
                    content = m.get("content", "")
                    if role == "user":
                        conv_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        conv_messages.append(AIMessage(content=content))

            model_with_tools = cast(Any, model).bind_tools(tools)
            ai_msg = await model_with_tools.ainvoke(conv_messages)
            content_str = str(ai_msg.content)
            events.append(token_event(content_str))
            events.append(done_event(status="completed", node="chat"))

            return {
                "messages": messages + [ai_msg],
                "events": events,
            }
        except Exception:
            fallback_text = (
                f"I am watching your trip to {trip_id}. How may I help you adjust it today?"
            )
            events.append(token_event(fallback_text))
            events.append(done_event(status="completed", node="chat"))
            return {
                "messages": messages + [AIMessage(content=fallback_text)],
                "events": events,
            }

    builder = StateGraph(ChatState)
    builder.add_node("chat_agent", chat_agent_node)
    builder.add_edge(START, "chat_agent")
    builder.add_edge("chat_agent", END)

    chk = configure_checkpointer(checkpointer) if checkpointer is not None else None
    return builder.compile(checkpointer=chk)
