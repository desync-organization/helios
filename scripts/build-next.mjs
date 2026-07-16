import { spawn } from "node:child_process";
import {
    copyFile,
    cp,
    lstat,
    mkdtemp,
    rename,
    rm,
    stat,
    symlink,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import {
    dirname,
    isAbsolute,
    join,
    relative,
    resolve,
    sep,
} from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const nextCli = join(repositoryRoot, "node_modules", "next", "dist", "bin", "next");
const nodeExecutable = process.platform === "win32" ? "node.exe" : "node";
const staticExportEnabled = process.env.TAURI_STATIC_EXPORT === "true";
const stagedProjectFiles = [
    "components.json",
    "next-env.d.ts",
    "next.config.ts",
    "package.json",
    "postcss.config.mjs",
    "tsconfig.json",
];

class NextBuildError extends Error {
    constructor(exitCode) {
        super(`Next.js build exited with code ${exitCode}.`);
        this.exitCode = exitCode;
    }
}

async function pathExists(path) {
    try {
        await lstat(path);
        return true;
    } catch (error) {
        if (error?.code === "ENOENT") {
            return false;
        }

        throw error;
    }
}

function assertContained(parent, target) {
    const containedPath = relative(resolve(parent), resolve(target));
    if (
        containedPath === "" ||
        containedPath === ".." ||
        containedPath.startsWith(`..${sep}`) ||
        isAbsolute(containedPath)
    ) {
        throw new Error(`Refusing to remove path outside ${parent}: ${target}`);
    }
}

async function removeTree(parent, target) {
    assertContained(parent, target);
    await rm(target, { force: true, recursive: true });
}

async function requireFile(path) {
    const file = await stat(path);
    if (!file.isFile()) {
        throw new Error(`Expected build output file was not created: ${path}`);
    }
}

function runNext(cwd, args, env = process.env) {
    return new Promise((resolvePromise, rejectPromise) => {
        const child = spawn(nodeExecutable, [nextCli, ...args], {
            cwd,
            env,
            shell: false,
            stdio: "inherit",
            windowsHide: true,
        });

        child.once("error", rejectPromise);
        child.once("exit", (exitCode, signal) => {
            if (signal) {
                rejectPromise(new Error(`Next.js build terminated by signal ${signal}.`));
                return;
            }

            resolvePromise(exitCode ?? 1);
        });
    });
}

async function stageStaticProject(stageRoot) {
    const sourceRoot = join(repositoryRoot, "src");
    const apiRoot = resolve(sourceRoot, "app", "api");
    const shouldCopySource = (source) => {
        const resolvedSource = resolve(source);
        return resolvedSource !== apiRoot && !resolvedSource.startsWith(`${apiRoot}${sep}`);
    };

    await Promise.all([
        cp(sourceRoot, join(stageRoot, "src"), {
            filter: shouldCopySource,
            recursive: true,
        }),
        cp(join(repositoryRoot, "public"), join(stageRoot, "public"), {
            recursive: true,
        }),
        ...stagedProjectFiles.map((file) =>
            copyFile(join(repositoryRoot, file), join(stageRoot, file)),
        ),
    ]);

    const nodeModulesType = process.platform === "win32" ? "junction" : "dir";
    await symlink(
        join(repositoryRoot, "node_modules"),
        join(stageRoot, "node_modules"),
        nodeModulesType,
    );

    if (await pathExists(join(stageRoot, "src", "app", "api"))) {
        throw new Error("The staged Tauri project unexpectedly contains src/app/api.");
    }
}

async function publishStaticOutput(stagedOut) {
    const publishedOut = join(repositoryRoot, "out");
    const transactionRoot = await mkdtemp(join(repositoryRoot, ".tauri-publish-"));
    const candidateOut = join(transactionRoot, "candidate");
    const previousOut = join(transactionRoot, "previous");
    let previousMoved = false;
    let candidatePublished = false;

    try {
        await cp(stagedOut, candidateOut, { recursive: true });
        await Promise.all([
            requireFile(join(candidateOut, "index.html")),
            requireFile(join(candidateOut, "404.html")),
        ]);

        if (await pathExists(publishedOut)) {
            await rename(publishedOut, previousOut);
            previousMoved = true;
        }

        try {
            await rename(candidateOut, publishedOut);
            candidatePublished = true;
        } catch (error) {
            if (previousMoved) {
                await rename(previousOut, publishedOut);
                previousMoved = false;
            }

            throw error;
        }

        if (previousMoved) {
            await removeTree(transactionRoot, previousOut);
            previousMoved = false;
        }
    } finally {
        if (previousMoved && !(await pathExists(publishedOut))) {
            await rename(previousOut, publishedOut);
            previousMoved = false;
        }

        if (previousMoved && candidatePublished) {
            await removeTree(transactionRoot, previousOut);
            previousMoved = false;
        }

        await removeTree(repositoryRoot, transactionRoot);
    }
}

async function buildServer() {
    const exitCode = await runNext(repositoryRoot, ["build"]);
    if (exitCode !== 0) {
        throw new NextBuildError(exitCode);
    }
}

async function buildStaticExport() {
    const temporaryRoot = resolve(tmpdir());
    const stageRoot = await mkdtemp(join(temporaryRoot, "helios-tauri-"));

    console.log("Building a staged Tauri export without src/app/api...");

    try {
        await stageStaticProject(stageRoot);

        const exitCode = await runNext(stageRoot, ["build", "--webpack"], {
            ...process.env,
            TAURI_STATIC_EXPORT: "true",
        });
        if (exitCode !== 0) {
            throw new NextBuildError(exitCode);
        }

        const stagedOut = join(stageRoot, "out");
        await Promise.all([
            requireFile(join(stagedOut, "index.html")),
            requireFile(join(stagedOut, "404.html")),
        ]);
        await publishStaticOutput(stagedOut);
        console.log(`Published verified Tauri export to ${join(repositoryRoot, "out")}`);
    } finally {
        await removeTree(temporaryRoot, stageRoot);
    }
}

try {
    await stat(nextCli);
    if (staticExportEnabled) {
        await buildStaticExport();
    } else {
        await buildServer();
    }
} catch (error) {
    console.error(error);
    process.exitCode = error instanceof NextBuildError ? error.exitCode : 1;
}
