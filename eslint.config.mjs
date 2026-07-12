import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // The accepted/frozen frontend predates the React 19 set-state rule and contains
  // existing untyped WebSocket/Three.js boundaries. Keep them visible as warnings
  // without making Member 2 backend CI modify presentation-owned files.
  {
    files: [
      "src/app/page.tsx",
      "src/components/blueprint-canvas.tsx",
      "src/components/chat-page.tsx",
      "src/components/multiverse/card-stream.tsx",
      "src/components/multiverse/multiverse-scene.tsx",
      "src/components/workstation.tsx",
      "src/lib/orchestrator-store.ts",
    ],
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "Member 2/**",
  ]),
]);

export default eslintConfig;
