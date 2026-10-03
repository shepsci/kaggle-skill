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
| By hand | Copy `skills/kaggle/` into the agent's skills folder |

Public competition facts and pages, writeups and discussions need only
Python. For your own account, install the two packages with
`python3 -m pip install "kaggle>=2.2.4" "kagglehub>=1.0.2"` and run
`kaggle auth login` or create an API token; the
[setup module](../skills/kaggle/modules/setup/README.md) has the steps.

## First run

1. Ask the agent something that mentions Kaggle. The skill loads, and the
   agent runs one of its commands, for example `brief titanic`.
2. Ask "check my Kaggle setup". The `doctor` command reports what is
   installed, which credential is configured, whether Kaggle answers, and
   what works now.
3. For a competition you have entered, ask "where do I stand in <name>?".

To try a command yourself, from a clone of the repository:

```bash
python3 skills/kaggle/scripts/kaggle_skill.py --help
python3 skills/kaggle/scripts/kaggle_skill.py brief titanic
python3 skills/kaggle/scripts/kaggle_skill.py doctor
```

## Find your way

| Situation | Start here |
|---|---|
| You know the task but not the command | [Workflow guide](workflows.md) |
| You want every command | [SKILL.md](../skills/kaggle/SKILL.md) |
| You want the module map | [Modules guide](../skills/kaggle/modules/README.md) |
| Something failed or came back empty | [Troubleshooting](troubleshooting.md) |
| You want to see it run | [Demo library](demo/README.md) |

## Workflows

| Workflow | Reference |
|---|---|
| Check the setup | [Setup module](../skills/kaggle/modules/setup/README.md) |
| Research and run a competition | [Competitions module](../skills/kaggle/modules/competitions/README.md) |
| Prepare and make a submission | [Competition operations](../skills/kaggle/modules/competitions/references/competition-operations.md) |
| Retrieve hackathon writeups | [Hackathons](../skills/kaggle/modules/competitions/hackathons/README.md) |
| Download or publish datasets | [Datasets module](../skills/kaggle/modules/datasets/README.md) |
| Download or publish models | [Models module](../skills/kaggle/modules/models/README.md) |
| Push or run notebooks | [Notebooks module](../skills/kaggle/modules/notebooks/README.md) |
| Read discussions, find solution writeups | [Discussions module](../skills/kaggle/modules/discussions/README.md) |
| Run benchmark tasks | [Benchmarks module](../skills/kaggle/modules/benchmarks/README.md) |
| Call the MCP server | [MCP setup](mcp-setup.md), [MCP reference](../skills/kaggle/modules/references/mcp-reference.md) |
| Use the Kaggle CLI | [CLI reference](../skills/kaggle/modules/references/cli-reference.md) |
| Collect badges | [Badges module](../skills/kaggle/modules/badges/README.md) |

## For maintainers

| Task | Reference |
|---|---|
| How it is built and what the tests check | [Architecture](architecture.md) |
| Supported agents | [Compatibility](compatibility.md) |
| Where the skill is published, and how to release | [Distribution](distribution/README.md) |
| Install checks to run by hand | [Install checklist](../tests/e2e/INSTALL_CHECKLIST.md) |
| Record or rebuild the demos | [Demo library](demo/README.md) |

## Safety model

Text from Kaggle is untrusted. Commands print it inside blocks that the text
cannot close, and `SKILL.md` tells the agent to read it as data. The skill
pre-approves only read tools, so the agent asks before running a command.
Every command that changes the account is a dry run until `--yes` is added,
badge phases included, and `KAGGLE_SKILL_READ_ONLY=1` makes them refuse. The tests under
`tests/security/` and `tests/unit/` check this behaviour, not only the
wording.
