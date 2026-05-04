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

## `get_benchmark_leaderboard` — 🔒 BLOCKED (permission-gated)

Read the leaderboard for an existing benchmark.

**Parameters:**
- `benchmarkSlug` (string)
- `ownerSlug` (string)

**Auth:** Returns a permission-denied error in standard auth contexts. The
endpoint exists and is documented but requires elevated access (likely benchmark
ownership or hackathon judge role). When you hit the denial, capture the exact
error text as evidence and surface it; do not silently fall back to scraping.

```python
resp = mcp_call("get_benchmark_leaderboard", {
    "benchmarkSlug": "some-benchmark",
    "ownerSlug": "owner-handle",
}, token=token)
# Expect: error with permission-related message
```

## When to use which

- **Creating tasks for evaluation runs** → `create_benchmark_task_from_prompt`.
  Returns a `kernel_url` — keep it; that's how downstream submissions reference
  the task.
- **Reading leaderboard data for a hackathon writeup that links to a benchmark**
  → `get_benchmark_leaderboard`. Expect a permission denial unless authenticated
  as the benchmark owner / hackathon host. Document the denial as evidence.
