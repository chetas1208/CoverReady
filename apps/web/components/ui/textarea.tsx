import * as React from "react";

import { cn } from "@/lib/utils";

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(
        "min-h-32 w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-ink outline-none placeholder:text-slate-400 focus:border-accent focus:ring-2 focus:ring-teal-100",
        props.className,
      )}
    />
  );
}
