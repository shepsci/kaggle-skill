# Badges

Badge inventory, dry run, phases, and the streak helper.

```bash
python3 modules/badges/scripts/orchestrator.py --dry-run
python3 modules/badges/scripts/orchestrator.py --status
python3 modules/badges/scripts/orchestrator.py --phase 1
python3 modules/badges/scripts/orchestrator.py --resume
```

Always run `--dry-run` first and get the user's go-ahead before a phase.

## What a phase does to the account

| Phase | Actions |
|---|---|
| 1 | Pushes notebooks, creates datasets and models. All private, named `kaggle-badges-...` |
| 2 | Submits to Titanic, and to one playground and one community competition that the CLI lists at that time |
| 3 | Pushes notebooks, waits for the runs, creates a dataset and a model from the output |
| 4 | Nothing. It prints the steps to do on kaggle.com |
| 5 | Lists datasets and submits to Titanic once, then writes a daily script you can schedule yourself |

Submissions use the day's submission slots, and notebook runs use quota.

## Progress

- `earned` means the action that earns the badge completed. The scripts cannot
  see your profile; check it for the badge itself.
- `skipped` means there is a manual step. The reason is shown by `--status`.
- Streak badges stay `attempting`. Run `--resume` each day; without it, a
  badge left as `attempting` or `skipped` is not tried again.
- Progress is saved in `badge-progress.json` in the skill folder. Set
  `KAGGLE_BADGES_STATE_DIR` to keep it, and the scratch files, somewhere else.

Nothing here posts comments or votes.

## References

- [badge-catalog.md](references/badge-catalog.md)
