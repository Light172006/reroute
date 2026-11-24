# Legacy Agent Prototype (Deprecated)

This directory (`reroute-backend/app/agents/`) contains an early proof-of-concept prototype of the LangGraph agent definitions using TypedDict data structures.

## Production Implementation Notice

The canonical, production-grade agent implementation lives in:
- `agents/reroute_agents/` (primary repository package)
- `reroute-backend/reroute_agents/` (synchronized copy for self-contained backend builds)

The running backend services (`app.services.agent_gateway`, `app.api.routers.agent`) exclusively use `reroute_agents`.

Do not add new code to `app/agents/`.
