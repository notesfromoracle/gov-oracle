import type { FailedQuestion } from "@/lib/types";

const severityStyles: Record<string, string> = {
  critical: "border-rose-300 bg-rose-50",
  high: "border-orange-300 bg-orange-50",
  medium: "border-amber-200 bg-amber-50",
  low: "border-slate-200 bg-slate-50",
};

const statusStyles: Record<string, string> = {
  answered: "bg-emerald-100 text-emerald-700",
  partial: "bg-amber-100 text-amber-700",
  failed: "bg-rose-100 text-rose-700",
};

const answerStyles: Record<string, string> = {
  answered: "border-emerald-200 bg-emerald-50 text-emerald-900",
  partial: "border-amber-200 bg-white text-slate-800",
  failed: "border-slate-200 bg-white text-slate-700",
};

export function FailedQuestionCard({ question }: { question: FailedQuestion }) {
  const status = question.answerability_status ?? question.status ?? "failed";
  const findings = question.findings ?? [];
  const evidence = question.evidence ?? [];

  return (
    <div className={`rounded-lg border p-4 ${severityStyles[question.severity] ?? severityStyles.low}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-800">{question.question}</p>
        <div className="flex shrink-0 items-center gap-2">
          {question.confidence != null && question.confidence > 0 && (
            <span className="text-xs text-slate-400">
              {(question.confidence * 100).toFixed(0)}%
            </span>
          )}
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusStyles[status]}`}>
            {status}
          </span>
        </div>
      </div>

      {question.answer && (
        <div className={`mt-3 rounded border p-3 ${answerStyles[status]}`}>
          <p className="text-[11px] font-semibold uppercase tracking-wide opacity-60">
            {status === "answered" ? "Answer (verify against evidence below)" : "Partial information found"}
          </p>
          <p className="mt-1 whitespace-pre-line text-sm leading-relaxed">{question.answer}</p>
        </div>
      )}

      {findings.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-slate-500">Supporting records</p>
          <ul className="mt-1 space-y-1">
            {findings.map((f, i) => (
              <li key={`${f.title}-${i}`} className="text-xs text-slate-600">
                {f.source_url ? (
                  <a href={f.source_url} target="_blank" rel="noreferrer" className="text-blue-600 underline hover:text-blue-800">
                    {f.title}
                  </a>
                ) : (
                  <span>{f.title}</span>
                )}
                {f.detail && <span className="text-slate-400"> · {f.detail}</span>}
                {f.amount != null && (
                  <span className="font-medium">
                    {" "}· {f.amount.toLocaleString()} {f.currency ?? ""}
                  </span>
                )}
                {f.date && <span className="text-slate-400"> · {String(f.date).slice(0, 10)}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {question.reason_failed && (
        <p className="mt-2 text-xs text-slate-600">{question.reason_failed}</p>
      )}
      {question.missing_data.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          <strong>Missing data:</strong> {question.missing_data.join("; ")}
        </p>
      )}
      {question.recommendation && (
        <p className="mt-2 text-xs text-slate-500">
          <strong>What would fix this:</strong> {question.recommendation}
        </p>
      )}
      {evidence.length > 0 && (
        <p className="mt-2 text-xs text-slate-400">
          Evidence:{" "}
          {evidence.map((e, i) => (
            <span key={e.url}>
              {i > 0 && " · "}
              <a href={e.url} target="_blank" rel="noreferrer" className="underline hover:text-slate-600">
                {e.title.length > 60 ? `${e.title.slice(0, 60)}…` : e.title}
              </a>
            </span>
          ))}
        </p>
      )}
    </div>
  );
}
