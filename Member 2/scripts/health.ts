import { required, serverToken } from "./env";

const checks: Array<{ name: string; url: string; headers: Record<string, string> }> = [
  { name: "worker", url: `${required("WORKER_URL").replace(/\/$/, "")}/status`, headers: {} },
  { name: "control-plane", url: `${required("CONTROL_PLANE_URL").replace(/\/$/, "")}/runtime/control`, headers: { Authorization: `Bearer ${serverToken("CONTROL_PLANE_INGEST_TOKEN")}` } },
];
let failed = false;
for (const check of checks) {
  try {
    const response = await fetch(check.url, { headers: check.headers });
    console.log(`${check.name}: ${response.ok ? "healthy" : `failed (${response.status})`}`);
    failed ||= !response.ok;
  } catch (error) { failed = true; console.log(`${check.name}: unavailable (${error instanceof Error ? error.message : "unknown"})`); }
}
if (failed) process.exit(1);
