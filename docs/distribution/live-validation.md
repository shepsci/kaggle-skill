# Live Validation Notes

Last run: 2026-07-03

## Kaggle CLI

Live CLI checks should run against an isolated Python 3.11 environment with the
project's declared Kaggle CLI floor, so validation does not depend on whichever
`kaggle` binary happens to be installed globally:

```bash
uv run --no-project --python 3.11 --with "kaggle>=2.2.3" kaggle --version
```

Result:

```text
Kaggle CLI 2.2.3
```

Live tests:

```bash
uv run --no-project --python 3.11 \
  --with pytest \
  --with requests \
  --with "kaggle>=2.2.3" \
  --with "kagglehub>=1.0.0" \
  --with "kagglesdk>=0.1.33,<1.0" \
  python -m pytest tests/integration/test_cli_live.py --run-live -q
```

Result: passed.

## Kaggle MCP

Live tests:

```bash
uv run --no-project --python 3.11 \
  --with pytest \
  --with requests \
  python -m pytest --run-live \
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
marketplace manifest is sufficient for installation.
The pytest smoke also validates the plugin, adds this repository as a temporary
local Claude marketplace, installs `kaggle@shepsci`, and verifies that Claude
lists the installed plugin.
