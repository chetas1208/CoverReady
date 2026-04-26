import type { CoverReadySnapshot, DocumentSummary, EvidenceItem, EvidenceStrength, ProcessingJobRead } from "@coverready/contracts";

export type EvidenceReviewState = "pending_review" | "approved" | "edited" | "rejected";
export type UploadDisplayStatus = "queued" | "extracting" | "normalizing" | "scoring" | "processed" | "failed" | "uploaded";

export interface VaultEvidenceRecord {
  id: string;
  category: string;
  field: string;
  normalizedValue: string;
  evidenceStrength: EvidenceStrength;
  confidence: number;
  sourceDocument: string;
  sourceDocumentId: string;
  pageRef: string;
  pageNumber: number;
  reviewStatus: EvidenceReviewState;
  rawSnippet: string;
  sourcePreviewLabel: string;
  bbox?: { x: number; y: number; width: number; height: number };
  linkedScoreComponents: string[];
  createdAt?: string | null;
}

export interface ExtractionTimelineStep {
  id: string;
  label: string;
  at: string;
  tone: "success" | "processing" | "warning" | "critical" | "neutral";
}

export interface UploadDocumentRecord {
  id: string;
  sourceFilename: string;
  documentType: string;
  status: UploadDisplayStatus;
  progress: number;
  currentStage: string;
  pages: number;
  updatedAt: string;
  linkedEvidenceIds: string[];
  extractionTimeline: ExtractionTimelineStep[];
  error?: string | null;
  sourceSnippet?: string | null;
  bbox?: { x: number; y: number; width: number; height: number };
  latestJob?: ProcessingJobRead | null;
}

export interface MissingDocumentPlan {
  id: string;
  title: string;
  severity: "critical" | "important" | "recommended";
  status: "missing" | "weak_evidence" | "expired" | "partially_verified" | "conflicting";
  whyItMatters: string;
  scoreDimension: string;
  scoreImpact: string;
  uploadActionLabel: string;
  suggestedProofTypes: string[];
  completionHint: string;
}

const scoreDimensionLabels: Record<string, string> = {
  documentation_completeness: "Documentation Completeness",
  property_safety_readiness: "Property Safety Readiness",
  operational_controls: "Operational Controls",
  coverage_alignment: "Coverage Alignment",
  renewal_readiness: "Renewal Readiness",
};

const terminalJobStatuses = new Set(["ready", "failed"]);

export function hasActiveWork(snapshot: CoverReadySnapshot | null | undefined, jobs: ProcessingJobRead[] = []) {
  const documentActive = snapshot?.documents.some((document) => {
    const status = document.processing_status ?? document.status;
    return status ? !terminalJobStatuses.has(status) : false;
  });
  return Boolean(documentActive || jobs.some((job) => !terminalJobStatuses.has(job.status)));
}

export function statusTone(status: UploadDisplayStatus) {
  if (status === "processed") return "success" as const;
  if (status === "failed") return "critical" as const;
  if (status === "uploaded") return "neutral" as const;
  return "processing" as const;
}

export function mapBackendStatus(status?: string | null): UploadDisplayStatus {
  if (status === "ready") return "processed";
  if (status === "failed") return "failed";
  if (status === "extracting" || status === "normalizing" || status === "scoring" || status === "queued") return status;
  return "uploaded";
}

function asPageNumber(item: EvidenceItem) {
  if (item.page_number) return item.page_number;
  const match = item.page_ref?.match(/(\d+)/);
  return match ? Number(match[1]) : 1;
}

function formatTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "";
}

function bboxFromEvidence(item: EvidenceItem) {
  const box = item.source_bbox_json;
  if (!box || box.xmin === undefined || box.ymin === undefined || box.xmax === undefined || box.ymax === undefined) {
    return undefined;
  }
  return {
    x: box.xmin * 100,
    y: box.ymin * 100,
    width: Math.max(0, box.xmax - box.xmin) * 100,
    height: Math.max(0, box.ymax - box.ymin) * 100,
  };
}

function normalizeReviewStatus(value?: string | null): EvidenceReviewState {
  if (value === "approved" || value === "edited" || value === "rejected") return value;
  return "pending_review";
}

