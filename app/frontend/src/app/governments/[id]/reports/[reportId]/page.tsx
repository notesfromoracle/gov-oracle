"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { FailedQuestionCard } from "@/components/FailedQuestionCard";
import { NoteCard } from "@/components/NoteCard";
import { RawJsonToggle } from "@/components/RawJsonToggle";
import { ScoreGrid } from "@/components/ScoreGrid";

export default function ReportDetailPage() {
  const { id, reportId } = useParams<{ id: string; reportId: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.report(reportId),
  });

  if (isLoading) return <p className="text-slate-500">Loading report…</p>;
  if (error || !data) return <p className="text-rose-600">Report not found.</p>;

  const missingData = Array.from(
    new Set(data.failed_questions.flatMap((q) => q.missing_data))
  );

  return (
    <div className="space-y-8">
      <div>
        <Link href={`/governments/${id}`} className="text-sm text-blue-600 underline">
          ← Back to dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-bold">
          {data.government} — {data.date}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {data.run_type} run · overall score {data.transparency_scores.overall}/100
        </p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Executive summary
        </h2>
        <p className="mt-2 leading-relaxed text-slate-700">{data.executive_summary}</p>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Scores and explanations</h2>
        <ScoreGrid scores={data.transparency_scores} explanations={data.score_explanations} />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">All notes ({data.today_notes.length})</h2>
        <div className="space-y-4">
          {data.today_notes.map((note) => (
            <NoteCard key={note.title} note={note} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">
          Civic questions ({data.failed_questions.length} attempted)
        </h2>
        <div className="space-y-3">
          {data.failed_questions.map((q) => (
            <FailedQuestionCard key={q.question} question={q} />
          ))}
        </div>
      </section>

      {missingData.length > 0 && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="font-semibold text-amber-900">Missing public data</h2>
          <ul className="mt-2 list-inside list-disc text-sm text-amber-800">
            {missingData.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <RawJsonToggle data={data} />
      </section>
    </div>
  );
}
