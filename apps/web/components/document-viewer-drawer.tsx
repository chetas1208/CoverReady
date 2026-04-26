"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ChevronLeft, ChevronRight, Info, X } from "lucide-react";
import { useMemo, useState } from "react";

import { API_BASE } from "@/lib/api";
import type { UploadDocumentRecord, VaultEvidenceRecord } from "@/lib/live-records";
import { statusTone } from "@/lib/live-records";
import { StatusChip } from "@/components/status-chip";
import { StrengthBadge } from "@/components/strength-badge";
import { Button } from "@/components/ui/button";

function toneForStatus(status: UploadDocumentRecord["status"]) {
  return statusTone(status);
}

export function DocumentViewerDrawer({
  selected,
  linkedEvidence,
  onClose,
}: {
  selected: UploadDocumentRecord | null;
  linkedEvidence: VaultEvidenceRecord[];
  onClose: () => void;
}) {
  const [page, setPage] = useState(1);

  const pageCount = useMemo(() => selected?.pages ?? 1, [selected?.pages]);
  const documentUrl = selected ? `${API_BASE}/documents/${selected.id}/download` : "";

  return (
    <AnimatePresence>
      {selected ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-slate-950/30 backdrop-blur-sm"
        >
          <div className="flex h-full justify-end p-3 md:p-4">
            <motion.aside
              initial={{ x: 30, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 30, opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="glass-panel flex h-full w-full max-w-[1100px] flex-col rounded-lg bg-white"
            >
              <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
                <div>
                  <p className="section-eyebrow">Document viewer</p>
                  <h3 className="mt-1 text-xl font-semibold text-ink">{selected.sourceFilename}</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {selected.documentType.replace(/_/g, " ")} · Updated {selected.updatedAt}
                  </p>
                </div>
                <Button variant="ghost" onClick={onClose} aria-label="Close document viewer">
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto p-5 lg:grid-cols-[1.3fr_0.9fr]">
                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-800">PDF / image preview</p>
                      <div className="flex items-center gap-2">
                        <Button variant="secondary" onClick={() => setPage((current) => Math.max(1, current - 1))}>
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <p className="text-xs text-slate-600">Page {page} / {pageCount}</p>
                        <Button variant="secondary" onClick={() => setPage((current) => Math.min(pageCount, current + 1))}>
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="relative h-80 rounded-md border border-slate-200 bg-[linear-gradient(180deg,#f9fafb_0%,#edf2f7_100%)] p-4">
                      <iframe title={selected.sourceFilename} src={documentUrl} className="h-full w-full rounded border-0 bg-white" />
                      {selected.bbox ? (
                        <div
                          className="absolute border-2 border-teal-600/80 bg-teal-200/20"
                          style={{
                            left: `${selected.bbox.x}%`,
                            top: `${selected.bbox.y}%`,
                            width: `${selected.bbox.width}%`,
                            height: `${selected.bbox.height}%`,
                          }}
                        />
                      ) : null}
                    </div>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Source snippet</p>
                    <p className="mt-2 rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">{selected.sourceSnippet}</p>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Linked evidence</p>
                    <div className="mt-2 space-y-2">
                      {linkedEvidence.length ? (
                        linkedEvidence.map((evidence) => (
                          <div key={evidence.id} className="rounded-md border border-slate-200 p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-sm font-semibold text-slate-800">{evidence.field}</p>
                              <StrengthBadge strength={evidence.evidenceStrength} />
                            </div>
                            <p className="mt-1 text-sm text-slate-600">{evidence.normalizedValue}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-slate-600">No linked evidence yet.</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800">Extraction metadata</p>
                      <StatusChip status={selected.status} tone={toneForStatus(selected.status)} />
                    </div>
                    <div className="mt-3 space-y-2 text-sm text-slate-600">
                      <p>Current stage: {selected.currentStage.replace(/_/g, " ")}</p>
                      <p>Progress: {selected.progress}%</p>
                      <p>Pages: {selected.pages}</p>
                      <p>Linked evidence: {selected.linkedEvidenceIds.length}</p>
                    </div>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Extraction timeline</p>
                    <div className="mt-3 space-y-2">
                      {selected.extractionTimeline.map((step) => (
                        <div key={step.id} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2">
                          <p className="text-sm text-slate-700">{step.label}</p>
                          <div className="flex items-center gap-2">
                            <StatusChip status={step.tone} tone={step.tone} />
                            <p className="text-xs text-slate-500">{step.at}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {selected.error ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-700" />
                        <div>
                          <p className="text-sm font-semibold text-amber-900">Processing error</p>
                          <p className="mt-1 text-sm text-amber-800">Error: {selected.error}</p>
                          <p className="mt-2 text-xs text-amber-700">
                            <Info className="mr-1 inline h-3.5 w-3.5" />
                            Retry creates a new backend job and this panel updates from the database.
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </motion.aside>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
