# kaggle-skill

An [OpenClaw-compatible](https://github.com/openclaw) skill for everything Kaggle: account setup, competition landscape reports, dataset/model downloads, notebook execution, competition submissions, badge collection, and general Kaggle questions.

Works with **any LLM or agentic coding system** that supports the SKILL format — including [Claude Code](https://claude.com/claude-code), [gemini-cli](https://github.com/google-gemini/gemini-cli), [Cursor](https://cursor.com), and others — so long as `api.kaggle.com`, `www.kaggle.com`, and `storage.googleapis.com` are network-reachable.

Merges four individual skills into a single self-contained package:
- **Registration** — Account creation, API key generation, credential storage
- **Competition Reports** — Landscape reports with Playwright-powered scraping
- **Kaggle Interaction (kllm)** — kagglehub, kaggle-cli, MCP Server, UI workflows
- **Badge Collector** — Systematic badge earning across 5 phases (~38 automatable)

## Compatibility

This skill is **agent-agnostic**. It uses standard tools (Bash, Read, WebFetch) and plain Python scripts, so it runs on any agentic system that can:

1. Read a `SKILL.md` file (OpenClaw format)
2. Execute shell commands
3. Reach Kaggle's endpoints over HTTPS

| Platform | Status |
|----------|--------|
| Claude Code | Tested |
| gemini-cli | Compatible |
| Cursor | Compatible |
| Any OpenClaw-compatible agent | Compatible |

**Network requirements:** outbound HTTPS to `api.kaggle.com`, `www.kaggle.com`, and `storage.googleapis.com`.

## Installation

### Via skills.sh

```bash
npx skills add shepsci/kaggle-skill
```

### Via Anthropic Marketplace

Search for `kaggle-skill` in the Claude Code skill marketplace.

### Via ClawHub / Open Claw

Install via the Open Claw Chrome extension or ClawHub directory.

### Manual

```bash
git clone https://github.com/shepsci/kaggle-skill.git
cd kaggle-skill
pip install kagglehub kaggle python-dotenv requests
```

## Prerequisites

- Python 3.11+
- `pip install kagglehub kaggle python-dotenv requests`
- Kaggle credentials (run the skill to set up)
- Optional: `pip install playwright && playwright install chromium` (for browser badges and competition reports)
- Optional: Playwright MCP tools in your agent (for competition report scraping)

## Usage

Once installed, your agent automatically detects the skill. Invoke it by asking anything Kaggle-related:

- "Set up my Kaggle credentials"
- "Generate a Kaggle competition report"
- "Download the Titanic dataset"
- "Earn Kaggle badges"
- "Enter a Kaggle competition"
- "What competitions are running right now?"

The skill walks through credential setup, generates a competition landscape report, and offers an interactive menu for further actions.

## Security

- Credentials are stored in `.env` (gitignored) and `~/.kaggle/kaggle.json` (chmod 600)
- The `.gitignore` excludes all credential files, API tokens, and downloaded data
- A `detect-secrets` pre-commit hook prevents accidental credential commits
- **Never** commit `.env`, `kaggle.json`, or any file containing API keys

## Project Structure

```
kaggle-skill/
├── skills/kaggle/
│   ├── SKILL.md                    # Main skill orchestrator
│   ├── shared/                     # Unified credential checker
│   └── modules/
│       ├── registration/           # Account & credential setup
│       ├── comp-report/            # Competition landscape reports
│       ├── kllm/                   # Core Kaggle interaction
│       └── badge-collector/        # Badge earning automation
├── .claude/settings.json           # Network allowlists + hooks
├── .claude-plugin/marketplace.json # Marketplace config
└── tests/                          # Test suite
```

## License

MIT
