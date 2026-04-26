"use client";

import { useState } from "react";
import { Languages } from "lucide-react";
import type { TranslatorResult } from "@coverready/contracts";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { translateClauseText } from "@/lib/api";
import { useWorkspace } from "@/components/workspace-context";

export function CoverageTranslatorClient() {
  const { activeWorkspaceId } = useWorkspace();
  const [clauseText, setClauseText] = useState(
    "This endorsement applies if deep fat frying operations are conducted after 10:00 PM unless an approved automatic suppression system is serviced and maintained.",
  );
  const [result, setResult] = useState<TranslatorResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function explain() {
    if (!activeWorkspaceId) return;
    setIsPending(true);
    setError(null);
    try {
      setResult(await translateClauseText(clauseText, activeWorkspaceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Translator request failed.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Coverage Translator"
        title="Policy language review"
        description="Plain-English reading list for clauses, endorsements, and conditions."
      />

      <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardContent className="space-y-4">
            <Textarea value={clauseText} onChange={(event) => setClauseText(event.target.value)} />
            <Button
              onClick={() => void explain()}
              disabled={!activeWorkspaceId || isPending}
            >
              <Languages className="h-4 w-4" />
              {isPending ? "Explaining..." : "Explain clause"}
            </Button>
            {error ? <p className="text-sm font-semibold text-rose-700">{error}</p> : null}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            {result ? (
              <>
                <div>
                  <p className="text-sm font-semibold text-slate-700">Plain-English summary</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{result.plain_english_summary}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-700">Why it matters</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{result.why_it_matters}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-700">Questions to verify</p>
                  <div className="mt-2 space-y-2">
                    {result.questions_to_verify.map((question) => (
                      <div key={question} className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">
                        {question}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
                Submit policy text to create a live translator run for this workspace.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
