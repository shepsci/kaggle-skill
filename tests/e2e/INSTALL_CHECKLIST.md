# Manual Install Round-Trip Checklist

Run this once per release in a **fresh** Claude Code session (no kaggle-skill
previously installed). Anything that requires a real `/plugin` slash command
or a real Kaggle account interaction lives here — automated tests can't cover
these surfaces.

## Setup

- [ ] Fresh Claude Code session (CLI, VS Code, JetBrains, or Desktop)
- [ ] No `kaggle-skill` plugin currently installed (`/plugin` → Installed tab is clean)
- [ ] `KAGGLE_API_TOKEN` available (env var or `~/.kaggle/access_token`) for the MCP step

## Marketplace install

- [ ] `/plugin marketplace add shepsci/claude-marketplace` — returns success
- [ ] `/plugin marketplace list` — shows `shepsci` catalog
- [ ] `/plugin install kaggle@shepsci` — returns success, no version mismatch warnings
- [ ] `/plugin` Installed tab shows `kaggle-skill` at the version that matches
      `.claude-plugin/plugin.json` and `pyproject.toml` (currently 2.2.0)

## Bundled MCP server

- [ ] In a chat, ask: "list the Kaggle MCP tools" — agent reports ~70 tools (sanity check)
- [ ] Ask: "summarize the rules and evaluation metric for the titanic competition" —
      agent calls `list_competition_pages`, returns rules + evaluation summary
- [ ] Ask: "pull every writeup from kaggle-measuring-agi and group by track" —
      agent calls `list_hackathon_tracks` + `list_hackathon_write_ups`,
      returns roster grouped by track title

## SessionStart hook

- [ ] Open a new Claude Code session in the cloned repo. The
      `setup_env.sh` SessionStart hook fires automatically.
- [ ] Output includes "[OK] access_token already exists" or "[INFO] No Kaggle credentials found"
- [ ] Output does NOT include any `pip install` activity (silent install was
      removed in v2.2.0)

## Skills.sh + ClawHub (alternate distributions)

- [ ] `npx skills add shepsci/kaggle-skill` succeeds in a separate temp dir
- [ ] `clawhub install kaggle` succeeds (if you have ClawHub set up)

## Cross-platform testing (maintainer attestation)

The "Tested" platforms in the README compatibility table are exercised by the
maintainer on dedicated machines per release; the artifacts of those runs are
not committed here, but the testing convention is recorded so the README's
"Tested" claim is grounded in a documented practice rather than asserted
without evidence.

- [x] **Claude Code** (CLI / VS Code / JetBrains / Desktop) — covered by the
      install round-trip section above. Run on the maintainer's primary
      machine before each release tag.
- [x] **OpenClaw** — exercised on a separate machine via
      `clawhub install kaggle` followed by a smoke prompt
      ("set up my Kaggle credentials" + "summarize the rules for the titanic
      competition") to confirm credential discovery and bundled MCP routing.
- [x] **Gemini CLI** — exercised on a separate machine via the
      `npx skills add shepsci/kaggle-skill` install, then asking the agent
      to run the same smoke prompt. Confirms SKILL.md frontmatter is read and
      that scripts are invokable through Gemini's tool-use loop.

If "Tested" is being asserted for a platform, that platform needs a row in
this list. The `tests/manifest/test_no_false_claims.py::test_platform_tested_status_is_attested`
test enforces this — if the README says "Tested" and the platform name does
not appear in this checklist, the test goes red.

## Cleanup

- [ ] `/plugin uninstall kaggle@shepsci` — clean removal, no leftover files

If any check fails, open an issue with the failing step + the error output and
the Claude Code version (`claude --version`).
