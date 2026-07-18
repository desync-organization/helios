import { existsSync } from "node:fs";
import { createConnection, createServer } from "node:net";
import { resolve } from "node:path";

const root = resolve(import.meta.dir, "..");
const runtimeRoot = resolve(root, "krishang");
const windows = process.platform === "win32";
const runtimePython = resolve(
    runtimeRoot,
    ".venv",
    windows ? "Scripts/python.exe" : "bin/python",
);
const nextCli = resolve(root, "node_modules", "next", "dist", "bin", "next");

const ollamaUrl = validateLocalUrl(
    process.env.HELIOS_OLLAMA_URL ?? "http://127.0.0.1:11434",
);
const siteModel = validateModelName(
    process.env.HELIOS_OLLAMA_SITE_MODEL ?? "llama3.2:latest",
);
const slmBaseModel = validateModelName(
    process.env.HELIOS_OLLAMA_SLM_BASE_MODEL ?? "gemma3:4b",
);
const defaultSpecialistModels = {
    "html-slm": "helios-html-slm:latest",
    "css-slm": "helios-css-slm:latest",
    "javascript-slm": "helios-javascript-slm:latest",
} as const;
const specialistModels = {
    "html-slm": validateModelName(
        process.env.HELIOS_OLLAMA_HTML_SLM_MODEL ?? defaultSpecialistModels["html-slm"],
    ),
    "css-slm": validateModelName(
        process.env.HELIOS_OLLAMA_CSS_SLM_MODEL ?? defaultSpecialistModels["css-slm"],
    ),
    "javascript-slm": validateModelName(
        process.env.HELIOS_OLLAMA_JAVASCRIPT_SLM_MODEL
            ?? defaultSpecialistModels["javascript-slm"],
    ),
} as const;
const expectedModelDigest = process.env.HELIOS_OLLAMA_SITE_DIGEST?.trim() || null;
const autoPullModel = parseBoolean(process.env.HELIOS_OLLAMA_AUTO_PULL, true);
const preferredRuntimePort = parsePort(process.env.HELIOS_API_PORT, 8788);
const preferredWebPort = parsePort(process.env.HELIOS_WEB_PORT, 3000);

type Child = ReturnType<typeof Bun.spawn>;

interface ManagedService {
    name: string;
    child: Child;
}

interface OllamaModel {
    name: string;
    digest: string;
}

interface OllamaStack {
    head: OllamaModel;
    specialists: OllamaModel[];
}

const services: ManagedService[] = [];
let stopping = false;

function parseBoolean(value: string | undefined, fallback: boolean): boolean {
    if (value === undefined || value === "") return fallback;
    if (["1", "true", "yes", "on"].includes(value.toLowerCase())) return true;
    if (["0", "false", "no", "off"].includes(value.toLowerCase())) return false;
    throw new Error(`invalid boolean value: ${value}`);
}

function parsePort(value: string | undefined, fallback: number): number {
    const port = value === undefined || value === "" ? fallback : Number(value);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new Error(`invalid TCP port: ${value}`);
    }
    return port;
}

function validateLocalUrl(value: string): string {
    const url = new URL(value);
    if (
        url.protocol !== "http:" ||
        !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
        url.username ||
        url.password ||
        url.search ||
        url.hash
    ) {
        throw new Error("HELIOS_OLLAMA_URL must be an uncredentialed localhost HTTP URL");
    }
    return url.toString().replace(/\/$/, "");
}

function validateModelName(value: string): string {
    if (!/^[A-Za-z0-9_.:/-]{1,128}$/.test(value)) {
        throw new Error(`invalid Ollama model name: ${value}`);
    }
    return value;
}

function systemEnvironment(): Record<string, string> {
    const exact = new Set([
        "COMSPEC",
        "HOME",
        "LANG",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    ]);
    const safePrefixes = ["CUDA_", "HIP_", "ROCM_"];
    return Object.fromEntries(
        Object.entries(process.env).flatMap(([name, value]) => (
            value !== undefined &&
            (exact.has(name.toUpperCase()) || safePrefixes.some((prefix) => name.startsWith(prefix)))
                ? [[name, value]]
                : []
        )),
    );
}

