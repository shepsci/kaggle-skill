# Competition Operations

What to do before and after a submission, so that a slot or a GPU hour is not
spent on something that could have been caught first. Every step that changes
the account needs the user's go-ahead.

Commands are run as `python3 scripts/kaggle_skill.py <command>`; only the
command is written below.

## Before any submission

1. **Know the rules that apply.** `brief <slug>` gives the metric, the
   deadline, the team size and the daily limit. Read the pages the question
   needs:

   ```bash
   python3 scripts/kaggle_skill.py pages <slug> --page rules
   python3 scripts/kaggle_skill.py pages <slug> --page evaluation
   ```

2. **Check where you stand.**

   ```bash
   python3 scripts/kaggle_skill.py status <slug>
   ```

   It shows how many submissions are left today, what is still being scored,
   your best and latest scores, and the GPU hours left this week. The rules
   page and the count can disagree. Plan on the smaller number unless the
   host has confirmed the larger one.

3. **Look at what was already submitted**, so the same file is not sent
   twice. `status` lists the latest submissions, `ledger` lists what went
   through this skill, and the dry run in step 5 warns when the same file was
   sent before.

4. **Validate the file locally.**

   ```bash
   python3 scripts/kaggle_skill.py validate <slug> ./submission.csv
   ```

   It compares the file with the sample submission: same columns, same ids,
   same row count, no empty values, finite numbers. An empty value in a text
   column is a warning, not a failure: check on the evaluation page whether
   an empty prediction is allowed. It cannot check a format
   rule that only the evaluation page states, or the range the metric
   expects: read that page. A submission that errors on Kaggle can still use
   one of the day's slots.

5. **Tell the user** which file, which competition, what message, and how
   many slots remain. The dry run prints exactly that, and runs step 4's
   checks again (`--sample PATH` names the sample):

   ```bash
   python3 scripts/kaggle_skill.py submit <slug> ./submission.csv -m "what changed" --expect 0.81
   ```

   Wait for a yes.

## A file submission

```bash
python3 scripts/kaggle_skill.py submit <slug> ./submission.csv -m "what changed" --expect 0.81 --yes
python3 scripts/kaggle_skill.py watch <slug>
```

`submit --yes` sends the file and adds a line to `./.kaggle-skill/ledger.jsonl`
with the file's SHA-256, the message and the expected score. A rejected
submission gives a non-zero exit status and is not recorded.

`watch` checks every 30 seconds until Kaggle has scored the submission, for
up to 30 minutes (`--timeout`). It prints the public score, records it, and
reports the difference from `--expect`. Exit status 124 means it is still
being scored: run `watch` again. Exit status 4 means the last check could not
read the submission, so its state is not known.

`--expect` is the score your own validation predicts. A large difference
between it and the public score is worth telling the user about: it points at
a leak, a mismatch between the validation and the test data, or a bug.

## A code competition

The submission is a notebook version, and Kaggle reruns it on hidden data.
`brief` says "submit with: a notebook" for these.

1. **Check the quota.** `status <slug>` shows this week's GPU and TPU hours
   for the whole account. Only two GPU runs can be active at a time.
2. **Check the notebook's settings** in `kernel-metadata.json`: internet off
   if the rules require it, the competition listed under
   `competition_sources`, datasets and models listed as sources, and the
   accelerator the rules allow. The dry run shows them:

   ```bash
   python3 scripts/kaggle_skill.py notebook-run ./notebook-dir
   ```

3. **Push, which starts a run.**

   ```bash
   python3 scripts/kaggle_skill.py notebook-run ./notebook-dir --timeout 7200 --yes
   ```

   It stops if the push is rejected, waits for the run, downloads the output,
   and prints the end of the log when the run fails.
4. **Read the output** before submitting. Check that the submission file
   exists and passes `validate`.
5. **Submit that version.** The version number is on the notebook's page and
   in the push output.

   ```bash
   python3 scripts/kaggle_skill.py submit <slug> --notebook <owner>/<notebook> --version <N> -m "what changed" --yes
   ```

   This uses a slot. Ask first.
6. **Watch the result.** A code submission can fail during the rerun on
   hidden data even when the public run passed: time limit, memory, or a
   missing file. `watch <slug>` reports the state and exits 1 on an error.

## A simulation competition

- Only your latest two submissions stay in play. A new one replaces the older
  of the two.
- Ratings settle over many episodes. Do not judge a submission from its first
  few games.
- `episodes <submission-id>` lists the games with rewards and opponents.
  `episodes --replay <episode-id>` and `episodes --logs <episode-id>` save a
  game and your agent's log. See
  [episode-endpoints.md](../hackathons/references/episode-endpoints.md).

## The leaderboard

```bash
python3 scripts/kaggle_skill.py leaderboard <slug>
```

Your row, the gap to the leader, and the score at each medal line. The medal
lines follow Kaggle's table (kaggle.com/progression/competitions) at today's
team count; they move as teams join, and the private leaderboard decides the
result. Run it again later to see what moved.

## Final submissions

Which submissions count at the end is chosen on the competition's website.
No command or MCP tool shows or changes the selection. Remind the user to
check it before the deadline.

## What cannot be done from here

Accepting the rules, joining or merging teams, identity checks, and choosing
final submissions are done on kaggle.com. Say so, and give the address.
