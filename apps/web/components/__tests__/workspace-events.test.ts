import { describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";

import { invalidateForWorkspaceEvent } from "@/lib/use-workspace-events";

describe("workspace event invalidation", () => {
  it("invalidates snapshot and jobs for job events", () => {
    const queryClient = new QueryClient();
    const spy = vi.spyOn(queryClient, "invalidateQueries");

    invalidateForWorkspaceEvent(queryClient, "ws_1", "job.updated");

    expect(spy).toHaveBeenCalledWith({ queryKey: ["workspace", "ws_1", "snapshot"] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["workspace", "ws_1", "jobs"] });
  });
});