function selectedEnvironment(names: string[]): Record<string, string> {
    return Object.fromEntries(
        names.flatMap((name) => process.env[name] === undefined
            ? []
            : [[name, process.env[name]!]]),
    );
}

async function runCommand(
    command: string[],
    options: { cwd: string; env?: Record<string, string>; quiet?: boolean },
): Promise<void> {
    const child = Bun.spawn(command, {
        cwd: options.cwd,
        env: options.env,
        stdin: options.quiet ? "ignore" : "inherit",
        stdout: options.quiet ? "ignore" : "inherit",
        stderr: options.quiet ? "ignore" : "inherit",
    });
    const exitCode = await child.exited;
    if (exitCode !== 0) {
        throw new Error(`${command[0]} exited with code ${exitCode}`);
    }
}

async function commandSucceeds(command: string[], cwd: string): Promise<boolean> {
    try {
        await runCommand(command, { cwd, quiet: true });
        return true;
    } catch {
        return false;
    }
}

async function ensureFrontendDependencies(): Promise<void> {
    if (existsSync(nextCli)) return;
    console.log("setup: installing locked frontend dependencies");
    await runCommand([process.execPath, "install", "--frozen-lockfile"], { cwd: root });
    if (!existsSync(nextCli)) {
        throw new Error("Next.js is still unavailable after bun install");
    }
}

async function ensureRuntimeEnvironment(): Promise<string> {
    const importCheck = [runtimePython, "-c", "import fastapi, helios, httpx, uvicorn"];
    if (existsSync(runtimePython) && await commandSucceeds(importCheck, runtimeRoot)) {
        return runtimePython;
    }

    const uv = Bun.which("uv");
    if (uv) {
        console.log("setup: synchronizing the locked Helios Python environment");
        await runCommand([uv, "sync", "--project", runtimeRoot, "--frozen"], { cwd: root });
    } else {
        const python = await findPython312();
        console.log("setup: creating the Helios Python environment");
        await runCommand([...python, "-m", "venv", ".venv"], { cwd: runtimeRoot });
        await runCommand([runtimePython, "-m", "pip", "install", "-e", "."], {
            cwd: runtimeRoot,
        });
    }

    if (!existsSync(runtimePython) || !await commandSucceeds(importCheck, runtimeRoot)) {
        throw new Error("Helios Python dependencies are unavailable after setup");
    }
    return runtimePython;
}

async function findPython312(): Promise<string[]> {
    const candidates: string[][] = [
        ...(Bun.which("python") ? [[Bun.which("python")!]] : []),
        ...(Bun.which("python3") ? [[Bun.which("python3")!]] : []),
        ...(Bun.which("py") ? [[Bun.which("py")!, "-3.12"]] : []),
    ];
    for (const command of candidates) {
        if (await commandSucceeds([
            ...command,
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)",
        ], root)) {
            return command;
        }
    }
    throw new Error("Python 3.12+ or uv is required to bootstrap the Helios runtime");
}

async function isAddressAvailable(port: number, host: string): Promise<boolean> {
    return await new Promise((resolveResult) => {
        const server = createServer();
        server.unref();
        server.once("error", (error: NodeJS.ErrnoException) => {
            resolveResult(
                host === "::1" &&
                ["EAFNOSUPPORT", "EADDRNOTAVAIL"].includes(error.code ?? ""),
            );
        });
        server.listen({ host, port, exclusive: true }, () => {
            server.close(() => resolveResult(true));
        });
    });
}

async function isAddressListening(port: number, host: string): Promise<boolean> {
    return await new Promise((resolveResult) => {
        const socket = createConnection({ host, port });
        let settled = false;
        const settle = (listening: boolean) => {
            if (settled) return;
            settled = true;
            socket.destroy();
            resolveResult(listening);
        };
        socket.setTimeout(300);
        socket.once("connect", () => settle(true));
        socket.once("error", () => settle(false));
        socket.once("timeout", () => settle(false));
    });
}

