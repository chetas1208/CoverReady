"use client";

import { UploadIntakeClient } from "@/components/upload-intake-client";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";

export default function UploadsPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();

  if (isLoading) return <LoadingState title="Loading uploads..." />;
  if (error || !snapshot) return <ErrorState title="Couldn't load upload data." onRetry={() => void refetch()} />;

  return <UploadIntakeClient snapshot={snapshot} />;
}