export function buildVaultEvidenceRecords(snapshot: CoverReadySnapshot): VaultEvidenceRecord[] {
  const documents = new Map(snapshot.documents.map((document) => [document.id, document]));
  const linkedByEvidence = snapshot.proof.reasons.reduce<Record<string, string[]>>((accumulator, reason) => {
    for (const evidenceId of reason.source_evidence_ids) {
      if (!accumulator[evidenceId]) accumulator[evidenceId] = [];
      accumulator[evidenceId].push(`${scoreDimensionLabels[reason.dimension] ?? reason.dimension} · ${reason.rule_id}`);
    }
    return accumulator;
  }, {});

  return snapshot.evidence.map((item) => {
    const sourceDocument = item.document_id ? documents.get(item.document_id) : null;
    return {
      id: item.id,
      category: item.category,
      field: item.field_name ?? item.field,
      normalizedValue: item.normalized_value ?? item.value ?? "",
      evidenceStrength: item.evidence_strength,
      confidence: item.confidence,
      sourceDocument: sourceDocument?.source_filename ?? "Manual evidence",
      sourceDocumentId: item.document_id ?? "manual",
      pageRef: item.page_ref ?? "p1",
      pageNumber: asPageNumber(item),
      reviewStatus: normalizeReviewStatus(item.review_status),
      rawSnippet: item.source_evidence ?? item.source_snippet ?? "",
      sourcePreviewLabel: item.extractor_model_id ?? "Database evidence",
      bbox: bboxFromEvidence(item),
      linkedScoreComponents: linkedByEvidence[item.id] ?? [],
      createdAt: item.created_at,
    };
  });
}

export function buildUploadDocumentRecords(
  documents: DocumentSummary[],
  evidence: EvidenceItem[],
  jobs: ProcessingJobRead[] = [],
): UploadDocumentRecord[] {
  const evidenceByDocument = evidence.reduce<Record<string, string[]>>((accumulator, item) => {
    if (!item.document_id) return accumulator;
    if (!accumulator[item.document_id]) accumulator[item.document_id] = [];
    accumulator[item.document_id].push(item.id);
    return accumulator;
  }, {});
  const jobsByDocument = new Map(jobs.map((job) => [job.document_id, job]));

  return documents.map((document) => {
    const latestJob = document.latest_job_id ? jobs.find((job) => job.id === document.latest_job_id) : jobsByDocument.get(document.id);
    const backendStatus = latestJob?.status ?? document.processing_status ?? document.status;
    const firstEvidence = evidence.find((item) => item.document_id === document.id);
    return {
      id: document.id,
      sourceFilename: document.source_filename,
      documentType: document.document_type,
      status: mapBackendStatus(backendStatus),
      progress: latestJob?.progress_percent ?? (backendStatus === "ready" ? 100 : backendStatus === "failed" ? 100 : 0),
      currentStage: latestJob?.stage ?? document.latest_job_stage ?? backendStatus ?? "uploaded",
      pages: Math.max(1, ...evidence.filter((item) => item.document_id === document.id).map(asPageNumber)),
      updatedAt: formatTime(document.updated_at ?? document.created_at),
      linkedEvidenceIds: evidenceByDocument[document.id] ?? [],
      extractionTimeline: timelineFromJob(latestJob, document),
      error: latestJob?.error_message ?? document.latest_error,
      sourceSnippet: firstEvidence?.source_evidence ?? firstEvidence?.source_snippet ?? null,
      bbox: firstEvidence ? bboxFromEvidence(firstEvidence) : undefined,
      latestJob,
    };
  });
}

function timelineFromJob(job: ProcessingJobRead | undefined, document: DocumentSummary): ExtractionTimelineStep[] {
  const steps: ExtractionTimelineStep[] = [
    {
      id: `${document.id}-created`,
      label: "Document created",
      at: formatTime(document.created_at),
      tone: "success",
    },
  ];
  if (!job) return steps;
  steps.push({
    id: `${job.id}-queued`,
    label: "Job queued",
    at: formatTime(job.created_at),
    tone: job.status === "failed" ? "critical" : "processing",
  });
  if (job.started_at) {
    steps.push({
      id: `${job.id}-started`,
      label: `${job.stage} started`,
      at: formatTime(job.started_at),
      tone: job.status === "failed" ? "critical" : job.status === "ready" ? "success" : "processing",
    });
  }
  if (job.completed_at) {
    steps.push({
      id: `${job.id}-completed`,
      label: job.status === "failed" ? "Job failed" : "Job completed",
      at: formatTime(job.completed_at),
      tone: job.status === "failed" ? "critical" : "success",
    });
  }
  return steps;
}

export function buildMissingDocumentPlans(snapshot: CoverReadySnapshot): MissingDocumentPlan[] {
  return snapshot.missingDocuments.map((item) => {
    const dimension = scoreDimensionLabels[item.dimension] ?? item.dimension;
    const severity = item.severity === "critical" ? "critical" : item.severity === "important" ? "important" : "recommended";
    return {
      id: item.rule_id,
      title: item.label,
      severity,
      status: item.status as MissingDocumentPlan["status"],
      whyItMatters: `${item.label} is ${item.status.replace(/_/g, " ")} for ${dimension}.`,
      scoreDimension: dimension,
      scoreImpact: item.cap_id ? `This item is tied to score cap ${item.cap_id}.` : `This item affects ${dimension}.`,
      uploadActionLabel: `Upload ${item.label.toLowerCase()}`,
      suggestedProofTypes: [item.label],
      completionHint: "Upload current proof with business name, relevant date, and source details visible.",
    };
  });
}
