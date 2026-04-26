"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import type { ScenarioSimulation } from "@coverready/contracts";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { simulateScenarioChange } from "@/lib/api";
import { useWorkspace } from "@/components/workspace-context";

export function ScenarioSimulatorClient() {
  const { activeWorkspaceId } = useWorkspace();
  const [scenario, setScenario] = useState("Upload current fire suppression service proof");
  const [result, setResult] = useState<ScenarioSimulation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function simulate() {
    if (!activeWorkspaceId) return;
    setIsPending(true);
    setError(null);
    try {
      setResult(await simulateScenarioChange(scenario, activeWorkspaceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scenario request failed.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Scenario Simulator"
        title="Improvement simulator"
        description="Estimate how a documentation change affects readiness and underwriting clarity."
      />

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardContent className="space-y-4">
            <Input value={scenario} onChange={(event) => setScenario(event.target.value)} />
            <Button
              onClick={() => void simulate()}
              disabled={!activeWorkspaceId || isPending}
            >
              <Sparkles className="h-4 w-4" />
              {isPending ? "Simulating..." : "Simulate change"}
            </Button>
            {error ? <p className="text-sm font-semibold text-rose-700">{error}</p> : null}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-4">
            {result ? (
              <>
                <div className="rounded-lg bg-[#13201d] px-4 py-3 text-sm font-semibold uppercase text-white">
                  Likely direction: {result.likely_score_direction}
                </div>
                <p className="text-sm leading-6 text-slate-600">{result.estimated_impact_summary}</p>
                <div>
                  <p className="text-sm font-semibold text-slate-700">Why</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{result.why}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-700">Still needed</p>
                  <div className="mt-2 space-y-2">
                    {result.still_needed.map((item) => (
                      <div key={item} className="rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
                Run a live scenario for the active workspace to see impact guidance.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
