"use client";

import { AlertTriangle, ArrowRight, FileWarning, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StrengthBadge } from "@/components/strength-badge";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";

export default function OverviewPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();

  if (isLoading) return <LoadingState title="Loading workspace data..." />;
  if (error || !snapshot) return <ErrorState title="Couldn't load workspace data." onRetry={() => void refetch()} />;

  const score = snapshot.scorecard;
  const recentUploads = [...snapshot.documents].slice(0, 4);
  const evidenceNeedingReview = snapshot.evidence.filter((item) => item.evidence_strength !== "verified").slice(0, 4);

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title={`${snapshot.workspace.name} workspace`}
        description="Understand readiness at a glance: what is strong, what is missing, and what to do next."
      />

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="bg-[#13201d] text-white">
          <CardContent>
            <p className="text-sm font-semibold text-teal-100">Readiness score</p>
            <div className="mt-3 flex items-end justify-between">
              <p className="text-6xl font-semibold leading-none">{score.total_score}</p>
              <div className="text-right text-sm text-teal-100">
                <p>Updated {new Date(snapshot.workspace.updated_at).toLocaleDateString()}</p>
                <p>{snapshot.documents.length} documents · {snapshot.evidence.length} evidence</p>
              </div>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full rounded-full bg-teal-300" style={{ width: `${score.total_score}%` }} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-teal-700" />
              <p className="font-semibold text-slate-800">Quick wins</p>
            </div>
            <div className="mt-3 space-y-2">
              {score.quick_wins.map((win) => (
                <div key={win.action} className="rounded-md border border-slate-200 bg-white p-3">
                  <p className="text-sm font-semibold text-slate-800">{win.action}</p>
                  <p className="mt-1 text-xs text-slate-500">{win.expected_score_impact}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-600" />
              <p className="font-semibold text-slate-800">Top blockers</p>
            </div>
            <div className="mt-3 space-y-2">
              {score.top_risk_drivers.map((driver) => (
                <div key={driver} className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-900">
                  {driver}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <div className="flex items-center gap-2">
              <FileWarning className="h-4 w-4 text-rose-700" />
              <p className="font-semibold text-slate-800">Missing critical documents</p>
            </div>
            <div className="mt-3 space-y-2">
              {snapshot.missingDocuments.slice(0, 3).map((item) => (
                <div key={item.rule_id} className="rounded-md border border-slate-200 p-3 text-sm">
                  <p className="font-semibold text-slate-800">{item.label}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.dimension.replace(/_/g, " ")}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <p className="font-semibold text-slate-800">Broker packet status</p>
            <p className="mt-2 text-sm text-slate-600">{snapshot.brokerPacket.score_summary}</p>
            <p className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-teal-800">
              Ready for review with missing items highlighted
              <ArrowRight className="h-4 w-4" />
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardContent>
            <p className="font-semibold text-slate-800">Recent uploads</p>
            <div className="mt-3 space-y-2">
              {recentUploads.map((document) => (
                <div key={document.id} className="flex items-center justify-between rounded-md border border-slate-200 p-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{document.source_filename}</p>
                    <p className="text-xs text-slate-500">{document.document_type.replace(/_/g, " ")}</p>
                  </div>
                  <span className="text-xs text-slate-500">{new Date(document.created_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <p className="font-semibold text-slate-800">Evidence needing review</p>
            <div className="mt-3 space-y-2">
              {evidenceNeedingReview.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-md border border-slate-200 p-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{item.field}</p>
                    <p className="text-xs text-slate-500">{item.value}</p>
                  </div>
                  <StrengthBadge strength={item.evidence_strength} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
