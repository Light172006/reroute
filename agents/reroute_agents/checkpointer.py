"""Checkpointer utilities and serializer configuration for LangGraph state persistence."""

from __future__ import annotations

import inspect
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer, _create_msgpack_ext_hook

import reroute_agents.state as agent_state

AGENT_STATE_TYPES = [
    cls
    for _, cls in inspect.getmembers(agent_state, inspect.isclass)
    if cls.__module__ == "reroute_agents.state"
]


def create_default_checkpointer() -> MemorySaver:
    """Create in-memory MemorySaver with all reroute_agents state models registered in msgpack allowlist."""
    serde = JsonPlusSerializer(allowed_msgpack_modules=AGENT_STATE_TYPES)
    return MemorySaver(serde=serde)


def configure_checkpointer(checkpointer: Any | None = None) -> Any:
    """Ensure checkpointer has reroute_agents custom types registered in its msgpack allowlist.

    If checkpointer is None, returns a configured default MemorySaver.
    If checkpointer has JsonPlusSerializer with default allowlist, updates it to include AGENT_STATE_TYPES.
    """
    if checkpointer is None:
        return create_default_checkpointer()

    serde = getattr(checkpointer, "serde", None)
    if isinstance(serde, JsonPlusSerializer):
        current = serde._allowed_msgpack_modules
        if current is True or current is None:
            checkpointer.serde = JsonPlusSerializer(
                pickle_fallback=serde.pickle_fallback,
                allowed_json_modules=serde._allowed_json_modules,
                allowed_msgpack_modules=AGENT_STATE_TYPES,
            )
        elif isinstance(current, set):
            for cls in AGENT_STATE_TYPES:
                current.add((cls.__module__, cls.__name__))
            checkpointer.serde._unpack_ext_hook = _create_msgpack_ext_hook(current)

    return checkpointer
