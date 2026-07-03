# kaggle-skill Documentation

This hub points to the shortest useful path for each Kaggle workflow. The
repository is `kaggle-skill`; the public skill and plugin selector is `kaggle`.
This is an independent, unofficial project. It is not affiliated with,
endorsed by, or sponsored by Kaggle or Google.

## Start Here

| Environment | Install |
|---|---|
| Antigravity CLI (`agy`) | `npx skills add shepsci/kaggle-skill` |
| Claude Code | `/plugin marketplace add shepsci/kaggle-skill` then `/plugin install kaggle@shepsci` |
| Codex | `codex plugin marketplace add shepsci/kaggle-skill --ref main` then `codex plugin add kaggle@shepsci` |
| skills.sh agents | `npx skills add shepsci/kaggle-skill` |
| OpenClaw | `clawhub install kaggle` |
| Manual clone | install the dependencies in `pyproject.toml`, then copy `skills/kaggle/` into the agent skills directory |

Before running Kaggle workflows, set `KAGGLE_API_TOKEN` or create
`~/.kaggle/access_token`. The [setup module](../skills/kaggle/modules/setup/README.md)
has the detailed credential walkthrough.

## Choose A Path

| Situation | Best First Stop |
|---|---|
| You know the task but not the module | [Workflow guide](workflows.md) |
| You want the module map | [Modules guide](../skills/kaggle/modules/README.md) |
| Something failed or returned empty data | [Troubleshooting guide](troubleshooting.md) |
| You want to see the flows in motion | [Demo library](demo/README.md) |

## Common Workflows

| Workflow | Reference |
|---|---|
| Check credentials | [Setup module](../skills/kaggle/modules/setup/README.md) |
| Summarize rules, evaluation, data pages, and timelines | [Competitions module](../skills/kaggle/modules/competitions/README.md) |
| Retrieve hackathon writeups | [Hackathon workflow](../skills/kaggle/modules/competitions/hackathons/README.md) |
| Download or publish datasets | [Datasets module](../skills/kaggle/modules/datasets/README.md) |
| Download or publish models | [Models module](../skills/kaggle/modules/models/README.md) |
| Publish or run notebooks | [Notebooks module](../skills/kaggle/modules/notebooks/README.md) |
| Search forums and resource topics | [Discussions module](../skills/kaggle/modules/discussions/README.md) |
| Discover leaderboard solution writeup links | [Discussions module](../skills/kaggle/modules/discussions/README.md) |
| Author and run benchmark tasks | [Benchmarks module](../skills/kaggle/modules/benchmarks/README.md) |
| Inspect MCP tool coverage | [MCP reference](../skills/kaggle/modules/references/mcp-reference.md) |
| Collect badges | [Badges module](../skills/kaggle/modules/badges/README.md) |

## Maintainer Docs

| Task | Reference |
|---|---|
| Validate live Kaggle CLI, MCP, and plugin install paths | [Live validation notes](distribution/live-validation.md) |
| Prepare Codex curated-plugin review material | [Codex request packet](distribution/codex-curated-plugin-request.md) |
| Prepare Claude directory submission material | [Claude directory packet](distribution/claude-community-submission.md) |
| Run manual install checks | [Manual install checklist](../tests/e2e/INSTALL_CHECKLIST.md) |
| Watch or record screencasts | [Demo library](demo/README.md) |

## Safety Model

Kaggle-supplied text is treated as untrusted data. Scripts that print forum
topics, writeup bodies, overview pages, leaderboard rosters, or submission
lists wrap those outputs in `<untrusted-content>` markers. Credential redaction,
zip extraction, dynamic import/eval avoidance, and manifest drift are enforced
by tests under `tests/security/` and `tests/manifest/`.

The repo marketplace install paths are self-hosted. Official Claude directory,
Anthropic Verified, and OpenAI-curated Codex listings are separate review
outcomes tracked in the distribution packets.
