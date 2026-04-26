"use client";

import { useEffect, useState } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";

import { API_BASE } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

const eventTypes = [
  "job.created",
  "job.updated",
  "document.updated",
  "evidence.created",
  "evidence.updated",
  "evidence.reviewed",
  "score.updated",
  "packet.updated",
] as const;

export type WorkspaceEventType = (typeof eventTypes)[number];

export function invalidateForWorkspaceEvent(queryClient: QueryClient, workspaceId: string, eventType: string) {
  queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(workspaceId) });
  if (eventType.startsWith("job.")) {
    queryClient.invalidateQueries({ queryKey: queryKeys.jobs(workspaceId) });
  }
  if (eventType === "document.updated" || eventType.startsWith("evidence.") || eventType === "score.updated" || eventType === "packet.updated") {
    queryClient.invalidateQueries({ queryKey: queryKeys.jobs(workspaceId) });
  }
}

export function useWorkspaceEvents(workspaceId: string | null | undefined) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!workspaceId || typeof window === "undefined" || !("EventSource" in window)) {
      setConnected(false);
      return;
    }

    const source = new EventSource(`${API_BASE}/workspaces/${workspaceId}/events`);
    const handleMessage = (event: Event) => {
      const typed = event as MessageEvent;
      invalidateForWorkspaceEvent(queryClient, workspaceId, typed.type);
    };

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    for (const eventType of eventTypes) {
      source.addEventListener(eventType, handleMessage);
    }

    return () => {
      for (const eventType of eventTypes) {
        source.removeEventListener(eventType, handleMessage);
      }
      source.close();
      setConnected(false);
    };
  }, [queryClient, workspaceId]);

  return { connected };
}
