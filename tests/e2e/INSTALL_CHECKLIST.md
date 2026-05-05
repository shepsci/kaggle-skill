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
- [ ] `/plugin install kaggle-skill@shepsci` — returns success, no version mismatch warnings
- [ ] `/plugin` Installed tab shows `kaggle-skill` at the version that matches
      `.claude-plugin/plugin.json` and `pyproject.toml` (currently 2.2.0)

## Bundled MCP server

- [ ] In a chat, ask: "list the Kaggle MCP tools" — agent reports ~66 tools (sanity check)
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

## Cleanup

- [ ] `/plugin uninstall kaggle-skill@shepsci` — clean removal, no leftover files

If any check fails, open an issue with the failing step + the error output and
the Claude Code version (`claude --version`).
