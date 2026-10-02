# Kaggle Competition Categories

How competition types map to what the API and the CLI accept.

## `--category`

| Competition type | `category` value | Notes |
|---|---|---|
| Featured | `featured` | Prize competitions |
| Research | `research` | Research problems, often with unusual metrics |
| Playground | `playground` | For practice; small prizes or swag |
| Getting Started | `gettingStarted` | Long-running tutorials such as Titanic |
| Recruitment | `recruitment` | Sponsored by a company that is hiring |
| Masters | `masters` | Limited to Masters and Grandmasters |

The accepted values are `all`, `featured`, `research`, `recruitment`,
`gettingStarted`, `masters`, and `playground`.

## `--group`

| Group | What it lists |
|---|---|
| `general` | The default: Kaggle-run competitions |
| `entered` | Competitions you have entered |
| `community` | Community competitions, which `general` leaves out |
| `hosted` | Competitions you host |
| `unlaunched`, `unlaunched_community` | Not yet launched, for hosts |

`inClass`, which the CLI's help still mentions, is rejected.

```bash
kaggle competitions list --group community --sort-by recentlyCreated --format json
kaggle competitions list --category playground --sort-by latestDeadline --format json
```

`list_competitions.py` queries every category, then no category, then the
community group, and removes duplicates.

## Types that share a category

Some types are told apart by tags or fields, not by category:

- **Simulation**: tags such as `simulation`. Submissions are agents that play
  episodes. Only the latest two submissions stay in play.
- **Hackathon**: tag `hackathon`. Judged from writeups, with no leaderboard.
  `list_competitions.py` reports a hackathon as active after its deadline,
  because results appear only when the judges finish.
- **Code competition**: `is_kernels_submissions_only` is true. Submissions are
  notebooks.

## Getting Started competitions

Titanic, House Prices, Digit Recognizer and the like have no real start or
end, and their leaderboards roll over every two months. Leave them out of
"recently launched" reports unless the user asks for them.
