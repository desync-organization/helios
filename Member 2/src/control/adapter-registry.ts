import { Adapter, type Adapter as AdapterValue } from "../../packages/contracts/src/adapter";
import { ControlPlaneError } from "../errors";

export interface PromotionAudit { adapterId: string; roles: string[]; action: "activate" | "rollback"; predecessorByRole: Record<string, string | undefined>; at: number }

export class AdapterRegistry {
  private readonly adapters = new Map<string, AdapterValue>();
  private pointers: Record<string, string> = {};
  readonly audit: PromotionAudit[] = [];

  register(adapter: AdapterValue): void { this.adapters.set(adapter.adapterId, Adapter.parse(adapter)); }

  activate(adapterId: string, now = Date.now()): Readonly<Record<string, string>> {
    const adapter = this.adapters.get(adapterId);
    if (!adapter) throw new ControlPlaneError("NOT_FOUND", "Adapter not found", 404, false);
    if (!adapter.tenRunBenchmarkPassed || adapter.stableGauntletRuns.length !== 3 || !adapter.safetySubgroupsPassed || !adapter.qualityApprovedBy || !adapter.compatibilityApprovedBy) {
      throw new ControlPlaneError("POLICY_DENIED", "Adapter promotion gates have not passed", 403, false);
    }
    const predecessorByRole = Object.fromEntries(adapter.activeRoles.map((role) => [role, this.pointers[role]]));
    const next = { ...this.pointers };
    for (const role of adapter.activeRoles) next[role] = adapter.adapterId;
    this.pointers = next;
    this.audit.push({ adapterId, roles: [...adapter.activeRoles], action: "activate", predecessorByRole, at: now });
    return structuredClone(this.pointers);
  }

  rollback(adapterId: string, now = Date.now()): Readonly<Record<string, string>> {
    const activation = [...this.audit].reverse().find((entry) => entry.adapterId === adapterId && entry.action === "activate");
    if (!activation) throw new ControlPlaneError("CONFLICT", "No activation record exists for this adapter", 409, false);
    const next = { ...this.pointers };
    for (const role of activation.roles) {
      const predecessor = activation.predecessorByRole[role];
      if (predecessor) next[role] = predecessor; else delete next[role];
    }
    this.pointers = next;
    this.audit.push({ adapterId, roles: activation.roles, action: "rollback", predecessorByRole: activation.predecessorByRole, at: now });
    return structuredClone(this.pointers);
  }
}
