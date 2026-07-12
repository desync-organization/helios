import { existsSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dir, "..", "..");
const member2 = resolve(root, "Member 2");
const runtimeRoot = resolve(root, "krishang");
const gatewayRoot = resolve(root, "member 3");
const windows = process.platform === "win32";
const runtimePython = resolve(runtimeRoot, ".venv", windows ? "Scripts/python.exe" : "bin/python");
const gatewayPython = resolve(gatewayRoot, ".venv", windows ? "Scripts/python.exe" : "bin/python");

interface Service {
  name: string;
  command: string[];
  cwd: string;
  env?: Record<string, string>;
  required: boolean;
}

const services: Service[] = [
  { name: "convex", command: ["bunx", "convex", "dev"], cwd: member2, required: true },
  { name: "worker", command: ["bunx", "wrangler", "dev", "--config", "infra/wrangler.toml"], cwd: member2, required: true },
  {
    name: "runtime",
    command: [runtimePython, "-m", "helios.main"],
    cwd: runtimeRoot,
    required: false,
    env: {
      CONVEX_HTTP_URL: process.env.WORKER_URL ?? "http://127.0.0.1:8787",
      HELIOS_RUNTIME_TOKEN: process.env.RUNTIME_BEARER_TOKEN ?? "",
    },
  },
  {
    name: "gateway",
    command: [gatewayPython, "-m", "hermes_gateway"],
    cwd: gatewayRoot,
    required: false,
    env: {
      HERMES_CONTROL_PLANE_URL: process.env.CONTROL_PLANE_URL ?? "http://127.0.0.1:3210",
      HERMES_GATEWAY_UPSTREAM_TOKEN: process.env.GATEWAY_BEARER_TOKEN ?? "",
    },
  },
];

const processes: Bun.Subprocess[] = [];
for (const service of services) {
  const executable = service.command[0];
  if (!Bun.which(executable) && !existsSync(executable)) {
    if (service.required) throw new Error(`${service.name}: missing executable ${executable}`);
    console.log(`${service.name}: environment not installed; continuing without it`);
    continue;
  }
  console.log(`${service.name}: starting`);
  processes.push(Bun.spawn(service.command, {
    cwd: service.cwd,
    stdin: "inherit",
    stdout: "inherit",
    stderr: "inherit",
    env: { ...process.env, ...service.env },
  }));
}

if (processes.length < 2) throw new Error("Convex and Worker services are required");
const stop = () => { for (const process of processes) process.kill(); };
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
await Promise.race(processes.map((child) => child.exited));
stop();
