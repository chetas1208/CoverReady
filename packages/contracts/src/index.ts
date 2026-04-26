export type EvidenceStrength =
  | "verified"
  | "partially_verified"
  | "weak_evidence"
  | "missing"
  | "expired"
  | "conflicting";

export type DimensionName =
  | "documentation_completeness"
  | "property_safety_readiness"
  | "operational_controls"
  | "coverage_alignment"
  | "renewal_readiness";

export interface EvidenceItem {
  id: string;
  category: string;
  field: string;
  field_name?: string | null;
  value: string | null;
  normalized_value?: string | null;
  raw_value?: string | null;
  evidence_strength: EvidenceStrength;
  confidence: number;
  source_evidence: string | null;
  source_snippet?: string | null;
  source_bbox_json?: {
    xmin?: number;
    ymin?: number;
    xmax?: number;
    ymax?: number;
    coordinate_system?: "relative";
  } | null;
  document_id?: string | null;
  page_ref?: string | null;
  page_number?: number | null;
  expires_on?: string | null;
  is_conflicting?: boolean;
  extractor_model_id?: string | null;
  prompt_version?: string | null;
  status?: string | null;
  review_status?: string | null;
  created_at?: string | null;
}

export interface ScoreReason {
  rule_id: string;
  dimension: DimensionName;
  points_awarded: number;
  points_possible: number;
  status: EvidenceStrength;
  plain_reason: string;
  source_evidence_ids: string[];
}

export interface DimensionScore {
  score: number;
  max_score: number;
  reason: string;
  items: ScoreReason[];
}

export interface Subscores {
  documentation_completeness: DimensionScore;
  property_safety_readiness: DimensionScore;
  operational_controls: DimensionScore;
  coverage_alignment: DimensionScore;
  renewal_readiness: DimensionScore;
}

export interface ScoreCap {
  cap_id: string;
  title: string;
  max_total_score: number;
  reason: string;
  triggered_by_rule_ids: string[];
  triggered_by_fields: string[];
}

export interface QuickWin {
  action: string;
  expected_score_impact: string;
  effort: "low" | "medium" | "high";
  reason: string;
}

export interface Scorecard {
  id?: string | null;
  business_profile_id?: string | null;
  total_score: number;
  uncapped_total_score: number;
  score_caps: ScoreCap[];
  subscores: Subscores;
  top_risk_drivers: string[];
  quick_wins: QuickWin[];
  missing_documents: string[];
  manual_review_needed: string[];
  ruleset_id: string;
  ruleset_version: string;
  input_hash: string;
  explanation_source: string;
}

export interface MissingRequirement {
  rule_id: string;
  label: string;
  dimension: DimensionName;
  severity: string;
  status: EvidenceStrength;
  cap_id?: string | null;
  source_evidence_ids: string[];
}

export interface DocumentSummary {
  id: string;
  business_profile_id: string;
  workspace_id?: string | null;
  document_type: string;
  status: string;
  processing_status?: string | null;
  latest_job_id?: string | null;
  latest_job_stage?: string | null;
  latest_job_attempt?: number | null;
  latest_error?: string | null;
  origin: string;
  source_filename: string;
  mime_type?: string | null;
  checksum?: string | null;
  summary?: string | null;
  document_date?: string | null;
  expiration_date?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ProcessingJobRead {
  id: string;
  workspace_id?: string | null;
  document_id: string;
  job_type: string;
  status: string;
  stage: string;
  attempt_count: number;
  max_attempts: number;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  completed_at?: string | null;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatusResponse {
  document: DocumentSummary;
  job: ProcessingJobRead | null;
}

export interface UploadResponse {
  document: DocumentSummary;
  extraction_status: string;
}

export interface ReviewActionResponse {
  evidence: EvidenceItem;
  scorecard: Scorecard;
}

export interface WorkspaceRead {
  id: string;
  name: string;
  address: string | null;
  industry_code: string;
  state: string | null;
  origin: string;
  created_at: string;
  updated_at: string;
}

export interface ClaimRecord {
  id: string;
  key: string;
  title: string;
  value: string | null;
  status: string;
  source_evidence_ids: string[];
}

export interface DemoState {
  business_profile_id: string;
  business_name: string;
  documents_count: number;
  evidence_count: number;
  latest_scorecard: Scorecard | null;
}

export interface TranslatorResult {
  plain_english_summary: string;
  why_it_matters: string;
  questions_to_verify: string[];
  suggested_next_steps: string[];
}

export interface ScenarioSimulation {
  scenario: string;
  likely_score_direction: "up" | "flat" | "uncertain" | "down";
  estimated_impact_summary: string;
  why: string;
  still_needed: string[];
}

export interface BrokerPacketPreview {
  business_name: string;
  address: string | null;
  score_summary: string;
  top_strengths: string[];
  missing_documents: string[];
  next_best_actions: string[];
  documents: DocumentSummary[];
}

export interface ProofLookup {
  scorecard_id: string;
  reasons: ScoreReason[];
  evidence_lookup: Record<string, EvidenceItem>;
}

export interface CoverReadySnapshot {
  workspace: WorkspaceRead;
  scorecard: Scorecard;
  proof: ProofLookup;
  missingDocuments: MissingRequirement[];
  documents: DocumentSummary[];
  evidence: EvidenceItem[];
  claims: ClaimRecord[];
  brokerPacket: BrokerPacketPreview;
}
