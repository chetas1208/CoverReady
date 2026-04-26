"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import type { WorkspaceInfo } from "@/lib/api";
import { getWorkspaces } from "@/lib/api";

interface WorkspaceContextValue {
  workspaces: WorkspaceInfo[];
  activeWorkspaceId: string | null;
  activeWorkspace: WorkspaceInfo | null;
  setActiveWorkspaceId: (id: string) => void;
  isLoading: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextValue>({
  workspaces: [],
  activeWorkspaceId: null,
  activeWorkspace: null,
  setActiveWorkspaceId: () => {},
  isLoading: true,
});

export function useWorkspace() {
  return useContext(WorkspaceContext);
}

const STORAGE_KEY = "coverready_active_workspace";

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getWorkspaces()
      .then((ws) => {
        if (cancelled) return;
        setWorkspaces(ws);
        const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
        const validStored = stored && ws.some((w) => w.id === stored);
        setActiveWorkspaceId(validStored ? stored : ws[0]?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setWorkspaces([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const handleSetActive = (id: string) => {
    setActiveWorkspaceId(id);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, id);
    }
  };

  const activeWorkspace = workspaces.find((ws) => ws.id === activeWorkspaceId) ?? null;

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        activeWorkspaceId,
        activeWorkspace,
        setActiveWorkspaceId: handleSetActive,
        isLoading,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}
