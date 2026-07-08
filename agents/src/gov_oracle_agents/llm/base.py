"""LLM abstraction.

Agents call `complete_json` with a task name, instructions, and payload.
Implementations: OpenAICompatibleClient (any OpenAI-compatible endpoint)
and RuleBasedAnalyst (deterministic heuristics, no network, used when no
API key is configured and in tests).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    name: str = "abstract"

    @abstractmethod
    def complete_json(self, task: str, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON-serializable dict for the given task."""

    @abstractmethod
    def complete_text(self, task: str, instructions: str, payload: dict[str, Any]) -> str:
        """Return prose for the given task."""
