# kaggle-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-kaggle--skill-blue)](https://skills.sh/shepsci/kaggle-skill/kaggle)
[![ClawHub](https://img.shields.io/badge/ClawHub-kaggle-green)](https://clawhub.ai/skills/kaggle)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/shepsci/kaggle-skill?style=social)](https://github.com/shepsci/kaggle-skill)

An agent skill for everything Kaggle: account setup, competition landscape reports, dataset/model downloads, notebook execution, competition submissions, **hackathon writeup retrieval**, badge collection, and general Kaggle questions.

Works with **any AI coding agent** that supports the SKILL format — including [Claude Code](https://claude.com/claude-code), [OpenClaw](https://openclaw.ai), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Cursor](https://cursor.com), [Codex](https://openai.com/codex), and [35+ more agents via skills.sh](https://skills.sh).

## Available On

| Platform | Link | Install Command |
|----------|------|-----------------|
| **skills.sh** | [skills.sh/shepsci/kaggle-skill](https://skills.sh/shepsci/kaggle-skill/kaggle) | `npx skills add shepsci/kaggle-skill` |
| **ClawHub** | [clawhub.ai/skills/kaggle](https://clawhub.ai/skills/kaggle) | `clawhub install kaggle` |
| **Claude Code Marketplace** | [shepsci/claude-marketplace](https://github.com/shepsci/claude-marketplace) | `/plugin marketplace add shepsci/claude-marketplace` then `/plugin install kaggle-skill@shepsci` |

## Modules

- **Registration** — Account creation, API token generation, credential storage
- **Competition Reports** — Landscape reports (Python API + optional Playwright via host agent)
- **Kaggle Interaction (kllm)** — kagglehub, kaggle-cli, MCP Server (66 tools), UI workflows. Includes the **`hackathon/`** sub-module for writeup retrieval and overview/rubric extraction.
- **Badge Collector** — Systematic badge earning across 5 phases (~38 automatable; ~30 single-session, the rest are multi-day streaks or manual-walkthrough fallbacks)

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
python3 skills/kaggle/shared/check_all_credentials.py
```

## Usage

Once installed, your agent automatically detects the skill when you mention anything Kaggle-related:

- "Set up my Kaggle credentials"
- "Summarize the rules and evaluation metric for the titanic competition"
- "Generate a Kaggle competition landscape report for the last 30 days"
- "Download the Titanic dataset"
- "Pull every writeup from kaggle-measuring-agi and group by track"
- "What badges can I still earn through API activity?"
- "Push this notebook to Kaggle Kernels and tell me when it finishes"
- "What competitions are running right now?"

### Quick examples (run from the agent OR directly from a shell)

#### Pull the rules + evaluation metric for any competition

```bash
python3 skills/kaggle/modules/kllm/scripts/list_competition_pages.py \
    --competition titanic --summary
# → page count, key-page detection (rules / evaluation / data-description / timeline)

python3 skills/kaggle/modules/kllm/scripts/list_competition_pages.py \
    --competition titanic --page evaluation
# → just the evaluation page content (host-authored markdown/HTML)
```

#### Enumerate every writeup in a hackathon

```bash
python3 skills/kaggle/modules/kllm/hackathon/scripts/list_writeups.py \
    --competition kaggle-measuring-agi --array | jq '.total_count'
# → 1069
```

#### Fetch a specific writeup body with the safe fallback chain

```bash
python3 skills/kaggle/modules/kllm/hackathon/scripts/fetch_writeup.py --writeup-id 71617
# → tries get_writeup → get_writeup_by_topic → get_writeup_by_slug; first wins
```

#### Verify all 66 MCP tools work against the live server

```bash
pytest tests/integration/test_mcp_live.py --run-live -v
# → 33 endpoint probes + tool-inventory drift check
```

All script output that contains Kaggle-supplied text (overview pages, writeup
bodies, submission rosters) is wrapped in
`<untrusted-content source="kaggle-mcp" tool="...">` markers so the agent
treats it as data, not directives. Enforced by
`tests/security/test_untrusted_content_wrappers.py`.

## Bundled MCP Server (Claude Code)

When installed as a Claude Code plugin, this skill includes a `.mcp.json` that configures the official Kaggle MCP server, giving direct access to **66 Kaggle tools** (verified live on 2026-05-04 in `tests/integration/test_mcp_live.py`; baseline inventory comes from the [shepsci/kmcp-tools](https://github.com/shepsci/kmcp-tools) 2026-04-22 audit):

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

Each property below is enforced by a test in `tests/security/` — claims that aren't tested are claims that drift.

| Property | Enforced by |
|---|---|
| No `eval` / `exec` / `compile` / `__import__` in any script | `tests/security/test_no_dynamic_eval.py` |
| Credentials never echoed to stdout / stderr / logs | `tests/security/test_no_credential_leakage.py` |
| Kaggle-supplied text wrapped in `<untrusted-content>` boundaries (prompt-injection guard) | `tests/security/test_untrusted_content_wrappers.py` |
| Zip archives extracted with path-traversal protection (no zip-slip) | `tests/security/test_zip_slip_protection.py` |
| Dataset slugs validated against `owner/name` regex before shell use | `tests/security/test_dataset_slug_validation.py` |
| `SessionStart` hook does not auto-`pip install` or source `.env` from CWD | `tests/security/test_session_start_hook_safety.py` |
| `~/.kaggle/access_token` and `kaggle.json` auto-tightened to mode 0600 | `skills/kaggle/shared/check_all_credentials.py:_ensure_mode_600` |
| `.mcp.json` uses HTTPS + env-var token substitution (no literal token) | `tests/manifest/test_mcp_json_valid.py` |
| No Phase 5 cron job / launchd plist auto-installed | Phase 5 generates a script only; user opts in |

Network egress: scripts only contact `*.kaggle.com`, `storage.googleapis.com`, `pypi.org`, `files.pythonhosted.org`, and `github.com`. Allowlist is in `.claude/settings.json`.

Reviewed comprehensively in v2.2.0; all MEDIUM findings fixed (zip-slip, untrusted-content wrappers, SessionStart hook tightening). See PR description for details.

## Project Structure

```
kaggle-skill/
├── .claude-plugin/plugin.json     # Claude Code plugin manifest (v2.x)
├── .claude/settings.json          # Per-plugin permissions + SessionStart hook
├── .mcp.json                      # Bundled Kaggle MCP server (66 tools)
├── PRIVACY.md                     # Privacy policy
├── docs/demo/                     # Screencast script + vhs tape + asciinema recorder
├── skills/kaggle/
│   ├── SKILL.md                   # Main skill definition (all agents)
│   ├── shared/                    # mcp_client.py + unified credential checker
│   └── modules/
│       ├── registration/          # Account & credential setup
│       ├── comp-report/           # Competition landscape reports
│       ├── kllm/                  # Core Kaggle interaction (66-tool MCP, kagglehub, CLI)
│       │   ├── references/
│       │   │   └── competition-overview.md   # list_competition_pages reference
│       │   └── hackathon/         # MCP-driven hackathon workflows (sub-module of kllm)
│       │       ├── README.md
│       │       ├── references/    # hackathon-endpoints / benchmark-endpoints / episode-endpoints
│       │       └── scripts/       # list_writeups, fetch_writeup, hackathon_overview
│       └── badge-collector/       # Badge earning automation
└── tests/
    ├── unit/                      # Mock-backed unit tests (no network)
    ├── manifest/                  # Plugin/skill metadata validation
    ├── security/                  # Defensive guards (eval, leakage, zip-slip, etc.)
    ├── integration/               # Live MCP probes (--run-live)
    └── e2e/                       # Manual install round-trip checklist
```

## Compatibility

| Platform | Status |
|----------|--------|
| **Claude Code** (CLI, VS Code, JetBrains, Desktop) | Tested |
| **OpenClaw** | Tested |
| **Codex** | Compatible |
| **Gemini CLI** | Tested |
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
