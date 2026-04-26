"use client";

import type { CoverReadySnapshot } from "@coverready/contracts";
import { ArrowUpRight, ShieldAlert, Sparkles, TriangleAlert } from "lucide-react";
import { useMemo } from "react";

import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/state-panels";
import { StatusChip } from "@/components/status-chip";
import { StrengthBadge } from "@/components/strength-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { buildMissingDocumentPlans } from "@/lib/live-records";

function severityTone(severity: "critical" | "important" | "recommended") {
  if (severity === "critical") return "critical" as const;
  if (severity === "important") return "warning" as const;
  return "processing" as const;
}

const severityOrder: Array<"critical" | "important" | "recommended"> = ["critical", "important", "recommended"];

export function MissingDocumentsClient({ snapshot }: { snapshot: CoverReadySnapshot }) {
  const plans = useMemo(() => buildMissingDocumentPlans(snapshot), [snapshot]);

  const grouped = useMemo(() => {
    return severityOrder.map((severity) => ({
      severity,
      items: plans.filter((item) => item.severity === severity),
    }));
  }, [plans]);

  const completed = plans.filter((item) => item.status !== "missing").length;
  const completionPercent = plans.length ? Math.round((completed / plans.length) * 100) : 0;

  return (
    <>
      <PageHeader
        eyebrow="Missing Documents"
        title="Clear action plan"
        description="Turn documentation gaps into practical next steps with score impact and acceptable proof guidance."
        aside={
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <p className="metric-label">Completion progress</p>
            <p className="mt-1 text-3xl font-semibold text-ink">{completionPercent}%</p>
            <p className="text-xs text-slate-500">{completed} of {plans.length} items underway</p>
          </div>
        }
      />

      <Card>
        <CardContent>
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 text-teal-700" />
            <div>
              <p className="text-sm font-semibold text-slate-800">Calm guidance for non-experts</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                These are the exact documents underwriters still need and why they matter. Each item includes acceptable proof options and the likely score effect.
              </p>
            </div>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-teal-500" style={{ width: `${completionPercent}%` }} />
          </div>
        </CardContent>
      </Card>

      <div className="mt-4 space-y-4">
        {!plans.length ? (
          <EmptyState
            title="No missing documents"
            body="Great job — your submission currently has no outstanding document gaps."
          />
        ) : null}

        {grouped.map((bucket) => (
          <Card key={bucket.severity}>
            <CardContent>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {bucket.severity === "critical" ? (
                    <TriangleAlert className="h-4 w-4 text-rose-700" />
                  ) : (
                    <Sparkles className="h-4 w-4 text-amber-700" />
                  )}
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-700">{bucket.severity}</p>
                </div>
                <StatusChip status={`${bucket.items.length} item${bucket.items.length === 1 ? "" : "s"}`} tone={severityTone(bucket.severity)} />
              </div>

              <div className="space-y-3">
                {bucket.items.map((item) => (
                  <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-base font-semibold text-slate-900">{item.title}</p>
                        <p className="mt-1 text-sm text-slate-500">Affects {item.scoreDimension}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusChip status={item.severity} tone={severityTone(item.severity)} />
                        <StrengthBadge strength={item.status} />
                      </div>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-3">
                      <div className="rounded-md bg-slate-50 p-3">
                        <p className="text-xs font-semibold uppercase text-slate-500">Why it matters</p>
                        <p className="mt-1 text-sm text-slate-700">{item.whyItMatters}</p>
                      </div>
                      <div className="rounded-md bg-slate-50 p-3">
                        <p className="text-xs font-semibold uppercase text-slate-500">Score impact</p>
                        <p className="mt-1 text-sm text-slate-700">{item.scoreImpact}</p>
                      </div>
                      <div className="rounded-md bg-slate-50 p-3">
                        <p className="text-xs font-semibold uppercase text-slate-500">Suggested acceptable proof</p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {item.suggestedProofTypes.map((proof) => (
                            <StatusChip key={proof} status={proof} tone="neutral" />
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-slate-500">{item.completionHint}</p>
                      <Button variant="secondary" onClick={() => window.location.assign("/uploads")}>
                        {item.uploadActionLabel}
                        <ArrowUpRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
