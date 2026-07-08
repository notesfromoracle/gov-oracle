export function scoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-100 text-emerald-800 border-emerald-300";
  if (score >= 40) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-rose-100 text-rose-800 border-rose-300";
}

export function ScoreBadge({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  const sizing =
    size === "lg" ? "h-20 w-20 text-3xl" : "h-12 w-12 text-lg";
  return (
    <div
      className={`flex items-center justify-center rounded-full border font-bold ${sizing} ${scoreColor(score)}`}
      title={`${score}/100`}
    >
      {score}
    </div>
  );
}
