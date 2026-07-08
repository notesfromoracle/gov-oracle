"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

export default function SourcesPage() {
  const governments = useQuery({ queryKey: ["governments"], queryFn: api.governments });
  const [selected, setSelected] = useState<number | null>(null);
  const governmentId = selected ?? governments.data?.[0]?.id ?? null;

  const sources = useQuery({
    queryKey: ["sources", governmentId],
    queryFn: () => api.sources(governmentId!),
    enabled: governmentId != null,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold">Source transparency</h1>
      <p className="mt-2 max-w-2xl text-sm text-slate-600">
        Every note and score is derived from these public sources. Reliability reflects the
        source type (official records rank above news reporting); status reflects the most
        recent crawl.
      </p>

      {governments.data && governments.data.length > 1 && (
        <select
          className="mt-4 rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          value={governmentId ?? ""}
          onChange={(e) => setSelected(Number(e.target.value))}
        >
          {governments.data.map((gov) => (
            <option key={gov.id} value={gov.id}>
              {gov.name}
            </option>
          ))}
        </select>
      )}

      <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Reliability</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last checked</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sources.data?.map((source) => (
              <tr key={source.id}>
                <td className="px-4 py-3">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 underline hover:text-blue-800"
                  >
                    {source.name}
                  </a>
                </td>
                <td className="px-4 py-3 text-slate-600">{source.source_type}</td>
                <td className="px-4 py-3 text-slate-600">
                  {(source.reliability_score * 100).toFixed(0)}%
                </td>
                <td className="px-4 py-3">
                  <span
                    className={
                      source.status === "active"
                        ? "rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"
                        : "rounded bg-rose-100 px-2 py-0.5 text-xs text-rose-700"
                    }
                  >
                    {source.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {source.last_checked_at
                    ? new Date(source.last_checked_at).toLocaleString()
                    : "never"}
                </td>
              </tr>
            ))}
            {sources.data?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  No sources registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
