# Competitions

Research a competition, then run it: status, data, submissions, scores.
Hackathons are in [hackathons/README.md](hackathons/README.md).

## Research (no credential for a public competition)

```bash
python3 scripts/kaggle_skill.py brief titanic
python3 scripts/kaggle_skill.py pages titanic
python3 scripts/kaggle_skill.py pages titanic --page evaluation
```

- `brief` is one screen: metric, deadline with the time left, prize, team
  size, daily submission limit, whether it is a code competition, whether it
  awards medals, how much data there is, and the names of its pages. With a
  credential it adds whether you have entered and your rank.
- `pages` lists the pages with their sizes. `--page NAME` prints one as text
  (part of the name is enough); a page longer than 12,000 characters is cut
  with a note, and `--max-chars 0` prints all of it. `--all` prints every
  page, `--raw` keeps the stored HTML or Markdown.

Start with `brief`. A rules page alone is 6,000 to 9,000 tokens, so read a
page only when the question needs it.

## Find competitions (credential)

```bash
python3 scripts/kaggle_skill.py competitions --days 30
python3 scripts/kaggle_skill.py competitions --mine
python3 scripts/kaggle_skill.py competitions --category featured,research --status active
python3 scripts/kaggle_skill.py details titanic --top 10
```

- `competitions` prints one line per competition: deadline, category, teams,
  prize, slug and title. Community competitions with fewer than ten teams are
  left out unless `--min-teams` says otherwise. `--search TEXT`, `--limit N`.
- `details` prints the data files with sizes, the top of the leaderboard and
  the most-voted notebooks. A lookup that fails is reported and the others
  are still printed.

## Where you stand (credential)

```bash
python3 scripts/kaggle_skill.py status rsna-knee-abnormality-detection
python3 scripts/kaggle_skill.py leaderboard rsna-knee-abnormality-detection
```

- `status`: the deadline, your rank, submissions made today and left, the
  submissions still being scored, your best and latest scores, and this
  week's GPU and TPU hours. Facts only.
- `leaderboard`: the top rows, your row with the gap to the leader, and the
  score at each medal line when the competition awards medals. Each run saves
  a snapshot under `./.kaggle-skill/leaderboard/`, and the next run says what
  moved. The public leaderboard is not the final one; after the deadline,
  `--private` shows the one that decides the final ranks.

## Data

```bash
python3 scripts/kaggle_skill.py download titanic ./data --unzip
python3 scripts/kaggle_skill.py download titanic --file train.csv
```

Needs the Kaggle CLI, a credential, and the competition's rules accepted on
kaggle.com. The total size is read first and a download above `--max-gb`
(default 20) is refused: some competitions hold hundreds of gigabytes.
`--unzip` extracts archives and refuses any member that would land outside
the folder.

## Submit

```bash
python3 scripts/kaggle_skill.py validate titanic ./submission.csv
python3 scripts/kaggle_skill.py submit titanic ./submission.csv -m "baseline" --expect 0.77
python3 scripts/kaggle_skill.py submit titanic ./submission.csv -m "baseline" --expect 0.77 --yes
python3 scripts/kaggle_skill.py watch titanic
python3 scripts/kaggle_skill.py ledger
```

- `validate` compares a CSV with the sample submission: columns, row count,
  ids, empty values, non-finite numbers. An empty value in a text column the
  sample never leaves empty is a warning (WARN), since some competitions take
  an empty prediction. It checks the shape, not the predictions.
- `submit` without `--yes` prints what would be sent and how many submissions
  are left today, and stops. With `--yes` it submits and adds a line to
  `./.kaggle-skill/ledger.jsonl`. A code competition takes
  `--notebook OWNER/NAME --version N` instead of a file.
- `watch` waits until the submission is scored, prints the score, records it,
  and reports the difference from `--expect`. `--ref ID` watches another of
  your submissions; one that is not among your latest 100 in the competition
  is shown but not recorded, since it may belong to another competition.
- `ledger` shows the record.

Submit only after the user confirms. Read
[competition-operations.md](references/competition-operations.md) first.

The ledger and the leaderboard snapshots are plain files in
`./.kaggle-skill/`, in the folder the commands are run from. They are local
records: nothing reads them but these commands. A project that should not
carry them can list `.kaggle-skill/` in its `.gitignore`.

## Simulation competitions

```bash
python3 scripts/kaggle_skill.py episodes 56699264
python3 scripts/kaggle_skill.py episodes --replay 117015562
python3 scripts/kaggle_skill.py episodes --logs 117015562 --agent 0
```

The first lists a submission's games with rewards and opponents. The other
two save a replay or your agent's log under `./downloads/episodes/`.

## Scripts

`scripts/competition_brief.py`, `competition_pages.py`, `list_competitions.py`,
`competition_details.py`, `competition_status.py`,
`competition_leaderboard.py`, `competition_download.py`,
`competition_validate.py`, `competition_submit.py`, `competition_watch.py`,
`competition_ledger.py`, `competition_episodes.py`. Each answers `--help`.

## References

- [competition-operations.md](references/competition-operations.md): before
  and after a submission
- [competition-research.md](references/competition-research.md)
- [competition-overview.md](references/competition-overview.md)
- [competition-categories.md](references/competition-categories.md)
- [hackathon-endpoints.md](hackathons/references/hackathon-endpoints.md)
- [episode-endpoints.md](hackathons/references/episode-endpoints.md)
