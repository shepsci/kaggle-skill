# Kaggle Competition Categories

Reference for mapping competition types to API categories.

## API Category Mapping

| Competition Type       | API `category` Value | Notes                                              |
|------------------------|----------------------|----------------------------------------------------|
| Featured Prediction    | `featured`           | Standard prize competitions                        |
| Research Prediction    | `research`           | Research-oriented, often with novel evaluation      |
| Playground             | `playground`         | Learning-focused, smaller prizes or swag            |
| Getting Started        | `gettingStarted`     | Semi-permanent tutorials (Titanic, Housing, etc.)   |
| Recruitment            | `recruitment`        | Company-sponsored talent search                     |
| Masters                | `masters`            | Restricted to Masters/Grandmasters tier             |
| Simulation             | `featured`           | Tags contain "simulation"; uses agent-based eval    |
| Game Arena             | `featured` or `all`  | Tags contain "game" or "arena"                      |
| Featured Hackathon     | `featured`           | Tags contain "hackathon"; shorter duration           |
| Community              | (varies)             | Catch-all; query `category=""` minus known types    |

## Identifying Special Types

Some competition types share the `featured` category but can be distinguished by tags:

- **Simulation**: Look for tags like `simulation`, `agent`, `game-theory`
- **Game Arena**: Look for tags like `game`, `arena`, `multi-agent`
- **Hackathon**: Look for tags like `hackathon`; also tend to have deadlines < 7 days from launch. **Hackathons are classified as active until winners are announced** (no leaderboard — results appear on a Winners tab after judging, often weeks/months after deadline)
- **Code competitions**: Check `isKernelsSubmissionsOnly == true`

## Notes on Getting Started Competitions

Getting Started competitions (Titanic, Housing Prices, Digit Recognizer, etc.) are
semi-permanent and don't have meaningful "launch" or "completion" dates. They should
generally be excluded from "recently launched" reports unless specifically requested.

## Querying Strategy

1. Query each specific category (`featured`, `research`, `playground`, etc.) with
   `sort_by=recentlyCreated` to get the latest in each bucket.
2. Also query with no category filter (empty string) to catch competitions that may
   not appear under specific categories.
3. Deduplicate by slug since the same competition may appear in multiple queries.
