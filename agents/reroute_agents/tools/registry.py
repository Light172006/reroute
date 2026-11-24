"""Tool Registry: Scoped tool registration and permission enforcement for agents."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

VALID_AGENTS = frozenset({"web", "plan", "replan", "chat"})


class ToolAccessViolationError(PermissionError):
    """Raised when an agent attempts to access or execute an unauthorized tool."""


class ToolRegistry:
    """Central registry enforcing agent-level tool isolation.

    Each tool must be explicitly registered to an agent scope ('web', 'plan',
    'replan', or 'chat'). Attempting to retrieve or invoke tools outside an
    agent's registered scope fails loudly with ToolAccessViolationError.
    """

    def __init__(self) -> None:
        self._tools_by_agent: dict[str, dict[str, BaseTool]] = {
            agent: {} for agent in VALID_AGENTS
        }

    def register(self, agent_name: str, tools: BaseTool | Sequence[BaseTool]) -> None:
        """Register one or more tools under a specific agent scope."""
        agent_key = agent_name.lower().strip()
        if agent_key not in VALID_AGENTS:
            raise ValueError(
                f"Unknown agent '{agent_name}'. Must be one of: {sorted(VALID_AGENTS)}"
            )

        tool_sequence = [tools] if isinstance(tools, BaseTool) else tools
        for tool_instance in tool_sequence:
            name = getattr(tool_instance, "name", str(tool_instance))
            self._tools_by_agent[agent_key][name] = tool_instance
            logger.debug("Registered tool '%s' for agent '%s'", name, agent_key)

    def for_agent(self, agent_name: str) -> list[BaseTool]:
        """Return only the tools authorized for the specified agent.

        Fails loud if an unknown agent name is supplied.
        """
        agent_key = agent_name.lower().strip()
        if agent_key not in VALID_AGENTS:
            raise ValueError(
                f"Unknown agent '{agent_name}'. Authorized agents: {sorted(VALID_AGENTS)}"
            )
        return list(self._tools_by_agent[agent_key].values())

    def validate_tool_access(self, agent_name: str, tool_name: str) -> BaseTool:
        """Validate that the given agent is permitted to execute the named tool.

        Returns the BaseTool instance if authorized; raises ToolAccessViolationError
        if unauthorized.
        """
        agent_key = agent_name.lower().strip()
        if agent_key not in VALID_AGENTS:
            raise ToolAccessViolationError(
                f"Unknown agent '{agent_name}'. Authorized agents: {sorted(VALID_AGENTS)}"
            )

        agent_tools = self._tools_by_agent[agent_key]
        if tool_name not in agent_tools:
            allowed = sorted(agent_tools.keys())
            raise ToolAccessViolationError(
                f"Tool '{tool_name}' is not registered to agent '{agent_key}'. "
                f"Allowed tools for '{agent_key}': {allowed}"
            )
        return agent_tools[tool_name]

    def clear(self) -> None:
        """Clear all registered tools (primarily for testing isolation)."""
        for agent in self._tools_by_agent:
            self._tools_by_agent[agent].clear()


# Global registry singleton
registry = ToolRegistry()


def for_agent(name: str) -> list[BaseTool]:
    """Retrieve registered tools for the given agent name."""
    return registry.for_agent(name)


def validate_tool_access(agent_name: str, tool_name: str) -> BaseTool:
    """Validate tool authorization for an agent."""
    return registry.validate_tool_access(agent_name, tool_name)
