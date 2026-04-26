import { cn } from "@/lib/utils";

type StatusTone = "neutral" | "success" | "warning" | "critical" | "processing";

const tones: Record<StatusTone, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-1 ring-slate-200",
  success: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200",
  warning: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
  critical: "bg-rose-50 text-rose-800 ring-1 ring-rose-200",
  processing: "bg-cyan-50 text-cyan-800 ring-1 ring-cyan-200",
};

function normalizeLabel(value: string) {
  return value.replace(/_/g, " ");
}

export function StatusChip({ status, tone = "neutral", className }: { status: string; tone?: StatusTone; className?: string }) {
  return (
    <span className={cn("inline-flex rounded-md px-2 py-1 text-xs font-semibold capitalize", tones[tone], className)}>
      {normalizeLabel(status)}
    </span>
  );
}
