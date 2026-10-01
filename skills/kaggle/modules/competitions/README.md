# Competitions

Competition discovery, overview pages, landscape reports, data downloads,
submissions, and hackathons.

## Read

```bash
python3 modules/competitions/scripts/competition_pages.py --competition titanic --summary
python3 modules/competitions/scripts/competition_pages.py --competition titanic --page evaluation
python3 modules/competitions/scripts/list_competitions.py --lookback-days 30 --output json
python3 modules/competitions/scripts/competition_details.py --slug titanic --top-n 5
```

- `competition_pages.py` prints the host's pages (rules, evaluation, data
  description, timeline). It needs no credential.
- `list_competitions.py` lists recent competitions in every category with
  team count, metric, reward, deadline, daily submission limit, and whether
  you have entered. It needs a credential. If every query fails it exits with
  status 1 instead of printing an empty list.
- `competition_details.py` prints the data files with sizes, the top of the
  leaderboard, and the most-voted notebooks. If one of the three lookups
  fails, the others are still printed and the failure is listed under
  `errors`. At most 200 files and 200 leaderboard rows are returned; a longer
  file list ends with an entry marked `"truncated": true`.

## Download data

```bash
bash modules/competitions/scripts/cli_download.sh titanic ./data --unzip
```

You must have accepted the competition's rules on kaggle.com. `--unzip`
extracts the archive and refuses any file that would land outside the folder.

## Submit

```bash
bash modules/competitions/scripts/cli_submit.sh titanic ./submission.csv "baseline"
bash modules/competitions/scripts/cli_submit.sh titanic ./submission.csv "baseline" --yes
```

Without `--yes` nothing is submitted: the script prints the submission limits
and what it would send. Submit only after the user confirms. Read
[competition-operations.md](references/competition-operations.md) first.

## Hackathons

Hackathons are competitions judged from writeups. See
[hackathons/README.md](hackathons/README.md).

```bash
python3 modules/competitions/hackathons/scripts/hackathon_overview.py --competition kaggle-measuring-agi --summary
python3 modules/competitions/hackathons/scripts/list_writeups.py --competition kaggle-measuring-agi --winner-only --array
python3 modules/competitions/hackathons/scripts/fetch_writeup.py --writeup-id 123456
```

## References

- [competition-operations.md](references/competition-operations.md): before
  and after a submission
- [competition-overview.md](references/competition-overview.md)
- [competition-categories.md](references/competition-categories.md)
- [competition-research.md](references/competition-research.md)
- [hackathon-endpoints.md](hackathons/references/hackathon-endpoints.md)
- [episode-endpoints.md](hackathons/references/episode-endpoints.md)
