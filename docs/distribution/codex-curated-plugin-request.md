# Codex Plugin Distribution Request Package

Status: ready for maintainer/product review after the release PR merges.

Official Codex docs used:

- Build plugins: https://developers.openai.com/codex/plugins/build
- Plugin install/deeplink behavior: https://developers.openai.com/codex/app/commands

Codex public curated status is not claimed by this repository. The OpenAI docs
describe the curated marketplace, repo marketplaces, personal marketplaces, and
workspace sharing, but they do not currently document a public self-serve
submission form for the curated marketplace. This package is the review packet
to send through the appropriate OpenAI/plugin partner channel if one is made
available.

## Plugin Metadata

- Public plugin name: `kaggle`
- Public skill name: `kaggle`
- Repository: https://github.com/shepsci/kaggle-skill
- Marketplace name: `shepsci`
- Category: Data Science
- License: MIT
- Privacy policy: https://github.com/shepsci/kaggle-skill/blob/main/PRIVACY.md
- Third-party notices: `THIRD_PARTY_NOTICES.md`

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

## Review Notes

- The plugin includes a remote Kaggle MCP server config that requires the
  user's Kaggle API token.
- All Kaggle-supplied text handled by bundled scripts is wrapped in
  `<untrusted-content>` markers.
- The public copy explicitly says Codex curated listing is a separate review
  process and does not claim curated status.
- The repo marketplace uses `source.path: "./"` so the plugin resolves from
  the repository root after Codex clones the marketplace.
