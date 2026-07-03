# Kaggle Modules

The modules are organized by user workflow. Old catch-all paths were removed,
so use the table below when routing a task or updating docs.

| Need | Module |
|---|---|
| Account setup, token checks, environment setup, network checks | [setup](setup/README.md) |
| Competition pages, reports, submissions, hackathons | [competitions](competitions/README.md) |
| Dataset download or publishing | [datasets](datasets/README.md) |
| Model download or publishing | [models](models/README.md) |
| Notebook publish, execution, polling, output download | [notebooks](notebooks/README.md) |
| Forums, resource topics, leaderboard solution writeups | [discussions](discussions/README.md) |
| Benchmark task commands and endpoint notes | [benchmarks](benchmarks/README.md) |
| Badge inventory, dry runs, and phase execution | [badges](badges/README.md) |
| Shared CLI, MCP, and platform references | [references](references/README.md) |

## Routing Notes

- Use `setup/` before any live Kaggle operation.
- Use `competitions/` for both standard competitions and hackathons.
- Use `datasets/` and `models/` separately; their kagglehub helpers are split.
- Use `discussions/` when any forum, topic, or writeup text will be read by an
  agent.
- Use `benchmarks/` before running commands that can create tasks or consume
  quota.
- Use `badges/` only after an explicit dry-run or user confirmation.
