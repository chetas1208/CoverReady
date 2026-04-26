import * as React from "react";

import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
}

export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-9 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed",
        variant === "primary" &&
          "bg-accent text-white shadow-sm hover:bg-[#086b63] disabled:bg-slate-300",
        variant === "secondary" &&
          "border border-slate-300 bg-white text-ink hover:border-slate-400 hover:bg-slate-50",
        variant === "ghost" && "text-ink hover:bg-slate-100",
        className,
      )}
      {...props}
    />
  );
}
