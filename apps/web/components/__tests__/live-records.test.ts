import { describe, expect, it } from "vitest";
import type { DocumentSummary, EvidenceItem, ProcessingJobRead } from "@coverready/contracts";

import { buildUploadDocumentRecords, hasActiveWork } from "@/lib/live-records";

const document: DocumentSummary = {
  id: "doc_1",
  business_profile_id: "ws_1",
  workspace_id: "ws_1",
  document_type: "business_license",
  status: "ready",
  processing_status: "ready",
  latest_job_id: "job_1",
  latest_job_stage: "ready",
  latest_job_attempt: 1,
  latest_error: null,
  origin: "live",
  source_filename: "license.pdf",
  mime_type: "application/pdf",
  checksum: "abc",
  summary: null,
  document_date: null,
  expiration_date: null,
  created_at: "2026-04-26T00:00:00Z",
  updated_at: "2026-04-26T00:01:00Z",
};

const job: ProcessingJobRead = {
  id: "job_1",
  workspace_id: "ws_1",
  document_id: "doc_1",
  job_type: "document_extraction",
  status: "ready",
  stage: "ready",
  attempt_count: 1,
  max_attempts: 3,
  error_message: null,
  started_at: "2026-04-26T00:00:10Z",
  finished_at: "2026-04-26T00:01:00Z",
  completed_at: "2026-04-26T00:01:00Z",
  progress_percent: 100,
  created_at: "2026-04-26T00:00:00Z",
  updated_at: "2026-04-26T00:01:00Z",
};

const evidence: EvidenceItem = {
  id: "ev_1",
  category: "license",
  field: "license.current",
  value: "active",
  evidence_strength: "verified",
  confidence: 0.95,
  source_evidence: "License status active",
  document_id: "doc_1",
  page_ref: "p1",
};

describe("live records", () => {
  it("maps real backend job state into upload records", () => {
    const [record] = buildUploadDocumentRecords([document], [evidence], [job]);
    expect(record.status).toBe("processed");
    expect(record.progress).toBe(100);
    expect(record.currentStage).toBe("ready");
    expect(record.linkedEvidenceIds).toEqual(["ev_1"]);
  });

  it("detects active polling work from live states", () => {
    expect(hasActiveWork(null, [{ ...job, status: "extracting", stage: "extracting", progress_percent: 35 }])).toBe(true);
    expect(hasActiveWork(null, [job])).toBe(false);
  });
});
