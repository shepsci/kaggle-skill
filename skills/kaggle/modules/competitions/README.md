# Competitions

Use this module for competition discovery, overview pages, landscape reports,
competition data downloads, submissions, and hackathons.

## Scripts

```bash
python3 modules/competitions/scripts/list_competitions.py --lookback-days 30 --output json
python3 modules/competitions/scripts/competition_details.py --slug titanic
python3 modules/competitions/scripts/competition_pages.py --competition titanic --summary
bash modules/competitions/scripts/cli_competition.sh titanic submission.csv ./downloads/titanic
```

`cli_competition.sh` can download competition files and submit predictions.
Run it only after the user has accepted the rules and explicitly asked for the
account-visible action.

## Hackathons

Hackathons live under this module because they are Kaggle competitions with
extra MCP endpoints for overview pages, tracks, and writeups.

```bash
python3 modules/competitions/hackathons/scripts/hackathon_overview.py --competition kaggle-measuring-agi
python3 modules/competitions/hackathons/scripts/list_writeups.py --competition kaggle-measuring-agi
python3 modules/competitions/hackathons/scripts/fetch_writeup.py --writeup-id 123456
```

Role-gated responses are evidence. Preserve permission denials instead of
treating them as empty public data.

## References

- [competition-categories.md](references/competition-categories.md)
- [competition-overview.md](references/competition-overview.md)
- [competition-research.md](references/competition-research.md)
- [hackathon-endpoints.md](hackathons/references/hackathon-endpoints.md)
- [episode-endpoints.md](hackathons/references/episode-endpoints.md)
