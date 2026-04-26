"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useWorkspace } from "@/components/workspace-context";
import { updateWorkspace } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export default function SettingsPage() {
  const { activeWorkspace } = useWorkspace();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [industryCode, setIndustryCode] = useState("");
  const [state, setState] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setName(activeWorkspace?.name ?? "");
    setAddress(activeWorkspace?.address ?? "");
    setIndustryCode(activeWorkspace?.industry_code ?? "");
    setState(activeWorkspace?.state ?? "");
  }, [activeWorkspace]);

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!activeWorkspace) throw new Error("No active workspace selected.");
      return updateWorkspace(activeWorkspace.id, {
        name,
        address: address || null,
        industry_code: industryCode,
        state: state || null,
      });
    },
    onSuccess: (workspace) => {
      setMessage("Workspace saved to the live database.");
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces });
      queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(workspace.id) });
    },
    onError: (error) => setMessage(error instanceof Error ? error.message : "Workspace save failed."),
  });

  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="Workspace controls"
        description="Edit the active business profile stored in the live database."
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardContent className="space-y-3">
            <p className="text-sm font-semibold text-slate-800">Business profile</p>
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Business name" />
            <Input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="Address" />
            <Input value={industryCode} onChange={(event) => setIndustryCode(event.target.value)} placeholder="Industry code" />
            <Input value={state} onChange={(event) => setState(event.target.value)} placeholder="State" />
            <Button onClick={() => saveMutation.mutate()} disabled={!activeWorkspace || saveMutation.isPending}>
              {saveMutation.isPending ? "Saving..." : "Save workspace"}
            </Button>
            {message ? <p className="text-sm text-slate-600">{message}</p> : null}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3">
            <p className="text-sm font-semibold text-slate-800">Realtime mode</p>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              The app polls live database endpoints and listens for workspace SSE events. Redis is used only to fan out events between API and worker processes.
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
