# kaggle-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-kaggle--skill-blue)](https://skills.sh/shepsci/kaggle-skill/kaggle)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/shepsci/kaggle-skill?style=social)](https://github.com/shepsci/kaggle-skill)

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
| OpenClaw | Tested |

**Network requirements:** outbound HTTPS to `api.kaggle.com`, `www.kaggle.com`, and `storage.googleapis.com`.

## Installation

### Via skills.sh

```bash
npx skills add shepsci/kaggle-skill
```

### Manual

```bash
git clone https://github.com/shepsci/kaggle-skill.git
cd kaggle-skill
pip install kagglehub kaggle python-dotenv requests
```

## Prerequisites

- Python 3.9+
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

## Tested Environments

| Environment | Date | Python | Result |
|-------------|------|--------|--------|
| **OpenClaw** (macOS arm64, Darwin 25.2.0) | 2026-02-11 | 3.9 | ✅ All tests pass |

### Test Results Summary (OpenClaw, 2026-02-11)

| Category | Test | Result | Notes |
|----------|------|--------|-------|
| **Credentials** | check_all_credentials.py | ✅ Pass | All 3 credential types detected |
| | check_registration.py | ✅ Pass | |
| | check_credentials.py (kllm) | ✅ Pass | |
| | network_check.sh | ✅ Pass | Both endpoints reachable |
| | setup_env.sh (registration) | ✅ Pass | kaggle.json already configured |
| | setup_env.sh (kllm) | ✅ Pass | |
| **Competition Reports** | list_competitions.py | ✅ Pass | Returns JSON with active competitions |
| | competition_details.py --slug titanic | ✅ Pass | Files, leaderboard, kernels returned |
| **Kaggle CLI** | kaggle competitions list | ✅ Pass | |
| | kaggle datasets list | ✅ Pass | |
| | kaggle datasets files heptapod/titanic | ✅ Pass | |
| | kaggle datasets download heptapod/titanic | ✅ Pass | 83KB downloaded |
| | kaggle kernels list | ✅ Pass | |
| | kaggle models list | ✅ Pass | |
| **kagglehub** | dataset_download("heptapod/titanic") | ✅ Pass | Cached locally |
| | competition_download("titanic") | ⚠️ Expected fail | 401 — rules not accepted via API; use CLI/UI |
| **MCP Server** | tools/list | ✅ Pass | 40+ tools returned |
| | search_competitions | ✅ Pass | Requires KAGGLE_API_TOKEN (KGAT_), not KAGGLE_KEY |
| | get_competition (titanic) | ✅ Pass | |
| | search_datasets | ✅ Pass | |
| | get_dataset_info | ✅ Pass | |
| | search_notebooks | ✅ Pass | |
| | list_models | ✅ Pass | |
| **Badge Collector** | orchestrator.py --status | ✅ Pass | 0/55 earned (fresh) |
| | orchestrator.py --dry-run --phase 1 | ✅ Pass | 16 badges planned |
| **Shell Scripts** | cli_download.sh (parameterized) | ✅ Pass | Downloads heptapod/titanic |
| | cli_execute.sh (usage check) | ✅ Pass | Parameterized, requires args |
| | cli_competition.sh (usage check) | ✅ Pass | Parameterized, requires args |
| | cli_publish.sh (usage check) | ✅ Pass | Parameterized, requires args |
| | poll_kernel.sh (usage check) | ✅ Pass | Parameterized, requires args |
| | kagglehub_download.py --dataset | ✅ Pass | Parameterized with argparse |
| | kagglehub_publish.py --help | ✅ Pass | Shows usage |

**Key finding:** MCP server requires `KAGGLE_API_TOKEN` (KGAT_ prefix), not the legacy `KAGGLE_KEY`. The mcp-reference.md has been updated accordingly.

## License

MIT
