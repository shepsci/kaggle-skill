# kaggle-skill Documentation

This hub points to the shortest useful path for each Kaggle workflow. The
repository is `kaggle-skill`; the public skill and plugin selector is `kaggle`.

## Start Here

| Environment | Install |
|---|---|
| Claude Code | `/plugin marketplace add shepsci/claude-marketplace` then `/plugin install kaggle@shepsci` |
| Codex | `codex plugin marketplace add shepsci/kaggle-skill --ref main` then `codex plugin add kaggle@shepsci` |
| skills.sh agents | `npx skills add shepsci/kaggle-skill` |
| OpenClaw | `clawhub install kaggle` |
| Manual clone | install the dependencies in `pyproject.toml`, then copy `skills/kaggle/` into the agent skills directory |

Before running Kaggle workflows, set `KAGGLE_API_TOKEN` or create
`~/.kaggle/access_token`. The [registration module](../skills/kaggle/modules/registration/README.md)
has the detailed credential walkthrough.

## Common Workflows

| Workflow | Reference |
|---|---|
| Check credentials | [Registration module](../skills/kaggle/modules/registration/README.md) |
| Summarize rules, evaluation, data pages, and timelines | [KLLM task workflows](../skills/kaggle/modules/kllm/README.md) |
| Generate competition landscape reports | [Competition report module](../skills/kaggle/modules/comp-report/README.md) |
| Search forums and resource topics | [Forums/writeups reference](../skills/kaggle/modules/kllm/references/forums-writeups.md) |
| Discover leaderboard solution writeup links | [Forums/writeups reference](../skills/kaggle/modules/kllm/references/forums-writeups.md) |
| Retrieve hackathon writeups | [Hackathon workflow](../skills/kaggle/modules/kllm/hackathon/README.md) |
| Use current Kaggle CLI commands | [CLI reference](../skills/kaggle/modules/kllm/references/cli-reference.md) |
| Author and run benchmark tasks | [Benchmarks reference](../skills/kaggle/modules/kllm/references/benchmarks-cli.md) |
| Inspect MCP tool coverage | [MCP reference](../skills/kaggle/modules/kllm/references/mcp-reference.md) |
| Collect badges | [Badge collector module](../skills/kaggle/modules/badge-collector/README.md) |

## Maintainer Docs

| Task | Reference |
|---|---|
| Validate live Kaggle CLI, MCP, and plugin install paths | [Live validation notes](distribution/live-validation.md) |
| Prepare Codex curated-plugin review material | [Codex request packet](distribution/codex-curated-plugin-request.md) |
| Prepare Claude community marketplace material | [Claude submission packet](distribution/claude-community-submission.md) |
| Run manual install checks | [Manual install checklist](../tests/e2e/INSTALL_CHECKLIST.md) |
| Record the README demo | [Demo script](demo/demo-script.md) |

## Safety Model

Kaggle-supplied text is treated as untrusted data. Scripts that print forum
topics, writeup bodies, overview pages, leaderboard rosters, or submission
lists wrap those outputs in `<untrusted-content>` markers. Credential redaction,
zip extraction, dynamic import/eval avoidance, and manifest drift are enforced
by tests under `tests/security/` and `tests/manifest/`.
