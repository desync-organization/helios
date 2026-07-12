"""Capture ten or more real warmed fast-lane runs from the compatibility gateway."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hermes_training.io import write_json_atomic
from websockets.asyncio.client import connect


async def run_once(url: str, ticket: str, prompt: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    actual_cost = 0.0
    equivalent_cost = 0.0
    result_url: str | None = None
    async with connect(f"{url}?ticket={ticket}", max_size=1_048_576) as websocket:
        await websocket.send(json.dumps({"type": "prompt", "data": prompt}))
        async with asyncio.timeout(timeout):
            async for raw in websocket:
                message = json.loads(raw)
                if message.get("type") == "token_usage":
                    data = message.get("data", {})
                    actual_cost += float(data.get("cost_usd", 0))
                    equivalent_cost += float(data.get("cost_cloud_equivalent_usd", 0))
                if message.get("type") == "complete":
                    result_url = message.get("githubUrl")
                    break
                if message.get("type") == "error":
                    raise RuntimeError(str(message.get("data")))
    if not result_url:
        raise RuntimeError("fast-lane run ended without a persisted result URL")
    return {
        "latencyMs": round((time.perf_counter() - started) * 1000, 3),
        "actualCostUsd": actual_cost,
        "cloudEquivalentCostUsd": equivalent_cost,
        "resultUrl": result_url,
    }


async def benchmark(args: argparse.Namespace) -> None:
    prompts = [
        line.strip()
        for line in args.prompts.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(prompts) < 10:
        raise ValueError("fast-lane acceptance requires at least ten prompts")
    runs = [
        await run_once(args.url, args.ticket, f"{prompt}\nbenchmark-run:{index}", args.timeout)
        for index, prompt in enumerate(prompts, start=1)
    ]
    latencies = [run["latencyMs"] for run in runs]
    report = {
        "schemaVersion": "1.0",
        "capturedAt": datetime.now(UTC).isoformat(),
        "dataClass": "live",
        "runCount": len(runs),
        "latencyMedianMs": statistics.median(latencies),
        "latencyMaxMs": max(latencies),
        "allUnderSixtySeconds": all(latency < 60_000 for latency in latencies),
        "runs": runs,
    }
    write_json_atomic(args.output, report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://127.0.0.1:9100/ws")
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    asyncio.run(benchmark(parser.parse_args()))


if __name__ == "__main__":
    main()
