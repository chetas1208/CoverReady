"use client";

import { ScoreDashboardClient } from "@/components/score-dashboard-client";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";

export default function ScoreDashboardPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();

  if (isLoading) return <LoadingState title="Loading score dashboard..." />;
  if (error || !snapshot) return <ErrorState title="Couldn't load score data." onRetry={() => void refetch()} />;

  return <ScoreDashboardClient snapshot={snapshot} />;
}
