import type {
  BrokerPacketPreview,
  CoverReadySnapshot,
  DocumentStatusResponse,
  DocumentSummary,
  EvidenceItem,
  MissingRequirement,
  ProcessingJobRead,
  ProofLookup,
  ReviewActionResponse,
  ScenarioSimulation,
  Scorecard,
  TranslatorResult,
  UploadResponse,
  WorkspaceRead,
} from "@coverready/contracts";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type WorkspaceInfo = WorkspaceRead;

type ApiEvidenceItem = EvidenceItem & { source_snippet?: string | null };

function normalizeEvidenceItem(item: ApiEvidenceItem): EvidenceItem {
  return {
    ...item,
    source_evidence: item.source_evidence ?? item.source_snippet ?? null,
  };
}

function normalizeProof(proof: ProofLookup): ProofLookup {
  return {
    ...proof,
    evidence_lookup: Object.fromEntries(
      Object.entries(proof.evidence_lookup).map(([id, item]) => [id, normalizeEvidenceItem(item as ApiEvidenceItem)]),
    ),
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

async function requestForm<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function getWorkspaces(): Promise<WorkspaceInfo[]> {
  return requestJson<WorkspaceInfo[]>("/workspaces");
}

export async function updateWorkspace(workspaceId: string, payload: Partial<Pick<WorkspaceRead, "name" | "address" | "industry_code" | "state">>) {
  return requestJson<WorkspaceRead>(`/workspaces/${workspaceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

function bpQuery(workspaceId: string): string {
  return `?business_profile_id=${encodeURIComponent(workspaceId)}`;
}

export async function getCoverReadySnapshot(workspaceId: string): Promise<CoverReadySnapshot> {
  const q = bpQuery(workspaceId);
  const [workspace, scorecard, missingDocuments, documents, evidence, claims, brokerPacket] = await Promise.all([
    requestJson<WorkspaceRead>(`/workspaces/${workspaceId}`),
    requestJson<Scorecard>(`/workspaces/${workspaceId}/score`),
    requestJson<MissingRequirement[]>(`/missing-documents${q}`),
    requestJson<DocumentSummary[]>(`/documents${q}`),
    requestJson<EvidenceItem[]>(`/evidence${q}`),
    requestJson<CoverReadySnapshot["claims"]>(`/claims${q}`),
    requestJson<BrokerPacketPreview>(`/broker-packet/preview${q}`),
  ]);

  const proof = scorecard.id
    ? await requestJson<ProofLookup>(`/scorecards/${scorecard.id}/proof`)
    : { scorecard_id: "", reasons: [], evidence_lookup: {} };

  return {
    workspace,
    scorecard,
    proof: normalizeProof(proof),
    missingDocuments,
    documents,
    evidence: evidence.map((item) => normalizeEvidenceItem(item as ApiEvidenceItem)),
    claims,
    brokerPacket,
  };
}

export async function getWorkspaceJobs(workspaceId: string): Promise<ProcessingJobRead[]> {
  return requestJson<ProcessingJobRead[]>(`/workspaces/${workspaceId}/jobs`);
}

export async function getDocumentStatus(documentId: string): Promise<DocumentStatusResponse> {
  return requestJson<DocumentStatusResponse>(`/documents/${documentId}/status`);
}

export async function uploadLocalDocument(file: File, documentType: string | undefined, workspaceId: string): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (documentType) formData.append("document_type", documentType);
  formData.append("business_profile_id", workspaceId);
  return requestForm<UploadResponse>("/documents/upload", formData);
}

export async function reprocessDocument(documentId: string): Promise<DocumentStatusResponse> {
  return requestJson<DocumentStatusResponse>(`/documents/${documentId}/reprocess`, { method: "POST" });
}

export async function updateEvidenceValue(evidenceId: string, normalizedValue: string): Promise<ReviewActionResponse> {
  return requestJson<ReviewActionResponse>(`/evidence/${evidenceId}`, {
    method: "PATCH",
    body: JSON.stringify({ normalized_value: normalizedValue }),
  });
}

export async function approveEvidence(evidenceId: string): Promise<ReviewActionResponse> {
  return requestJson<ReviewActionResponse>(`/evidence/${evidenceId}/approve`, { method: "POST" });
}

export async function rejectEvidence(evidenceId: string): Promise<ReviewActionResponse> {
  return requestJson<ReviewActionResponse>(`/evidence/${evidenceId}/reject`, { method: "POST" });
}

export async function createManualEvidence(payload: {
  workspace_id: string;
  category: string;
  field_name: string;
  normalized_value: string;
  source_snippet?: string | null;
}): Promise<ReviewActionResponse> {
  return requestJson<ReviewActionResponse>("/evidence", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function translateClauseText(clauseText: string, workspaceId: string): Promise<TranslatorResult> {
  return requestJson<TranslatorResult>("/translator/explain", {
    method: "POST",
    body: JSON.stringify({ clause_text: clauseText, business_profile_id: workspaceId }),
  });
}

export async function simulateScenarioChange(scenario: string, workspaceId: string): Promise<ScenarioSimulation> {
  return requestJson<ScenarioSimulation>("/scenarios/simulate", {
    method: "POST",
    body: JSON.stringify({ scenario, business_profile_id: workspaceId }),
  });
}

export async function generateBrokerPacket(workspaceId: string): Promise<BrokerPacketPreview> {
  return requestJson<BrokerPacketPreview>(`/broker-packet/generate${bpQuery(workspaceId)}`, { method: "POST" });
}

export async function recalculateScorecard(workspaceId: string): Promise<Scorecard> {
  return requestJson<Scorecard>(`/scorecards/recalculate${bpQuery(workspaceId)}`, { method: "POST" });
}
