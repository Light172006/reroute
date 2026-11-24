"""Chat Agent: ReAct assistant interacting with travelers to refine itineraries."""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph

from reroute_agents.state import ChatState
from reroute_agents.tools.registry import for_agent


def build_chat_agent() -> Any:
    """Build and compile the Chat Agent graph using dedicated chat tools."""
    # Ensure this agent only touches chat-registered tools
    tools = for_agent("chat")
    _ = tools

    builder: StateGraph[ChatState] = StateGraph(ChatState)

    async def conversational_react(state: ChatState) -> dict[str, Any]:
        return {}

    builder.add_node("conversational_react", conversational_react)
    builder.set_entry_point("conversational_react")
    builder.set_finish_point("conversational_react")
    return builder.compile()
