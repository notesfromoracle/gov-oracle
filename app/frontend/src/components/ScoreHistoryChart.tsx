"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreHistoryPoint } from "@/lib/types";

const SERIES = [
  { key: "overall", color: "#0f172a", width: 3 },
  { key: "documentation", color: "#2563eb", width: 1.5 },
  { key: "timeliness", color: "#7c3aed", width: 1.5 },
  { key: "accessibility", color: "#059669", width: 1.5 },
  { key: "completeness", color: "#d97706", width: 1.5 },
  { key: "traceability", color: "#dc2626", width: 1.5 },
  { key: "explainability", color: "#0891b2", width: 1.5 },
];

export function ScoreHistoryChart({ history }: { history: ScoreHistoryPoint[] }) {
  if (history.length === 0) {
    return <p className="text-sm text-slate-500">No score history yet.</p>;
  }
  const data = history.map((point, index) => ({
    ...point,
    label: `${point.report_date} (#${index + 1})`,
  }));
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {SERIES.map(({ key, color, width }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={color}
              strokeWidth={width}
              dot={{ r: 2 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
