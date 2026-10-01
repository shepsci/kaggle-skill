# Competition Operations

What to do before and after a submission, so that a slot or a GPU hour is not
spent on something that could have been caught first. Every step that changes
the account needs the user's go-ahead.

## Before any submission

1. **Read the rules and the evaluation page.**

   ```bash
   python3 modules/competitions/scripts/competition_pages.py --competition <slug> --page rules
   python3 modules/competitions/scripts/competition_pages.py --competition <slug> --page evaluation
   ```

2. **Check how many submissions are left today.**

   ```bash
   kaggle competitions submission-limits <slug>
   ```

   The rules page and this command can disagree. Plan on the smaller number
   unless the host has confirmed the larger one.

3. **Look at what was already submitted**, so the same file is not sent
   twice.

   ```bash
   kaggle competitions submissions <slug> --format json
   ```

4. **Validate the file locally.** Compare it with the sample submission:
   same columns, same ids, same row count, no missing values, values in the
   range the metric expects, and any format rule on the evaluation page. A
   submission that errors on Kaggle can still use one of the day's slots.

5. **Tell the user** which file, which competition, what message, and how
   many slots remain. Wait for a yes.

## A file submission

```bash
bash modules/competitions/scripts/cli_submit.sh <slug> ./submission.csv "what changed"
bash modules/competitions/scripts/cli_submit.sh <slug> ./submission.csv "what changed" --yes
```

The first form is a dry run. The second submits and then lists recent
submissions. A rejected submission gives a non-zero exit status.

After submitting, the score takes a while. Check with:

```bash
kaggle competitions submissions <slug> --format json
```

Kaggle CLI 2.2.4 cannot wait for the score. The next release adds a wait
option to `submit` and a command that downloads a submission's file.

## A code competition

The submission is a notebook version, and Kaggle reruns it on hidden data.

1. **Check the quota.** `kaggle quota` shows this week's GPU and TPU hours
   for the whole account. Only two GPU runs can be active at a time.
2. **Check the notebook's settings** in `kernel-metadata.json`: internet off
   if the rules require it, the competition listed under
   `competition_sources`, datasets and models listed as sources, and the
   accelerator the rules allow.
3. **Push, which starts a run.**

   ```bash
   bash modules/notebooks/scripts/cli_execute.sh ./notebook-dir <owner>/<notebook> ./output 3600
   ```

   The script stops if the push is rejected, waits for the run, and prints
   the log when the run fails.
4. **Read the log and the output** before submitting. Check that the
   submission file exists and passes the same local checks as above.

   ```bash
   kaggle kernels logs <owner>/<notebook>
   ```

5. **Submit that version.** The version number is on the notebook's page and
   in the push output.

   ```bash
   kaggle competitions submit <slug> -f submission.csv -k <owner>/<notebook> -v <version> -m "what changed"
   ```

   This uses a slot. Ask first.
6. **Watch the result.** A code submission can fail during the rerun on
   hidden data even when the public run passed: time limit, memory, or a
   missing file. `kaggle competitions submissions <slug>` shows the state.

## A simulation competition

- Only your latest two submissions stay in play. A new one replaces the older
  of the two.
- Ratings settle over many episodes. Do not judge a submission from its first
  few games.
- Read episodes with `kaggle competitions episodes <submission-id>`, and a
  game with `kaggle competitions replay <episode-id>`. See
  [episode-endpoints.md](../hackathons/references/episode-endpoints.md).

## Final submissions

Which submissions count at the end is chosen on the competition's website.
No command or MCP tool shows or changes the selection. Remind the user to
check it before the deadline.

## What cannot be done from here

Accepting the rules, joining or merging teams, identity checks, and choosing
final submissions are done on kaggle.com. Say so, and give the address.
