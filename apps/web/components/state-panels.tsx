import { AlertTriangle, FilePlus2, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function LoadingState({ title = "Loading workspace evidence..." }: { title?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
      <LoaderCircle className="h-5 w-5 animate-spin text-teal-700" />
      <p className="text-sm font-medium">{title}</p>
    </div>
  );
}

export function ErrorState({ title = "We couldn’t load this section.", onRetry }: { title?: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-6">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 text-rose-700" />
        <div>
          <p className="text-sm font-semibold text-rose-900">{title}</p>
          <p className="mt-1 text-sm text-rose-700">Retry to refresh from the live database.</p>
          {onRetry ? (
            <Button onClick={onRetry} variant="secondary" className="mt-3 border-rose-300 bg-white text-rose-800 hover:bg-rose-100">
              Retry
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <FilePlus2 className="mx-auto h-7 w-7 text-slate-400" />
      <h3 className="mt-3 text-base font-semibold text-slate-800">{title}</h3>
      <p className="mx-auto mt-1 max-w-xl text-sm leading-6 text-slate-600">{body}</p>
      {action ? (
        <Button onClick={action.onClick} variant="secondary" className="mt-4">
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
