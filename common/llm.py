"""Shared LLM factory for all agents.

Uses OpenRouter as an OpenAI-compatible API, so any provider's model
can be selected via the OPENROUTER_MODEL env var.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client pointed at OpenRouter."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path, override=True)

    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "Missing OPENROUTER_API_KEY. Add a real OpenRouter key to .env "
            "(it should start with sk-or-v1-)."
        )
    if not api_key.startswith("sk-or-v1-"):
        raise RuntimeError(
            "OPENROUTER_API_KEY does not look like an OpenRouter key. "
            "Use a key that starts with sk-or-v1-."
        )

    return ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5"),
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
        max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "300")),
        max_retries=3,
    )
