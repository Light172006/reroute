"""Chat Agent: ReAct assistant interacting with travelers to refine itineraries."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import time
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from reroute_agents.agents.chat.tools import get_chat_tools
from reroute_agents.checkpointer import configure_checkpointer
from reroute_agents.config import settings
from reroute_agents.events import (
    done_event,
    error_event,
    proposal_event,
    token_event,
    tool_call_event,
    tool_result_event,
)
from reroute_agents.llm import FakeLLM, get_llm
from reroute_agents.repositories.interfaces import RepositoriesBundle
from reroute_agents.state import ChatState, DiffItem, ReplanProposal

logger = logging.getLogger(__name__)


def _load_chat_prompt() -> str:
    path = Path(__file__).resolve().parent.parent.parent / "prompts" / "chat_v1.md"
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


def build_chat_agent(
    repos: RepositoriesBundle,
    llm_override: Any | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile conversational chat agent graph with dedicated chat tools and ReAct loop."""
    system_prompt = _load_chat_prompt()

    # Register and bound dedicated chat tools
    chat_tools = get_chat_tools(
        catalog_repo=repos.places,
        expense_repo=repos.expenses,
        cache_repo=getattr(repos, "cache", None),
    )

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

    tools_list = [get_itinerary, modify_item] + chat_tools
    tools_map = {t.name: t for t in tools_list}

    # -------------------------------------------------------------------------
    # Node 1: Chat Agent (LLM Reasoning & Tool Calling)
    # -------------------------------------------------------------------------
    async def chat_agent_node(state: ChatState) -> dict[str, Any]:
        trip_id = state["trip_id"]
        t_uuid = UUID(trip_id) if isinstance(trip_id, str) else trip_id
        messages = list(state.get("messages", []))
        iteration = state.get("iteration", 0)

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
            redirect_msg = AIMessage(
                content="I can assist you strictly in managing your travel itinerary for this trip. I cannot assist with coding, math equations, or out-of-scope tasks."
            )
            return {
                "messages": messages + [redirect_msg],
                "iteration": iteration + 1,
            }

        curr_version = await repos.itineraries.get_current_version(t_uuid)
        current_summary = curr_version.get("summary", "No itinerary yet") if curr_version else "None"

        augmented_system = (
            f"{system_prompt}\n\n"
            f"Trip ID: {trip_id}\n"
            f"Current Itinerary Status: {current_summary}\n"
            f"Tools available: {list(tools_map.keys())}"
        )

        llm = llm_override or get_llm("small")

        if isinstance(llm, FakeLLM):
            canned_tool_calls = llm.canned_responses.get("tool_calls")
            if canned_tool_calls and iteration == 0:
                ai_msg = AIMessage(
                    content="",
                    tool_calls=canned_tool_calls,
                )
            else:
                resp_text = llm.canned_responses.get(
                    "text", f"I received your message: '{last_user_msg}'"
                )
                ai_msg = AIMessage(content=resp_text)
        else:
            conv_messages: list[Any] = [SystemMessage(content=augmented_system)]
            for m in messages:
                if isinstance(m, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
                    conv_messages.append(m)
                elif isinstance(m, dict):
                    role = m.get("role")
                    content = str(m.get("content", ""))
                    if role == "user":
                        conv_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        conv_messages.append(AIMessage(content=content))

            model = llm.chain_specs[0] if hasattr(llm, "chain_specs") else llm
            from reroute_agents.llm import create_model_instance

            model_inst = create_model_instance(model) if isinstance(model, str) else model
            model_with_tools = cast(Any, model_inst).bind_tools(tools_list)
            ai_msg = await model_with_tools.ainvoke(conv_messages)

        return {
            "messages": messages + [ai_msg],
            "iteration": iteration + 1,
        }

    # -------------------------------------------------------------------------
    # Node 2: Tools Execution Node (ReAct execution of pending tool calls)
    # -------------------------------------------------------------------------
    async def tools_node(state: ChatState) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        last_msg = messages[-1]
        events = []
        proposal_created: ReplanProposal | None = None

        tool_calls = getattr(last_msg, "tool_calls", [])
        tool_messages: list[ToolMessage] = []

        for call in tool_calls:
            tool_name = call.get("name", "")
            tool_args = call.get("args", {})
            call_id = call.get("id", str(uuid4()))

            events.append(tool_call_event(tool=tool_name, args=tool_args, node="chat_tools"))

            if tool_name == "modify_item":
                try:
                    stable_key = tool_args.get("item_stable_key", "")
                    reason = tool_args.get("reason", "User requested change")
                    trip_id = state["trip_id"]
                    t_uuid = UUID(trip_id) if isinstance(trip_id, str) else trip_id

                    curr_v = await repos.itineraries.get_current_version(t_uuid)
                    if curr_v:
                        items = await repos.itineraries.get_version_items(curr_v["id"])
                        sk_uuid = UUID(stable_key)
                        target_item = next((it for it in items if it.stable_key == sk_uuid), None)

                        if target_item:
                            updates: dict[str, Any] = {}
                            if tool_args.get("new_title"):
                                updates["title"] = tool_args["new_title"]
                            if tool_args.get("start_time"):
                                try:
                                    sh, sm = map(int, tool_args["start_time"].split(":"))
                                    updates["start_time"] = time(sh, sm)
                                except Exception as ex:
                                    logger.debug("Failed parsing start_time: %s", ex)
                            if tool_args.get("end_time"):
                                try:
                                    eh, em = map(int, tool_args["end_time"].split(":"))
                                    updates["end_time"] = time(eh, em)
                                except Exception as ex:
                                    logger.debug("Failed parsing end_time: %s", ex)

                            mod_item = target_item.model_copy(update=updates)
                            diff_item = DiffItem(
                                op="replace",
                                day=target_item.day_index,
                                stable_key=target_item.stable_key,
                                before=target_item.model_dump(mode="json"),
                                after=mod_item.model_dump(mode="json"),
                                why=reason,
                            )

                            run_id_raw = state.get("run_id")
                            run_id_val = (
                                UUID(run_id_raw)
                                if isinstance(run_id_raw, str)
                                else (run_id_raw or uuid4())
                            )
                            proposal = ReplanProposal(
                                trip_id=t_uuid,
                                run_id=run_id_val,
                                base_version_id=curr_v["id"],
                                status="pending",
                                reason=f"Chat requested change: {reason}",
                                explanation=f"User requested updating {target_item.title}.",
                                diff=[diff_item],
                                proposed_items=[
                                    mod_item if it.stable_key == sk_uuid else it for it in items
                                ],
                            )
                            await repos.proposals.save_proposal(proposal)
                            proposal_created = proposal
                            events.append(
                                proposal_event(proposal_id=proposal.id, node="chat_tools")
                            )

                            res: dict[str, Any] = {
                                "ok": True,
                                "proposal_id": str(proposal.id),
                                "message": f"Proposal {proposal.id} created for traveler review and approval.",
                            }
                        else:
                            res = {
                                "ok": False,
                                "error": f"Item with stable_key {stable_key} not found",
                            }
                    else:
                        res = {"ok": False, "error": "No current itinerary version found"}
                except Exception as exc:
                    res = {"ok": False, "error": f"Failed to build proposal: {exc}"}

            elif tool_name in tools_map:
                tool_instance = tools_map[tool_name]
                try:
                    if hasattr(tool_instance, "ainvoke"):
                        res = await tool_instance.ainvoke(tool_args)
                    elif hasattr(tool_instance, "invoke"):
                        res = tool_instance.invoke(tool_args)
                    elif callable(tool_instance):
                        call_fn = cast(Callable[..., Any], tool_instance)
                        res = call_fn(**tool_args)
                    else:
                        raise TypeError(
                            f"Tool '{tool_name}' is not callable and has no invoke method"
                        )
                except Exception as exc:
                    err_msg = f"Tool execution failed for '{tool_name}': {exc}"
                    logger.warning(err_msg)
                    res = {"ok": False, "error": err_msg}
                    events.append(
                        error_event(
                            message=err_msg,
                            code="tool_error",
                            node="chat_tools",
                        )
                    )
            else:
                err_msg = f"Unknown tool: '{tool_name}'"
                logger.warning(err_msg)
                res = {"ok": False, "error": err_msg}
                events.append(
                    error_event(
                        message=err_msg,
                        code="tool_not_found",
                        node="chat_tools",
                    )
                )

            summary_text = (
                str(res.get("message", f"Tool {tool_name} completed"))
                if isinstance(res, dict)
                else f"Tool {tool_name} completed"
            )
            events.append(
                tool_result_event(
                    tool=tool_name,
                    ok=res.get("ok", True) if isinstance(res, dict) else True,
                    summary=summary_text,
                    data=res,
                    node="chat_tools",
                )
            )

            tool_messages.append(
                ToolMessage(
                    tool_call_id=call_id,
                    name=tool_name,
                    content=json.dumps(res, default=str),
                )
            )

        update_dict: dict[str, Any] = {
            "messages": messages + tool_messages,
            "events": events,
        }
        if proposal_created is not None:
            update_dict["proposal"] = proposal_created

        return update_dict

    # -------------------------------------------------------------------------
    # Node 3: Finalize Node (Emit final token events & done event)
    # -------------------------------------------------------------------------
    async def finalize_node(state: ChatState) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        iteration = state.get("iteration", 0)
        events = []

        last_msg = messages[-1] if messages else None

        if isinstance(last_msg, AIMessage) and not getattr(last_msg, "tool_calls", None):
            content_str = str(last_msg.content)
        elif iteration >= settings.max_chat_iterations:
            content_str = (
                "I have reached the maximum reasoning steps for this request. "
                "Please review the actions taken or provide further clarification."
            )
            messages.append(AIMessage(content=content_str))
        else:
            content_str = (
                str(getattr(last_msg, "content", ""))
                or "I am watching your trip. Let me know if you would like to make any adjustments."
            )

        events.append(token_event(content_str, node="chat"))
        events.append(done_event(node="chat_finalize"))

        return {
            "messages": messages,
            "events": events,
        }

    # -------------------------------------------------------------------------
    # Routing Condition
    # -------------------------------------------------------------------------
    def route_after_chat_agent(state: ChatState) -> Literal["tools", "finalize"]:
        messages = list(state.get("messages", []))
        if not messages:
            return "finalize"

        last_msg = messages[-1]
        iteration = state.get("iteration", 0)

        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls and iteration < settings.max_chat_iterations:
            return "tools"

        return "finalize"

    # -------------------------------------------------------------------------
    # Build LangGraph StateGraph
    # -------------------------------------------------------------------------
    builder = StateGraph(cast(Any, ChatState))
    builder.add_node("chat_agent", chat_agent_node)
    builder.add_node("tools", tools_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "chat_agent")
    builder.add_conditional_edges(
        "chat_agent",
        route_after_chat_agent,
        {
            "tools": "tools",
            "finalize": "finalize",
        },
    )
    builder.add_edge("tools", "chat_agent")
    builder.add_edge("finalize", END)

    chk = configure_checkpointer(checkpointer) if checkpointer is not None else None
    return builder.compile(checkpointer=chk)
