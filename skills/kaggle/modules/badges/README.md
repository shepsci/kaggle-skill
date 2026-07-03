# Badges

Use this module for badge inventory, dry-run planning, phase execution, and
manual streak helpers.

## Commands

```bash
python3 modules/badges/scripts/orchestrator.py --dry-run
python3 modules/badges/scripts/orchestrator.py --phase 1
python3 modules/badges/scripts/orchestrator.py --status
```

Always run `--dry-run` before any phase. Badge workflows can create private
datasets, notebooks, models, comments, votes, or submissions, and some outcomes
can become profile-visible.

Created helper resources use the `kaggle-badges-` prefix and are private by
default.

## References

- [badge-catalog.md](references/badge-catalog.md)
