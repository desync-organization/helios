const commands: Array<{ name: string; command: string[]; optional?: boolean }> = [
  { name: "convex", command: ["bunx", "convex", "dev"] },
  { name: "worker", command: ["bunx", "wrangler", "dev", "--config", "infra/wrangler.toml"] },
  { name: "runtime", command: ["python", "-m", "runtime"], optional: true },
  { name: "gateway", command: ["bun", "run", "../gateway/src/index.ts"], optional: true },
];
const processes: Bun.Subprocess[] = [];
for (const entry of commands) {
  const executable = Bun.which(entry.command[0]);
  if (!executable || entry.optional && !(await Bun.file(entry.command.at(-1)!).exists()) && entry.command[0] === "bun") { console.log(`${entry.name}: not present yet; continuing with owned services`); continue; }
  console.log(`${entry.name}: starting`);
  processes.push(Bun.spawn(entry.command, { cwd: new URL("..", import.meta.url).pathname, stdin: "inherit", stdout: "inherit", stderr: "inherit", env: process.env }));
}
if (processes.length === 0) throw new Error("No services could be started");
const stop = () => { for (const process of processes) process.kill(); };
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
await Promise.race(processes.map((child) => child.exited));
stop();
