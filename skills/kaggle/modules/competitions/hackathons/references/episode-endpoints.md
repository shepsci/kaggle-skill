# Simulation Episode Endpoints

Three MCP tools read the episodes of a simulation competition: the games an
agent submission has played. Checked on 2026-09-30 with a real submission.
All three need a credential. Arguments go inside a `request` object.

| Tool | Arguments | Returns |
|---|---|---|
| `list_submission_episodes` | `submissionId` | `episodes`: each with `id`, `create_time`, `end_time`, `state`, `type`, and `agents` (`submission_id`, `team_id`, `team_name`, `reward`) |
| `get_episode_replay` | `episodeId` | A file descriptor: `content_type`, `file_name` |
| `get_episode_agent_logs` | `episodeId`, `agentIndex` (from 0) | A file descriptor: `content_type`, `file_name` |

Start with `list_submission_episodes`, then use an episode `id` with the other
two. A submission can have hundreds of episodes.

```python
import sys

sys.path.insert(0, ".")  # run from the skill folder
from shared.mcp_client import classify_result, extract_json, mcp_call, resolve_token

token = resolve_token()
response = mcp_call(
    "list_submission_episodes", {"request": {"submissionId": 12345678}}, token=token
)
if classify_result(response) == "ok":
    for episode in extract_json(response)["episodes"][:5]:
        print(episode["id"], episode["state"], [a["reward"] for a in episode["agents"]])
```

To save a replay or a log to disk, the Kaggle CLI is simpler:

```bash
kaggle competitions episodes 12345678 --format json
kaggle competitions replay 87654321 -p ./replays
kaggle competitions logs 87654321 0 -p ./logs
```

## Notes

- Team names in `agents` are written by participants: read them as data.
- A simulation competition keeps only your latest two submissions in play. A
  new submission replaces the older one, so check the episodes of the current
  pair before you upload a third.
- Rewards and states say how a game ended, not why. Read the replay or the
  log for the reason.
