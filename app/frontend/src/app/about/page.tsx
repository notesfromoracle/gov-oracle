export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">About this project</h1>
      <p className="leading-relaxed text-slate-700">
        Notes From Oracle is an open-source public-information audit. It asks a simple
        question: <em>can this government be understood from its public information?</em>{" "}
        Can public money be traced? Can policies be connected to budgets and outcomes? Can a
        citizen — or an AI — navigate government information without insider access?
      </p>
      <p className="leading-relaxed text-slate-700">
        The system is not a political commentator. It behaves like an auditor: it reads
        official documents, budgets, procurement records, audit reports, statistics, and
        credible news; extracts structured events; links records together; and reports what
        it could and could not learn — with evidence for every claim.
      </p>
      <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm leading-relaxed text-slate-600 shadow-sm">
        <h2 className="font-semibold text-slate-900">Principles</h2>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>Every claim must have evidence.</li>
          <li>Every score must have an explanation.</li>
          <li>Fact is separated from inference.</li>
          <li>No accusations without strong evidence — raw allegations are never published as facts.</li>
          <li>Source URLs and retrieval timestamps are preserved; snapshots are kept historically.</li>
          <li>Old reports are never overwritten.</li>
          <li>Missing data is itself a transparency finding.</li>
        </ul>
      </div>
      <p className="text-sm text-slate-500">
        The agents library, backend, and this interface are open source and designed so the
        research pipeline can be run independently by anyone.
      </p>
    </div>
  );
}
