import Link from "next/link";

export default function HomePage() {
  return (
    <div className="py-12">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
          Can an AI understand your government?
        </h1>
        <p className="mt-6 text-lg text-slate-600">
          We measure how transparent, navigable, and explainable public institutions are
          using only publicly available data.
        </p>
        <p className="mt-4 text-sm text-slate-500">
          Notes From Oracle reads public documents, budgets, procurement records, reports,
          and news to produce evidence-backed civic notes and transparency scores.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            href="/governments"
            className="rounded-lg bg-slate-900 px-6 py-3 text-sm font-medium text-white hover:bg-slate-700"
          >
            Browse governments
          </Link>
          <Link
            href="/methodology"
            className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            How scoring works
          </Link>
        </div>
      </div>

      <div className="mx-auto mt-16 grid max-w-4xl gap-6 md:grid-cols-3">
        {[
          {
            title: "Evidence-backed notes",
            body: "Every claim links to the public document it came from, with retrieval timestamps.",
          },
          {
            title: "Six transparency scores",
            body: "Documentation, timeliness, accessibility, completeness, traceability, explainability — each with a plain-language explanation.",
          },
          {
            title: "Failed questions",
            body: "Civic questions the AI could not answer from public data — because missing data is itself a transparency finding.",
          },
        ].map((card) => (
          <div key={card.title} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="font-semibold text-slate-900">{card.title}</h3>
            <p className="mt-2 text-sm text-slate-600">{card.body}</p>
          </div>
        ))}
      </div>

    </div>
  );
}
