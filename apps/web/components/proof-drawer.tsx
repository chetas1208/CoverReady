"use client";

import type { ProofLookup, ScoreReason } from "@coverready/contracts";
import { X } from "lucide-react";

import { StrengthBadge } from "@/components/strength-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function ProofDrawer({
  selectedReason,
  proof,
  onClose,
}: {
  selectedReason: ScoreReason | null;
  proof: ProofLookup;
  onClose: () => void;
}) {
  if (!selectedReason) {
    return null;
  }

  const evidenceItems = selectedReason.source_evidence_ids
    .map((id) => proof.evidence_lookup[id])
    .filter(Boolean);

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/35 p-4 backdrop-blur-sm">
      <div className="ml-auto flex h-full max-w-xl flex-col">
        <Card className="h-full overflow-hidden">
          <CardContent className="flex items-start justify-between border-b border-slate-200 pb-4">
            <div>
              <p className="section-eyebrow">Proof Detail</p>
              <h3 className="mt-2 text-xl font-semibold text-ink">{selectedReason.plain_reason}</h3>
            </div>
            <Button variant="ghost" onClick={onClose} aria-label="Close proof drawer">
              <X className="h-4 w-4" />
            </Button>
          </CardContent>
          <div className="space-y-4 overflow-y-auto p-5">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-slate-700">{selectedReason.rule_id}</span>
                <StrengthBadge strength={selectedReason.status} />
              </div>
              <p className="mt-3 text-sm text-slate-600">
                Points: {selectedReason.points_awarded} / {selectedReason.points_possible}
              </p>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700">Linked evidence</h4>
              {evidenceItems.length ? (
                evidenceItems.map((item) => (
                  <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-ink">{item.field}</p>
                      <StrengthBadge strength={item.evidence_strength} />
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{item.value ?? "No value captured."}</p>
                    <p className="mt-3 text-sm text-slate-500">{item.source_evidence ?? "No snippet captured."}</p>
                    <p className="mt-2 text-xs uppercase text-slate-400">
                      Evidence ID {item.id}
                      {item.page_ref ? ` - ${item.page_ref}` : ""}
                    </p>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
                  No source evidence IDs were attached to this reason. This usually means the gap is a missing document rather than a present one.
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
