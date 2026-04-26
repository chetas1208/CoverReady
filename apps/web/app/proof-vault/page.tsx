"use client";

import { ProofVaultClient } from "@/components/proof-vault-client";
import { LoadingState, ErrorState } from "@/components/state-panels";
import { useSnapshot } from "@/lib/use-snapshot";

export default function ProofVaultPage() {
  const { snapshot, isLoading, error, refetch } = useSnapshot();

  if (isLoading) return <LoadingState title="Loading proof vault..." />;
  if (error || !snapshot) return <ErrorState title="Couldn't load proof vault data." onRetry={() => void refetch()} />;

  return <ProofVaultClient snapshot={snapshot} />;
}
