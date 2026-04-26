"use client";

import { useQuery } from "@tanstack/react-query";
import type { CoverReadySnapshot } from "@coverready/contracts";
import { getCoverReadySnapshot } from "@/lib/api";
import { useWorkspace } from "@/components/workspace-context";
import { hasActiveWork } from "@/lib/live-records";
import { queryKeys } from "@/lib/query-keys";

/** Hook to fetch the CoverReady snapshot for the currently active workspace. */
export function useSnapshot() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspace();

  const { data, isLoading, error, refetch } = useQuery<CoverReadySnapshot>({
    queryKey: queryKeys.snapshot(activeWorkspaceId),
    queryFn: () => getCoverReadySnapshot(activeWorkspaceId as string),
    enabled: !wsLoading && !!activeWorkspaceId,
    refetchInterval: (query) => (hasActiveWork(query.state.data) ? 2_000 : 15_000),
    staleTime: 15_000,
  });

  return {
    snapshot: data ?? null,
    isLoading: wsLoading || isLoading,
    error,
    refetch,
  };
}
