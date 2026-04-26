"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";
import { generateBrokerPacket } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export default function BrokerPacketPreviewPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();
  const queryClient = useQueryClient();
  const packetMutation = useMutation({
    mutationFn: () => generateBrokerPacket(snapshot?.workspace.id ?? ""),
    onSuccess: () => {
      if (snapshot) queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(snapshot.workspace.id) });
    },
  });

  if (isLoading) return <LoadingState title="Loading broker packet..." />;
  if (error || !snapshot) return <ErrorState title="Couldn't load broker packet." onRetry={() => void refetch()} />;

  const packet = snapshot.brokerPacket;

  return (
    <>
      <PageHeader
        eyebrow="Broker Packet Preview"
        title="Broker packet"
        description={`${packet.business_name} - ${packet.score_summary}`}
        aside={
          <Button onClick={() => packetMutation.mutate()} disabled={packetMutation.isPending}>
            <RefreshCcw className={`h-4 w-4 ${packetMutation.isPending ? "animate-spin" : ""}`} />
            Refresh packet
          </Button>
        }
      />

      <Card>
        <CardContent className="space-y-5">
          <div>
            <p className="section-eyebrow">Business</p>
            <h3 className="mt-2 text-3xl font-semibold text-ink">{packet.business_name}</h3>
            <p className="mt-1 text-sm text-slate-600">{packet.address}</p>
          </div>

          <div className="rounded-lg bg-[#13201d] p-4 text-white">
            <p className="text-sm uppercase text-slate-300">Score summary</p>
            <p className="mt-2 text-lg">{packet.score_summary}</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold text-slate-700">Top strengths</p>
              <div className="mt-3 space-y-2">
                {packet.top_strengths.map((item) => (
                  <div key={item} className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold text-slate-700">Missing documents</p>
              <div className="mt-3 space-y-2">
                {packet.missing_documents.map((item) => (
                  <div key={item} className="rounded-lg bg-orange-50 px-4 py-3 text-sm text-orange-900">
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-sm font-semibold text-slate-700">Next best actions</p>
              <div className="mt-3 space-y-2">
                {packet.next_best_actions.map((item) => (
                  <div key={item} className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
