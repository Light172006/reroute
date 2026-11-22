"""LLM gateway: provides model instances with fallback chains.

This module centralizes all LLM configuration so the agent graphs
can use a single interface with automatic fallback.
"""
from __future__ import annotations

import logging
from typing import Optional
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from app.core.config import settings

log = logging.getLogger("reroute.llm")


class MockChatModel(BaseChatModel):
    """Mock LLM for demo/testing mode.

    Returns deterministic responses based on the prompt content.
    Useful for development without API keys.
    """

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(
        self,
        messages: list,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs,
    ) -> ChatResult:
        # Return a canned response based on the last user message
        last_msg = messages[-1].content if messages else ""
        response = self._mock_response(last_msg)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response))])

    async def _agenerate(
        self,
        messages: list,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs,
    ) -> ChatResult:
        last_msg = messages[-1].content if messages else ""
        response = self._mock_response(last_msg)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response))])

    def _mock_response(self, prompt: str) -> str:
        """Generate a mock structured response."""
        # The actual structured output parsing happens in the caller
        # via with_structured_output(), so we return a valid JSON
        if "TripSpec" in prompt or "intake" in prompt.lower():
            return '{"destination": "Darjeeling", "start_date": "2026-12-12", "end_date": "2026-12-14", "group_size": 3, "budget_total": 15000, "currency": "INR", "pace": "balanced", "vibe_tags": ["food", "nature"], "notes": "Vegetarian friendly"}'
        elif "PlannerOutput" in prompt or "planner" in prompt.lower():
            return '{"items": [], "summary": "Mock itinerary"}'
        else:
            return '{"response": "Mock response"}'

    @property
    def _identifying_params(self) -> dict:
        return {"model": "mock"}


def _try_google() -> Optional[BaseChatModel]:
    """Try to create a Google Gemini model."""
    if not settings.GOOGLE_API_KEY:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=True,
        )
    except Exception as e:
        log.warning("Google model unavailable: %s", e)
        return None


def _try_groq() -> Optional[BaseChatModel]:
    """Try to create a Groq model."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.1-70b-versatile",
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.1,
        )
    except Exception as e:
        log.warning("Groq model unavailable: %s", e)
        return None


def _try_openrouter() -> Optional[BaseChatModel]:
    """Try to create an OpenRouter model."""
    if not settings.OPENROUTER_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="anthropic/claude-3.5-sonnet",
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
        )
    except Exception as e:
        log.warning("OpenRouter model unavailable: %s", e)
        return None


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Get the best available LLM with fallback chain.

    Priority: Mock (if MOCK_TOOLS=true) -> Google -> Groq -> OpenRouter -> Mock
    """
    if settings.MOCK_TOOLS:
        log.info("MOCK_TOOLS is true; using MockChatModel")
        return MockChatModel()

    # Try each provider in order
    for provider_fn in (_try_google, _try_groq, _try_openrouter):
        model = provider_fn()
        if model:
            log.info("Using LLM: %s", model._llm_type)
            return model

    # Fall back to mock
    log.info("No API keys configured; using MockChatModel")
    return MockChatModel()


def get_structured_llm(output_model):
    """Get an LLM configured for structured output with the given Pydantic model."""
    llm = get_llm()
    return llm.with_structured_output(output_model)