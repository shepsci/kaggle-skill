# kaggle-skill Documentation

The repository is `kaggle-skill`; the skill and the plugin are named
`kaggle`. This is an independent, unofficial project. It is not affiliated
with, endorsed by, or sponsored by Kaggle or Google.

## Install

| Where | Command |
|---|---|
| Claude Code | `/plugin marketplace add shepsci/kaggle-skill` then `/plugin install kaggle@shepsci` |
| Codex | `codex plugin marketplace add shepsci/kaggle-skill --ref main` then `codex plugin add kaggle@shepsci` |
| Antigravity CLI and other skills.sh agents | `npx skills add shepsci/kaggle-skill` |
| OpenClaw | `clawhub install kaggle` |
| By hand | Install the dependencies in `pyproject.toml`, then copy `skills/kaggle/` into the agent's skills folder |

Public competition pages, datasets, models, and writeups can be read without
a credential. For the rest, run `kaggle auth login` or create an API token;
the [setup module](../skills/kaggle/modules/setup/README.md) has the steps.

## Find your way

| Situation | Start here |
|---|---|
| You know the task but not the module | [Workflow guide](workflows.md) |
| You want the module map | [Modules guide](../skills/kaggle/modules/README.md) |
| Something failed or came back empty | [Troubleshooting](troubleshooting.md) |
| You want to see it run | [Demo library](demo/README.md) |

## Workflows

| Workflow | Reference |
|---|---|
| Check credentials | [Setup module](../skills/kaggle/modules/setup/README.md) |
| Read rules, metric, data pages, timeline | [Competitions module](../skills/kaggle/modules/competitions/README.md) |
| Prepare and make a submission | [Competition operations](../skills/kaggle/modules/competitions/references/competition-operations.md) |
| Retrieve hackathon writeups | [Hackathons](../skills/kaggle/modules/competitions/hackathons/README.md) |
| Download or publish datasets | [Datasets module](../skills/kaggle/modules/datasets/README.md) |
| Download or publish models | [Models module](../skills/kaggle/modules/models/README.md) |
| Push or run notebooks | [Notebooks module](../skills/kaggle/modules/notebooks/README.md) |
| Search forums, find solution writeups | [Discussions module](../skills/kaggle/modules/discussions/README.md) |
| Run benchmark tasks | [Benchmarks module](../skills/kaggle/modules/benchmarks/README.md) |
| Call the MCP server | [MCP reference](../skills/kaggle/modules/references/mcp-reference.md) |
| Use the Kaggle CLI | [CLI reference](../skills/kaggle/modules/references/cli-reference.md) |
| Collect badges | [Badges module](../skills/kaggle/modules/badges/README.md) |

## For maintainers

| Task | Reference |
|---|---|
| Where the skill is published, and how to release | [Distribution](distribution/README.md) |
| Install checks to run by hand | [Install checklist](../tests/e2e/INSTALL_CHECKLIST.md) |
| Record or rebuild screencasts | [Demo library](demo/README.md) |

## Safety model

Text from Kaggle is untrusted. Scripts print it inside blocks that the text
cannot close, and `SKILL.md` tells the agent to read it as data. The skill
pre-approves only read tools, so the agent asks before running a script.
Scripts that change the account need a clear request, and the submission
script is a dry run by default. The tests under `tests/security/` and
`tests/unit/` check this behaviour, not only the wording.
