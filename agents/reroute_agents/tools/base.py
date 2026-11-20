"""Tool layer base decorators: timeout, retry, error normalization, and caching."""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from reroute_agents.config import settings

logger = logging.getLogger(__name__)

R = TypeVar("R", bound=dict[str, Any])


def safe_tool(
    timeout_sec: float = 10.0,
    max_retries: int = 2,
) -> Callable[..., Callable[..., Coroutine[Any, Any, dict[str, Any]]]]:
    """Decorator ensuring tools never raise exceptions into the LangGraph state.

    Catches timeouts, network errors, and exceptions, normalizing them to:
    {"ok": False, "error": "...", "details": {...}}
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    ) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_sec)
                except TimeoutError as te:
                    last_err = te
                    logger.warning(
                        "Tool %s timed out after %ss (attempt %d/%d)",
                        func.__name__,
                        timeout_sec,
                        attempt + 1,
                        max_retries,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                except Exception as ex:
                    last_err = ex
                    logger.warning(
                        "Tool %s failed: %s (attempt %d/%d)",
                        func.__name__,
                        ex,
                        attempt + 1,
                        max_retries,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))

            err_msg = str(last_err) if last_err else "Tool execution failed"
            return {
                "ok": False,
                "error": err_msg,
                "tool": func.__name__,
            }

        return wrapper

    return decorator


def is_mock_tools() -> bool:
    """Return whether tools should return deterministic mock results."""
    return settings.mock_tools