async function isPortAvailable(port: number): Promise<boolean> {
    if (
        await isAddressListening(port, "127.0.0.1") ||
        await isAddressListening(port, "::1")
    ) {
        return false;
    }
    return await isAddressAvailable(port, "127.0.0.1")
        && await isAddressAvailable(port, "::1");
}

async function findAvailablePort(preferred: number): Promise<number> {
    for (let port = preferred; port < Math.min(preferred + 20, 65536); port += 1) {
        if (await isPortAvailable(port)) return port;
    }
    throw new Error(`no free local port found from ${preferred} through ${preferred + 19}`);
}

async function fetchJson(url: string, timeoutMs = 1500): Promise<unknown> {
    const response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
    if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
    return await response.json();
}

async function ollamaModels(): Promise<OllamaModel[] | null> {
    try {
        const payload = await fetchJson(`${ollamaUrl}/api/tags`);
        if (!payload || typeof payload !== "object" || !("models" in payload)) return null;
        const models = (payload as { models?: unknown }).models;
        if (!Array.isArray(models)) return null;
        return models.flatMap((item) => {
            if (!item || typeof item !== "object") return [];
            const record = item as Record<string, unknown>;
            const name = typeof record.name === "string"
                ? record.name
                : typeof record.model === "string" ? record.model : "";
            const digest = typeof record.digest === "string" ? record.digest : "";
            return name ? [{ name, digest }] : [];
        });
    } catch {
        return null;
    }
}

async function waitFor<T>(
    label: string,
    probe: () => Promise<T | null>,
    timeoutMs: number,
): Promise<T> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const value = await probe();
        if (value !== null) return value;
        await Bun.sleep(250);
    }
    throw new Error(`${label} did not become ready within ${Math.ceil(timeoutMs / 1000)} seconds`);
}

async function ensureOllama(): Promise<OllamaStack> {
    let models = await ollamaModels();
    if (models === null) {
        const ollama = Bun.which("ollama");
        if (!ollama) {
            throw new Error("Ollama is required; install it and rerun bun dev");
        }
        console.log("ollama: starting local model service");
        const child = Bun.spawn([ollama, "serve"], {
            cwd: root,
            env: {
                ...systemEnvironment(),
                ...Object.fromEntries(
                    Object.entries(process.env).filter(
                        ([name, value]) => name.startsWith("OLLAMA_") && value !== undefined,
                    ) as Array<[string, string]>,
                ),
            },
            stdin: "ignore",
            stdout: "inherit",
            stderr: "inherit",
        });
        services.push({ name: "ollama", child });
        models = await waitFor("Ollama", ollamaModels, 30_000);
    }

    const ollama = Bun.which("ollama");
    if (!ollama) throw new Error("Ollama CLI is required to provision local models");

    async function ensureInstalled(modelName: string): Promise<OllamaModel> {
        let installed = models!.find((model) => model.name === modelName);
        if (installed) return installed;
        if (!autoPullModel) {
            throw new Error(
                `Ollama model ${modelName} is missing and HELIOS_OLLAMA_AUTO_PULL is disabled`,
            );
        }
        console.log(`ollama: pulling ${modelName}`);
        await runCommand([ollama!, "pull", modelName], { cwd: root });
        models = await waitFor("Ollama model inventory", ollamaModels, 10_000);
        installed = models.find((model) => model.name === modelName);
        if (!installed) throw new Error(`Ollama did not expose model ${modelName} after pull`);
        return installed;
    }

    const head = await ensureInstalled(siteModel);
    if (expectedModelDigest && head.digest !== expectedModelDigest) {
        throw new Error(
            `Ollama model digest mismatch for ${siteModel}; expected ${expectedModelDigest}`,
        );
    }

    const roles = Object.keys(specialistModels) as Array<keyof typeof specialistModels>;
    const bundledRoles = roles.filter(
        (role) => specialistModels[role] === defaultSpecialistModels[role],
    );
    if (bundledRoles.length !== 0 && bundledRoles.length !== roles.length) {
        throw new Error(
            "configure either all bundled site SLMs or three explicit custom specialist models",
        );
    }
    if (bundledRoles.length === roles.length) {
        if (slmBaseModel !== "gemma3:4b") {
            throw new Error(
                "bundled site SLM definitions require HELIOS_OLLAMA_SLM_BASE_MODEL=gemma3:4b",
            );
        }
        await ensureInstalled(slmBaseModel);
        for (const role of roles) {
            const modelfile = resolve(runtimeRoot, "ollama", `${role}.Modelfile`);
            if (!existsSync(modelfile)) {
                throw new Error(`missing ${role} specialization: ${modelfile}`);
            }
            console.log(`ollama: provisioning ${specialistModels[role]} from ${slmBaseModel}`);
            await runCommand([
                ollama,
                "create",
                specialistModels[role],
                "-f",
                modelfile,
            ], { cwd: runtimeRoot });
        }
        models = await waitFor("Ollama specialist model inventory", ollamaModels, 10_000);
    } else {
        for (const role of roles) await ensureInstalled(specialistModels[role]);
    }

    const specialists = roles.map((role) => {
        const installed = models!.find((model) => model.name === specialistModels[role]);
        if (!installed) {
            throw new Error(`Ollama did not expose specialist model ${specialistModels[role]}`);
        }
        return installed;
    });
    if (new Set([head.name, ...specialists.map((model) => model.name)]).size !== 4) {
        throw new Error("head, HTML, CSS, and JavaScript models require distinct identities");
    }
    return { head, specialists };
}

