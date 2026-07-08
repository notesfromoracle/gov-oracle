from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import Settings, get_settings
from .base import LLMClient

SYSTEM_PROMPT = """You are a public-information auditor. You evaluate whether a government
can be understood from its publicly available information. You are calm, evidence-backed,
non-partisan, precise, and skeptical but fair. You never accuse individuals or organizations
without strong evidence. You separate fact from inference and always cite the documents you
were given. Missing data is itself a finding: describe what is missing rather than speculating."""


class OpenAICompatibleClient(LLMClient):
    name = "openai-compatible"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _chat(self, messages: list[dict[str, str]], json_mode: bool) -> str:
        body: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": 0.2,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        response = httpx.post(
            f"{self.settings.openai_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json=body,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def complete_json(self, task: str, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        content = self._chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Task: {task}\n\n{instructions}\n\n"
                        f"Input data (JSON):\n{json.dumps(payload, default=str)}\n\n"
                        "Respond with a single JSON object only."
                    ),
                },
            ],
            json_mode=True,
        )
        return json.loads(content)

    def complete_text(self, task: str, instructions: str, payload: dict[str, Any]) -> str:
        return self._chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Task: {task}\n\n{instructions}\n\n"
                        f"Input data (JSON):\n{json.dumps(payload, default=str)}"
                    ),
                },
            ],
            json_mode=False,
        )
