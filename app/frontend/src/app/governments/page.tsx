"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { ScoreBadge } from "@/components/ScoreBadge";

export default function GovernmentsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["governments"],
    queryFn: api.governments,
  });

  if (isLoading) return <p className="text-slate-500">Loading governments…</p>;
  if (error)
    return (
      <p className="text-rose-600">
        Could not reach the API. Is the backend running? ({String(error)})
      </p>
    );

  return (
    <div>
      <h1 className="text-2xl font-bold">Governments</h1>
      <p className="mt-1 text-sm text-slate-500">
        Jurisdictions currently monitored by the public-information audit.
      </p>
      <div className="mt-6 space-y-3">
        {data?.map((gov) => (
          <Link
            key={gov.id}
            href={`/governments/${gov.id}`}
            className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300"
          >
            <div>
              <h2 className="font-semibold text-slate-900">{gov.name}</h2>
              <p className="mt-1 text-xs text-slate-500">
                {gov.country_code} · {gov.jurisdiction_type}
                {gov.latest_report && ` · last report ${gov.latest_report.report_date}`}
              </p>
            </div>
            {gov.latest_report?.overall_score != null && (
              <ScoreBadge score={gov.latest_report.overall_score} />
            )}
          </Link>
        ))}
        {data?.length === 0 && (
          <p className="text-sm text-slate-500">
            No governments yet. Seed one with:{" "}
            <code className="rounded bg-slate-100 px-1">
              python -m gov_oracle_agents.run --government &quot;Government of Bangladesh&quot;
            </code>
          </p>
        )}
      </div>
    </div>
  );
}
