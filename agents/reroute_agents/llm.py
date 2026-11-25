"""LLM Gateway: Multi-tier provider chaining, fallback resilience, and FakeLLM."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from reroute_agents.config import settings
from reroute_agents.events import llm_call_event
from reroute_agents.state import AgentEvent

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class TokenBucket:
    """Async token bucket rate limiter to prevent hammering free tier limits."""

    def __init__(self, rate_rps: float = 2.0, capacity: int = 10) -> None:
        self.rate = rate_rps
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.last_check = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_check
            self.last_check = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


_global_rate_limiter = TokenBucket(
    rate_rps=settings.llm_rate_limit_rps,
    capacity=settings.llm_token_burst,
)


class FakeStructuredRunner(Generic[T]):
    """Mock structured output runner that returns scripted Pydantic models."""

    def __init__(self, schema: type[T], handler: Callable[[Any], T]) -> None:
        self.schema = schema
        self.handler = handler

    async def ainvoke(self, messages: Any, config: dict[str, Any] | None = None) -> T:
        return self.handler(messages)


class FakeLLM:
    """Scripted deterministic LLM for graph and unit tests (zero real API calls)."""

    def __init__(
        self,
        name: str = "fake:mock-model",
        canned_responses: dict[str, Any] | None = None,
        fail_times: int = 0,
        fail_exception: Exception | None = None,
    ) -> None:
        self.name = name
        self.canned_responses = canned_responses or {}
        self.fail_times = fail_times
        self.fail_exception = fail_exception or RuntimeError("Simulated LLM rate limit or failure")
        self.calls: list[dict[str, Any]] = []

    def with_structured_output(self, schema: type[T]) -> FakeStructuredRunner[T]:
        def _handler(messages: Any) -> T:
            self.calls.append({"messages": messages, "schema": schema})
            if self.fail_times > 0:
                self.fail_times -= 1
                raise self.fail_exception

            # Check if schema class name exists in canned_responses
            key = schema.__name__
            if key in self.canned_responses:
                val = self.canned_responses[key]
                if isinstance(val, schema):
                    return val
                if isinstance(val, dict):
                    return schema.model_validate(val)
                if callable(val):
                    res = val(messages)
                    if isinstance(res, schema):
                        return res
                    return schema.model_validate(res)

            # Check generic default
            if "default" in self.canned_responses:
                def_val = self.canned_responses["default"]
                if isinstance(def_val, schema):
                    return def_val
                if isinstance(def_val, dict):
                    return schema.model_validate(def_val)

            raise ValueError(f"FakeLLM has no canned response for schema {key}")

        return FakeStructuredRunner(schema, _handler)

    async def ainvoke(self, messages: Any, config: dict[str, Any] | None = None) -> Any:
        self.calls.append({"messages": messages, "schema": None})
        if self.fail_times > 0:
            self.fail_times -= 1
            raise self.fail_exception

        text = self.canned_responses.get("text", "Mock chat response from FakeLLM.")
        from langchain_core.messages import AIMessage

        return AIMessage(content=text)


def create_model_instance(spec: str) -> Any:
    """Instantiate a LangChain chat model based on provider:model spec."""
    if ":" not in spec:
        provider = "gemini"
        model_name = spec
    else:
        provider, model_name = spec.split(":", 1)

    provider = provider.lower().strip()
    model_name = model_name.strip()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = settings.google_api_key
        if not key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=key,
            temperature=0.2,
            timeout=15.0,
            max_retries=0,
            max_output_tokens=4096,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        key = settings.groq_api_key
        if not key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        return cast(Any, ChatGroq)(
            model_name=model_name,
            groq_api_key=key,
            temperature=0.2,
            request_timeout=20.0,
            max_retries=0,
            max_tokens=4096,
        )

    if provider == "ollama":
        from langchain_core.messages import AIMessage

        # Lightweight fallback client for local Ollama without heavy extra dependencies
        class OllamaClient:
            def __init__(self, model: str, base_url: str) -> None:
                self.model = model
                self.base_url = base_url

            async def ainvoke(self, messages: Any, **kwargs: Any) -> AIMessage:
                import httpx

                prompt = str(messages)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json={"model": self.model, "prompt": prompt, "stream": False},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return AIMessage(content=data.get("response", ""))

        return OllamaClient(model_name, settings.ollama_base_url)

    raise ValueError(f"Unknown LLM provider '{provider}' in spec '{spec}'")


class ResilientLLMChain:
    """Executes structured and text calls across an ordered fallback chain."""

    def __init__(self, chain_specs: list[str], tier: str = "strong") -> None:
        self.chain_specs = chain_specs
        self.tier = tier

    async def ainvoke_structured(
        self,
        schema: type[T],
        prompt: Any,
        events: list[AgentEvent] | None = None,
        node_name: str | None = None,
    ) -> T:
        """Attempt structured generation across the fallback chain with tenacity backoff."""
        if settings.mock_llm:
            raise RuntimeError("MOCK_LLM is enabled but no FakeLLM was injected")

        last_error: Exception | None = None
        for i, spec in enumerate(self.chain_specs):
            is_fallback = i > 0
            try:
                model = create_model_instance(spec)
                await _global_rate_limiter.acquire()
                start_t = time.monotonic()

                @retry(
                    reraise=True,
                    stop=stop_after_attempt(1),
                    wait=wait_exponential_jitter(initial=1.0, max=3.0),
                    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
                )
                async def _call(current_model: Any = model) -> T:
                    runner = current_model.with_structured_output(schema)
                    return await asyncio.wait_for(runner.ainvoke(prompt), timeout=20.0)  # type: ignore[no-any-return]

                result = await _call()
                latency_ms = int((time.monotonic() - start_t) * 1000)

                if events is not None:
                    events.append(
                        llm_call_event(
                            model=spec,
                            latency_ms=latency_ms,
                            fallback=is_fallback,
                            node=node_name,
                        )
                    )
                return result

            except Exception as e:
                logger.warning("LLM model %s failed: %s; trying next in chain", spec, e)
                last_error = e
                continue

        raise RuntimeError(
            f"All models in chain {self.chain_specs} failed. Last error: {last_error}"
        )


def get_llm(tier: str = "strong") -> ResilientLLMChain:
    """Return configured model fallback chain for the specified tier."""
    if tier == "strong":
        return ResilientLLMChain(settings.llm_strong_chain, tier=tier)
    if tier == "small":
        return ResilientLLMChain(settings.llm_small_chain, tier=tier)
    if tier == "local":
        return ResilientLLMChain(settings.llm_local_chain, tier=tier)
    raise ValueError(f"Unknown LLM tier: {tier}")
