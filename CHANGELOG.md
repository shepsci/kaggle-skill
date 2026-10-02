# Changelog

All notable changes to this project are documented in this file.

## 2.5.0 - 2026-09-30

Fixes found by running the skill against today's Kaggle CLI (2.2.4) and MCP
server (71 tools), plus a refresh of every reference.

### Fixed

- The bundled Kaggle MCP server now loads in Claude Code. `.mcp.json` lacked
  `"type": "http"`, so the entry was dropped without a message.
- Sign-in to the bundled MCP server completes in Claude Code. The entry now
  names the OAuth client ID. Without it, Claude Code registers itself, Kaggle
  answers with an empty `client_secret`, and the sign-in stops with
  `client_secret_basic authentication requires a client_secret`. Codex reads
  an entry of its own, `.codex-plugin/mcp.json`.
- `cli_execute.sh` and `poll_kernel.sh` detect the end of a notebook run. They
  read the quoted status only, retry a failed status call, and stop after a
  maximum wait.
- `list_competitions.py` and `competition_details.py` report real team
  counts, metrics, file sizes, and votes, and print valid JSON. Community
  competitions are included.
- Server errors are no longer reported as success. The MCP client decides by
  `isError`, not by words in the text.
- `list_writeups.py` filters winners (`winner: true`), reports a denial as a
  denial, flags an incomplete roster, and fills in `slug` and `url`.
- `models/cli_download.sh` asks for the version number the CLI needs, and
  `models/cli_publish.sh` creates the variation, uploads subfolders, and finds
  an existing model (`kaggle models get -p` crashes in 2.2.4).
- Kaggle CLI commands that fail with exit status 0 are treated as failures.
- `forums.py` rejects flags the CLI would ignore.
- Badges: `--dry-run` works without `--phase`, `--resume` retries unfinished
  badges, token-only users can run it, a badge is recorded as earned only when
  its action completed, and the catalog totals match (55 badges, 38 in
  phases).

### Security

- `allowed-tools` is now `Read Grep Glob`. The skill no longer pre-approves
  `Bash` or `WebFetch`.
- Text from Kaggle is printed inside blocks whose tag has a random suffix, so
  the text cannot close its block. Every script uses it, including the shell
  scripts, the competition scripts, and error output.
- Writeup previews are fetched without a credential and only from
  `www.kaggle.com`. The bundled MCP entries carry no credential.
- The MCP client no longer puts the token on a command line.
- The scripts clear `VERBOSE`, `VERBOSE_OUTPUT`, and `KAGGLE_API_ENVIRONMENT`
  before calling the Kaggle CLI, which otherwise prints the bearer token.
- Publish scripts refuse a folder that contains a credential file.
- Notebook output is downloaded only after its file names are checked, and
  competition archives are extracted with a path check.
- A `.env` file is read only when `KAGGLE_ENV_FILE` names it, and only its
  credential lines are used. The credential checker no longer writes anything.
- The kagglehub download scripts refuse an `--output-dir` that has files in
  it. kagglehub would delete them before downloading again.
- An OAuth access token is read from the last line of the CLI's output, and a
  value that is not a single token is never sent. HTTP errors are reported
  without the library's message, which can quote a header.
- `--verify` makes a call the server checks (`kaggle quota`). `kaggle config
  view` alone passes for a revoked legacy key.
- Dependency floors: `kaggle>=2.2.4`, `kagglehub>=1.0.2`, `requests>=2.32.4`.

### Changed

- `cli_competition.sh` is split into `cli_download.sh` and `cli_submit.sh`.
  Submitting is a dry run unless `--yes` is given.
- One credential checker, `check_all_credentials.py`, with `--verify` and
  `--json`. It follows the Kaggle CLI's order and sees `kaggle auth login`.
  `check_credentials.py` and `check_registration.py` are removed.
- Public reads need no credential: competition pages, hackathon overviews,
  leaderboard writeups, and content search.
- Exit codes are the same across scripts; see `SKILL.md`.
- The unused `.claude/settings.json` hook and the `.claude/skills` symlink are
  removed.

### Added

- `competition-operations.md`: what to check before and after a submission.
- A root `plugin.json` in the Agent Plugins format.
- An eval suite under `evals/` for `claude plugin eval`.
- CI on every pull request, and a weekly job that compares Kaggle's MCP tool
  list, CLI command tree, package versions, and OAuth registration answer
  with committed snapshots.
- `tools/`: read-only probes of the MCP server and the snapshot tools.

### Documentation

- `cli-reference.md`, `mcp-reference.md`, `kaggle-knowledge.md`, and
  `kaggle-setup.md` are rewritten from what the tools do today. Every
  documented `kaggle` command is tested against the CLI's own help.
- The MCP reference shows, for each of the 71 tools, whether it reads or
  writes and whether it needs a credential, and how to connect with a token
  instead of signing in.

## 2.4.0 - 2026-07-04

Screencast and docs refresh:

- Re-rendered every demo GIF from its source `.cast` file (the previously
  committed renders were broken 1-frame images).
- Rebuilt the demo casts from verbatim live command output.
- Removed the dead VHS recording pipeline (`docs/demo/demo.tape`); asciinema
  is the only supported recording path.
- Added retrieval QC and a Vesuvius Challenge demo (PR #25): leaderboard
  writeup join/preview with a `--fallback-search` path, a badges self-test
  fix, live retrieval tests, and a Kaggle CLI 2.2.x live test suite.

After the 2.4.0 tag, and shipped in 2.5.0: the `codex-install` cast became
verbatim output, the bearer token stopped going to non-Kaggle hosts in
writeup previews, and `extract_ranked_teams` began to honor private
leaderboards.

## 2.3.0 (unreleased milestone)

- Truthfulness audit: dropped overstated claims and synced drifted counts.
- Reorganized modules by workflow instead of by resource type.
- Hardened docs validation.
- Updated platform compatibility documentation.
- Added Antigravity CLI install documentation.
- Added an affiliation disclaimer.
- Added an ARC-AGI writeups cast (later replaced by the Vesuvius demo).

## 2.2.0 (unreleased milestone)

- Refreshed Kaggle CLI docs and plugin distribution.
- Added a direct Claude marketplace install path.
- Added the first README demo casts.
