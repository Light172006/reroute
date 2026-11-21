"""Chat Graph: ReAct-style conversational assistant with bounded multi-turn tool execution."""

from __future__ import annotations

import json
import logging
from datetime import time
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

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
from reroute_agents.tools.places import create_places_tools
from reroute_agents.tools.routing import create_routing_tool

logger = logging.getLogger(__name__)


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
    """Build and compile conversational chat agent graph with bounded ReAct tool loop."""
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

    # Bind tools dictionary
    tools_list = [get_itinerary, modify_item, search_places, estimate_route]
    tools_map = {t.name: t for t in tools_list}

    # -------------------------------------------------------------------------
    # Node 1: Chat Agent (LLM Reasoning & Tool Calling)
    # -------------------------------------------------------------------------
    async def chat_agent_node(state: ChatState) -> dict[str, Any]:
        trip_id = state["trip_id"]
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
            resp_text = (
                "I specialize strictly in managing your travel itinerary and logistics "
                "for this trip. How can I help with your plan?"
            )
            return {
                "messages": messages + [AIMessage(content=resp_text)],
                "iteration": iteration + 1,
            }

        llm = llm_override or get_llm("small")

        if isinstance(llm, FakeLLM):
            # Check for canned tool calls in FakeLLM
            canned_tool_calls = llm.canned_responses.get("tool_calls")
            if canned_tool_calls and iteration == 0:
                ai_msg = AIMessage(
                    content="",
                    tool_calls=canned_tool_calls,
                )
                return {
                    "messages": messages + [ai_msg],
                    "iteration": iteration + 1,
                }

            reply_text = (
                f"I can certainly help you with your trip to {trip_id}. "
                "Let me know if you would like to adjust any stops."
            )
            if "change" in last_user_msg.lower() or "relax" in last_user_msg.lower():
                reply_text = (
                    "I have drafted a proposal to adjust your schedule. "
                    "Please review and approve the changes in the proposal banner."
                )
            ai_msg = AIMessage(content=reply_text)
            return {
                "messages": messages + [ai_msg],
                "iteration": iteration + 1,
            }

        # Real / Structured LLM invocation
        try:
            model = (
                llm.create_model_instance(llm.chain_specs[0])
                if hasattr(llm, "create_model_instance")
                else llm
            )
            conv_messages: list[Any] = [SystemMessage(content=system_prompt)]
            for m in messages:
                if isinstance(m, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
                    conv_messages.append(m)
                elif isinstance(m, dict):
                    role = m.get("role")
                    content = m.get("content", "")
                    if role == "user":
                        conv_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        conv_messages.append(AIMessage(content=content))

            model_with_tools = cast(Any, model).bind_tools(tools_list)
            ai_msg = await model_with_tools.ainvoke(conv_messages)

            return {
                "messages": messages + [ai_msg],
                "iteration": iteration + 1,
            }
        except Exception as exc:
            logger.warning("Chat model invocation failed, falling back: %s", exc)
            fallback_text = (
                f"I am watching your trip to {trip_id}. How may I help you adjust it today?"
            )
            return {
                "messages": messages + [AIMessage(content=fallback_text)],
                "iteration": iteration + 1,
            }

    # -------------------------------------------------------------------------
    # Node 2: Tools Execution Node (ReAct execution of pending tool calls)
    # -------------------------------------------------------------------------
    async def tools_node(state: ChatState) -> dict[str, Any]:
        trip_id = state["trip_id"]
        run_id = state.get("run_id")
        messages = list(state.get("messages", []))
        last_msg = messages[-1] if messages else None

        tool_calls = getattr(last_msg, "tool_calls", [])
        tool_messages: list[ToolMessage] = []
        events = []
        proposal_created: ReplanProposal | None = None

        for call in tool_calls:
            tool_name = call.get("name", "")
            tool_args = call.get("args", {})
            call_id = call.get("id", str(uuid4()))

            events.append(tool_call_event(tool=tool_name, args=tool_args, node="chat_tools"))

            # Handle modify_item specifically to build proposal and preserve HITL invariant
            if tool_name == "modify_item":
                try:
                    t_uuid = UUID(trip_id)
                    curr = await repos.itineraries.get_current_version(t_uuid)
                    if curr:
                        items = await repos.itineraries.get_version_items(curr["id"])
                        stable_key = tool_args.get("item_stable_key", "")
                        reason = tool_args.get("reason", "User requested change")
                        target_idx = next(
                            (i for i, it in enumerate(items) if str(it.stable_key) == stable_key),
                            None,
                        )

                        if target_idx is not None:
                            target_it = items[target_idx]
                            updates: dict[str, Any] = {}
                            if tool_args.get("new_title"):
                                updates["title"] = tool_args["new_title"]
                            if tool_args.get("start_time"):
                                try:
                                    sh, sm = map(int, tool_args["start_time"].split(":"))
                                    updates["start_time"] = time(sh, sm)
                                except (ValueError, TypeError, IndexError) as p_err:
                                    logger.debug("Could not parse start_time: %s", p_err)
                            if tool_args.get("end_time"):
                                try:
                                    eh, em = map(int, tool_args["end_time"].split(":"))
                                    updates["end_time"] = time(eh, em)
                                except (ValueError, TypeError, IndexError) as p_err:
                                    logger.debug("Could not parse end_time: %s", p_err)

                            modified_it = target_it.model_copy(update=updates)
                            proposed_items = list(items)
                            proposed_items[target_idx] = modified_it

                            cost_delta = modified_it.est_cost - target_it.est_cost
                            diff = [
                                DiffItem(
                                    stable_key=target_it.stable_key,
                                    op="replace",
                                    day=target_it.day_index,
                                    before=target_it.model_dump(mode="json"),
                                    after=modified_it.model_dump(mode="json"),
                                    why=reason,
                                )
                            ]

                            prop_id = uuid4()
                            run_uuid = UUID(run_id) if run_id else uuid4()
                            proposal = ReplanProposal(
                                id=prop_id,
                                trip_id=t_uuid,
                                run_id=run_uuid,
                                base_version_id=curr["id"],
                                proposed_items=proposed_items,
                                diff=diff,
                                cost_delta=cost_delta,
                                reason=f"User requested modification: {reason}",
                                explanation=f"Adjusted {target_it.title} in response to concierge chat request.",
                                status="pending",
                            )
                            await repos.proposals.save_proposal(proposal)
                            proposal_created = proposal
                            events.append(proposal_event(proposal_id=proposal.id, node="chat_tools"))

                            res = {
                                "ok": True,
                                "action": "proposal_created",
                                "proposal_id": str(prop_id),
                                "message": (
                                    f"Created pending proposal to modify '{target_it.title}'. "
                                    "Changes will only take effect once approved."
                                ),
                            }
                        else:
                            res = {
                                "ok": False,
                                "error": f"Item with stable_key {stable_key} not found",
                            }
                    else:
                        res = {
                            "ok": False,
                            "error": f"No active itinerary version found for trip {trip_id}",
                        }
                except Exception as exc:
                    logger.warning("Error creating modify_item proposal: %s", exc)
                    res = {"ok": False, "error": str(exc)}

            elif tool_name in tools_map:
                tool_fn = tools_map[tool_name]
                try:
                    if hasattr(tool_fn, "ainvoke"):
                        res = await tool_fn.ainvoke(tool_args)
                    else:
                        res = tool_fn(**tool_args)
                except Exception as exc:
                    err_msg = f"Tool execution failed for '{tool_name}': {exc}"
                    logger.warning(err_msg)
                    events.append(
                        error_event(
                            code="tool_error",
                            message=err_msg,
                            recoverable=True,
                            node="chat_tools",
                        )
                    )
                    res = {"ok": False, "error": str(exc)}
            else:
                err_msg = f"Unknown tool: '{tool_name}'"
                events.append(
                    error_event(
                        code="tool_not_found",
                        message=err_msg,
                        recoverable=True,
                        node="chat_tools",
                    )
                )
                res = {"ok": False, "error": err_msg}

            ok = bool(res.get("ok", True)) if isinstance(res, dict) else True
            summary = (
                str(res.get("message", f"Tool {tool_name} completed"))
                if isinstance(res, dict)
                else f"Tool {tool_name} completed"
            )
            events.append(
                tool_result_event(
                    tool=tool_name,
                    ok=ok,
                    summary=summary,
                    data=res,
                    node="chat_tools",
                )
            )

            tool_messages.append(
                ToolMessage(
                    content=json.dumps(res, default=str),
                    tool_call_id=call_id,
                    name=tool_name,
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
    # Node 3: Finalize Node (Token Streaming & Done Event)
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

        events.append(token_event(content_str))
        events.append(done_event(status="completed", node="chat"))

        return {
            "messages": messages,
            "events": events,
        }

    # -------------------------------------------------------------------------
    # Routing Logic
    # -------------------------------------------------------------------------
    def route_after_chat_agent(state: ChatState) -> Literal["tools", "finalize"]:
        messages = state.get("messages", [])
        if not messages:
            return "finalize"
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", None)
        iteration = state.get("iteration", 0)

        if tool_calls and iteration < settings.max_chat_iterations:
            return "tools"
        return "finalize"

    # -------------------------------------------------------------------------
    # Build LangGraph StateGraph
    # -------------------------------------------------------------------------
    builder = StateGraph(ChatState)
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
