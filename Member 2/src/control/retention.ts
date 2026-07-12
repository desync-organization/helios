export interface RetainableRecord { id: string; expiresAt: number; immutableAudit?: boolean; searchableProjection?: string; payload?: unknown }

export function applyRetention<T extends RetainableRecord>(records: T[], now = Date.now()): { retained: T[]; deletedIds: string[] } {
  const retained: T[] = [];
  const deletedIds: string[] = [];
  for (const record of records) {
    if (record.expiresAt > now) { retained.push(structuredClone(record)); continue; }
    deletedIds.push(record.id);
    if (record.immutableAudit) retained.push({ ...structuredClone(record), searchableProjection: undefined, payload: undefined });
  }
  return { retained, deletedIds };
}
