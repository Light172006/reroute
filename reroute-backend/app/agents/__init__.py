"""DEPRECATED LEGACY PROTOTYPE.

DO NOT USE.
This module contains early prototype agent code that was superseded by the production
multi-agent system in `reroute_agents`.

The production backend exclusively imports from `reroute_agents.gateway` and
`reroute_agents.repositories`.
"""
import warnings

warnings.warn(
    "app.agents is deprecated and will be removed. Use reroute_agents instead.",
    DeprecationWarning,
    stacklevel=2,
)
