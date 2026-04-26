"use client";

import type { DimensionScore, ScoreReason } from "@coverready/contracts";
import { Eye } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function ScoreDimensionCard({
  label,
  dimension,
  onOpen,
}: {
  label: string;
  dimension: DimensionScore;
  onOpen: (reason: ScoreReason) => void;
}) {
  const firstClickableReason = dimension.items[0];
  const progress = Math.round((dimension.score / dimension.max_score) * 100);

  return (
    <Card className="h-full border-l-4 border-l-teal-700">
      <CardContent className="flex h-full flex-col gap-3">
        <div>
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-semibold text-slate-700">{label}</p>
            <p className="text-xl font-semibold text-ink">
              {dimension.score}
              <span className="text-sm text-slate-400">/{dimension.max_score}</span>
            </p>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-teal-700" style={{ width: `${progress}%` }} />
          </div>
        </div>
        <p className="line-clamp-3 text-sm leading-6 text-slate-600">{dimension.reason}</p>
        <Button
          className="mt-auto w-full"
          variant="secondary"
          onClick={() => firstClickableReason && onOpen(firstClickableReason)}
        >
          <Eye className="h-4 w-4" />
          {dimension.items.length} reasons
        </Button>
      </CardContent>
    </Card>
  );
}
