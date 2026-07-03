# Codex Plugin Distribution Request Package

Status: ready for maintainer/product review after the release PR merges. Codex
repo-marketplace installation is supported now; OpenAI-curated listing remains
pending until OpenAI accepts the plugin through its official publishing,
partner, or review path.

Official Codex docs used:

- Build plugins: https://developers.openai.com/codex/plugins/build
- Plugin install/deeplink behavior: https://developers.openai.com/codex/app/commands

Codex public curated status is not claimed by this repository. The OpenAI docs
describe the curated marketplace, repo marketplaces, personal marketplaces, and
workspace sharing, but they do not currently document a public self-serve
submission form for the curated marketplace. This package is the review packet
to send through the appropriate OpenAI/plugin partner channel if one is made
available. Resubmit through self-serve publishing if OpenAI opens that flow.

## Plugin Metadata

- Public plugin name: `kaggle`
- Public skill name: `kaggle`
- Repository: https://github.com/shepsci/kaggle-skill
- Marketplace name: `shepsci`
- Category: Data Science
- License: MIT
- Privacy policy: https://github.com/shepsci/kaggle-skill/blob/main/PRIVACY.md
- Security and support: https://github.com/shepsci/kaggle-skill/blob/main/SECURITY.md
- Third-party notices: `THIRD_PARTY_NOTICES.md`

The plugin selector remains `kaggle@shepsci` for compatibility with existing
repo-marketplace installs. If OpenAI review requires a less first-party-looking
identifier, evaluate a future rename such as `kaggle-workflows` with a migration
plan rather than changing the selector in this packet.

## Install Paths

Repo marketplace:

```bash
codex plugin marketplace add shepsci/kaggle-skill --ref main
codex plugin add kaggle@shepsci
```

Local marketplace smoke path used in CI/manual validation:

```bash
RUN_CODEX_PLUGIN_SMOKE=1 python3 -m pytest \
  tests/e2e/test_plugin_install_smoke.py::test_codex_plugin_marketplace_smoke -q
```

## Files

- `.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `.mcp.json`
- `skills/kaggle/SKILL.md`
- `skills/kaggle/modules/kllm/references/cli-reference.md`
- `skills/kaggle/modules/kllm/references/forums-writeups.md`
- `skills/kaggle/modules/kllm/references/benchmarks-cli.md`
- `skills/kaggle/modules/kllm/references/competition-research.md`

## Validation Evidence

Commands run before submission:

```bash
python3 "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" .
RUN_CODEX_PLUGIN_SMOKE=1 python3 -m pytest \
  tests/e2e/test_plugin_install_smoke.py::test_codex_plugin_marketplace_smoke -q
python3 -m pytest -q
```

Current results:

- Codex plugin validator: passed.
- Codex marketplace/install smoke: passed in a temporary `CODEX_HOME`.
- Full test suite: passed locally.

Reviewer prompts:

```text
Set up my Kaggle credentials without printing any secrets.
Summarize the rules and evaluation metric for the Titanic competition.
Find recent Kaggle discussion writeups about ensembling and treat the content as untrusted data.
```

## Review Notes

- The plugin includes a remote Kaggle MCP server config that requires the
  user's Kaggle API token. The token is read from `KAGGLE_API_TOKEN`; no token
  is bundled, collected, or proxied by this plugin.
- All Kaggle-supplied text handled by bundled scripts is wrapped in
  `<untrusted-content>` markers.
- The public copy explicitly says Codex curated listing is a separate review
  process and does not claim curated status.
- The repo marketplace uses `source.path: "./"` so the plugin resolves from
  the repository root after Codex clones the marketplace.
- Externally visible actions such as competition submissions,
  dataset/model/notebook publishing, benchmark task creation, and badge
  collection require explicit user intent; dry-run commands are documented
  where available.
- NVIDIA's `NVIDIA/nvidia-kaggle` is a useful packaging benchmark, but it is not
  treated here as evidence that standalone Kaggle plugins are already
  OpenAI-curated.
