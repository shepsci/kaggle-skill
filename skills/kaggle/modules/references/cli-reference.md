# Kaggle CLI Reference

Checked against `kaggle` 2.2.4 (PyPI, released 2026-07-23) on 2026-09-30.
Every command on this page is tested against that release's `--help` tree.

This page is a map plus the things `--help` does not tell you. For the full
syntax of a command, use one of these instead of guessing:

- `kaggle <command> --help`, which always matches the installed version.
- Kaggle's own agent skill for the CLI, `kaggle-cli`, in the CLI repository:
  https://github.com/Kaggle/kaggle-cli/tree/main/skills
- The CLI docs: https://github.com/Kaggle/kaggle-cli/tree/main/docs

## Install and sign in

```bash
python3 -m pip install --upgrade "kaggle>=2.2.4"
kaggle --version
```

The CLI tries credentials in this order and uses the first that works:

1. API token: `KAGGLE_API_TOKEN` (the token, or the path of a file holding
   it), then `~/.kaggle/access_token`.
2. Legacy key: `KAGGLE_USERNAME` + `KAGGLE_KEY`, then `kaggle.json` in
   `KAGGLE_CONFIG_DIR` or `~/.kaggle`.
3. OAuth login: `kaggle auth login`, saved in `~/.kaggle/credentials.json`.

```bash
kaggle auth login
kaggle config view
```

`kaggle config view` prints `- username: <name>`. It rejects an API token that
Kaggle does not accept, but for a legacy key or an OAuth login it does not
contact the server, so it also passes for a revoked key. To test a credential,
run `kaggle quota`: it needs a signed-in account and exits with status 1 and
"Authentication required" otherwise.

With a credential Kaggle no longer accepts, commands that also work without
an account do not fail. They answer as for an anonymous user: `kaggle datasets
list --mine` prints `No datasets found`. An empty result is therefore not
proof that the account has nothing.

Public datasets, models, and notebooks download without any credential.

`kaggle auth print-access-token` prints the OAuth access token for use as a
bearer token elsewhere. It prints a secret: never run it where the output is
logged or shown. `kaggle auth revoke` revokes that token.

## Output and paging

```bash
kaggle competitions list --format json
kaggle competitions topics list titanic --format "json(title,commentCount)"
kaggle datasets files heptapod/titanic --page-size 50 --format json
```

- `--format` takes `table`, `csv`, or `json`, and a field list in
  parentheses. Field names are the ones the CLI prints in its error when a
  name is wrong, for example `authorName, commentCount, id, postDate, title,
  votes` for topics. `--csv` is the older switch; do not combine the two.
- When there are more results, the CLI prints a line `Next page token: ...`
  after the data. With `--format json` that line makes the output invalid
  JSON. Read only the text from the first `[` to the last `]`, or use the
  skill's scripts, which do that.
- Pass the token back with `--page-token`. Some older commands page with
  `--page` (`competitions list`, `competitions topics list`).
  `competitions topics list` accepts `--page-size` and `--page-token` but
  ignores them, with a warning.

## Where the CLI's help text is wrong

Checked on 2.2.4. The CLI rejects the value its own help suggests.

| Command | Help says | Accepted values |
|---|---|---|
| `kaggle competitions list --group` | `general`, `entered`, `inClass` | `general`, `entered`, `community`, `hosted`, `unlaunched`, `unlaunched_community` |
| `kaggle kernels list --output-type` | `all`, `visualizations`, `data` | `all`, `visualization`, `data` |

`kaggle competitions topic-messages --sort-by` takes `hot`, `new`, `old`, or
`top`. Under `kaggle models variations versions`, `--help` lists an `init`
subcommand that does not exist.

`kaggle models get <owner/model> -p <dir>` crashes on a model that exists
(`TypeError: Object of type datetime is not JSON serializable`). Without `-p`
it prints the model and exits with 0.

