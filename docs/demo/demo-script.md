# What the demo casts run

The casts in this folder are built by `tools/build_casts.py`, version 2.5.0
of the skill. Each one runs the commands below and keeps their output. Rebuild
them after a change to a command or to what it prints.

Everything here reads. Nothing is submitted or published, and no credential
is printed: the casts avoid the credential checker, because its output names
credential files.

## vesuvius-top-writeups

The request an agent gets: "retrieve and preview the writeups of the top 3
teams in the Vesuvius Challenge surface detection competition".

```bash
python3 skills/kaggle/modules/discussions/scripts/leaderboard_writeups.py \
  vesuvius-challenge-surface-detection --top-k 3 --preview --pretty
```

No credential is needed.

## install-and-demo

```bash
claude plugin marketplace add shepsci/kaggle-skill
claude plugin install kaggle@shepsci
python3 skills/kaggle/modules/competitions/scripts/competition_pages.py --competition titanic --summary
python3 skills/kaggle/modules/discussions/scripts/forums.py forum-topics \
  --category competition_write_ups --sort-by recent --page-size 2
```

The builder installs from the local checkout, in a throwaway config folder, so
the first line in the cast reads `claude plugin marketplace add ./kaggle-skill`.

## competition-brief

```bash
python3 skills/kaggle/modules/competitions/scripts/competition_pages.py --competition titanic --summary
python3 skills/kaggle/modules/competitions/scripts/competition_pages.py --competition titanic --page evaluation
```

No credential is needed.

## hackathon-writeups

```bash
python3 skills/kaggle/modules/competitions/hackathons/scripts/hackathon_overview.py \
  --competition kaggle-measuring-agi --summary
python3 skills/kaggle/modules/competitions/hackathons/scripts/list_writeups.py \
  --competition kaggle-measuring-agi --winner-only --array
```

The second command needs a credential, and an account that is a host, judge,
or teammate of that hackathon.

## mcp-config

```bash
cat .mcp.json
python3 tools/mcp_snapshot.py --check
```

## codex-install

```bash
codex plugin marketplace add shepsci/kaggle-skill --ref main --json
codex plugin add kaggle@shepsci --json
```

Built from the local checkout in a throwaway `CODEX_HOME`.

## antigravity-install

```bash
agy --version
npx skills add shepsci/kaggle-skill --list
```

`--list` shows what the skills CLI finds without installing it. To install
for one agent: `npx skills add shepsci/kaggle-skill -a antigravity`.

## Before committing a cast

```bash
python3 -m pytest tests/manifest/test_docs_freshness.py tests/manifest/test_demo_gifs_animated.py -q
```