function runtimeEnvironment(runtimePort: number, webOrigin: string): Record<string, string> {
    return {
        ...systemEnvironment(),
        ...selectedEnvironment([
            "HELIOS_LOCAL_API_TOKEN",
            "HELIOS_MAX_VRAM_MB",
            "HELIOS_MAX_PARALLEL_NODES",
            "HELIOS_FAST_LANE_TIMEOUT_S",
            "HELIOS_DEEP_LANE_TIMEOUT_S",
            "HELIOS_SECURITY_SCAN_TIMEOUT_S",
            "HELIOS_OLLAMA_SITE_DIGEST",
            "HELIOS_OLLAMA_SITE_TIMEOUT_S",
        ]),
        ENVIRONMENT: "development",
        PYTHONUNBUFFERED: "1",
        CONTROL_PLANE_URL: "",
        WORKER_URL: "",
        CONVEX_HTTP_URL: "",
        RUNTIME_BEARER_TOKEN: "",
        HELIOS_RUNTIME_TOKEN: "",
        HELIOS_INFERENCE_MODE: "deterministic",
        HELIOS_API_HOST: "127.0.0.1",
        HELIOS_API_PORT: String(runtimePort),
        HELIOS_ALLOWED_ORIGIN: webOrigin,
        HELIOS_OLLAMA_URL: ollamaUrl,
        HELIOS_OLLAMA_SITE_MODEL: siteModel,
        HELIOS_OLLAMA_SLM_BASE_MODEL: slmBaseModel,
        HELIOS_OLLAMA_HTML_SLM_MODEL: specialistModels["html-slm"],
        HELIOS_OLLAMA_CSS_SLM_MODEL: specialistModels["css-slm"],
        HELIOS_OLLAMA_JAVASCRIPT_SLM_MODEL: specialistModels["javascript-slm"],
    };
}

async function waitForSiteRuntime(runtimePort: number): Promise<void> {
    const url = `http://127.0.0.1:${runtimePort}/health/site`;
    await waitFor("Helios site runtime", async () => {
        try {
            const payload = await fetchJson(url);
            const record = payload && typeof payload === "object"
                ? payload as Record<string, unknown>
                : null;
            const roles = Array.isArray(record?.roles)
                ? record.roles as Array<Record<string, unknown>>
                : [];
            const expectedRoles = new Map<string, string>([
                ["head", siteModel],
                ["html-slm", specialistModels["html-slm"]],
                ["css-slm", specialistModels["css-slm"]],
                ["javascript-slm", specialistModels["javascript-slm"]],
            ]);
            if (
                record?.ready === true &&
                record.model === siteModel &&
                roles.length === expectedRoles.size &&
                roles.every((role) => (
                    role.ready === true &&
                    typeof role.role === "string" &&
                    role.model === expectedRoles.get(role.role)
                ))
            ) {
                return true;
            }
        } catch {
            // The runtime is still starting.
        }
        return null;
    }, 30_000);
}

