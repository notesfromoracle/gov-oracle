"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { FailedQuestionCard } from "@/components/FailedQuestionCard";
import { NoteCard } from "@/components/NoteCard";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ScoreGrid } from "@/components/ScoreGrid";
import { ScoreHistoryChart } from "@/components/ScoreHistoryChart";

export default function GovernmentDashboard() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const government = useQuery({ queryKey: ["government", id], queryFn: () => api.government(id) });
  const report = useQuery({
    queryKey: ["latest-report", id],
    queryFn: () => api.latestReport(id),
    retry: false,
  });
  const history = useQuery({ queryKey: ["history", id], queryFn: () => api.scoreHistory(id) });
  const reports = useQuery({ queryKey: ["reports", id], queryFn: () => api.reports(id) });

  const runMutation = useMutation({
    mutationFn: () => api.triggerRun(id),
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["latest-report", id] });
        queryClient.invalidateQueries({ queryKey: ["history", id] });
        queryClient.invalidateQueries({ queryKey: ["reports", id] });
      }, 3000);
    },
  });

  if (government.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (government.error) return <p className="text-rose-600">Government not found.</p>;

  const data = report.data;
  const highPriority = data?.today_notes.filter((n) => n.importance === "high") ?? [];
  const failedOnly =
    data?.failed_questions.filter(
      (q) => (q.answerability_status ?? q.status) !== "answered"
    ) ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{government.data?.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {government.data?.country_code} · {government.data?.jurisdiction_type}
            {data && ` · latest report ${data.date} (${data.run_type})`}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {data && <ScoreBadge score={data.transparency_scores.overall} size="lg" />}
          <button
            type="button"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {runMutation.isPending ? "Queuing…" : "Run report now"}
          </button>
        </div>
      </div>

      {runMutation.isSuccess && (
        <p className="rounded bg-blue-50 p-3 text-sm text-blue-700">
          Run queued ({runMutation.data.backend}). New reports appear here when the run
          finishes — refresh in a minute.
        </p>
      )}
      {data?.stale && (
        <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">{data.warning}</p>
      )}

      {report.isLoading && <p className="text-slate-500">Loading latest report…</p>}
      {report.error && (
        <p className="rounded bg-slate-100 p-4 text-sm text-slate-600">
          No report yet for this government. Trigger a run above, or from the CLI:{" "}
          <code className="rounded bg-white px-1">
            python -m gov_oracle_agents.run --government &quot;{government.data?.name}&quot;
          </code>
        </p>
      )}

      {data && (
        <>
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Executive summary
            </h2>
            <p className="mt-2 leading-relaxed text-slate-700">{data.executive_summary}</p>
            <div className="mt-4 flex flex-wrap gap-6 text-xs text-slate-500">
              <span>{data.source_coverage.sources_checked} sources checked</span>
              <span>{data.source_coverage.sources_successful} reachable</span>
              <span>{data.source_coverage.sources_failed} failed</span>
              <span>{data.source_coverage.new_documents_found} new documents</span>
              <Link className="text-blue-600 underline" href={`/governments/${id}/reports/${data.report_id}`}>
                Full report →
              </Link>
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Transparency scores</h2>
            <ScoreGrid scores={data.transparency_scores} explanations={data.score_explanations} />
          </section>

          {highPriority.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">High-priority findings</h2>
              <div className="space-y-4">
                {highPriority.map((note) => (
                  <NoteCard key={note.title} note={note} />
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-3 text-lg font-semibold">Today&apos;s notes</h2>
            <div className="space-y-4">
              {data.today_notes.map((note) => (
                <NoteCard key={note.title} note={note} />
              ))}
              {data.today_notes.length === 0 && (
                <p className="text-sm text-slate-500">No notes generated in this run.</p>
              )}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">
              Questions the AI could not answer
            </h2>
            <div className="space-y-3">
              {failedOnly.map((q) => (
                <FailedQuestionCard key={q.question} question={q} />
              ))}
            </div>
          </section>
        </>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Score history</h2>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <ScoreHistoryChart history={history.data ?? []} />
        </div>
      </section>

      {reports.data && reports.data.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Past reports</h2>
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white shadow-sm">
            {reports.data.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/governments/${id}/reports/${r.id}`}
                  className="flex items-center justify-between p-4 hover:bg-slate-50"
                >
                  <span className="text-sm text-slate-700">
                    {r.report_date} · {r.run_type}
                  </span>
                  <span className="text-sm font-semibold text-slate-900">
                    {r.overall_score ?? "—"}/100
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
