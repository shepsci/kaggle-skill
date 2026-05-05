# Benchmark Endpoints

Two MCP tools, both in the AGI/evaluation surface.

## `create_benchmark_task_from_prompt` — ✅ PASS

Create a new benchmark task on Kaggle from a prompt + assertion.

**Parameters:**
- `taskDescription` (string) — natural-language description of what the task is
- `assertionDescription` (string) — natural-language description of how to score

**Returns:** an object with `kernel_url` pointing at the created benchmark task.

```python
from skills.kaggle.shared.mcp_client import mcp_call, resolve_token

token = resolve_token()
resp = mcp_call("create_benchmark_task_from_prompt", {
    "taskDescription": "Compute the Fibonacci sequence up to n=20",
    "assertionDescription": "Output must be a comma-separated list matching the canonical sequence",
}, token=token)
```

## `get_benchmark_leaderboard` — ✅ PASS (was 🔒 BLOCKED)

Read the leaderboard for an existing benchmark.

**Parameters:**
- `benchmarkSlug` (string)
- `ownerSlug` (string)

**Auth:** Was permission-gated in the 2026-04-22 audit. Verified **PASS** in
the 2026-05-04 retest with an ordinary KGAT token — no elevated access needed.
A non-existent benchmark/owner pair returns a not-found error rather than a
permission denial; treat both as data-not-available and surface the response.

```python
resp = mcp_call("get_benchmark_leaderboard", {
    "benchmarkSlug": "some-benchmark",
    "ownerSlug": "owner-handle",
}, token=token)
```

## When to use which

- **Creating tasks for evaluation runs** → `create_benchmark_task_from_prompt`.
  Returns a `kernel_url` — keep it; that's how downstream submissions reference
  the task.
- **Reading leaderboard data for a hackathon writeup that links to a benchmark**
  → `get_benchmark_leaderboard`. Works with an ordinary KGAT token as of
  2026-05-04. If the response is empty / not-found, surface that as evidence
  rather than silently falling back to scraping.
