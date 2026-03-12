# kaggle-skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/shepsci/kaggle-skill?style=social)](https://github.com/shepsci/kaggle-skill)

A Claude Code plugin (and agent skill) for everything Kaggle: account setup, competition landscape reports, dataset/model downloads, notebook execution, competition submissions, badge collection, and general Kaggle questions.

Works with **Claude Code** (CLI, VS Code, JetBrains, Desktop) and other agentic systems that support the SKILL format (gemini-cli, Cursor, etc.).

**Bundled Kaggle MCP Server:** This plugin automatically configures the [official Kaggle MCP server](https://www.kaggle.com/docs/mcp), giving Claude direct access to 40+ Kaggle tools (search competitions, download datasets, push notebooks, etc.).

## Modules

- **Registration** — Account creation, API token generation, credential storage
- **Competition Reports** — Landscape reports with API + Playwright scraping
- **Kaggle Interaction (kllm)** — kagglehub, kaggle-cli, MCP Server, UI workflows
- **Badge Collector** — Systematic badge earning across 5 phases (~38 automatable)

## Installation

### Claude Code Plugin (recommended)

```bash
# Install from marketplace
/plugin install kaggle-skill

# Or install from GitHub directly
claude --plugin-dir /path/to/kaggle-skill
```

### Via skills.sh (OpenClaw)

```bash
npx skills add shepsci/kaggle-skill
```

### Manual

```bash
git clone https://github.com/shepsci/kaggle-skill.git
pip install kagglehub kaggle python-dotenv requests
```

## Prerequisites

- Python 3.9+
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

The plugin also supports legacy credentials (`~/.kaggle/kaggle.json`). Run the credential checker for details:
```bash
python3 shared/check_all_credentials.py
```

## Usage

Once installed, Claude automatically detects the skill when you mention anything Kaggle-related:

- "Set up my Kaggle credentials"
- "Generate a Kaggle competition report"
- "Download the Titanic dataset"
- "Earn Kaggle badges"
- "Enter a Kaggle competition"
- "What competitions are running right now?"

## Bundled MCP Server

This plugin includes a `.mcp.json` that configures the official Kaggle MCP server. When installed, Claude Code can directly call Kaggle MCP tools for:

- Searching and listing competitions, datasets, models, notebooks
- Downloading competition data and datasets
- Submitting predictions to competitions
- Pushing and executing notebooks on Kaggle Kernels
- Publishing datasets and models

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
├── .mcp.json                     # Bundled Kaggle MCP server
├── skills/kaggle/
│   ├── SKILL.md                  # Main skill definition
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
| Claude Code (CLI, VS Code, JetBrains) | Tested |
| gemini-cli | Compatible |
| Cursor | Compatible |
| OpenClaw | Tested |

**Network requirements:** outbound HTTPS to `api.kaggle.com`, `www.kaggle.com`, and `storage.googleapis.com`.

## License

MIT
