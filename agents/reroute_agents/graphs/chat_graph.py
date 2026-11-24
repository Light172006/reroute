"""Chat Graph: Delegates to dedicated Chat Agent."""

from __future__ import annotations

from reroute_agents.agents.chat.agent import build_chat_agent as build_chat_graph

__all__ = ["build_chat_graph"]