The CLI can print warnings on standard output before its data: an
out-of-date notice, or a warning that `kaggle.json` is readable by others.
Do not treat the whole output as the answer. This matters most for
`kaggle auth print-access-token`, where the token is the last line.

## Exit status 0 does not always mean success

After some failed writes the CLI prints an error and still exits with 0:

- `Kernel push error: ...`
- `Dataset creation error: ...` and `Dataset version creation error: ...`
- `Model creation error: ...` and `Model instance creation error: ...`
- `Could not submit to competition: ...`
- `Upload unsuccessful`

The skill's scripts treat these as failures. If you call `kaggle` yourself,
read the output before you report success.

Setting `VERBOSE` or `VERBOSE_OUTPUT` in the environment makes the CLI print
request headers, including the bearer token. The skill's scripts remove both
before they call it. Do not set them.

## Command map

### Competitions

```bash
kaggle competitions list --group community --sort-by latestDeadline --format json
kaggle competitions files titanic --format json
kaggle competitions download titanic -p ./data
kaggle competitions pages titanic --content --page-name rules
kaggle competitions submission-limits titanic
kaggle competitions submit titanic -f submission.csv -m "baseline"
kaggle competitions submissions titanic --format json
kaggle competitions leaderboard titanic --show
kaggle competitions team-submissions 12345
kaggle competitions topics list titanic --sort-by recent --format json
kaggle competitions topic-messages titanic 12345 --sort-by top
```

- There is no command to join a competition. Accept the rules on kaggle.com.
- `kaggle competitions list --group community` lists community competitions.
- `kaggle competitions submission-limits` shows how many submissions are
  left today. Use `--json` for machine-readable output; it has no `--format`.
- `competitions download` has no `--unzip` in this release. The skill's
  `modules/competitions/scripts/cli_download.sh --unzip` extracts with a path
  check.
- `-k` and `-v` on `competitions submit` submit a notebook version to a code
  competition. `--sandbox` is for hosts.
- Simulation competitions: `kaggle competitions episodes <submission-id>`,
  `kaggle competitions replay <episode-id>`, and
  `kaggle competitions logs <episode-id> <agent-index>`.
- Host commands: `competitions init`, `create`, `launch`, `hosts`,
  `pages create|update|delete`, `data update`, `settings get|update`,
  `solution create|status`.

### Datasets

```bash
kaggle datasets list --search titanic --sort-by votes --format json
kaggle datasets files heptapod/titanic
kaggle datasets download heptapod/titanic -p ./data --unzip
kaggle datasets init -p ./data
kaggle datasets create -p ./data --dir-mode zip
kaggle datasets version -p ./data -m "notes" --dir-mode zip
kaggle datasets status owner/dataset
kaggle datasets topics list owner/dataset
```

`datasets create` and `datasets version` upload everything in the folder
except what `--ignore-patterns` excludes. New datasets are private unless you
pass `--public`. `datasets version --delete-old-versions` removes earlier
versions.

### Notebooks (kernels)

```bash
kaggle kernels list --competition titanic --sort-by voteCount --format json
kaggle kernels init -p ./nb
kaggle kernels push -p ./nb
kaggle kernels status owner/kernel
kaggle kernels logs owner/kernel --follow
kaggle kernels output owner/kernel -p ./out
kaggle kernels pull owner/kernel -p ./nb --metadata
kaggle kernels files owner/kernel --format json
```

- `kernels push` always starts a run. `--accelerator` picks the hardware and
  `--timeout` limits the run.
- `kernels status` prints `<owner/kernel> has status
  "KernelWorkerStatus.COMPLETE"`. The states are `QUEUED`, `RUNNING`,
  `COMPLETE`, `ERROR`, `CANCEL_REQUESTED`, `CANCEL_ACKNOWLEDGED`, and
  `NEW_SCRIPT`. Match on the quoted word, not on the line: the line starts
  with the notebook's name.
