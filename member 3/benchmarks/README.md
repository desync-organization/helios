# Acceptance Benchmarks

`run_fast_lane.py` records at least ten real warmed maintainer runs and refuses any run without a
persisted external result URL. It retains actual and cloud-equivalent cost separately. Do not run
training concurrently with demo inference. Store generated reports outside Git or copy reviewed,
redacted summaries into `evidence/` with exact commit/model/adapter/policy versions.

