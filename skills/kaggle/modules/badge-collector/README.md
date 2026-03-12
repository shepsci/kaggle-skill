# Badge Collector

Systematically earns Kaggle badges across 5 phases using kagglehub, kaggle-cli,
Playwright, and cron/launchd automation. Builds on the `kllm` module for credential
management and Kaggle API interaction.

## Quick Start

```bash
# 1. Verify credentials
python3 modules/kllm/scripts/check_credentials.py

# 2. Dry run — see what will happen
python3 modules/badge-collector/scripts/orchestrator.py --dry-run

# 3. Run Phase 1 (instant API badges, ~20 badges in 5-10 min)
python3 modules/badge-collector/scripts/orchestrator.py --phase 1

# 4. Check progress
python3 modules/badge-collector/scripts/orchestrator.py --status

# 5. Run all phases
python3 modules/badge-collector/scripts/orchestrator.py --phase all
```

## Phases

| Phase | Name | Badges | Time |
|-------|------|--------|------|
| 1 | Instant API | ~16 | 5-10 min |
| 2 | Competition | ~7 | 10-15 min |
| 3 | Pipeline | ~3 | 15-30 min |
| 4 | Browser | ~8 | 5-10 min |
| 5 | Streaks | ~4 | Setup only (runs daily) |

## Prerequisites

- Kaggle credentials configured (KAGGLE_USERNAME + KAGGLE_KEY)
- `pip install kagglehub kaggle requests`
- For Phase 4: `pip install playwright && playwright install chromium`
- For Phase 2: Must accept competition rules at kaggle.com first

## CLI Options

```
--phase N     Run phase N (1-5) or 'all'
--status      Show badge progress table
--resume      Skip already-earned badges
--dry-run     Show planned actions without executing
```

## Resource Naming

All created resources are prefixed with `badge-collector-` and created as **private**.
A 5-second delay between API calls prevents throttling.

## Progress Tracking

Progress is saved to `badge-progress.json` at the repo root (gitignored).
Use `--status` to view progress or `--resume` to continue from where you left off.

## Scripts

- `scripts/orchestrator.py` — Main entry point
- `scripts/badge_registry.py` — All 59 badge definitions
- `scripts/badge_tracker.py` — JSON progress persistence
- `scripts/phase_1_instant_api.py` — Instant API badges
- `scripts/phase_2_competition.py` — Competition badges
- `scripts/phase_3_pipeline.py` — Pipeline badges (requires KKB)
- `scripts/phase_4_browser.py` — Browser badges (Playwright)
- `scripts/phase_5_streaks.py` — Streak automation setup
- `scripts/utils.py` — Shared utilities

## References

- [badge-catalog.md](references/badge-catalog.md) — Complete 59-badge catalog with earning criteria
