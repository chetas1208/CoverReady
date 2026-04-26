import type { EvidenceStrength } from "@coverready/contracts";
import { strengthToneMap } from "@coverready/ui";

import { cn } from "@/lib/utils";

function labelize(value: EvidenceStrength) {
  return value.replace(/_/g, " ");
}

export function StrengthBadge({ strength }: { strength: EvidenceStrength }) {
  return (
    <span className={cn("inline-flex rounded-md px-2 py-1 text-xs font-semibold capitalize", strengthToneMap[strength])}>
      {labelize(strength)}
    </span>
  );
}
