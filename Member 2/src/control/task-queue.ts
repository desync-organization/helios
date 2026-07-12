import { newId } from "../../packages/contracts/src/ids";
import { Task, type Lease, type Task as TaskValue } from "../../packages/contracts/src/task";
import { ControlPlaneError } from "../errors";

export interface ClaimResult {
  task: TaskValue;
  lease: Lease;
}

export class TaskQueue {
  private readonly tasks = new Map<string, TaskValue>();
  private readonly dedupe = new Map<string, string>();

  enqueue(task: TaskValue): { task: TaskValue; duplicate: boolean } {
    const parsed = Task.parse(task);
    const repositoryKey = `${parsed.repo}:${parsed.dedupeKey}`;
    const existingId = this.dedupe.get(repositoryKey);
    if (existingId) return { task: structuredClone(this.tasks.get(existingId)!), duplicate: true };
    this.tasks.set(parsed.taskId, structuredClone(parsed));
    this.dedupe.set(repositoryKey, parsed.taskId);
    return { task: structuredClone(parsed), duplicate: false };
  }

  claim(ownerId: string, leaseMs: number, now = Date.now()): ClaimResult | null {
    const candidate = [...this.tasks.values()]
      .filter((task) => task.status === "pending" || ((task.status === "claimed" || task.status === "running") && task.lease && task.lease.expiresAt <= now))
      .sort((a, b) => a.createdAt - b.createdAt)[0];
    if (!candidate) return null;
    const lease: Lease = { ownerId, token: `${newId("event")}${newId("event")}`, acquiredAt: now, heartbeatAt: now, expiresAt: now + Math.min(Math.max(leaseMs, 5_000), 300_000) };
    const updated = { ...candidate, status: "claimed" as const, lease, updatedAt: now };
    this.tasks.set(candidate.taskId, updated);
    return { task: structuredClone(updated), lease: structuredClone(lease) };
  }

  heartbeat(taskId: string, ownerId: string, leaseToken: string, extensionMs: number, now = Date.now()): Lease {
    const task = this.requireLease(taskId, ownerId, leaseToken, now);
    const lease = { ...task.lease!, heartbeatAt: now, expiresAt: now + Math.min(Math.max(extensionMs, 5_000), 300_000) };
    this.tasks.set(taskId, { ...task, status: "running", lease, updatedAt: now });
    return structuredClone(lease);
  }

  finish(taskId: string, ownerId: string, leaseToken: string, resultUrls: string[], now = Date.now()): TaskValue {
    const task = this.requireLease(taskId, ownerId, leaseToken, now);
    if (resultUrls.length === 0 || resultUrls.some((url) => !url.startsWith("https://"))) {
      throw new ControlPlaneError("VALIDATION_FAILED", "Live completion requires at least one persisted HTTPS result URL", 422, false);
    }
    const updated = Task.parse({ ...task, status: "done", resultUrls, lease: undefined, updatedAt: now });
    this.tasks.set(taskId, updated);
    return structuredClone(updated);
  }

  fail(taskId: string, ownerId: string, leaseToken: string, escalated = false, now = Date.now()): TaskValue {
    const task = this.requireLease(taskId, ownerId, leaseToken, now);
    const updated = Task.parse({ ...task, status: escalated ? "escalated" : "failed", lease: undefined, updatedAt: now });
    this.tasks.set(taskId, updated);
    return structuredClone(updated);
  }

  requireLease(taskId: string, ownerId: string, leaseToken: string, now = Date.now()): TaskValue {
    const task = this.tasks.get(taskId);
    if (!task) throw new ControlPlaneError("NOT_FOUND", "Task not found", 404, false);
    const lease = task.lease;
    if (!lease || lease.ownerId !== ownerId || lease.token !== leaseToken || lease.expiresAt <= now) {
      throw new ControlPlaneError("LOST_LEASE", "The task lease is missing, expired, or belongs to another runtime", 409, false);
    }
    return structuredClone(task);
  }

  get(taskId: string): TaskValue | undefined { const task = this.tasks.get(taskId); return task ? structuredClone(task) : undefined; }
}
