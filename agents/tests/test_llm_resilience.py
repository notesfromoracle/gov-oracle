"""LLM hardening: per-call fallback and output normalization."""
from __future__ import annotations

import pytest

from gov_oracle_agents.agents.document_extraction import normalize_confidence, normalize_doc_type
from gov_oracle_agents.llm import LLMClient, ResilientLLMClient


class FlakyClient(LLMClient):
    name = "flaky"

    def __init__(self):
        self.calls = 0

    def complete_json(self, task, instructions, payload):
        self.calls += 1
        if self.calls % 2 == 1:
            raise RuntimeError("rate limited")
        return {"document_type": "Budget Document", "confidence": "0.9"}

    def complete_text(self, task, instructions, payload):
        raise RuntimeError("api down")


def test_resilient_client_falls_back_per_call():
    client = ResilientLLMClient(FlakyClient())
    # first call fails -> rule-based fallback answers
    result = client.complete_json("classify_document", "", {"title": "Annual budget", "text": ""})
    assert result["document_type"] == "budget"
    assert client.fallback_calls == 1
    # second call succeeds on the primary
    result = client.complete_json("classify_document", "", {"title": "x", "text": ""})
    assert result["document_type"] == "Budget Document"
    assert client.primary_calls == 1
    # text path falls back to deterministic prose
    text = client.complete_text("executive_summary", "", {"government": "X", "scores": {}})
    assert "X" in text
    assert client.fallback_calls == 2


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("budget", "budget"),
        ("Budget", "budget"),
        ("  BUDGET DOCUMENT ", "budget"),
        ("audit report", "audit"),
        ("procurement notice", "tender"),
        ("fiscal miscellany", "unknown"),
        (None, "unknown"),
        (42, "unknown"),
    ],
)
def test_normalize_doc_type(raw, expected):
    assert normalize_doc_type(raw) == expected


def test_rule_based_answer_synthesis():
    from gov_oracle_agents.llm import RuleBasedAnalyst

    analyst = RuleBasedAnalyst()
    findings = [
        {"title": "Contract award: hospital equipment", "detail": "Ministry of Health",
         "amount": 400000000, "currency": "BDT", "date": "2026-07-01", "confidence": 0.5},
        {"title": "Tender notice: road works", "confidence": 0.4},
    ]
    answered = analyst.complete_json(
        "answer_civic_question", "",
        {"question": "q", "answerability_status": "answered", "findings": findings, "missing_data": []},
    )
    assert "hospital equipment" in answered["answer"]
    assert "400,000,000 BDT" in answered["answer"]
    assert 0 < answered["confidence"] <= 0.6

    partial = analyst.complete_json(
        "answer_civic_question", "",
        {"question": "q", "answerability_status": "partial", "findings": findings,
         "missing_data": ["payment records"]},
    )
    assert "partial" in partial["answer"].lower()
    assert "payment records" in partial["answer"]

    # no findings -> no fabricated answer
    assert analyst.complete_json(
        "answer_civic_question", "",
        {"question": "q", "answerability_status": "failed", "findings": [], "missing_data": ["x"]},
    ) == {}


def test_normalize_confidence():
    assert normalize_confidence("0.9") == 0.9
    assert normalize_confidence(1.7) == 1.0
    assert normalize_confidence(-1) == 0.0
    assert normalize_confidence("high") == 0.3
    assert normalize_confidence(None) == 0.3
