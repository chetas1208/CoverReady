"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, PencilLine, ShieldAlert, X } from "lucide-react";

import type { EvidenceReviewState, VaultEvidenceRecord } from "@/lib/live-records";
import { StrengthBadge } from "@/components/strength-badge";
import { StatusChip } from "@/components/status-chip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

function reviewTone(status: EvidenceReviewState) {
  if (status === "approved") return "success" as const;
  if (status === "rejected") return "critical" as const;
  if (status === "edited") return "processing" as const;
  return "warning" as const;
}

export function EvidenceDetailDrawer({
  selected,
  onClose,
  onApprove,
  onReject,
  onSave,
  isSaving = false,
  error,
}: {
  selected: VaultEvidenceRecord | null;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onSave: (id: string, normalizedValue: string) => void;
  isSaving?: boolean;
  error?: string | null;
}) {
  const [draftValue, setDraftValue] = useState("");

  useEffect(() => {
    setDraftValue(selected?.normalizedValue ?? "");
  }, [selected]);

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
              initial={{ x: 32, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 32, opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="glass-panel flex h-full w-full max-w-2xl flex-col rounded-lg bg-white"
            >
              <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
                <div>
                  <p className="section-eyebrow">Evidence detail</p>
                  <h3 className="mt-1 text-xl font-semibold text-ink">{selected.field}</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    Source: {selected.sourceDocument} · Page {selected.pageNumber}
                  </p>
                </div>
                <Button variant="ghost" onClick={onClose} aria-label="Close evidence drawer" className="mt-0.5">
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto p-5 lg:grid-cols-[1fr_1fr]">
                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <StrengthBadge strength={selected.evidenceStrength} />
                      <StatusChip status={selected.reviewStatus} tone={reviewTone(selected.reviewStatus)} />
                    </div>
                    <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">
                      Confidence {(selected.confidence * 100).toFixed(0)}%
                    </p>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Editable normalized value</p>
                    <Input
                      value={draftValue}
                      onChange={(event) => setDraftValue(event.target.value)}
                      className="mt-3"
                    />
                    <p className="mt-3 text-xs text-slate-500">Review changes before applying to preserve score explainability.</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button onClick={() => onSave(selected.id, draftValue)} disabled={isSaving}>
                        <PencilLine className="h-4 w-4" />
                        {isSaving ? "Saving..." : "Save edit"}
                      </Button>
                      <Button variant="secondary" onClick={() => onApprove(selected.id)} disabled={isSaving}>
                        <CheckCircle2 className="h-4 w-4" />
                        Approve
                      </Button>
                      <Button variant="secondary" onClick={() => onReject(selected.id)} disabled={isSaving}>
                        <ShieldAlert className="h-4 w-4" />
                        Reject
                      </Button>
                    </div>
                    {error ? <p className="mt-3 text-xs font-semibold text-rose-700">{error}</p> : null}
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Raw extracted snippet</p>
                    <Textarea value={selected.rawSnippet} readOnly className="mt-3 min-h-28" />
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Linked score components</p>
                    <div className="mt-2 space-y-2">
                      {selected.linkedScoreComponents.map((item) => (
                        <div key={item} className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-800">Source preview</p>
                      <p className="text-xs text-slate-500">{selected.sourcePreviewLabel}</p>
                    </div>
                    <div className="relative mt-3 h-56 rounded-md border border-slate-200 bg-[linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)] p-3">
                      <p className="text-xs leading-5 text-slate-600">{selected.rawSnippet}</p>
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
                    <p className="mt-2 text-xs text-slate-500">Page {selected.pageNumber} · {selected.pageRef}</p>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-800">Database state</p>
                    <div className="mt-3 space-y-2 text-sm text-slate-600">
                      <p>Evidence ID: {selected.id}</p>
                      <p>Review status: {selected.reviewStatus.replace(/_/g, " ")}</p>
                      <p>Created: {selected.createdAt ? new Date(selected.createdAt).toLocaleString() : "Unavailable"}</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.aside>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
