import ReactMarkdown from "react-markdown";
import type { GovernmentNote } from "@/lib/types";

const importanceStyles: Record<string, string> = {
  high: "bg-rose-100 text-rose-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-slate-100 text-slate-600",
};

export function NoteCard({ note }: { note: GovernmentNote }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${importanceStyles[note.importance]}`}>
          {note.importance}
        </span>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
          {note.category}
        </span>
        <span className="ml-auto text-xs text-slate-400">
          confidence {(note.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <h3 className="mt-3 font-semibold text-slate-900">{note.title}</h3>
      <p className="mt-2 text-sm text-slate-600">{note.summary}</p>
      <div className="prose prose-sm mt-3 max-w-none text-sm leading-relaxed text-slate-700">
        <ReactMarkdown>{note.analysis}</ReactMarkdown>
      </div>
      {note.what_is_missing && (
        <p className="mt-3 rounded bg-amber-50 p-3 text-xs text-amber-800">
          <strong>Missing from the public record:</strong> {note.what_is_missing}
        </p>
      )}
      {note.open_questions.length > 0 && (
        <ul className="mt-3 list-inside list-disc text-xs text-slate-500">
          {note.open_questions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ul>
      )}
      {note.evidence.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <p className="text-xs font-medium text-slate-500">Evidence</p>
          <ul className="mt-1 space-y-1">
            {note.evidence.map((e) => (
              <li key={e.url} className="text-xs">
                <a
                  href={e.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 underline hover:text-blue-800"
                >
                  {e.title}
                </a>
                {e.retrieved_at && (
                  <span className="ml-2 text-slate-400">
                    retrieved {new Date(e.retrieved_at).toLocaleDateString()}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
