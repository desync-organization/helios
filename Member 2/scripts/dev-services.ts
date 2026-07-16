import { existsSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dir, "..", "..");
const member2 = resolve(root, "Member 2");
const runtimeRoot = resolve(root, "krishang");
const gatewayRoot = resolve(root, "member 3");
const windows = process.platform === "win32";
const runtimePython = resolve(runtimeRoot, ".venv", windows ? "Scripts/python.exe" : "bin/python");
const gatewayPython = resolve(gatewayRoot, ".venv", windows ? "Scripts/python.exe" : "bin/python");
const gatewayCommand = existsSync(gatewayPython)
    ? [gatewayPython, "-m", "hermes_gateway"]
    : ["uv", "run", "--project", gatewayRoot, "python", "-m", "hermes_gateway"];
const environmentFile = resolve(root, ".env");
const localWorkerUrl = process.env.HELIOS_DEV_WORKER_URL ?? "http://127.0.0.1:8787";
const controlPlaneUrl = process.env.CONTROL_PLANE_URL ?? "http://127.0.0.1:3210";
const usesRemoteControlPlane = /^https:\/\//i.test(controlPlaneUrl);
const demoRepository = process.env.DEMO_REPOSITORY ?? "";
const defaultRepositoryUrl = process.env.HERMES_DEFAULT_REPOSITORY_URL ?? (
    /^[A-Za-z0-9_.-]{1,100}\/[A-Za-z0-9_.-]{1,100}$/.test(demoRepository)
        ? `https://github.com/${demoRepository}`
        : ""
);

if (!existsSync(environmentFile)) {
    throw new Error(".env is required at the repository root; copy .env.example and supply rotated secrets");
}

interface Service {
    name: string;
    command: string[];
    cwd: string;
    env?: Record<string, string>;
    inheritEnvironment?: boolean;
    required: boolean;
}

function hostEnvironment(): Record<string, string> {
    const allowed = [
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
    ];
    return Object.fromEntries(
        allowed.flatMap((name) => (process.env[name] ? [[name, process.env[name]!]] : [])),
    );
}

function selectedEnvironment(prefixes: string[], names: string[]): Record<string, string> {
    return Object.fromEntries(
        Object.entries(process.env).filter(
            ([name, value]) =>
                value !== undefined &&
                (names.includes(name) || prefixes.some((prefix) => name.startsWith(prefix))),
        ) as Array<[string, string]>,
    );
}

const services: Service[] = [
    ...(!usesRemoteControlPlane ? [{
        name: "convex",
        command: ["bunx", "convex", "dev"],
        cwd: member2,
        required: true,
        env: selectedEnvironment(["CONVEX_"], [
            "ENVIRONMENT",
            "CONTROL_PLANE_INGEST_TOKEN",
            "RUNTIME_BEARER_TOKEN",
            "GATEWAY_BEARER_TOKEN",
        ]),
    } satisfies Service] : []),
    {
        name: "worker",
        command: [
            "bunx",
            "wrangler",
            "dev",
            "--config",
            "infra/wrangler.toml",
            "--env-file",
            environmentFile,
        ],
        cwd: member2,
        inheritEnvironment: true,
        required: true,
    },
    {
        name: "runtime",
        command: [runtimePython, "-m", "helios.main"],
        cwd: runtimeRoot,
        required: true,
        env: {
            ...selectedEnvironment(
                ["HELIOS_", "LLAMA_", "GEMMA_"],
                ["ENVIRONMENT", "WORKER_URL", "CONTROL_PLANE_URL", "RUNTIME_BEARER_TOKEN"],
            ),
            WORKER_URL: localWorkerUrl,
            CONVEX_HTTP_URL: localWorkerUrl,
            HELIOS_RUNTIME_TOKEN: process.env.RUNTIME_BEARER_TOKEN ?? "",
        },
    },
    {
        name: "gateway",
        command: gatewayCommand,
        cwd: gatewayRoot,
        required: true,
        env: {
            ...selectedEnvironment(["HERMES_"], ["ENVIRONMENT"]),
            HERMES_CONTROL_PLANE_URL: controlPlaneUrl,
            HERMES_GATEWAY_UPSTREAM_TOKEN: process.env.GATEWAY_BEARER_TOKEN ?? "",
            HERMES_ALLOWED_ORIGIN:
                process.env.HELIOS_ALLOWED_ORIGIN ??
                process.env.APP_URL ??
                "http://127.0.0.1:3000",
            ...(defaultRepositoryUrl ? { HERMES_DEFAULT_REPOSITORY_URL: defaultRepositoryUrl } : {}),
        },
    },
];

const processes: Bun.Subprocess[] = [];
for (const service of services) {
    const executable = service.command[0];
    if (!Bun.which(executable) && !existsSync(executable)) {
        if (service.required) {
            throw new Error(`${service.name}: missing executable ${executable}`);
        }
        console.log(`${service.name}: environment not installed; continuing without it`);
        continue;
    }
    console.log(`${service.name}: starting`);
    processes.push(
        Bun.spawn(service.command, {
            cwd: service.cwd,
            stdin: "inherit",
            stdout: "inherit",
            stderr: "inherit",
            env: service.inheritEnvironment
                ? { ...process.env, ...service.env }
                : { ...hostEnvironment(), ...service.env },
        }),
    );
}

if (processes.length === 0) {
    throw new Error("No configured development service could be started");
}

const stop = () => {
    for (const process of processes) {
        process.kill();
    }
};
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
await Promise.race(processes.map((child) => child.exited));
stop();
