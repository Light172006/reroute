"""Chat graph: handles conversational itinerary modifications."""
from __future__ import annotations

import logging
from typing import AsyncIterator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import ChatState, ItineraryDraft, DraftItem
from app.agents.nodes.validator import validator
from app.agents.llm import get_llm, get_structured_llm
from app.agents.tools import search_places, get_weather_forecast, get_travel_time

log = logging.getLogger("reroute.graphs.chat")


SYSTEM_PROMPT_CHAT = """You are a travel assistant. The user wants to modify their itinerary through chat.
Given the current itinerary and user message, determine what changes to make.
Return a structured response with: action (modify/add/remove), target_item_stable_key (if modifying),
new_item (if adding), and explanation."""


SYSTEM_PROMPT_CLARIFY = """You are a travel assistant. The user's request is ambiguous.
Ask a clarifying question to understand what they want to change.
Return a question that will help you make the right modification."""


def build_chat_graph():
    """Build the chat modification graph."""
    llm = get_llm()
    tools = [search_places, get_weather_forecast, get_travel_time]

    graph = StateGraph(ChatState)

    # Add nodes
    graph.add_node("parse_intent", parse_intent(llm, tools))
    graph.add_node("execute_modification", execute_modification(llm, tools))
    graph.add_node("validator", validator)
    graph.add_node("respond", respond)

    # Add edges
    graph.add_edge(START, "parse_intent")
    graph.add_edge("parse_intent", "execute_modification")
    graph.add_edge("execute_modification", "validator")
    graph.add_edge("validator", "respond")
    graph.add_edge("respond", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


async def parse_intent(llm, tools) -> callable:
    """Parse the user's chat message to understand the intent."""
    async def _node(state: ChatState) -> ChatState:
        user_message = state.get("user_message", "")
        current_draft = state.get("current_draft")

        if not user_message:
            return {"intent": {"action": "none"}, "message": "No message to parse"}

        # Simple intent parsing without LLM for mock mode
        if not llm:
            intent = _mock_parse_intent(user_message, current_draft)
            return {"intent": intent, "message": f"Parsed intent: {intent.get('action')}"}

        try:
            # Use LLM to parse intent
            structured_llm = llm.with_structured_output(dict)
            prompt = f"""
Current itinerary: {current_draft}
User message: {user_message}

Parse the user's intent for itinerary modification.
Return: action (modify/add/remove/clarify), target_item_stable_key, new_item_details, explanation
"""
            result = await structured_llm.ainvoke(prompt)
            intent = result
        except Exception:
            intent = _mock_parse_intent(user_message, current_draft)

        return {"intent": intent, "message": f"Intent parsed: {intent.get('action')}"}

    return _node


def _mock_parse_intent(user_message: str, current_draft: dict) -> dict:
    """Simple keyword-based intent parsing for mock mode."""
    msg_lower = user_message.lower()

    if any(word in msg_lower for word in ["add", "include", "put", "insert"]):
        return {"action": "add", "explanation": "User wants to add something"}
    elif any(word in msg_lower for word in ["remove", "delete", "drop", "cancel"]):
        return {"action": "remove", "explanation": "User wants to remove something"}
    elif any(word in msg_lower for word in ["change", "modify", "swap", "replace", "move"]):
        return {"action": "modify", "explanation": "User wants to modify something"}
    elif any(word in msg_lower for word in ["?", "what", "how", "why", "tell me"]):
        return {"action": "clarify", "explanation": "User is asking a question"}
    else:
        return {"action": "modify", "explanation": "Default to modify"}


async def execute_modification(llm, tools) -> callable:
    """Execute the modification on the itinerary."""
    async def _node(state: ChatState) -> ChatState:
        intent = state.get("intent", {})
        current_draft = state.get("current_draft")
        action = intent.get("action", "none")

        if action == "none" or not current_draft:
            return {"updated_draft": current_draft, "message": "No modification needed"}

        items = current_draft.get("items", [])

        if action == "add":
            # Add a new item (simplified mock)
            new_item = intent.get("new_item", {})
            if not new_item:
                new_item = DraftItem(
                    stable_key=f"chat_added_{len(items)}",
                    day_index=1,
                    position=len(items),
                    place_id="new_place",
                    title="Chat Added Item",
                    category="activity",
                    setting="indoor",
                    start_time="10:00",
                    end_time="11:00",
                    est_cost=100,
                    lat=0.0,
                    lng=0.0,
                    is_locked=False,
                    travel_mode="walk",
                    travel_minutes=5,
                )
            items.append(new_item if isinstance(new_item, dict) else new_item)

        elif action == "remove":
            target_key = intent.get("target_item_stable_key")
            if target_key:
                items = [item for item in items if item.get("stable_key") != target_key]

        elif action == "modify":
            target_key = intent.get("target_item_stable_key")
            if target_key:
                for i, item in enumerate(items):
                    if item.get("stable_key") == target_key:
                        # Apply modifications
                        updates = intent.get("updates", {})
                        items[i] = {**item, **updates}
                        break

        updated_draft = {
            "items": items,
            "summary": f"Modified via chat: {action}",
        }

        return {"updated_draft": updated_draft, "message": f"Applied {action} modification"}

    return _node


async def respond(state: ChatState) -> ChatState:
    """Generate a response to the user."""
    intent = state.get("intent", {})
    action = intent.get("action", "none")
    updated_draft = state.get("updated_draft")

    if action == "clarify":
        response = "Could you clarify what you'd like to change? For example: 'Add a museum visit on day 2' or 'Remove the hiking activity'."
    elif action == "add":
        response = "I've added that to your itinerary."
    elif action == "remove":
        response = "I've removed that from your itinerary."
    elif action == "modify":
        response = "I've updated your itinerary."
    else:
        response = "I'm not sure what you'd like me to do. Could you rephrase?"

    return {"response": response, "message": "Response generated"}


async def run_chat_graph(run_id: str, trip_id: str, current_draft: dict, user_message: str) -> AsyncIterator[dict]:
    """Execute the chat graph and yield events."""
    graph = build_chat_graph()

    initial_state: ChatState = {
        "trip_id": trip_id,
        "run_id": run_id,
        "current_draft": current_draft,
        "user_message": user_message,
        "intent": {},
        "updated_draft": None,
        "response": "",
        "message": "",
    }

    config = {"configurable": {"thread_id": run_id}}

    try:
        async for step in graph.astream(initial_state, config=config):
            for node_name, node_output in step.items():
                if node_output:
                    if node_name == "parse_intent":
                        yield {"type": "step", "node": "parse_intent", "message": node_output.get("message", ""), "status": "done"}
                    elif node_name == "execute_modification":
                        yield {"type": "draft", "node": "execute_modification", "message": node_output.get("message", ""), "status": "running", "payload": {"days_ready": []}}
                    elif node_name == "validator":
                        yield {"type": "step", "node": "validator", "message": node_output.get("message", ""), "status": "done"}
                    elif node_name == "respond":
                        response = node_output.get("response", "")
                        yield {"type": "chat_response", "node": "respond", "message": response, "status": "done"}
    except Exception as e:
        log.exception("Chat graph failed")
        yield {"type": "error", "message": str(e), "payload": {"code": "graph_failed", "recoverable": False}}

    yield {"type": "done", "message": "Chat complete", "payload": {"status": "completed"}}