import { required, serverToken } from "./env";

const worker = required("WORKER_URL").replace(/\/$/, "");
const control = required("CONTROL_PLANE_URL").replace(/\/$/, "");
const [workerResponse, controlResponse] = await Promise.all([
  fetch(`${worker}/status`),
  fetch(`${control}/runtime/control`, { headers: { Authorization: `Bearer ${serverToken("CONTROL_PLANE_INGEST_TOKEN")}` } }),
]);
if (!workerResponse.ok || !controlResponse.ok) throw new Error(`Service check failed: worker=${workerResponse.status}, control=${controlResponse.status}`);
const state = await controlResponse.json() as { emergencyMode?: boolean; writebackMode?: string; securityScanMode?: string };
if (state.emergencyMode) throw new Error("Emergency mode is active");
console.log(JSON.stringify({ ready: true, worker: "healthy", controlPlane: "healthy", writebackMode: state.writebackMode, securityScanMode: state.securityScanMode, checkedAt: new Date().toISOString() }, null, 2));
