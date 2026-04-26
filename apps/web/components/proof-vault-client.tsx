"use client";

import type { CoverReadySnapshot } from "@coverready/contracts";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { EvidenceDetailDrawer } from "@/components/evidence-detail-drawer";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/state-panels";
import { StatusChip } from "@/components/status-chip";
import { StrengthBadge } from "@/components/strength-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { approveEvidence, createManualEvidence, rejectEvidence, updateEvidenceValue } from "@/lib/api";
import { useWorkspace } from "@/components/workspace-context";
import type { EvidenceReviewState, VaultEvidenceRecord } from "@/lib/live-records";
import { buildVaultEvidenceRecords } from "@/lib/live-records";
import { queryKeys } from "@/lib/query-keys";

type StrengthFilter = "all" | "verified" | "partially_verified" | "weak_evidence" | "missing" | "expired";
type GroupBy = "category" | "document";

function reviewTone(status: EvidenceReviewState) {
  if (status === "approved") return "success" as const;
  if (status === "rejected") return "critical" as const;
  if (status === "edited") return "processing" as const;
  return "warning" as const;
}

export function ProofVaultClient({ snapshot }: { snapshot: CoverReadySnapshot }) {
  const [query, setQuery] = useState("");
  const [strengthFilter, setStrengthFilter] = useState<StrengthFilter>("all");
  const [reviewFilter, setReviewFilter] = useState<"all" | EvidenceReviewState>("all");
  const [groupBy, setGroupBy] = useState<GroupBy>("category");
  const [selected, setSelected] = useState<VaultEvidenceRecord | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [newField, setNewField] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newCategory, setNewCategory] = useState("operations");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);
  const { activeWorkspaceId } = useWorkspace();
  const queryClient = useQueryClient();

  const rows = useMemo(() => buildVaultEvidenceRecords(snapshot), [snapshot]);

  useEffect(() => {
    if (!selected) return;
    const latest = rows.find((item) => item.id === selected.id);
    if (latest && latest !== selected) setSelected(latest);
  }, [rows, selected]);

  function invalidateLiveQueries() {
    if (!activeWorkspaceId) return;
    queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(activeWorkspaceId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.jobs(activeWorkspaceId) });
  }

  const saveMutation = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) => updateEvidenceValue(id, value),
    onSuccess: () => {
      setMutationError(null);
      invalidateLiveQueries();
    },
    onError: (error) => setMutationError(error instanceof Error ? error.message : "Evidence save failed."),
  });

  const approveMutation = useMutation({
    mutationFn: approveEvidence,
    onSuccess: () => {
      setMutationError(null);
      invalidateLiveQueries();
    },
    onError: (error) => setMutationError(error instanceof Error ? error.message : "Evidence approval failed."),
  });

  const rejectMutation = useMutation({
    mutationFn: rejectEvidence,
    onSuccess: () => {
      setMutationError(null);
      invalidateLiveQueries();
    },
    onError: (error) => setMutationError(error instanceof Error ? error.message : "Evidence rejection failed."),
  });

  const addMutation = useMutation({
    mutationFn: createManualEvidence,
    onSuccess: () => {
      setMutationError(null);
      setIsAdding(false);
      setNewCategory("operations");
      setNewField("");
      setNewValue("");
      invalidateLiveQueries();
    },
    onError: (error) => setMutationError(error instanceof Error ? error.message : "Manual evidence save failed."),
  });

  const filteredEvidence = useMemo(() => {
    const lowered = deferredQuery.trim().toLowerCase();
    return rows.filter((item) => {
      const matchesQuery = !lowered
        ? true
        : [item.field, item.normalizedValue, item.rawSnippet, item.sourceDocument]
            .join(" ")
            .toLowerCase()
            .includes(lowered);
      const matchesStrength = strengthFilter === "all" ? true : item.evidenceStrength === strengthFilter;
      const matchesReview = reviewFilter === "all" ? true : item.reviewStatus === reviewFilter;
      return matchesQuery && matchesStrength && matchesReview;
    });
  }, [deferredQuery, reviewFilter, rows, strengthFilter]);

  const groupedEvidence = useMemo(() => {
    return filteredEvidence.reduce<Record<string, VaultEvidenceRecord[]>>((accumulator, item) => {
      const key = groupBy === "document" ? item.sourceDocument : item.category;
      if (!accumulator[key]) {
        accumulator[key] = [];
      }
      accumulator[key].push(item);
      return accumulator;
    }, {});
  }, [filteredEvidence, groupBy]);

  function addManualEvidence() {
    if (!activeWorkspaceId || !newField.trim() || !newValue.trim()) {
      return;
    }
    addMutation.mutate({
      workspace_id: activeWorkspaceId,
      category: newCategory.trim(),
      field_name: newField.trim(),
      normalized_value: newValue.trim(),
      source_snippet: newValue.trim(),
    });
  }

  return (
    <>
      <PageHeader
        eyebrow="Proof Vault"
        title="Evidence inventory"
        description={`${snapshot.documents.length} documents linked to ${rows.length} evidence records`}
        aside={
          <Button variant="secondary" onClick={() => setIsAdding((current) => !current)}>
            <Plus className="h-4 w-4" />
            Manually add evidence
          </Button>
        }
      />

      <Card>
        <CardContent className="space-y-3">
          <div className="grid gap-3 lg:grid-cols-[2fr_1fr_1fr_1fr]">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by field, value, snippet, or document"
            />
            <select
              value={strengthFilter}
              onChange={(event) => setStrengthFilter(event.target.value as StrengthFilter)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-accent"
            >
              <option value="all">All strengths</option>
              <option value="verified">Verified</option>
              <option value="partially_verified">Partially verified</option>
              <option value="weak_evidence">Weak evidence</option>
              <option value="missing">Missing</option>
              <option value="expired">Expired</option>
            </select>
            <select
              value={reviewFilter}
              onChange={(event) => setReviewFilter(event.target.value as "all" | EvidenceReviewState)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-accent"
            >
              <option value="all">All review states</option>
              <option value="pending_review">Pending review</option>
              <option value="approved">Approved</option>
              <option value="edited">Edited</option>
              <option value="rejected">Rejected</option>
            </select>
            <select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value as GroupBy)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-accent"
            >
              <option value="category">Group by category</option>
              <option value="document">Group by document</option>
            </select>
          </div>

          {isAdding ? (
            <div className="grid gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 md:grid-cols-[1fr_1.1fr_1.2fr_auto] md:items-end">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Category</p>
                <Input value={newCategory} onChange={(event) => setNewCategory(event.target.value)} />
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Field</p>
                <Input value={newField} onChange={(event) => setNewField(event.target.value)} placeholder="operations.training.current" />
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase text-slate-500">Normalized value</p>
                <Input value={newValue} onChange={(event) => setNewValue(event.target.value)} placeholder="Fire safety drill completed 2026-04-20" />
              </div>
              <Button onClick={addManualEvidence} disabled={addMutation.isPending}>
                {addMutation.isPending ? "Saving..." : "Save"}
              </Button>
            </div>
          ) : null}

          {mutationError ? <p className="text-sm font-semibold text-rose-700">{mutationError}</p> : null}

          <div className="flex flex-wrap gap-2 text-xs text-slate-600">
            <StatusChip status="verified" tone="success" />
            <StatusChip status="weak" tone="warning" />
            <StatusChip status="missing" tone="critical" />
            <p className="ml-1 py-1">Click any row for source-backed detail, edits, and review actions.</p>
          </div>
        </CardContent>
      </Card>

      <div className="mt-4 space-y-4">
        {!filteredEvidence.length ? (
          <EmptyState
            title="No evidence matches these filters"
            body="Try clearing one or more filters, or add evidence manually to keep momentum."
            action={{ label: "Clear filters", onClick: () => {
              setQuery("");
              setStrengthFilter("all");
              setReviewFilter("all");
            } }}
          />
        ) : null}

        {Object.entries(groupedEvidence).map(([group, items]) => (
          <Card key={group}>
            <CardContent>
              <div className="mb-3 flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">{group}</h3>
                <p className="text-xs text-slate-500">{items.length} evidence item{items.length > 1 ? "s" : ""}</p>
              </div>

              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Category</th>
                      <th className="px-3 py-2">Field</th>
                      <th className="px-3 py-2">Normalized value</th>
                      <th className="px-3 py-2">Strength</th>
                      <th className="px-3 py-2">Confidence</th>
                      <th className="px-3 py-2">Source document</th>
                      <th className="px-3 py-2">Page</th>
                      <th className="px-3 py-2">Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <motion.tr
                        key={item.id}
                        layout
                        onClick={() => setSelected(item)}
                        className="cursor-pointer border-t border-slate-200 bg-white transition hover:bg-teal-50/40"
                      >
                        <td className="px-3 py-2 text-slate-700">{item.category}</td>
                        <td className="px-3 py-2 font-medium text-slate-800">{item.field}</td>
                        <td className="max-w-[280px] truncate px-3 py-2 text-slate-700">{item.normalizedValue}</td>
                        <td className="px-3 py-2"><StrengthBadge strength={item.evidenceStrength} /></td>
                        <td className="px-3 py-2 text-slate-700">{(item.confidence * 100).toFixed(0)}%</td>
                        <td className="px-3 py-2 text-slate-700">{item.sourceDocument}</td>
                        <td className="px-3 py-2 text-slate-700">{item.pageNumber}</td>
                        <td className="px-3 py-2"><StatusChip status={item.reviewStatus} tone={reviewTone(item.reviewStatus)} /></td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <EvidenceDetailDrawer
        selected={selected}
        onClose={() => setSelected(null)}
        onApprove={(id) => approveMutation.mutate(id)}
        onReject={(id) => rejectMutation.mutate(id)}
        onSave={(id, normalizedValue) => saveMutation.mutate({ id, value: normalizedValue })}
        isSaving={saveMutation.isPending || approveMutation.isPending || rejectMutation.isPending}
        error={mutationError}
      />
    </>
  );
}
