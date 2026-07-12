import { ControlPlaneError } from "./errors";

interface Bucket { count: number; resetAt: number }

export class FixedWindowRateLimiter {
  private readonly buckets = new Map<string, Bucket>();
  constructor(private readonly limit: number, private readonly windowMs: number, private readonly maximumKeys = 10_000) {}

  consume(key: string, now = Date.now()): void {
    const current = this.buckets.get(key);
    if (!current || current.resetAt <= now) {
      if (this.buckets.size >= this.maximumKeys) this.evictExpired(now);
      this.buckets.set(key, { count: 1, resetAt: now + this.windowMs });
      return;
    }
    current.count += 1;
    if (current.count > this.limit) throw new ControlPlaneError("RATE_LIMITED", "Rate limit exceeded", 429, true, { retryAfterMs: current.resetAt - now });
  }

  private evictExpired(now: number): void {
    for (const [key, bucket] of this.buckets) if (bucket.resetAt <= now) this.buckets.delete(key);
    if (this.buckets.size >= this.maximumKeys) this.buckets.delete(this.buckets.keys().next().value as string);
  }
}
