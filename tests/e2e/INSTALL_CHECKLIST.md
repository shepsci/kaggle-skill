# Manual Install Round-Trip Checklist

Run this once per release in a fresh Claude Code session. Anything that needs a
real slash command, browser, or Kaggle account interaction lives here rather
than in the automated test suite.

## Setup

- [ ] Fresh Claude Code session.
- [ ] No `kaggle` plugin currently installed (`/plugin` Installed tab is clean).
- [ ] `KAGGLE_API_TOKEN` or `~/.kaggle/access_token` available for MCP checks.

## Marketplace Install

- [ ] `/plugin marketplace add shepsci/kaggle-skill` returns success.
- [ ] `/plugin marketplace list` shows the `shepsci` catalog.
- [ ] `/plugin install kaggle@shepsci` returns success with no version mismatch warning.
- [ ] `/plugin` Installed tab shows `kaggle` at version `2.3.0`, matching
      `.claude-plugin/plugin.json` and `pyproject.toml`.

## Bundled MCP Server

- [ ] Ask: "list the Kaggle MCP tools" - agent reports about 70 tools.
- [ ] Ask: "summarize the rules and evaluation metric for the titanic competition" -
      agent calls `list_competition_pages` and returns rules plus evaluation summary.
- [ ] Ask: "search recent Kaggle competition writeup discussions and show three useful results" -
      agent uses the forum/topic or writeup workflow without exposing credentials.

## SessionStart Hook

- [ ] Open a new Claude Code session in the cloned repo. The `setup_env.sh`
      SessionStart hook fires automatically.
- [ ] Output includes `[OK] access_token already exists` or
      `[INFO] No Kaggle credentials found`.
- [ ] Output does not include `pip install` activity.

## Alternate Distributions

- [ ] `npx skills add shepsci/kaggle-skill` succeeds in a separate temp dir.
- [ ] `clawhub install kaggle` succeeds if ClawHub is available.
- [ ] `codex plugin marketplace add shepsci/kaggle-skill --ref main` followed by
      `codex plugin add kaggle@shepsci` succeeds in a temporary `CODEX_HOME`.

## Cross-Platform Testing

The "Tested" platforms in the README compatibility table are exercised by the
maintainer per release. These attestations keep the README grounded in an
explicit process instead of a loose compatibility claim.

- [x] Claude Code - covered by the install round-trip above.
- [x] OpenClaw - install with `clawhub install kaggle`, then run credential and
      Titanic summary smoke prompts.
- [x] Antigravity CLI (`agy`) - install with `npx skills add shepsci/kaggle-skill`,
      then run credential and Titanic summary smoke prompts.
- [x] Gemini CLI - legacy compatibility smoke test with
      `npx skills add shepsci/kaggle-skill`, then the same credential and
      Titanic summary smoke prompts. Prefer Antigravity CLI (`agy`) for new
      installs because it replaced Gemini CLI.
- [x] Codex - covered by the temporary `CODEX_HOME` repo marketplace smoke in
      Alternate Distributions and `tests/e2e/test_plugin_install_smoke.py`.

If "Tested" is asserted for a platform, that platform needs a row in this list.
`tests/manifest/test_no_false_claims.py::test_platform_tested_status_is_attested`
enforces this.

## Cleanup

- [ ] `/plugin uninstall kaggle@shepsci` removes the plugin cleanly.

If any check fails, open an issue with the failing step, error output, and
Claude Code version (`claude --version`).
