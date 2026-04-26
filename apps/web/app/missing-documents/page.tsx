"use client";

import { MissingDocumentsClient } from "@/components/missing-documents-client";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";

export default function MissingDocumentsPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();

  if (isLoading) return <LoadingState title="Loading missing documents..." />;
  if (error || !snapshot) return <ErrorState title="Couldn't load missing documents." onRetry={() => void refetch()} />;

  return <MissingDocumentsClient snapshot={snapshot} />;
}
