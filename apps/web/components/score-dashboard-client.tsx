"use client";

import type { CoverReadySnapshot, ScoreReason } from "@coverready/contracts";
import { AlertTriangle, ArrowRight, CheckCircle2, FileWarning, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ProofDrawer } from "@/components/proof-drawer";
import { ScoreDimensionCard } from "@/components/score-dimension-card";
import { Card, CardContent } from "@/components/ui/card";

const dimensionLabels = {
  documentation_completeness: "Documentation",
  property_safety_readiness: "Property Safety",
  operational_controls: "Operational Controls",
  coverage_alignment: "Coverage Alignment",
  renewal_readiness: "Renewal Readiness",
} as const;

const dimensionOrder = [
  "documentation_completeness",
  "property_safety_readiness",
  "operational_controls",
  "coverage_alignment",
  "renewal_readiness",
] as const;

export function ScoreDashboardClient({ snapshot }: { snapshot: CoverReadySnapshot }) {
  const [selectedReason, setSelectedReason] = useState<ScoreReason | null>(null);
  const { scorecard } = snapshot;
  const verifiedCount = snapshot.evidence.filter((item) => item.evidence_strength === "verified").length;
  const reviewCount = snapshot.missingDocuments.length + scorecard.manual_review_needed.length;

  return (
    <>
      <PageHeader
        eyebrow="Score Dashboard"
        title={`${snapshot.workspace.name} readiness`}
        description={`${snapshot.documents.length} documents, ${snapshot.evidence.length} evidence items, ${verifiedCount} verified proofs`}
        aside={
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <p className="metric-label">Readiness</p>
            <p className="mt-1 text-3xl font-semibold text-ink">{scorecard.total_score}/100</p>
          </div>
        }
      />

      <div className="grid gap-3 lg:grid-cols-[0.85fr_1.15fr_1fr]">
        <Card className="bg-[#13201d] text-white">
          <CardContent>
            <p className="text-sm font-semibold text-teal-100">Current score</p>
            <div className="mt-3 flex items-end justify-between gap-3">
              <p className="text-6xl font-semibold leading-none">{scorecard.total_score}</p>
              <div className="text-right text-sm text-teal-100">
                <p>Uncapped {scorecard.uncapped_total_score}</p>
                <p>{reviewCount} items to review</p>
              </div>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full rounded-full bg-teal-300" style={{ width: `${scorecard.total_score}%` }} />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-teal-700">
          <CardContent>
            <div className="flex items-start gap-3">
              <div className="rounded-md bg-teal-50 p-2 text-teal-800 ring-1 ring-teal-100">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="metric-label">Next action</p>
                <h3 className="mt-1 text-xl font-semibold leading-7 text-ink">{scorecard.quick_wins[0]?.action}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{scorecard.quick_wins[0]?.reason}</p>
                <p className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-teal-800">
                  {scorecard.quick_wins[0]?.expected_score_impact}
                  <ArrowRight className="h-4 w-4" />
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-600" />
                <p className="font-semibold text-slate-800">Score caps</p>
              </div>
              <span className="rounded-md bg-orange-50 px-2 py-1 text-xs font-semibold text-orange-800 ring-1 ring-orange-200">
                {scorecard.score_caps.length} active
              </span>
            </div>
            {scorecard.score_caps.map((cap) => (
              <div key={cap.cap_id} className="rounded-md border border-orange-200 bg-orange-50 px-3 py-2">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-orange-950">{cap.title}</p>
                  <span className="shrink-0 text-sm font-semibold text-orange-800">{cap.max_total_score}</span>
                </div>
                <p className="mt-1 text-xs leading-5 text-orange-800">{cap.reason}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-5">
        {dimensionOrder.map((key) => (
          <ScoreDimensionCard
            key={key}
            label={dimensionLabels[key as keyof typeof dimensionLabels]}
            dimension={scorecard.subscores[key]}
            onOpen={setSelectedReason}
          />
        ))}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              <FileWarning className="h-4 w-4 text-red-700" />
              <p className="font-semibold text-slate-800">Risk drivers</p>
            </div>
            <div className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200">
              {scorecard.top_risk_drivers.map((item) => (
                <div key={item} className="px-3 py-2.5 text-sm text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-600" />
              <p className="font-semibold text-slate-800">Manual review</p>
            </div>
            <div className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200">
              {scorecard.manual_review_needed.map((item) => (
                <div key={item} className="px-3 py-2.5 text-sm text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-700" />
              <p className="font-semibold text-slate-800">Quick wins</p>
            </div>
            <div className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200">
              {scorecard.quick_wins.map((item) => (
                <div key={item.action} className="px-3 py-2.5">
                  <p className="text-sm font-semibold text-slate-800">{item.action}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{item.expected_score_impact}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <ProofDrawer selectedReason={selectedReason} proof={snapshot.proof} onClose={() => setSelectedReason(null)} />
    </>
  );
}
