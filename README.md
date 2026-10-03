# kaggle-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-kaggle--skill-blue)](https://skills.sh/shepsci/kaggle-skill/kaggle)
[![ClawHub](https://img.shields.io/badge/ClawHub-kaggle-green)](https://clawhub.ai/shepsci/skills/kaggle)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/shepsci/kaggle-skill?style=social)](https://github.com/shepsci/kaggle-skill)

Ask your coding agent about a Kaggle competition and get a short, sourced
answer. Let it track where you stand, check a submission, and submit only
after you say yes.

An independent, unofficial skill and plugin named `kaggle`, for Claude Code,
Codex and other agents that load `SKILL.md` packages. Not affiliated with,
endorsed by, or sponsored by Kaggle or Google.

<!-- hero:start -->
> **You:** Which Kaggle competitions with prize money are running right now? A short list with each one's deadline, prize and metric, please.

![What is running now, with prizes and metrics](docs/demo/media/agent-competitions.gif)

A real session, recorded 2026-10-02 in Claude Code 2.1.286 (claude-opus-5-5): the agent ran `competitions`, then answered. [The whole answer](docs/demo/sessions/agent-competitions.json), [cast](docs/demo/agent-competitions.cast).
<!-- hero:end -->

## What you need

- Python 3.11 or later, and an agent that loads skills.
- Nothing else to read public content: a competition's facts and pages,
  solution writeups, discussions.
- For your own account (status, downloads, submissions, notebooks,
  publishing): a Kaggle credential, and two packages for the `python3` your
  agent uses: `python3 -m pip install "kaggle>=2.2.4" "kagglehub>=1.0.2"`.

## Install

1. Add it to your agent.

   | Where | Command |
   |---|---|
   | Claude Code | `/plugin marketplace add shepsci/kaggle-skill` then `/plugin install kaggle@shepsci` |
   | Codex | `codex plugin marketplace add shepsci/kaggle-skill --ref main` then `codex plugin add kaggle@shepsci` |
   | skills.sh (Antigravity CLI, Cursor, and others) | `npx skills add shepsci/kaggle-skill` |
   | OpenClaw | `clawhub install kaggle` |
   | By hand | Clone this repository and copy `skills/kaggle/` into your agent's skills folder |

2. Start a new session and ask something that mentions Kaggle: "What is the
   metric and deadline of the Kaggle Titanic competition?" The skill loads
   when Kaggle is named. It pre-approves only reading files, so in Claude
   Code's default mode the agent asks before it runs each command.

3. For anything on your account, sign in once with `kaggle auth login`, or
   create a token with "Generate New Token" at
   [kaggle.com/settings](https://www.kaggle.com/settings). Then ask "check my
   Kaggle setup", which runs the skill's `doctor` command. The
   [setup guide](skills/kaggle/modules/setup/references/kaggle-setup.md) has
   the details.

In Claude Code, `shepsci/kaggle-skill` is a marketplace that holds one
plugin, which is why there are two commands.

## What you can ask

- "Which Kaggle competitions with prize money are running, and what are their metrics?"
- "What is the metric, the deadline and the prize of this Kaggle competition?"
- "Summarize the rules that matter: team size, external data, submission limits."
- "What did the top teams do? Preview their solution writeups."
- "What are people discussing in this competition this week?"
- "Where do I stand: rank, submissions left today, best score, GPU hours?"
- "How far am I from the bronze line, and what moved since yesterday?"
- "Is this submission file well formed?"
- "Submit it." (You get a dry run first, and it submits after your yes.)
- "Wait for the score and tell me how it compares with my validation."
- "Download this dataset." "Push this notebook and tell me when the run ends."

## What it does on its own, and what it asks first

| Action | Without asking | What it costs |
|---|---|---|
| Read competition facts, pages, writeups, discussions | Yes | Nothing |
| Read your rank, submissions, scores, quota | Yes, with your credential | Nothing |
| Download competition data | Yes; refuses above 20 GB unless told | Disk space |
| Check a submission file | Yes | Nothing |
| Submit to a competition | No: a dry run, then `--yes` after you agree | One of the day's submissions |
| Push or run a notebook | No: a dry run first | Weekly GPU hours when a GPU is on |
| Publish a dataset or a model | No: a dry run first | A private resource on your account |
| Store a credential on disk | No: a dry run first | A file in `~/.kaggle` |
| Run a badge phase | No: a dry run first | Notebooks, datasets and submissions on your account |

`KAGGLE_SKILL_READ_ONLY=1` in the environment makes every write refuse, and
`KAGGLE_SKILL_HIDE_ACCOUNT=1` leaves your entries and ranks out of listings
and briefs, for screen sharing and recordings.
Text that comes from Kaggle is marked as data, which lowers the risk that an
instruction hidden in a forum post or a writeup is followed. The skill keeps
a local record of what it submitted and how it scored in `./.kaggle-skill/`;
nothing is sent anywhere but to Kaggle.

## How the pieces fit

| Piece | What it is | Sign-in it uses |
|---|---|---|
| The skill | `SKILL.md` and Python commands under `skills/kaggle/` | The Kaggle credential on your machine |
| The plugin | The skill plus the Kaggle MCP server entry, packaged for Claude Code and Codex | Same |
| Kaggle CLI (`kaggle`) | Kaggle's own tool; the skill calls it to download, submit, push | A token, a legacy key, or `kaggle auth login` |
| `kagglehub` | Kaggle's library; downloads and uploads datasets and models | A token or a legacy key, not `kaggle auth login`; none for public downloads |
| Kaggle MCP server | Kaggle's 71 remote tools | The skill's commands send your token; calling the tools from the agent needs a separate sign-in ([MCP setup](docs/mcp-setup.md)) |

An API token serves everything the skill does. An OAuth login
(`kaggle auth login`) serves the Kaggle CLI and the reads on your account,
not kagglehub: publish with `--via cli`. A legacy `kaggle.json` key serves the
CLI and kagglehub, not the commands that read your standing.

<!-- demos:start -->
## See it work

> **You:** What's the deadline and the metric of kaggle.com/competitions/arc-prize-2026-arc-agi-3?

![A question about one competition](docs/demo/media/agent-brief.gif)

A real session, recorded 2026-10-02 in Claude Code 2.1.286 (claude-opus-5-5): the agent ran `brief`, then answered. [The whole answer](docs/demo/sessions/agent-brief.json), [cast](docs/demo/agent-brief.cast).

> **You:** What did the top three teams of Kaggle's ARC Prize 2025 do? A few lines each.

![What the top teams did](docs/demo/media/agent-solutions.gif)

A real session, recorded 2026-10-02 in Claude Code 2.1.286 (claude-opus-5-5): the agent ran `solutions` and `writeup`, then answered. [The whole answer](docs/demo/sessions/agent-solutions.json), [cast](docs/demo/agent-solutions.cast).

> **You:** Submit ./submission.csv to the Titanic competition on Kaggle.

![A submission is a dry run first](docs/demo/media/agent-submit.gif)

The agent checks the file, shows the dry run, and asks before it submits. A real session, recorded 2026-10-02 in Claude Code 2.1.286 (claude-opus-5-5): the agent ran `submit`, then answered. [The whole answer](docs/demo/sessions/agent-submit.json), [cast](docs/demo/agent-submit.cast).

The sessions are recorded as they ran, read-only, and show nothing about an account; the [demo library](docs/demo/README.md) has the install demos and says how each one is made.
<!-- demos:end -->

## Update and uninstall

| Where | Update | Uninstall |
|---|---|---|
| Claude Code | `claude plugin marketplace update shepsci` then `claude plugin update kaggle@shepsci` | `claude plugin uninstall kaggle@shepsci` |
| Codex | `codex plugin marketplace upgrade` then `codex plugin add kaggle@shepsci` again | `codex plugin remove kaggle@shepsci` |
| skills.sh | `npx skills update` | `npx skills remove kaggle` |
| OpenClaw | `clawhub update kaggle` | `clawhub uninstall kaggle` |

Run these in a shell, then start a new agent session to load the new
version. Version 3.0.0 renamed the commands and made every write a dry run
by default; the [changelog](CHANGELOG.md) lists what changed.

## Documentation

| Need | Start here |
|---|---|
| Every command, as the agent sees it | [SKILL.md](skills/kaggle/SKILL.md) |
| Pick the right workflow | [Workflow guide](docs/workflows.md) |
| Before and after a submission | [Competition operations](skills/kaggle/modules/competitions/references/competition-operations.md) |
| Credentials | [Setup module](skills/kaggle/modules/setup/README.md) |
| Each module | [Modules guide](skills/kaggle/modules/README.md) |
| Kaggle CLI and MCP server | [CLI reference](skills/kaggle/modules/references/cli-reference.md), [MCP reference](skills/kaggle/modules/references/mcp-reference.md), [MCP setup](docs/mcp-setup.md) |
| When something fails | [Troubleshooting](docs/troubleshooting.md) |
| How it is built and tested | [Architecture](docs/architecture.md) |
| Supported agents, and Kaggle's own skills | [Compatibility](docs/compatibility.md) |
| Where it is published | [Distribution](docs/distribution/README.md) |
| All docs | [Docs hub](docs/README.md) |

## Security, license, privacy

The skill does not sandbox the agent and does not limit which hosts it can
reach. Review what an agent proposes before it submits or publishes. What the
skill guarantees, and the tests that hold it to it, are in
[Architecture](docs/architecture.md). Report security issues through
[SECURITY.md](SECURITY.md).

MIT license; see [LICENSE](LICENSE). The copy on ClawHub is under MIT-0, as
ClawHub requires. The skill collects no data: credentials and processing stay
on your machine; see [PRIVACY.md](PRIVACY.md).
