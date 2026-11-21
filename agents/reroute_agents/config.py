"""Configuration management for reroute_agents."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    # Model fallback chains
    llm_strong_chain: list[str] = field(
        default_factory=lambda: [
            m.strip()
            for m in os.getenv(
                "LLM_STRONG_CHAIN",
                "gemini:gemini-2.5-flash,groq:llama-3.3-70b-versatile",
            ).split(",")
            if m.strip()
        ]
    )
    llm_small_chain: list[str] = field(
        default_factory=lambda: [
            m.strip()
            for m in os.getenv(
                "LLM_SMALL_CHAIN",
                "groq:llama-3.1-8b-instant,gemini:gemini-2.5-flash",
            ).split(",")
            if m.strip()
        ]
    )
    llm_local_chain: list[str] = field(
        default_factory=lambda: [
            m.strip()
            for m in os.getenv(
                "LLM_LOCAL_CHAIN",
                "ollama:qwen2.5:7b,ollama:llama3.2:3b",
            ).split(",")
            if m.strip()
        ]
    )

    # API Keys
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    ors_api_key: str | None = os.getenv("ORS_API_KEY")

    # Local Ollama config
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Flags
    mock_tools: bool = os.getenv("MOCK_TOOLS", "false").lower() in ("true", "1", "yes")
    mock_llm: bool = os.getenv("MOCK_LLM", "false").lower() in ("true", "1", "yes")

    # Rate limiting
    llm_rate_limit_rps: float = float(os.getenv("LLM_RATE_LIMIT_RPS", "2.0"))
    llm_token_burst: int = int(os.getenv("LLM_TOKEN_BURST", "10"))

    # Regional altitude and travel constraints
    altitude_acclimatization_threshold_m: int = int(
        os.getenv("ALTITUDE_ACCLIMATIZATION_THRESHOLD_M", "1000")
    )
    altitude_high_risk_threshold_m: int = int(os.getenv("ALTITUDE_HIGH_RISK_THRESHOLD_M", "3000"))
    max_drive_hours_per_day: int = int(os.getenv("MAX_DRIVE_HOURS_PER_DAY", "7"))
    allow_night_driving: bool = os.getenv("ALLOW_NIGHT_DRIVING", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Pace limits (in minutes per day)
    pace_limits_minutes: dict[str, int] = field(
        default_factory=lambda: {
            "relaxed": 480,  # 8 hours
            "balanced": 600,  # 10 hours
            "packed": 720,  # 12 hours
        }
    )

    # Disruption detection thresholds
    precip_prob_threshold: float = 0.60
    delay_threshold_minutes: int = 30
    budget_overrun_pct_threshold: float = 0.10

    # Graph loop caps
    max_plan_iterations: int = 3
    max_replan_iterations: int = 2
    max_chat_iterations: int = 5


settings = Settings()
