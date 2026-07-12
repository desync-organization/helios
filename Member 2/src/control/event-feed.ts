import type { TraceEvent } from "../../packages/contracts/src/trace";
import { TraceEvent as TraceEventSchema } from "../../packages/contracts/src/trace";
import { ControlPlaneError } from "../errors";

export interface EventPage { events: TraceEvent[]; nextCursor: number; snapshotRequired: boolean }

export class CanonicalEventFeed {
  private readonly byRun = new Map<string, Map<number, TraceEvent>>();
  private readonly eventIds = new Set<string>();

  append(event: TraceEvent): { event: TraceEvent; duplicate: boolean } {
    const parsed = TraceEventSchema.parse(event);
    if (this.eventIds.has(parsed.eventId)) return { event: structuredClone(parsed), duplicate: true };
    const stream = this.byRun.get(parsed.runId) ?? new Map<number, TraceEvent>();
    const expected = stream.size === 0 ? 1 : Math.max(...stream.keys()) + 1;
    if (parsed.sequence !== expected) throw new ControlPlaneError("CONFLICT", `Expected sequence ${expected}, received ${parsed.sequence}`, 409, false, { expectedSequence: expected });
    stream.set(parsed.sequence, parsed);
    this.byRun.set(parsed.runId, stream);
    this.eventIds.add(parsed.eventId);
    return { event: structuredClone(parsed), duplicate: false };
  }

  page(runId: string, cursor = 0, limit = 100): EventPage {
    const stream = this.byRun.get(runId) ?? new Map();
    const oldest = stream.size ? Math.min(...stream.keys()) : 1;
    const snapshotRequired = cursor > 0 && cursor + 1 < oldest;
    const events = [...stream.values()].filter((event) => event.sequence > cursor).sort((a, b) => a.sequence - b.sequence).slice(0, Math.min(limit, 500));
    return { events: structuredClone(events), nextCursor: events.at(-1)?.sequence ?? cursor, snapshotRequired };
  }
}
