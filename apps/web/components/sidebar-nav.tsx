"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems } from "@coverready/ui";
import {
  Archive,
  BriefcaseBusiness,
  FileText,
  Gauge,
  Home,
  ListChecks,
  Languages,
  PackageCheck,
  Settings,
  Sparkles,
  Upload,
  FileWarning,
} from "lucide-react";

import { cn } from "@/lib/utils";

const icons = {
  "/overview": Home,
  "/uploads": Upload,
  "/proof-vault": Archive,
  "/score-dashboard": Gauge,
  "/missing-documents": FileWarning,
  "/coverage-translator": Languages,
  "/scenario-simulator": Sparkles,
  "/broker-packet": PackageCheck,
  "/jobs": ListChecks,
  "/settings": Settings,
  "/upload": BriefcaseBusiness,
};

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className="space-y-1">
      {navItems.map((item) => {
        const active = pathname === item.href;
        const Icon = icons[item.href as keyof typeof icons] ?? FileText;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition",
              active ? "bg-[#13201d] text-white" : "text-slate-600 hover:bg-slate-100 hover:text-ink",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
