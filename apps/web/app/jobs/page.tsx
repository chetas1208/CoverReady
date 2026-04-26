"use client";

import { PageHeader } from "@/components/page-header";
import { StatusChip } from "@/components/status-chip";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";
import { useWorkspace } from "@/components/workspace-context";
import { getWorkspaceJobs } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { hasActiveWork } from "@/lib/live-records";
import { useQuery } from "@tanstack/react-query";

export default function JobsPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();
  const { activeWorkspaceId } = useWorkspace();
  const {
    data: jobs = [],
    isLoading: jobsLoading,
    error: jobsError,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: queryKeys.jobs(activeWorkspaceId),
    queryFn: () => getWorkspaceJobs(activeWorkspaceId as string),
    enabled: !!activeWorkspaceId,
    refetchInterval: (query) => (hasActiveWork(snapshot, query.state.data ?? []) ? 2_000 : false),
  });

  if (isLoading || jobsLoading) return <LoadingState title="Loading jobs..." />;
  if (error || jobsError || !snapshot) {
    return <ErrorState title="Couldn't load jobs data." onRetry={() => { void refetch(); void refetchJobs(); }} />;
  }
  const documentsById = new Map(snapshot.documents.map((document) => [document.id, document]));

  return (
    <>
      <PageHeader
        eyebrow="Jobs"
        title="Pipeline activity"
        description="Monitor extraction and scoring jobs with retries, stages, and runtime visibility."
      />

      <Card>
        <CardContent>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Job</th>
                  <th className="px-3 py-2">Stage</th>
                  <th className="px-3 py-2">Progress</th>
                  <th className="px-3 py-2">Retries</th>
                  <th className="px-3 py-2">Last error</th>
                  <th className="px-3 py-2">Last update</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  const document = documentsById.get(job.document_id);
                  const lastAt = job.completed_at ?? job.updated_at;
                  return (
                    <tr key={job.id} className="border-t border-slate-200 bg-white">
                      <td className="px-3 py-2 font-medium text-slate-800">extract:{document?.source_filename ?? job.document_id}</td>
                      <td className="px-3 py-2 text-slate-700">{job.stage.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2 text-slate-700">{job.progress_percent}%</td>
                      <td className="px-3 py-2 text-slate-700">{job.attempt_count} / {job.max_attempts}</td>
                      <td className="max-w-[220px] truncate px-3 py-2 text-slate-600">{job.error_message ?? "none"}</td>
                      <td className="px-3 py-2 text-slate-700">
                        {lastAt ? new Date(lastAt).toLocaleString() : "pending"}
                      </td>
                      <td className="px-3 py-2">
                        <StatusChip
                          status={job.status}
                          tone={job.status === "ready" ? "success" : job.status === "failed" ? "critical" : "processing"}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
