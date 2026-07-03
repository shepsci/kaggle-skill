# kaggle-cli Command Reference

Pinned baseline:

- PyPI package: `kaggle` 2.2.3
- SDK floor: `kagglesdk>=0.1.33,<1.0`
- Python: 3.11+
- Main recheck: `Kaggle/kaggle-cli` commit `a430f0b` from 2026-07-02
- Source docs: https://github.com/Kaggle/kaggle-cli/tree/main/docs

## Install And Auth

```bash
pip install --upgrade "kaggle>=2.2.3" "kagglesdk>=0.1.33,<1.0"
kaggle --version
```

Auth options, in preferred order for new work:

```bash
kaggle auth login
export KAGGLE_API_TOKEN=...
mkdir -p ~/.kaggle && printf '%s' "$KAGGLE_API_TOKEN" > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
```

Legacy `~/.kaggle/kaggle.json` and `KAGGLE_USERNAME` + `KAGGLE_KEY` still work
for many commands.

## Output Formatting

Commands that historically accepted `--csv` now generally accept `--format`:

```bash
kaggle competitions list --format json
kaggle competitions list --format table
kaggle competitions list --format csv
kaggle forums topics list --format 'json(title,url,totalComments)'
```

Projection syntax is `format(field1,field2,...)`. Prefer JSON for agent
workflows. Avoid combining `--csv` and `--format`.

## Competitions

Participant commands:

```bash
kaggle competitions list [--group general|entered|inClass] \
  [--category all|featured|research|recruitment|gettingStarted|masters|playground] \
  [--sort-by grouped|prize|earliestDeadline|latestDeadline|numberOfTeams|recentlyCreated] \
  [-p PAGE] [-s SEARCH] [--format json]

kaggle competitions files COMPETITION [--page-size N] [--page-token TOKEN] [--format json]
kaggle competitions download COMPETITION [-f FILE] [-p PATH] [-w] [-o] [-q]
kaggle competitions submit COMPETITION -f FILE -m MESSAGE [-k KERNEL] [-v VERSION] [--sandbox]
kaggle competitions submissions COMPETITION [--format json]
kaggle competitions leaderboard COMPETITION [-s|--show] [-d|--download] [-p PATH] [--format json]
kaggle competitions team-submissions TEAM_ID [--format json]
```

Discussion and page commands:

```bash
kaggle competitions topics list [COMPETITION] [--sort-by recent] [-p PAGE] [--format json]
kaggle competitions topics show TOPIC_REF [TOPIC_ID] [--page-size N] [--page-token TOKEN] \
  [--format json]
kaggle competitions topic-messages COMPETITION TOPIC_ID [-s best|new|old] [-n N]

kaggle competitions pages COMPETITION [--content] [--format json]
kaggle competitions pages list COMPETITION [--content] [--format json]
```

Simulation competition commands:

```bash
kaggle competitions episodes SUBMISSION_ID [--format json]
kaggle competitions replay EPISODE_ID [-p PATH]
kaggle competitions logs EPISODE_ID AGENT_INDEX [-p PATH]
```

Host/admin commands:

```bash
kaggle competitions init [FOLDER]
kaggle competitions create [-p FOLDER]
kaggle competitions pages create COMPETITION --page-name NAME -f FILE \
  [--mime-type TYPE] [--post-title TITLE] [--publish]
kaggle competitions pages update COMPETITION --page-name NAME \
  [-f FILE] [--new-name NAME] [--mime-type TYPE] [--post-title TITLE] \
  [--publish|--unpublish]
kaggle competitions pages delete COMPETITION --page-name NAME [-y]
kaggle competitions launch COMPETITION [--at 2027-01-01T00:00:00Z]
```

Notes:

- There is no CLI command to join a competition. Accept rules in the UI.
- `competitions download` does not support `--unzip`; unzip locally with a
  zip-slip-safe helper.
- `--sandbox` submissions are for competition hosts/admins.

## Datasets

```bash
kaggle datasets list [--sort-by hottest|votes|updated|active] \
  [--file-type all|csv|sqlite|json|bigQuery|parquet] \
  [--license all|cc|gpl|odb|other] [--tags TAGS] [-s SEARCH] [-m] \
  [--user USER] [-p PAGE] [--min-size BYTES] [--max-size BYTES] [--format json]

kaggle datasets files OWNER/DATASET [--page-size N] [--page-token TOKEN] [--format json]
kaggle datasets download OWNER/DATASET [-f FILE] [-p PATH] [-w] [--unzip] [-o] [-q]
kaggle datasets init [-p DIRECTORY]
kaggle datasets create -p DIRECTORY [-u] [-q] [-t] [-r skip|zip|tar]
kaggle datasets version -p DIRECTORY -m MESSAGE [-q] [-t] [-r skip|zip|tar] [-d]
kaggle datasets metadata OWNER/DATASET [-p PATH] [--update]
kaggle datasets status OWNER/DATASET [--format json]
kaggle datasets delete OWNER/DATASET [-y]

kaggle datasets topics list OWNER/DATASET [--sort-by recent] [--search QUERY] [--format json]
kaggle datasets topics show TOPIC_REF [TOPIC_ID] [--format json]
```

Recent metadata update support includes dataset cover images, dataset images,
expected update frequency, user-specified sources, file descriptions, and
column descriptions when the metadata JSON contains those fields.

## Kernels / Notebooks

