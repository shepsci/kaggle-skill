# Demo Script for the README Screencast

The README demo is recorded after the documentation has been refreshed.
Re-record after material install, credential, or workflow changes.

## Goal of the demo

Show the current v2.4.0 experience in 60-90 seconds:

1. Install `kaggle@shepsci` from the in-repo Claude marketplace manifest.
2. Verify Kaggle credentials without displaying secrets.
3. Summarize the Titanic competition pages.
4. Retrieve recent Kaggle discussion/writeup content.

## Setup before recording

```bash
# Fresh Claude Code local plugin state with no kaggle plugin installed.
# Have a valid Kaggle API token available before recording, but do not paste
# or print the token during the cast.
# Use at least 100 columns x 30 rows for legibility.
asciinema --version
```

If credentials are already present in `~/.kaggle/access_token` or
`KAGGLE_API_TOKEN`, the demo should show only the verification result.

## Recording commands used in the cast

These are the commands shown in the cast:

```bash
claude plugin marketplace add shepsci/kaggle-skill --scope local
claude plugin install kaggle@shepsci --scope local

python3 skills/kaggle/modules/setup/scripts/check_all_credentials.py

python3 skills/kaggle/modules/competitions/scripts/competition_pages.py \
  --competition titanic --summary

kaggle --version
python3 skills/kaggle/modules/discussions/scripts/forums.py forum-topics \
  --category competition_write_ups --sort-by recent --page-size 2 --format json -q
```

Keep the terminal focused on confirmations, summaries, and short wrapped
Kaggle-supplied snippets. Do not scroll through full forum/writeup bodies,
pagination tokens, or long live API payloads in the cast.

The credential-check output is shown redacted: the real masked-token line is
replaced with a fixed `[OK] API Token: [redacted] (Legacy scoped API token)`
line before the cast is committed, so no token fragment ever ships in the
`.cast` file.

## Recording with asciinema

```bash
cd ~/work/kaggle-skill
bash docs/demo/record.sh
```

After recording:

```bash
asciinema cat docs/demo/install-and-demo.cast
asciinema upload docs/demo/install-and-demo.cast
```

Only add the returned cast id to public docs after replaying the uploaded cast
and confirming it is clean:

```markdown
[![asciicast](https://asciinema.org/a/<cast-id>.svg)](https://asciinema.org/a/<cast-id>)
```

Use an authenticated asciinema CLI for a permanent public URL. The source
`.cast` file should still be committed so the demo can be replayed or
re-uploaded.

Before committing the cast, scan it for secrets:

```bash
rg -n "KGAT_|KAGGLE_API_TOKEN|access_token|kaggle\\.json|\"key\"|\"username\"" \
  docs/demo/*.cast
```

The scan should return no credential material. Mentions of safe file names in
documentation text are acceptable only outside the committed cast.

## Additional cast plans

The demo library includes short task-focused source casts. Re-record these
after material changes to the relevant command surface.

### Antigravity CLI install

Goal: show the recommended terminal-first install path for new Google agent CLI
users.

```bash
agy --version
npx skills add shepsci/kaggle-skill
```

Source cast: [antigravity-install.cast](antigravity-install.cast)

### Antigravity MCP config

Goal: show the `serverUrl` config shape and `/mcp` verification path.

```bash
mkdir -p .agents
$EDITOR .agents/mcp_config.json
agy
/mcp
```

Source cast: [mcp-config.cast](mcp-config.cast)

### Competition briefing

Goal: show the shortest evidence-first competition overview path.

```bash
python3 skills/kaggle/modules/setup/scripts/check_all_credentials.py
python3 skills/kaggle/modules/competitions/scripts/competition_pages.py \
  --competition titanic --summary
```

Source cast: [competition-brief.cast](competition-brief.cast)

### Vesuvius top writeups

Goal: show a quick agent-facing prompt that retrieves leaderboard solution
writeup links and previews for the top 3 ranked Vesuvius Challenge surface
detection submissions.

```bash
claude
Use the kaggle skill to retrieve and preview the writeups from the top 3 ranked submissions in the Vesuvius Challenge surface detection competition.
python3 skills/kaggle/modules/discussions/scripts/leaderboard_writeups.py \
  vesuvius-challenge-surface-detection --top-k 3 --preview --pretty
```

Source cast: [vesuvius-top-writeups.cast](vesuvius-top-writeups.cast)

### Hackathon writeups

Goal: show the overview, roster, and fetch sequence while keeping Kaggle text
inside untrusted-content markers.

```bash
python3 skills/kaggle/modules/competitions/hackathons/scripts/hackathon_overview.py \
  --competition kaggle-measuring-agi --summary
python3 skills/kaggle/modules/competitions/hackathons/scripts/list_writeups.py \
  --competition kaggle-measuring-agi --page-size 2 --max-pages 1
python3 skills/kaggle/modules/competitions/hackathons/scripts/fetch_writeup.py \
  --writeup-id 71599 --pretty | head -c 1200
```

Source cast: [hackathon-writeups.cast](hackathon-writeups.cast)

### Codex CLI install

Goal: show the recommended isolated-environment install path for Codex CLI
users.

```bash
CODEX_HOME=... HOME=... codex plugin marketplace add shepsci/kaggle-skill --ref main --json
CODEX_HOME=... HOME=... codex plugin add kaggle@shepsci --json
```

Source cast: [codex-install.cast](codex-install.cast)
