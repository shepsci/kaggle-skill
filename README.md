# kaggle-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-kaggle--skill-blue)](https://skills.sh/shepsci/kaggle-skill/kaggle)
[![ClawHub](https://img.shields.io/badge/ClawHub-kaggle-green)](https://clawhub.ai/skills/kaggle)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/shepsci/kaggle-skill?style=social)](https://github.com/shepsci/kaggle-skill)

An agent skill for everything Kaggle: account setup, competition landscape reports, dataset/model downloads, notebook execution, competition submissions, **hackathon writeup retrieval and grading**, badge collection, and general Kaggle questions.

Works with **any AI coding agent** that supports the SKILL format — including [Claude Code](https://claude.com/claude-code), [OpenClaw](https://openclaw.ai), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Cursor](https://cursor.com), [Codex](https://openai.com/codex), and [35+ more agents via skills.sh](https://skills.sh).

## Available On

| Platform | Link | Install Command |
|----------|------|-----------------|
| **skills.sh** | [skills.sh/shepsci/kaggle-skill](https://skills.sh/shepsci/kaggle-skill/kaggle) | `npx skills add shepsci/kaggle-skill` |
| **ClawHub** | [clawhub.ai/skills/kaggle](https://clawhub.ai/skills/kaggle) | `clawhub install kaggle` |
| **Claude Code Marketplace** | [shepsci/claude-marketplace](https://github.com/shepsci/claude-marketplace) | `/plugin marketplace add shepsci/claude-marketplace` then `/plugin install kaggle-skill@shepsci` |

## Modules

- **Registration** — Account creation, API token generation, credential storage
- **Competition Reports** — Landscape reports with API + Playwright scraping
- **Kaggle Interaction (kllm)** — kagglehub, kaggle-cli, MCP Server (66 tools), UI workflows
- **Hackathon** — Writeup retrieval, overview/rubric extraction, role-aware grading bundles
- **Badge Collector** — Systematic badge earning across 5 phases (~38 automatable)

## Installation

### Via skills.sh (all agents)

Installs to Claude Code, OpenClaw, Codex, Cursor, Gemini CLI, and 35+ other agents:

```bash
npx skills add shepsci/kaggle-skill
```

### Via ClawHub (OpenClaw)

```bash
clawhub install kaggle
```

### Via Claude Code Plugin Marketplace

Add the catalog once, then install:

```bash
/plugin marketplace add shepsci/claude-marketplace
/plugin install kaggle-skill@shepsci
```

Or load directly from a local clone:
```bash
claude --plugin-dir /path/to/kaggle-skill
```

### Manual

```bash
git clone https://github.com/shepsci/kaggle-skill.git
pip install kagglehub kaggle python-dotenv requests
```

Then copy `skills/kaggle/` into your agent's skills directory.

## Prerequisites

- Python 3.11+
- `pip install kagglehub kaggle python-dotenv requests`
- Kaggle API token (the skill walks you through setup)
- Optional: Playwright for browser badges and competition report scraping

## Credential Setup

1. Go to [kaggle.com/settings](https://www.kaggle.com/settings)
2. Under **API Tokens (Recommended)**, click **Generate New Token**
3. Save the token:

```bash
mkdir -p ~/.kaggle
echo 'YOUR_TOKEN' > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
```

Or set the environment variable:
```bash
export KAGGLE_API_TOKEN=YOUR_TOKEN
```

Legacy credentials (`~/.kaggle/kaggle.json`) are also supported. Run the credential checker for details:
```bash
python3 shared/check_all_credentials.py
```

## Usage

Once installed, your agent automatically detects the skill when you mention anything Kaggle-related:

- "Set up my Kaggle credentials"
- "Generate a Kaggle competition report"
- "Download the Titanic dataset"
- "Earn Kaggle badges"
- "Enter a Kaggle competition"
- "What competitions are running right now?"

## Bundled MCP Server (Claude Code)

When installed as a Claude Code plugin, this skill includes a `.mcp.json` that configures the official Kaggle MCP server, giving direct access to **66 Kaggle tools** (verified against the live server in the [shepsci/kmcp-tools](https://github.com/shepsci/kmcp-tools) 2026-04-22 audit):

- Searching and listing competitions, datasets, models, notebooks
- Downloading competition data and datasets
- Submitting predictions to competitions
- Pushing and executing notebooks on Kaggle Kernels
- Publishing datasets and models
- **Hackathon writeup retrieval** — overview pages, submission rosters, full writeup bodies
- **Benchmark task creation** — `create_benchmark_task_from_prompt`
- **Episode/simulation data** — agent logs, replays, per-submission episode listings

See [`skills/kaggle/modules/kllm/references/mcp-reference.md`](skills/kaggle/modules/kllm/references/mcp-reference.md) for the full inventory with status flags (PASS / KNOWN_FAIL / role-gated).

The MCP server requires `KAGGLE_API_TOKEN` to be set.

## Security

- **No automatic persistence**: No cron jobs or launchd plists are auto-installed
- **No dynamic code execution**: All imports are explicit and static (no `__import__()`, `eval()`, `exec()`)
- **Untrusted content handling**: Scraped content is wrapped in `<untrusted-content>` boundary markers
- Credentials stored in `~/.kaggle/access_token` (chmod 600) — never logged or echoed

## Project Structure

```
kaggle-skill/
├── .claude-plugin/plugin.json    # Claude Code plugin manifest
├── .mcp.json                     # Bundled Kaggle MCP server (Claude Code)
├── PRIVACY.md                    # Privacy policy
├── skills/kaggle/
│   ├── SKILL.md                  # Main skill definition (all agents)
│   ├── shared/                   # Unified credential checker
│   └── modules/
│       ├── registration/         # Account & credential setup
│       ├── comp-report/          # Competition landscape reports
│       ├── kllm/                 # Core Kaggle interaction
│       └── badge-collector/      # Badge earning automation
└── README.md
```

## Compatibility

| Platform | Status |
|----------|--------|
| **Claude Code** (CLI, VS Code, JetBrains, Desktop) | Tested |
| **OpenClaw** | Tested |
| **Codex** | Compatible |
| **Gemini CLI** | Compatible |
| **Cursor** | Compatible |
| **GitHub Copilot** | Compatible |
| **Cline** | Compatible |
| **Amp** | Compatible |
| 35+ agents via skills.sh | Compatible |

**Network requirements:** outbound HTTPS to `api.kaggle.com`, `www.kaggle.com`, and `storage.googleapis.com`.

## License

MIT — see [LICENSE](LICENSE)

## Privacy

See [PRIVACY.md](PRIVACY.md) — this skill collects no data. All credentials and processing remain local.
