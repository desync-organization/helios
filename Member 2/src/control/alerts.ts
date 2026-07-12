import { SCHEMA_VERSION } from "../../packages/contracts/src/common";
import { newId } from "../../packages/contracts/src/ids";
import type { AlertEvent, AlertKind } from "../../packages/contracts/src/alert";

export interface OperationalSignal {
  kind: AlertKind;
  severity: "info" | "warning" | "critical";
  messageRedacted: string;
  ruleId: string;
  repo?: string;
  taskId?: string;
  runId?: string;
}

export class AlertEngine {
  private readonly events: AlertEvent[] = [];
  private readonly dedupe = new Set<string>();
  emit(signal: OperationalSignal, now = Date.now()): AlertEvent | null {
    const key = `${signal.ruleId}:${signal.repo ?? "global"}:${signal.taskId ?? ""}:${signal.runId ?? ""}:${Math.floor(now / 60_000)}`;
    if (this.dedupe.has(key)) return null;
    this.dedupe.add(key);
    const event = { schemaVersion: SCHEMA_VERSION, alertId: newId("alert", now), ...signal, createdAt: now } as AlertEvent;
    this.events.push(event);
    return structuredClone(event);
  }
  list(): AlertEvent[] { return structuredClone(this.events); }
}
