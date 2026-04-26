export const queryKeys = {
  workspaces: ["workspaces"] as const,
  snapshot: (workspaceId: string | null | undefined) => ["workspace", workspaceId, "snapshot"] as const,
  jobs: (workspaceId: string | null | undefined) => ["workspace", workspaceId, "jobs"] as const,
  documentStatus: (documentId: string | null | undefined) => ["document", documentId, "status"] as const,
};
