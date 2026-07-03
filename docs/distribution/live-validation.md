# Live Validation Notes

Last run: 2026-07-03

## Kaggle CLI

The system Kaggle CLI was `2.0.0`, below the new project floor. Live CLI
checks were therefore run against an isolated Python 3.11 virtual environment:

```bash
/opt/homebrew/bin/python3.11 -m venv /tmp/kaggle-skill-live-venv
/tmp/kaggle-skill-live-venv/bin/python -m pip install --upgrade pip
/tmp/kaggle-skill-live-venv/bin/python -m pip install \
  "kaggle>=2.2.3" "kagglesdk>=0.1.33,<1.0"
/tmp/kaggle-skill-live-venv/bin/kaggle --version
```

Result:

```text
Kaggle CLI 2.2.3
```

Live tests:

```bash
KAGGLE_CLI_BIN=/tmp/kaggle-skill-live-venv/bin/kaggle \
  python3 -m pytest --run-live tests/integration/test_cli_live.py -q
```

Result: passed.

## Kaggle MCP

Live tests:

```bash
python3 -m pytest --run-live \
  tests/integration/test_mcp_live.py \
  tests/manifest/test_mcp_inventory_drift.py -q
```

Result: passed. The live server exposed 70 tools on 2026-07-03.

## Codex Plugin

Validation:

```bash
python3 "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" .
RUN_CODEX_PLUGIN_SMOKE=1 python3 -m pytest \
  tests/e2e/test_plugin_install_smoke.py::test_codex_plugin_marketplace_smoke -q
```

Result: passed.

## Claude Plugin

Claude Code was installed from the official native install script because the
CLI was not present locally:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Installed version:

```text
2.1.199 (Claude Code)
```

Validation:

```bash
$HOME/.local/bin/claude plugin validate .
$HOME/.local/bin/claude plugin validate <claude-marketplace-root>
tmp=$(mktemp -d /tmp/kaggle-claude-direct.XXXXXX)
HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/xdg" \
  claude plugin marketplace add shepsci/kaggle-skill --scope local
HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/xdg" \
  claude plugin install kaggle@shepsci --scope local
PATH="$HOME/.local/bin:$PATH" RUN_CLAUDE_PLUGIN_SMOKE=1 python3 -m pytest \
  tests/e2e/test_plugin_install_smoke.py::test_claude_plugin_install_smoke -q
```

Result: passed. The direct smoke adds `shepsci/kaggle-skill` as the Claude
marketplace source, installs `kaggle@shepsci`, and verifies that the in-repo
marketplace manifest works without going through the separate personal catalog.
The pytest smoke also validates the plugin, adds this repository as a temporary
local Claude marketplace, installs `kaggle@shepsci`, and verifies that Claude
lists the installed plugin.
