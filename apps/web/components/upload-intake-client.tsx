"use client";

import type { CoverReadySnapshot } from "@coverready/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { LoaderCircle, RefreshCcw, UploadCloud } from "lucide-react";
import { useMemo, useState } from "react";

import { DocumentViewerDrawer } from "@/components/document-viewer-drawer";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-panels";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getWorkspaceJobs, reprocessDocument, uploadLocalDocument } from "@/lib/api";
import { useWorkspace } from "@/components/workspace-context";
import { buildUploadDocumentRecords, buildVaultEvidenceRecords, hasActiveWork, statusTone } from "@/lib/live-records";
import { queryKeys } from "@/lib/query-keys";

const documentHints = [
  "business_license",
  "inspection_report",
  "maintenance_receipt",
  "safety_certificate",
  "declarations_page",
  "generic_document",
];

export function UploadIntakeClient({ snapshot }: { snapshot: CoverReadySnapshot }) {
  const [statusText, setStatusText] = useState("Drop files or choose a document type shortcut to begin.");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDocType, setSelectedDocType] = useState<string | undefined>(undefined);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const { activeWorkspaceId } = useWorkspace();
  const queryClient = useQueryClient();

  const { data: jobs = [], isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.jobs(activeWorkspaceId),
    queryFn: () => getWorkspaceJobs(activeWorkspaceId as string),
    enabled: !!activeWorkspaceId,
    refetchInterval: (query) => (hasActiveWork(snapshot, query.state.data ?? []) ? 2_000 : false),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile || !activeWorkspaceId) return null;
      return uploadLocalDocument(selectedFile, selectedDocType, activeWorkspaceId);
    },
    onSuccess: (response) => {
      setStatusText(
        response
          ? `Uploaded ${response.document.source_filename} as ${response.document.document_type}.`
          : "Upload did not complete.",
      );
      setSelectedFile(null);
      if (activeWorkspaceId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(activeWorkspaceId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.jobs(activeWorkspaceId) });
      }
    },
    onError: (error) => setStatusText(error instanceof Error ? error.message : "Upload failed."),
  });

  const retryMutation = useMutation({
    mutationFn: reprocessDocument,
    onSuccess: (_, documentId) => {
      setStatusText(`Reprocessing started for ${documentId}.`);
      if (activeWorkspaceId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(activeWorkspaceId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.jobs(activeWorkspaceId) });
      }
    },
    onError: (error) => setStatusText(error instanceof Error ? error.message : "Reprocess failed."),
  });

  const documents = useMemo(() => buildUploadDocumentRecords(snapshot.documents, snapshot.evidence, jobs), [jobs, snapshot.documents, snapshot.evidence]);
  const evidenceRecords = useMemo(() => buildVaultEvidenceRecords(snapshot), [snapshot]);

  const selectedDocument = documents.find((item) => item.id === selectedDocumentId) ?? null;
  const linkedEvidence = selectedDocument
    ? evidenceRecords.filter((item) => selectedDocument.linkedEvidenceIds.includes(item.id))
    : [];

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (!file) return;
    setSelectedFile(file);
    setStatusText(`${file.name} is ready to upload.`);
  }

  return (
    <>
      <PageHeader
        eyebrow="Uploads"
        title="Document intake and processing"
        description="Upload insurance documents, watch extraction progress, and inspect source-backed results with confidence."
      />

      <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
        <Card>
          <CardContent className="space-y-4">
            <p className="text-sm font-semibold text-slate-700">Drag-and-drop upload</p>
            <div
              onDragOver={(event) => event.preventDefault()}
              onDrop={handleDrop}
              className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6"
            >
              <div className="text-center">
                <UploadCloud className="mx-auto h-8 w-8 text-teal-700" />
                <p className="mt-2 text-sm font-semibold text-slate-800">Drop PDF or image files here</p>
                <p className="mt-1 text-xs text-slate-500">Accepted: declarations pages, receipts, licenses, inspection reports</p>
              </div>
              <input
                type="file"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                className="mt-4 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
              />
              {selectedFile ? <p className="mt-2 text-xs text-slate-600">Ready: {selectedFile.name}</p> : null}
            </div>

            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Upload shortcuts by doc type</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {documentHints.map((hint) => (
                  <button
                    key={hint}
                    onClick={() => setSelectedDocType(hint)}
                    className={`rounded-md border px-2.5 py-1.5 text-xs font-semibold capitalize ${
                      selectedDocType === hint
                        ? "border-teal-300 bg-teal-50 text-teal-800"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    {hint.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => uploadMutation.mutate()} disabled={!selectedFile || uploadMutation.isPending}>
                {uploadMutation.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                Upload selected file
              </Button>
            </div>

            <div className="rounded-lg bg-slate-100 p-4 text-sm text-slate-600">
              {statusText}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <p className="text-sm font-semibold text-slate-700">Processing trust signals</p>
            <p className="text-sm leading-6 text-slate-600">
              Extraction timeline, fallback visibility, and source-linked evidence are shown for every document so users can trust what the model inferred.
            </p>
            <div className="space-y-3">
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-800">Average extraction confidence</p>
                  <p className="text-sm font-semibold text-slate-700">
                    {Math.round(
                      (evidenceRecords.reduce((total, item) => total + item.confidence, 0) /
                        Math.max(1, evidenceRecords.length)) *
                        100,
                    )}
                    %
                  </p>
                </div>
              </div>
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-800">Documents needing attention</p>
                  <p className="text-sm font-semibold text-slate-700">
                    {documents.filter((item) => item.status !== "processed").length}
                  </p>
                </div>
              </div>
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-800">Linked evidence count</p>
                  <p className="text-sm font-semibold text-slate-700">{evidenceRecords.length}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardContent>
          <p className="text-sm font-semibold text-slate-700">Document processing queue</p>
          <p className="mt-1 text-sm text-slate-600">Click a row to open document viewer, source snippets, and linked evidence.</p>

          <div className="mt-4 space-y-3">
            {isLoading ? <LoadingState title="Loading uploads..." /> : null}
            {isError ? <ErrorState title="Uploads couldn’t refresh." onRetry={() => void refetch()} /> : null}
            {!isLoading && !documents.length ? (
              <EmptyState
                title="No documents uploaded yet"
                body="Start by dropping a business license, lease, or declarations page to build your proof vault."
              />
            ) : null}

            {documents.map((document) => (
              <motion.div
                role="button"
                tabIndex={0}
                key={document.id}
                layout
                onClick={() => setSelectedDocumentId(document.id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSelectedDocumentId(document.id); }}
                className="w-full cursor-pointer rounded-lg border border-slate-200 bg-white p-4 text-left transition hover:border-teal-200 hover:bg-teal-50/40"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-800">{document.sourceFilename}</p>
                    <p className="text-xs text-slate-500">
                      {document.documentType.replace(/_/g, " ")} · {document.currentStage.replace(/_/g, " ")} · {document.pages} page(s)
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusChip status={document.status} tone={statusTone(document.status)} />
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={(event) => {
                        event.stopPropagation();
                        retryMutation.mutate(document.id);
                      }}
                      disabled={retryMutation.isPending}
                    >
                      <RefreshCcw className={`h-4 w-4 ${retryMutation.isPending ? "animate-spin" : ""}`} />
                      Reprocess
                    </Button>
                  </div>
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-teal-500" style={{ width: `${document.progress}%` }} />
                </div>

                <div className="mt-2 flex flex-wrap gap-2">
                  {document.extractionTimeline.map((step) => (
                    <StatusChip key={step.id} status={step.label} tone={step.tone} />
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      <DocumentViewerDrawer
        selected={selectedDocument}
        linkedEvidence={linkedEvidence}
        onClose={() => setSelectedDocumentId(null)}
      />
    </>
  );
}
