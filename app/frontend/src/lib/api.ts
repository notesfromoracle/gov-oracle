import type {
  FailedQuestion,
  GovernmentSummary,
  Report,
  ReportSummary,
  ScoreHistoryPoint,
  SourceRow,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5001/api";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  governments: () => fetchJson<GovernmentSummary[]>("/governments"),
  government: (id: number | string) => fetchJson<GovernmentSummary>(`/governments/${id}`),
  latestReport: (id: number | string) => fetchJson<Report>(`/governments/${id}/latest-report`),
  reports: (id: number | string) => fetchJson<ReportSummary[]>(`/governments/${id}/reports`),
  report: (reportId: number | string) => fetchJson<Report>(`/reports/${reportId}`),
  scoreHistory: (id: number | string) =>
    fetchJson<ScoreHistoryPoint[]>(`/governments/${id}/scores/history`),
  sources: (id: number | string) => fetchJson<SourceRow[]>(`/governments/${id}/sources`),
  failedQuestions: (id: number | string) =>
    fetchJson<FailedQuestion[]>(`/governments/${id}/failed-questions`),
  triggerRun: (id: number | string, runType: string = "manual") =>
    fetchJson<{ queued: boolean; backend: string }>(`/governments/${id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_type: runType }),
    }),
};
