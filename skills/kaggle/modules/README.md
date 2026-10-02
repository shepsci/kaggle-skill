# Kaggle Modules

One folder per kind of task.

| Need | Module |
|---|---|
| Account setup, credential check, network check | [setup](setup/README.md) |
| Competition pages, reports, data, submissions, hackathons | [competitions](competitions/README.md) |
| Dataset download or publishing | [datasets](datasets/README.md) |
| Model download or publishing | [models](models/README.md) |
| Notebook publish, run, polling, output download | [notebooks](notebooks/README.md) |
| Forums, topics, leaderboard solution writeups | [discussions](discussions/README.md) |
| Benchmark task commands | [benchmarks](benchmarks/README.md) |
| Badge inventory, dry run, phases | [badges](badges/README.md) |
| Kaggle CLI, MCP server, and platform references | [references](references/README.md) |

## Routing notes

- Reading public pages, datasets, models, and writeups needs no credential.
  Check credentials with `setup/` before anything private or any write.
- `competitions/` covers standard competitions and hackathons.
- `datasets/` and `models/` each have a kagglehub path and a Kaggle CLI path.
- Use `discussions/` whenever forum, topic, or writeup text will be read.
- Read `benchmarks/` before a command that creates a task or uses quota.
- Use `badges/` only after a dry run and the user's go-ahead.

## Shared code

`../shared/` holds what every script uses: the MCP client, the credential
resolver, the Kaggle CLI runner, the untrusted-content printer, the upload
check for credential files, and the safe zip extractor. Scripts print
Kaggle-supplied text through `shared/untrusted.py`; see "Reading script
output" in `SKILL.md`.
