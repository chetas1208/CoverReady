import * as React from "react";

import { cn } from "@/lib/utils";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-ink outline-none ring-0 placeholder:text-slate-400 focus:border-accent focus:ring-2 focus:ring-teal-100",
        props.className,
      )}
    />
  );
}
