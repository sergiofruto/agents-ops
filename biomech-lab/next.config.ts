import path from "node:path";
import type { NextConfig } from "next";
import { contentSecurityPolicy } from "./lib/csp";

const nextConfig: NextConfig = {
  // Pin the workspace root so a stray parent lockfile can't make Turbopack
  // treat a parent folder as the project (it froze the machine once).
  turbopack: { root: path.resolve(__dirname) },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: contentSecurityPolicy(process.env.NODE_ENV === "development"),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
