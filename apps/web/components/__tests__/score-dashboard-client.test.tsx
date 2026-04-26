import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CoverReadySnapshot, DimensionScore } from "@coverready/contracts";

import { ScoreDashboardClient } from "@/components/score-dashboard-client";

const emptyDimension: DimensionScore = {
  score: 0,
  max_score: 20,
  reason: "No evidence yet.",
  items: [],
};

const liveSnapshot: CoverReadySnapshot = {
  workspace: {
    id: "ws_live",
    name: "Live Bistro LLC",
    address: "145 Harbor Ave",
    industry_code: "restaurant",
    state: "OR",
    origin: "live",
    created_at: "2026-04-26T00:00:00Z",
    updated_at: "2026-04-26T00:00:00Z",
  },
  scorecard: {
    id: "score_live",
    business_profile_id: "ws_live",
    total_score: 60,
    uncapped_total_score: 68,
    score_caps: [
      {
        cap_id: "cap.restaurant_fire_safety_missing",
        title: "Restaurant fire-safety proof missing",
        max_total_score: 60,
        reason: "Current fire suppression service proof",
        triggered_by_rule_ids: ["safety.suppression_service.current"],
        triggered_by_fields: [],
      },
    ],
    subscores: {
      documentation_completeness: { ...emptyDimension, max_score: 25 },
      property_safety_readiness: { ...emptyDimension, max_score: 20 },
      operational_controls: { ...emptyDimension, max_score: 20 },
      coverage_alignment: { ...emptyDimension, max_score: 20 },
      renewal_readiness: { ...emptyDimension, max_score: 15 },
    },
    top_risk_drivers: ["Restaurant fire-safety proof missing"],
    quick_wins: [
      {
        action: "Upload current fire suppression service proof",
        expected_score_impact: "Improves property safety readiness",
        effort: "low",
        reason: "Current fire suppression service proof is missing.",
      },
    ],
    missing_documents: ["Current fire suppression service proof"],
    manual_review_needed: [],
    ruleset_id: "base+restaurant",
    ruleset_version: "1.0.0",
    input_hash: "hash",
    explanation_source: "deterministic",
  },
  proof: { scorecard_id: "score_live", reasons: [], evidence_lookup: {} },
  missingDocuments: [],
  documents: [],
  evidence: [],
  claims: [],
  brokerPacket: {
    business_name: "Live Bistro LLC",
    address: "145 Harbor Ave",
    score_summary: "Insurance-readiness score 60/100.",
    top_strengths: [],
    missing_documents: ["Current fire suppression service proof"],
    next_best_actions: ["Upload current fire suppression service proof"],
    documents: [],
  },
};

describe("ScoreDashboardClient", () => {
  it("shows the top next-best action first", () => {
    render(<ScoreDashboardClient snapshot={liveSnapshot} />);
    expect(
      screen.getByRole("heading", { name: "Upload current fire suppression service proof" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Score caps")).toBeInTheDocument();
  });
});
