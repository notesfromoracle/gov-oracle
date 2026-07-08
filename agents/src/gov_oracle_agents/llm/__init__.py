from __future__ import annotations

import logging
from typing import Any

from ..config import Settings, get_settings
from .base import LLMClient
from .openai_client import OpenAICompatibleClient
from .rule_based import RuleBasedAnalyst

logger = logging.getLogger(__name__)


class ResilientLLMClient(LLMClient):
    """Per-call fallback wrapper.

    A transient API failure (rate limit, network blip, malformed JSON) must
    degrade one document's analysis, never kill a multi-country study run.
    Fallback counts are tracked so runs can report how much of the analysis
    actually used the primary model.
    """

    def __init__(self, primary: LLMClient, fallback: LLMClient | None = None):
        self.primary = primary
        self.fallback = fallback or RuleBasedAnalyst()
        self.name = primary.name
        self.fallback_calls = 0
        self.primary_calls = 0

    def complete_json(self, task: str, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.primary.complete_json(task, instructions, payload)
            self.primary_calls += 1
            return result
        except Exception as exc:  # noqa: BLE001 — any API failure falls back
            self.fallback_calls += 1
            logger.warning("LLM call failed for task %s (%s); using rule-based fallback", task, exc)
            return self.fallback.complete_json(task, instructions, payload)

    def complete_text(self, task: str, instructions: str, payload: dict[str, Any]) -> str:
        try:
            result = self.primary.complete_text(task, instructions, payload)
            self.primary_calls += 1
            return result
        except Exception as exc:  # noqa: BLE001
            self.fallback_calls += 1
            logger.warning("LLM call failed for task %s (%s); using rule-based fallback", task, exc)
            return self.fallback.complete_text(task, instructions, payload)


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.openai_api_key:
        return ResilientLLMClient(OpenAICompatibleClient(settings))
    return RuleBasedAnalyst()


__all__ = [
    "LLMClient",
    "OpenAICompatibleClient",
    "ResilientLLMClient",
    "RuleBasedAnalyst",
    "get_llm_client",
]