```bash
kaggle kernels list [-m] [-p PAGE] [--page-size N] [-s SEARCH] \
  [--parent OWNER/KERNEL] [--competition SLUG] [--dataset OWNER/DATASET] \
  [--user USER] [--language all|python|r|sqlite|julia] \
  [--kernel-type all|script|notebook] [--output-type all|visualizations|data] \
  [--sort-by hotness|commentCount|dateCreated|dateRun|relevance|scoreAscending|scoreDescending|viewCount|voteCount] \
  [--format json]

kaggle kernels files OWNER/KERNEL [--page-size N] [--page-token TOKEN] [--format json]
kaggle kernels init -p DIRECTORY
kaggle kernels push -p DIRECTORY [--accelerator ACCELERATOR_ID] [-t TIMEOUT_SECONDS]
kaggle kernels pull OWNER/KERNEL[/VERSION] [-p PATH] [-w] [-m]
kaggle kernels output OWNER/KERNEL [-p PATH] [-w] [-o] [-q] \
  [--file-pattern REGEX] [--page-size N] [--page-token TOKEN]
kaggle kernels status OWNER/KERNEL
kaggle kernels logs OWNER/KERNEL [--follow]
kaggle kernels delete OWNER/KERNEL [-y]

kaggle kernels topics list OWNER/KERNEL [--sort-by recent] [--search QUERY] [--format json]
kaggle kernels topics show TOPIC_REF [TOPIC_ID] [--format json]
```

`kernels logs --follow` uses a streaming log path in current CLI releases.
Kernel output downloads support pagination and filename filtering.

## Models, Variations, Versions

```bash
kaggle models list [--owner OWNER] [--sort-by hotness|downloadCount|voteCount|notebookCount|createTime] \
  [-s SEARCH] [--page-size N] [--page-token TOKEN] [--format json]
kaggle models get OWNER/MODEL
kaggle models init -p DIRECTORY
kaggle models create -p DIRECTORY
kaggle models update -p DIRECTORY
kaggle models delete OWNER/MODEL [-y]
kaggle models topics list OWNER/MODEL [--format json]
kaggle models topics show TOPIC_REF [TOPIC_ID] [--format json]

kaggle models instances init -p DIRECTORY
kaggle models instances create -p DIRECTORY [-q] [-r skip|zip|tar]
kaggle models instances get OWNER/MODEL/FRAMEWORK/VARIATION -p PATH
kaggle models instances files OWNER/MODEL/FRAMEWORK/VARIATION [--page-size N] [--format json]
kaggle models instances update -p DIRECTORY
kaggle models instances delete OWNER/MODEL/FRAMEWORK/VARIATION [-y]

kaggle models instances versions create OWNER/MODEL/FRAMEWORK/VARIATION \
  -p DIRECTORY -n NOTES [-q] [-r skip|zip|tar]
kaggle models instances versions download OWNER/MODEL/FRAMEWORK/VARIATION/VERSION \
  [-p PATH] [--untar|--unzip] [-f] [-q]
kaggle models instances versions files OWNER/MODEL/FRAMEWORK/VARIATION/VERSION \
  [--page-size N] [--format json]
kaggle models instances versions delete OWNER/MODEL/FRAMEWORK/VARIATION/VERSION [-y]
```

`models variations` remains accepted as an alias for `models instances`.

## Forums And Topics

```bash
kaggle forums list [--format json]
kaggle forums topics list [FORUM] [--sort-by hot|top|new|recent|active|relevance] \
  [--search QUERY] [--category all|forums|competitions|datasets|competition_write_ups|models|benchmarks] \
  [--group all|owned|upvoted|bookmarked|my_activity|drafts] \
  [--page-size N] [--page-token TOKEN] [--format json]
kaggle forums topics show TOPIC_REF [TOPIC_ID] [--page-size N] [--page-token TOKEN] \
  [--format json]
```

For agent use, prefer:

```bash
python3 skills/kaggle/modules/discussions/scripts/forums.py forum-topics \
  --category competition_write_ups --format json
```

See [writeups.md](../discussions/references/writeups.md).

## Benchmarks

```bash
kaggle benchmarks auth [-y] [--env-file .env]
kaggle benchmarks init [-y] [--env-file .env] [--example-file example_task.py]
kaggle benchmarks tasks push TASK -f task.py [--wait [TIMEOUT]] \
  [--poll-interval SECONDS] [-d owner/dataset]
kaggle benchmarks tasks run TASK [-m MODEL ...] [--wait [TIMEOUT]]
kaggle benchmarks tasks list [--name-regex REGEX] [--status queued|running|completed|errored]
kaggle benchmarks tasks status TASK [-m MODEL ...]
kaggle benchmarks tasks download TASK [-m MODEL ...] [-o DIR] [--include-source] [--force]
kaggle benchmarks tasks log TASK [-m MODEL ...]
kaggle benchmarks tasks models
kaggle benchmarks tasks delete TASK [-y]
kaggle benchmarks tasks publish TASK [--no-publish-backing-notebook]
kaggle benchmarks topics list OWNER/BENCHMARK [--format json]
kaggle benchmarks topics show TOPIC_REF [TOPIC_ID] [--format json]
```

Aliases: `kaggle b`, `kaggle b t`, and `tasks logs`.
See [benchmarks-cli.md](../benchmarks/references/benchmarks-cli.md).

## Quota And Config

```bash
kaggle quota
kaggle config view
kaggle config set -n competition -v SLUG
kaggle config set -n path -v PATH
kaggle config set -n proxy -v URL
kaggle config unset -n competition|path|proxy
```

Run `kaggle quota` before GPU/TPU-heavy notebook plans or repeated benchmark
runs.
