# Benchmark Endpoints

The Kaggle MCP server has two benchmark tools. Arguments go inside a `request`
object; see [mcp-reference.md](../../references/mcp-reference.md).

## `get_benchmark_leaderboard` (read)

Reads the leaderboard of a published benchmark. It needs no credential.
Checked on 2026-09-30.

| Argument | Meaning |
|---|---|
| `ownerSlug` | The benchmark's owner, for example `kaggle` |
| `benchmarkSlug` | The benchmark, for example `icml-2025-experts` |
| `versionNumber` | Optional |

The answer has `rows`, one per model version, each with `model_version_name`,
`model_version_slug`, and `task_results`. A benchmark that does not exist
gives `Not found`.

```python
import sys

sys.path.insert(0, ".")  # run from the skill folder
from shared.mcp_client import classify_result, extract_json, mcp_call

response = mcp_call(
    "get_benchmark_leaderboard",
    {"request": {"ownerSlug": "kaggle", "benchmarkSlug": "icml-2025-experts"}},
)
if classify_result(response) == "ok":
    for row in extract_json(response)["rows"][:5]:
        print(row["model_version_name"])
```

The Kaggle CLI has the same data: `kaggle benchmarks leaderboard
kaggle/icml-2025-experts --show`.

## `create_benchmark_task_from_prompt` (write)

Creates a benchmark task on the account from two texts: `taskDescription` and
`assertionDescription`. It was not called for this reference, because it
changes the account. Ask the user before using it, and say that it creates a
task and a backing notebook.

For writing tasks in code, use `kaggle benchmarks tasks push` with a task
file; see [benchmarks-cli.md](benchmarks-cli.md).
