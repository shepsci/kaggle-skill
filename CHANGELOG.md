# Changelog

All notable changes to this project are documented in this file.

## 3.0.1 - 2026-10-03

Fewer steps for the questions people ask most. Recording the README's demo
sessions showed where the agent had to work around the skill; each of those
places is now one command.

### Changed

- `brief` quotes the start of the evaluation page next to the metric's name
  and lists the dated lines of the Timeline page (entry, team merger and
  final deadlines in the host's words), so "what is the metric and the
  deadline?" is answered by one command. It takes several competitions at
  once, one block each. "entry closes" is now "join by".
- `competitions` shows each competition's metric and the last day to join
  (or "submissions closed"), in two short lines per competition.
- `KAGGLE_SKILL_HIDE_ACCOUNT=1` leaves your entries and ranks out of
  `competitions` and `brief`, for screen sharing and recordings.
- `writeup` takes several ids or URLs and prints each in its own block. A
  body is cut after 8,000 characters with a note (`--max-chars 0` for all of
  it), so an agent no longer pipes it through `head`.
- `solutions` says whether its ranks and scores are from the private or the
  public leaderboard, and `--preview` shows how each writeup's body starts,
  read from the MCP server with no credential. Writeup pages show little before their
  scripts run, so the old previews were often the title alone.
- The `submit` dry run runs `validate`'s checks on the file and shows them
  with the plan (`--sample PATH` names the sample). The separate "check the
  file first" step is gone.
- The demo GIFs draw an answer as prose (no Markdown marks), show it a screen
  at a time with time to read, type long commands faster, and show block tags
  without their attributes. A new session lists the competitions running
  now with their prizes and metrics; the other three were recorded again
  with 3.0.1.

## 3.0.0 - 2026-10-02

The first run works with nothing installed, the output is short enough to
read, and the skill can run a competition as well as research one. Commands
were renamed and every write is a dry run by default, so this is a major
version: see "Changed" before you update.

### Added

- One entry point: `python3 scripts/kaggle_skill.py <command>`. It lists the
  commands with `--help` and runs each by name.
- `brief <competition>`: the metric, the deadline with the time left, the
  prize, the team size, the daily limit, whether it is a code competition,
  the size of the data and the page names. About 250 tokens, no credential.
- Competition operations:
  - `status`: time left, your rank, submissions made today and left, what is
    still being scored, your best and latest scores, GPU and TPU hours.
  - `leaderboard`: the top, your row, the gap to the leader and to each medal
    line, and what moved since the last run.
  - `validate`: a submission file against the sample submission.
  - `submit`: file or notebook version, with a local ledger line for every
    real submission.
  - `watch`: waits for the score, records it, and reports the difference from
    the score you expected.
  - `ledger`: the local record. `episodes`: a simulation submission's games,
    replays and logs.
- `topics` and `topic` read discussions through the Kaggle MCP server with no
  credential. A topic comes back as the post plus a capped number of
  comments.
- `doctor`: what is installed, which credential is configured, whether
  Kaggle answers, and what works now.
- `KAGGLE_SKILL_READ_ONLY=1` makes every write refuse.
- `tools/build_plugin.py` builds the plugin alone, about 100 files, for a
  plugin-only branch. An icon, and `displayName`, `documentationUrl` and
  `supportUrl` in the Claude Code manifest.
- The README's demos are real Claude Code sessions: a question about a
  competition, a submission that stops at the dry run and asks, and what the
  top teams did. `tools/record_session.py` records one, read-only and with no
  Kaggle credential, and keeps only the lines a demo shows.
- Three eval cases that measure usefulness (a brief, a status report, a
  writeup summary). The suite was run once before the release, in Claude
  Code 2.1.286: all 11 cases pass with the plugin; without it, 4 pass and
  2 half pass.

### Changed

- **Public reads need no installed package.** The MCP client and the writeup
  fetcher use the standard library; `requests` is no longer a dependency.
- **Short text is the default output.** `--json` gives the same content as
  JSON and `--full` everything the server returned. `pages` lists the pages
  with their sizes and prints one with `--page`; a long page is cut with a
  note. `competitions` and `writeups` print a line or a few per row.
  `writeup` prints the body once.
- **Every command that changes the account is a dry run until `--yes`:**
  `submit`, `dataset-publish`, `model-publish`, `notebook-push`,
  `notebook-run`, `save-credentials`, a badge phase run through `badges`,
  and any `cli --` command the skill does not know to be a read. Before
  3.0.0 only the submission script had a dry run. `SKILL.md` makes it a
  two-turn action: the agent shows the dry run and asks, and adds `--yes`
  only after the reply. A request such as "submit my file" is not that yes.
- **The shell scripts are Python.** One script per action. The dataset and
  model commands use kagglehub by default and take `--via cli` for the
  Kaggle CLI:

  | Before | Now |
  |---|---|
  | `cli_download.sh` (competitions) | `download` |
  | `cli_submit.sh` | `submit` |
  | `kagglehub_download.py`, `cli_download.sh` (datasets) | `dataset-download` |
  | `kagglehub_publish.py`, `cli_publish.sh` (datasets) | `dataset-publish` |
  | `kagglehub_download.py`, `cli_download.sh` (models) | `model-download` |
  | `kagglehub_publish.py`, `cli_publish.sh` (models) | `model-publish` |
  | `cli_publish.sh` (notebooks) | `notebook-push` |
  | `cli_execute.sh` | `notebook-run` |
  | `poll_kernel.sh` | `notebook-wait` |
  | `setup_env.sh` | `save-credentials` |
  | `network_check.sh` | `doctor` |

- Arguments follow one pattern: the competition is the first argument or
  `--competition`, as a slug or a URL, and positionals can come after
  options. The read commands take `--json`, and `--full` and `--limit` where
  they apply; `<command> --help` lists each command's options. The older
  spellings (`--slug`, `--top-k`, `--top-n`, `--winner-only`, `--array`,
  `--lookback-days`, `--summary`, `--pretty`) still work.
- `competitions` and `details` read the Kaggle MCP server, so they need an
  API token or an OAuth login. A legacy `kaggle.json` key no longer works for
  them; the message says what to do.
- Exit codes follow the table in `SKILL.md` for CLI-backed commands too
  (downloads, discussions, replays and logs): 2 for a missing or rejected
  credential, 3 for a denial, 127 for a missing tool with the install
  command.
- `leaderboard` asks for the public leaderboard, which the server stops
  sending by default once a competition ends; `--private` shows the final one
  after the deadline. `kaggle_skill.py cli` refuses `auth print-access-token`,
  which prints the token.
- Notebook runs read the notebook's name from `kernel-metadata.json`, use one
  default output folder, and print the last 40 lines of a failed run's log.
- Publishing no longer writes a metadata template into your folder. It says
  which `kaggle ... init` command writes one.
- Python 3.14 is tested in CI. `shellcheck` is gone with the shell scripts.

### Fixed

- Text is printed as written: a dash is a dash and an emoji an emoji. Before,
  every character outside ASCII came out as an escape code.
- Reading a forum topic returns the post. The CLI's JSON output, which the
  script used, holds only the comments.
- A missing Python package gives one line with the install command, never a
  traceback and never "could not sign in".
- The README said forum topics need no credential; through the script they
  did. They no longer do.
- `SKILL.md` named the wrong roles for the hackathon roster.
- `--help` on the setup scripts ran them. Every script now answers `--help`
  and does nothing else, and a test holds that.

### Security

- Characters a reader cannot see are removed from text and escaped in JSON:
  zero-width and bidirectional format characters, tag characters, private-use
  code points, control characters. A run of four or more leaves a note.
- A kaggle.com URL is rebuilt from its checked parts before it is requested,
  and a redirect is never followed automatically, so a token cannot be
  carried to another host.
- `download` reads the size of a competition's data first and refuses a
  download above `--max-gb` (default 20).
- `save-credentials` creates the file private from the start and never
  overwrites one.

### Removed

- `modules/competitions/scripts/utils.py`, `shared/lib.sh`, and the command
  line of `shared/untrusted.py`, which served the shell scripts.

## 2.5.1 - 2026-10-02

Small fixes after the 2.5.0 release, from what the Claude directory's and
ClawHub's scans reported.

- `.claude-plugin/plugin.json` names the privacy policy (`privacyPolicyUrl`).
- The ClawHub badge in the README points at the skill's current page.
- The credential order in `cli-reference.md` is worded so that a scanner does
  not read the variable name `KAGGLE_API_TOKEN` as a token.

## 2.5.0 - 2026-10-02

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
