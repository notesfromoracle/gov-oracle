"""Deterministic fallback analyst.

Used when no LLM API key is configured (and in tests). Produces sensible,
clearly-labeled heuristic output so the whole pipeline runs offline. Every
consumer of LLM output must tolerate this fallback — that keeps the system
runnable end to end and keeps prompts honest (structured in, structured out).
"""
from __future__ import annotations

from typing import Any

from .base import LLMClient


class RuleBasedAnalyst(LLMClient):
    name = "rule-based"

    def complete_json(self, task: str, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        if task == "classify_document":
            return self._classify_document(payload)
        if task == "answer_civic_question":
            return self._answer_civic_question(payload)
        if task == "extract_events":
            return {"events": []}  # heuristic extraction happens in the agent itself
        return {}

    def complete_text(self, task: str, instructions: str, payload: dict[str, Any]) -> str:
        if task == "executive_summary":
            return self._executive_summary(payload)
        if task == "note_analysis":
            return self._note_analysis(payload)
        return ""

    # --- task handlers -------------------------------------------------

    @staticmethod
    def _classify_document(payload: dict[str, Any]) -> dict[str, Any]:
        text = f"{payload.get('title', '')} {payload.get('text', '')}".lower()
        # more specific categories first: contract-award phrasing beats generic
        # procurement wording, budget wording beats everything downstream of it
        keyword_map = [
            ("contract", ["contract award", "awarded to", "notification of award"]),
            ("budget", ["budget", "allocation", "fiscal year", "adp", "annual development"]),
            ("tender", ["tender", "procurement", "invitation for bid", "e-gp", "rfq", "eoi"]),
            ("audit", ["audit", "comptroller", "objection", "irregularity"]),
            ("law", ["act,", "ordinance", "gazette", "section 1.", "parliament passed"]),
            ("policy", ["policy", "strategy", "action plan", "guideline"]),
            ("statistics", ["statistics", "survey", "census", "bulletin", "indicators"]),
            ("press release", ["press release", "press briefing", "spokesperson"]),
            ("project report", ["progress report", "implementation status", "imed"]),
            ("speech", ["speech", "address by", "remarks by"]),
            ("news article", ["reported", "correspondent", "news desk"]),
        ]
        for doc_type, keywords in keyword_map:
            if any(k in text for k in keywords):
                return {"document_type": doc_type, "confidence": 0.55, "method": "keyword-heuristic"}
        return {"document_type": "unknown", "confidence": 0.3, "method": "keyword-heuristic"}

    @staticmethod
    def _answer_civic_question(payload: dict[str, Any]) -> dict[str, Any]:
        """Deterministic answer synthesis: enumerate the findings, no prose invention."""
        findings = payload.get("findings", [])
        if not findings:
            return {}
        status = payload.get("answerability_status", "failed")
        lines = []
        for i, f in enumerate(findings[:5], 1):
            parts = [f.get("title", "untitled record")]
            if f.get("detail"):
                parts.append(f"({f['detail']})")
            if f.get("amount"):
                currency = f.get("currency") or ""
                parts.append(f"— {f['amount']:,.0f} {currency}".rstrip())
            if f.get("date"):
                parts.append(f"dated {str(f['date'])[:10]}")
            lines.append(f"{i}. " + " ".join(parts))
        if status == "answered":
            preamble = f"Based on {len(findings)} public records found:"
        else:
            missing = "; ".join(payload.get("missing_data", [])[:3])
            preamble = (
                f"Only partial information is available ({len(findings)} related public "
                f"records found; missing: {missing}). The records found are:"
            )
        confidences = [f.get("confidence", 0.4) for f in findings]
        confidence = min(0.6, sum(confidences) / len(confidences))
        return {"answer": preamble + "\n" + "\n".join(lines), "confidence": round(confidence, 2)}

    @staticmethod
    def _executive_summary(payload: dict[str, Any]) -> str:
        gov = payload.get("government", "the government")
        coverage = payload.get("source_coverage", {})
        scores = payload.get("scores", {})
        checked = coverage.get("sources_checked", 0)
        ok = coverage.get("sources_successful", 0)
        new_docs = coverage.get("new_documents_found", 0)
        failed_count = payload.get("failed_question_count", 0)
        answered = payload.get("answered_question_count", 0)
        overall = scores.get("overall", "n/a")
        parts = [
            f"This report evaluates how well {gov} can be understood from its public information.",
            f"The system checked {checked} known public sources; {ok} responded and "
            f"{new_docs} new or changed documents were captured.",
            f"Of the civic transparency questions attempted, {answered} could be answered from "
            f"public records and {failed_count} could not, usually because records were missing, "
            f"not machine-readable, or not linked to each other.",
            f"The overall information-navigability score for this run is {overall}/100.",
            "Scores reflect the availability and traceability of public information only; "
            "they do not assess policy or ideology.",
        ]
        return " ".join(parts)

    @staticmethod
    def _note_analysis(payload: dict[str, Any]) -> str:
        what = payload.get("what_happened", "A change was detected in monitored public sources.")
        why = payload.get("why_it_matters", "It affects how public activity can be traced.")
        missing = payload.get("what_is_missing")
        analysis = f"{what} {why}"
        if missing:
            analysis += (
                f" However, the public record is incomplete: {missing} "
                "This limits independent verification and is itself a transparency finding."
            )
        return analysis