async function waitForFrontend(webPort: number): Promise<void> {
    await waitFor("Next.js frontend", async () => {
        try {
            const response = await fetch(`http://127.0.0.1:${webPort}`, {
                signal: AbortSignal.timeout(120_000),
            });
            return response.status < 500 ? true : null;
        } catch {
            return null;
        }
    }, 180_000);
}

async function stopService(service: ManagedService): Promise<void> {
    if (service.child.exitCode !== null) return;
    try {
        service.child.kill();
    } catch {
        return;
    }
    const exited = await Promise.race([
        service.child.exited.then(() => true),
        Bun.sleep(3000).then(() => false),
    ]);
    if (exited) return;
    if (windows && service.child.pid) {
        const taskkill = Bun.spawn([
            "taskkill",
            "/PID",
            String(service.child.pid),
            "/T",
            "/F",
        ], { stdin: "ignore", stdout: "ignore", stderr: "ignore" });
        await taskkill.exited;
    } else {
        try {
            service.child.kill("SIGKILL");
        } catch {
            // The process exited between checks.
        }
    }
}

async function shutdown(exitCode: number): Promise<never> {
    if (stopping) {
        await new Promise<never>(() => undefined);
    }
    stopping = true;
    await Promise.all([...services].reverse().map(stopService));
    process.exit(exitCode);
}

async function main(): Promise<void> {
    console.log("Helios: preparing standalone prompt-to-site development stack");
    await ensureFrontendDependencies();
    const python = await ensureRuntimeEnvironment();
    const installedModels = await ensureOllama();
    const runtimePort = await findAvailablePort(preferredRuntimePort);
    const webPort = await findAvailablePort(preferredWebPort);
    const webOrigin = `http://127.0.0.1:${webPort}`;

    console.log(`runtime: starting on 127.0.0.1:${runtimePort}`);
    const runtime = Bun.spawn([python, "-m", "helios.main"], {
        cwd: runtimeRoot,
        env: runtimeEnvironment(runtimePort, webOrigin),
        stdin: "ignore",
        stdout: "inherit",
        stderr: "inherit",
    });
    services.push({ name: "runtime", child: runtime });
    await waitForSiteRuntime(runtimePort);

    console.log(`frontend: starting on ${webOrigin}`);
    const frontend = Bun.spawn([
        process.execPath,
        nextCli,
        "dev",
        "--hostname",
        "127.0.0.1",
        "--port",
        String(webPort),
    ], {
        cwd: root,
        env: {
            ...process.env,
            NEXT_PUBLIC_APP_URL: webOrigin,
            NEXT_PUBLIC_ORCHESTRATOR_URL: `ws://127.0.0.1:${runtimePort}/ws`,
        },
        stdin: "inherit",
        stdout: "inherit",
        stderr: "inherit",
    });
    services.push({ name: "frontend", child: frontend });
    await waitForFrontend(webPort);

    console.log("");
    console.log("Helios is ready.");
    console.log(`  App:     ${webOrigin}`);
    console.log(`  Runtime: http://127.0.0.1:${runtimePort}`);
    console.log(`  Head:    ${installedModels.head.name} (${installedModels.head.digest.slice(0, 12)})`);
    for (const specialist of installedModels.specialists) {
        console.log(`  SLM:     ${specialist.name} (${specialist.digest.slice(0, 12)})`);
    }
    console.log("  Stop:    Ctrl+C");

    const firstExit = await Promise.race(
        services.map(async (service) => ({
            name: service.name,
            code: await service.child.exited,
        })),
    );
    if (!stopping) {
        console.error(`${firstExit.name}: exited unexpectedly with code ${firstExit.code}`);
        await shutdown(firstExit.code || 1);
    }
}

process.on("SIGINT", () => void shutdown(0));
process.on("SIGTERM", () => void shutdown(0));

main().catch(async (error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    await shutdown(1);
});
