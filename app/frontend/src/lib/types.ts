export interface GovernmentSummary {
  id: number;
  name: string;
  country_code: string | null;
  jurisdiction_type: string;
  description: string | null;
  latest_report?: {
    id: number;
    report_date: string;
    overall_score: number | null;
    run_type: string;
  };
}

export interface EvidenceSource {
  title: string;
  url: string;
  source_type: string;
  retrieved_at: string | null;
}

export interface GovernmentNote {
  title: string;
  category: string;
  importance: "low" | "medium" | "high";
  summary: string;
  analysis: string;
  what_is_missing?: string | null;
  open_questions: string[];
  evidence: EvidenceSource[];
  confidence: number;
}

export interface TransparencyScores {
  documentation: number;
  timeliness: number;
  accessibility: number;
  completeness: number;
  traceability: number;
  explainability: number;
  overall: number;
}

export type ScoreDimension = Exclude<keyof TransparencyScores, "overall">;

export interface QuestionFinding {
  title: string;
  detail?: string | null;
  amount?: number | null;
  currency?: string | null;
  date?: string | null;
  source_url?: string | null;
  confidence: number;
}

export interface FailedQuestion {
  question: string;
  answerability_status?: "answered" | "partial" | "failed";
  status?: "answered" | "partial" | "failed";
  answer?: string | null;
  findings?: QuestionFinding[];
  evidence?: EvidenceSource[];
  confidence?: number;
  reason_failed: string;
  missing_data: string[];
  failed_step?: string | null;
  severity: "low" | "medium" | "high" | "critical";
  recommendation?: string | null;
}

export interface SourceCoverage {
  sources_checked: number;
  sources_successful: number;
  sources_failed: number;
  new_documents_found: number;
}

export interface Report {
  report_id: number;
  government: string;
  country_code: string | null;
  date: string;
  run_type: string;
  executive_summary: string;
  today_notes: GovernmentNote[];
  transparency_scores: TransparencyScores;
  score_explanations: Record<ScoreDimension, string>;
  failed_questions: FailedQuestion[];
  source_coverage: SourceCoverage;
  stale?: boolean;
  warning?: string;
  metadata?: Record<string, unknown>;
}

export interface ReportSummary {
  id: number;
  report_date: string;
  run_type: string;
  overall_score: number | null;
  executive_summary: string | null;
}

export interface ScoreHistoryPoint extends TransparencyScores {
  report_id: number;
  report_date: string;
}

export interface SourceRow {
  id: number;
  name: string;
  url: string;
  source_type: string;
  reliability_score: number;
  status: string;
  last_checked_at: string | null;
}
