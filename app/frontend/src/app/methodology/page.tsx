const dimensions = [
  {
    name: "Documentation",
    question: "How much expected public information is actually published?",
    signals:
      "Published budgets, audit reports, procurement notices, contract awards, project reports, statistics, laws, historical archives — and expected documents that are missing.",
  },
  {
    name: "Timeliness",
    question: "How quickly is information published after relevant events?",
    signals:
      "Publication delay, last-updated dates, stale datasets, late annual reports, missing quarterly reports, delayed award notices.",
  },
  {
    name: "Accessibility",
    question: "Can machines read and process the information?",
    signals:
      "HTML/CSV/API availability, scanned PDFs, broken links, captcha barriers, inconsistent formats, missing metadata, unstable URLs, language barriers.",
  },
  {
    name: "Completeness",
    question: "Is spending linked to projects, contracts, and outcomes?",
    signals:
      "Budget-to-project, project-to-tender, contract-to-vendor, contract-to-payment, and project-to-outcome linkage.",
  },
  {
    name: "Traceability",
    question: "Can public money be followed through the system?",
    signals:
      "Whether allocations, contracts, vendors, payments, and resulting assets can be traced as an unbroken chain. One missing link breaks the trail.",
  },
  {
    name: "Explainability",
    question: "Can the AI explain where money went and why decisions were made?",
    signals:
      "Successful answer rate on civic questions, citation coverage, confidence levels, missing evidence, contradictory records.",
  },
];

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Methodology</h1>
        <p className="mt-4 leading-relaxed text-slate-700">
          The system scores governments based on whether an independent AI can understand
          public activity using public information.
        </p>
        <ul className="mt-4 list-inside list-disc space-y-1 text-slate-700">
          <li>It does not score ideology.</li>
          <li>It does not endorse or oppose governments.</li>
          <li>
            It measures navigability, documentation, timeliness, accessibility,
            completeness, traceability, and explainability.
          </li>
        </ul>
      </div>

      <div>
        <h2 className="text-lg font-semibold">How a run works</h2>
        <ol className="mt-3 list-inside list-decimal space-y-2 text-sm leading-relaxed text-slate-700">
          <li>Resolve the government and its major institutions.</li>
          <li>Discover and monitor official public sources (budgets, procurement, audit, statistics, parliament, news).</li>
          <li>Capture documents, preserving historical snapshots — old versions are never overwritten.</li>
          <li>Extract structured civic events (allocations, tenders, awards, audit objections).</li>
          <li>Link records into a knowledge graph where evidence supports a relationship.</li>
          <li>Attempt a bank of civic transparency questions against the collected records.</li>
          <li>Score six dimensions from observable signals, each with a written explanation.</li>
        </ol>
      </div>

      <div>
        <h2 className="text-lg font-semibold">The six dimensions</h2>
        <div className="mt-3 space-y-4">
          {dimensions.map((d) => (
            <div key={d.name} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="font-semibold text-slate-900">{d.name}</h3>
              <p className="mt-1 text-sm italic text-slate-600">{d.question}</p>
              <p className="mt-2 text-sm text-slate-600">{d.signals}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg bg-slate-100 p-5 text-sm leading-relaxed text-slate-700">
        <strong>Ground rules.</strong> Every claim must have evidence. Every score must have
        an explanation. Facts are separated from inference. Confidence levels are always
        shown. Source URLs and retrieval timestamps are preserved. Missing data is itself a
        transparency finding — the system reports what it could not learn, not just what it
        could.
      </div>
    </div>
  );
}
