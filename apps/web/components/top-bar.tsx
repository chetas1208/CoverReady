"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, Building2, ChevronDown, Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/workspace-context";

export function TopBar() {
  const { workspaces, activeWorkspace, setActiveWorkspaceId, isLoading } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = workspaces.filter(
    (ws) =>
      ws.name.toLowerCase().includes(search.toLowerCase()) ||
      ws.industry_code.toLowerCase().includes(search.toLowerCase()) ||
      (ws.address ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  const displayName = isLoading ? "Loading..." : activeWorkspace?.name ?? "Select workspace";

  return (
    <div className="glass-panel sticky top-4 z-30 mb-4 rounded-lg px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setOpen(!open)}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
          >
            <Building2 className="h-4 w-4 text-teal-600" />
            <span className="max-w-[200px] truncate">{displayName}</span>
            <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
          </button>

          {open && (
            <div className="absolute left-0 top-full z-50 mt-1 w-[360px] rounded-lg border border-slate-200 bg-white shadow-xl">
              <div className="border-b border-slate-100 p-2">
                <Input
                  placeholder="Search workspaces..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="h-8 text-xs"
                  autoFocus
                />
              </div>
              <div className="max-h-[320px] overflow-y-auto p-1">
                {filtered.length === 0 && (
                  <p className="p-3 text-center text-xs text-slate-400">No workspaces found</p>
                )}
                {filtered.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setActiveWorkspaceId(ws.id);
                      setOpen(false);
                      setSearch("");
                    }}
                    className={`flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition hover:bg-slate-50 ${
                      ws.id === activeWorkspace?.id ? "bg-teal-50 ring-1 ring-teal-200" : ""
                    }`}
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#13201d] text-[10px] font-bold text-white">
                      {ws.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">{ws.name}</p>
                      <p className="truncate text-[11px] text-slate-500">
                        {ws.industry_code.replace(/_/g, " ")} · {ws.state ?? "N/A"}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
              <div className="border-t border-slate-100 px-3 py-2 text-[11px] text-slate-400">
                {workspaces.length} workspace{workspaces.length !== 1 ? "s" : ""} loaded
              </div>
            </div>
          )}
        </div>

        {activeWorkspace && (
          <span className="rounded-md bg-teal-50 px-2 py-1 text-[11px] font-semibold text-teal-700 ring-1 ring-teal-200">
            {activeWorkspace.industry_code.replace(/_/g, " ")}
          </span>
        )}

        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input placeholder="Search evidence, documents, claims..." className="pl-9" />
        </div>

        <Button variant="ghost" className="relative h-9 w-9 rounded-md p-0">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-teal-500" />
        </Button>

        <div className="ml-auto flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2 py-1.5 sm:ml-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#13201d] text-xs font-semibold text-white">
            SB
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-800">Workspace user</p>
            <p className="text-[11px] text-slate-500">Workspace admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}
