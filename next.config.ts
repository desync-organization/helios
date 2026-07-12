import type { NextConfig } from "next";

const useStaticExport = process.env.TAURI_STATIC_EXPORT === "true";

const nextConfig: NextConfig = {
  // API routes require a server build. Enable static output explicitly for a
  // Tauri packaging workflow that does not need these routes.
  ...(useStaticExport ? { output: "export" } : {}),

  // Silence turbopack "multiple lockfiles" warning
  turbopack: {
    root: __dirname,
  },

  // For Tauri: Disable Node.js image optimization
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
