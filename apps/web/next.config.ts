import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@coverready/contracts", "@coverready/ui"],
};

export default nextConfig;

