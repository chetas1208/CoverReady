export const strengthToneMap = {
  verified: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200",
  partially_verified: "bg-cyan-50 text-cyan-800 ring-1 ring-cyan-200",
  weak_evidence: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
  missing: "bg-slate-100 text-slate-700 ring-1 ring-slate-300",
  expired: "bg-orange-50 text-orange-800 ring-1 ring-orange-200",
  conflicting: "bg-red-50 text-red-800 ring-1 ring-red-200",
} as const;

export const navItems = [
  { href: "/overview", label: "Overview" },
  { href: "/uploads", label: "Uploads" },
  { href: "/proof-vault", label: "Proof Vault" },
  { href: "/score-dashboard", label: "Score Dashboard" },
  { href: "/missing-documents", label: "Missing Documents" },
  { href: "/coverage-translator", label: "Coverage Translator" },
  { href: "/scenario-simulator", label: "Scenario Simulator" },
  { href: "/broker-packet", label: "Broker Packet" },
  { href: "/jobs", label: "Jobs" },
  { href: "/settings", label: "Settings" },
];