- `kernels output` in this release writes files under the names the server
  sends, with no check that they stay inside the folder. The skill's notebook
  scripts check the names first.
- `kaggle kernels update` is another name for `push`, and `kaggle kernels
  get` for `pull`.

### Models

A model has three levels: the model, its variations (one per framework and
size), and the versions of a variation.

```bash
kaggle models list --owner google --format json
kaggle models get google/gemma -p ./meta
kaggle models init -p ./model
kaggle models create -p ./model
kaggle models variations init -p ./model
kaggle models variations create -p ./model
kaggle models variations versions create owner/model/framework/variation -p ./model -n "notes"
kaggle models variations versions list owner/model/framework/variation
kaggle models variations versions download owner/model/framework/variation/3 -p ./model
```

- `variations` is another name for `instances`; both work.
- `models variations create` uploads the files as version 1. Use
  `versions create` only for a variation that already exists.
- Both skip subfolders unless you pass `--dir-mode zip` (or `tar`).
- `versions download` needs the version number as the fifth part of the
  handle. `kagglehub` accepts the four-part handle and takes the latest.
- `--untar` on `versions download` extracts with no path check in this
  release. Leave the archive as downloaded, or extract it yourself.

### Forums and topics

```bash
kaggle forums list --format json
kaggle forums topics list getting-started --sort-by recent --format json
kaggle forums topics list --category competition_write_ups --search "1st place"
kaggle forums topics show 12345 --format json
```

Topic lists exist for every resource: `kaggle competitions topics`,
`kaggle datasets topics`, `kaggle kernels topics`, `kaggle models topics`,
and `kaggle benchmarks topics`, each with `list` and `show`. Only
`competitions topics list` lacks `--search`. The skill's
`modules/discussions/scripts/forums.py` wraps these and marks the output as
untrusted content. See [writeups.md](../discussions/references/writeups.md).

### Benchmarks

```bash
kaggle benchmarks init --yes
kaggle benchmarks tasks push my-task -f task.py --wait
kaggle benchmarks tasks run my-task -m gemini-2.5-pro --wait
kaggle benchmarks tasks status my-task
kaggle benchmarks tasks log my-task
kaggle benchmarks tasks download my-task --include-source
kaggle benchmarks leaderboard owner/benchmark --show
```

`kaggle b` and `kaggle b t` are the short forms. Pushing and running tasks
creates resources and uses quota. See
[benchmarks-cli.md](../benchmarks/references/benchmarks-cli.md).

### Files, quota, and configuration

```bash
kaggle quota
kaggle files upload ./big-folder
kaggle config view
kaggle config set -n competition -v titanic
kaggle config unset -n competition
```

`kaggle quota` shows this week's GPU and TPU use and when it resets. The
quota is for the whole account, so a run started anywhere else counts.
`kaggle files upload` uploads files to your Kaggle inbox.

## Not in a release yet

These exist on the CLI's `main` branch (33 commits past 2.2.4 on 2026-09-23)
and will arrive with the next release. Do not use them with 2.2.4.

<!-- cli-check: off -->

| Command or option | What it does |
|---|---|
| `kaggle search` | Search across competitions, datasets, notebooks, and models |
| `kaggle competitions submit --wait` (with `--poll-interval`) | Wait for the score after submitting |
| `kaggle competitions submission <ref>` | Show one submission |
| `kaggle competitions submission-download` | Download the file of one of your submissions |
| `kaggle competitions download --unzip` | Extract after download |
| `kaggle competitions host-add` | Add a host to a competition |
| `kaggle kernels push --no-run` | Save a notebook version without running it |
| `kaggle benchmarks quota` | Benchmark quota |
| `--debug` (any command) | Print debugging detail |

<!-- cli-check: on -->

The same branch fixes three path problems that 2.2.4 still has: file names
from the server in `kernels output`, tar members in `versions download
--untar`, and resumable-upload state kept in a shared temporary folder.
