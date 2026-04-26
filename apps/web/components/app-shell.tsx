"use client";

import type { ReactNode } from "react";
import { CircleCheck, Database, Server } from "lucide-react";

import { SidebarNav } from "@/components/sidebar-nav";
import { TopBar } from "@/components/top-bar";
import { useWorkspace } from "@/components/workspace-context";
import { useWorkspaceEvents } from "@/lib/use-workspace-events";

export function AppShell({ children }: { children: ReactNode }) {
  const { workspaces, activeWorkspace } = useWorkspace();
  const { connected } = useWorkspaceEvents(activeWorkspace?.id);

  return (
    <div className="mx-auto flex min-h-screen max-w-[1600px] gap-4 px-4 py-4 md:px-5">
      <aside className="glass-panel sticky top-4 hidden h-[calc(100vh-2rem)] w-64 shrink-0 rounded-lg p-4 lg:block">
        <div className="mb-5 border-b border-slate-200 pb-4">
          <p className="text-xl font-semibold text-ink">CoverReady</p>
          <p className="mt-1 text-xs text-slate-500">Underwriting readiness</p>
        </div>
        <SidebarNav />
        <div className="mt-5 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <CircleCheck className="h-4 w-4 text-emerald-600" />
            <span>{workspaces.length} workspaces loaded</span>
          </div>
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-cyan-700" />
            <span>SQLite evidence vault</span>
          </div>
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-emerald-600" />
            <span>{connected ? "Realtime stream connected" : "Polling live database"}</span>
          </div>
          {activeWorkspace && (
            <div className="mt-2 border-t border-slate-200 pt-2 text-[11px] text-slate-500">
              Active: {activeWorkspace.name}
            </div>
          )}
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <div className="glass-panel rounded-lg p-3 lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-xl font-semibold text-ink">CoverReady</h1>
            <span className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-200">
              Live
            </span>
          </div>
          <div className="mt-3">
            <SidebarNav />
          </div>
        </div>
        <div className="mt-4 lg:mt-0">
          <TopBar />
          {children}
        </div>
      </main>
    </div>
  );
}
