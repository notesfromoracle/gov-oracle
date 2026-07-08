"use client";

import { useState } from "react";
import type { ScoreDimension, TransparencyScores } from "@/lib/types";
import { scoreColor } from "./ScoreBadge";

const DIMENSIONS: { key: ScoreDimension; label: string; question: string }[] = [
  { key: "documentation", label: "Documentation", question: "How much expected public information is actually published?" },
  { key: "timeliness", label: "Timeliness", question: "How quickly is information published after relevant events?" },
  { key: "accessibility", label: "Accessibility", question: "Can machines read and process the information?" },
  { key: "completeness", label: "Completeness", question: "Is spending linked to projects, contracts, and outcomes?" },
  { key: "traceability", label: "Traceability", question: "Can public money be followed through the system?" },
  { key: "explainability", label: "Explainability", question: "Can the AI explain where money went and why decisions were made?" },
];

export function ScoreGrid({
  scores,
  explanations,
}: {
  scores: TransparencyScores;
  explanations?: Record<ScoreDimension, string>;
}) {
  const [expanded, setExpanded] = useState<ScoreDimension | null>(null);

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
      {DIMENSIONS.map(({ key, label, question }) => (
        <button
          key={key}
          type="button"
          onClick={() => setExpanded(expanded === key ? null : key)}
          className="rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-slate-300"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-600">{label}</span>
            <span
              className={`rounded-full border px-2 py-0.5 text-sm font-bold ${scoreColor(scores[key])}`}
            >
              {scores[key]}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">{question}</p>
          {expanded === key && explanations && (
            <p className="mt-3 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-600">
              {explanations[key]}
            </p>
          )}
          {explanations && (
            <p className="mt-2 text-[11px] text-slate-400">
              {expanded === key ? "Hide explanation" : "Why this score?"}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
