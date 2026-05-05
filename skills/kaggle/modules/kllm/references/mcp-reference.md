# Kaggle MCP Server Reference

> Official docs: https://www.kaggle.com/docs/mcp
> Blog: https://www.kaggle.com/blog/kaggles-official-mcp-server

## Endpoint

```
https://www.kaggle.com/mcp
```

Protocol: Streamable HTTP (MCP standard).

## Authentication

Pass your Kaggle API token as a Bearer token:

```
Authorization: Bearer <your_api_token>
```

Use the API token from "Generate New Token" at [kaggle.com/settings](https://www.kaggle.com/settings). Legacy API keys from `kaggle.json` also work but are deprecated.

## Client Configuration

### Claude Code (CLI)

```bash
claude mcp add kaggle --transport http https://www.kaggle.com/mcp \
  --header "Authorization: Bearer YOUR_API_KEY"
```

### gemini-cli

```bash
# Add to your gemini-cli MCP config (see gemini-cli docs for exact syntax)
# Endpoint: https://www.kaggle.com/mcp
# Header: Authorization: Bearer YOUR_API_KEY
```

### Generic MCP Client (Claude Desktop, Cursor, etc.)

```json
{
  "mcpServers": {
    "kaggle": {
      "url": "https://www.kaggle.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### OpenClaw (via HTTP/curl)

OpenClaw can call the Kaggle MCP server directly over HTTP using the Streamable HTTP transport:

```bash
# List available tools (use KAGGLE_API_TOKEN, not KAGGLE_KEY)
curl -s -X POST https://www.kaggle.com/mcp \
  -H "Authorization: Bearer ${KAGGLE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 -m json.tool

# Call a tool (e.g., search competitions)
curl -s -X POST https://www.kaggle.com/mcp \
  -H "Authorization: Bearer ${KAGGLE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_competitions","arguments":{"search":"titanic"}}}' | python3 -m json.tool
```

```python
# Python requests example
import os, requests, json

KAGGLE_KEY = os.environ["KAGGLE_API_TOKEN"]  # API token from "Generate New Token"
URL = "https://www.kaggle.com/mcp"
HEADERS = {"Authorization": f"Bearer {KAGGLE_KEY}", "Content-Type": "application/json"}

def mcp_call(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        payload["params"] = params
    resp = requests.post(URL, headers=HEADERS, json=payload)
    return resp.json()

# List tools
print(mcp_call("tools/list"))

# Search datasets
print(mcp_call("tools/call", {"name": "search_datasets", "arguments": {"search": "titanic"}}))
```

## Tool Inventory (66 live tools as of 2026-04-22, verified 2026-05-04)

Source: `tools/list` against `https://www.kaggle.com/mcp`, cross-referenced
against [shepsci/kmcp-tools](https://github.com/shepsci/kmcp-tools)
`data/endpoints.md`. Use `tools/list` to confirm against the current server.

**Status flag changes since the 2026-04-22 audit** (verified by
`tests/integration/test_mcp_live.py` on 2026-05-04):

- `get_hackathon_write_up` — was KNOWN_FAIL, **now PASS**. Kaggle shipped a fix.
- `get_benchmark_leaderboard` — was BLOCKED (permission-gated), **now PASS**
  for ordinary KGAT tokens.
- `get_competition` for classic competitions (titanic, playground-series-s6e2)
  — was KNOWN_FAIL, **now PASS**.

The hackathon module's `fetch_writeup.py` fallback chain (`get_writeup` →
`get_writeup_by_topic` → `get_writeup_by_slug`) is retained as defensive
plumbing but is no longer required to work around server bugs.

Status legend:
- ✅ verified PASS (as of 2026-05-04)
- 🔒 BLOCKED by role/permission (host or judge required)
- 🔬 BAD_PROBE (test infra issue, tool may still work)

### Auth
- ✅ `authorize` — Check whether the client can authorize with Kaggle
- ✅ `get_user_profile` — Fetch a public user profile

### Competition
- ✅ `get_competition` — Backend bug for classic competitions (titanic, playground-series-s6e2) was fixed between 2026-04-22 and 2026-05-04
- ✅ `search_competitions`
- ✅ `get_competition_data_files_summary`
- ✅ `get_competition_leaderboard`
- ✅ `get_competition_submission`
- ✅ `search_competition_submissions`
- ✅ `list_competition_data_files`
- ✅ `list_competition_data_tree_files`
- ✅ `list_competition_pages` — host-authored overview pages (rules, evaluation, data-description, FAQ, prizes, timeline). Universal: works for regular competitions, playgrounds, and hackathons. See [competition-overview.md](competition-overview.md) for the full reference and patterns. Wrapper script: `modules/kllm/scripts/list_competition_pages.py`.
- ✅ `download_competition_data_file`
- ✅ `download_competition_data_files`
- ✅ `download_competition_leaderboard`
- ✅ `start_competition_submission_upload`
- ✅ `submit_to_competition`
- 🔒 `create_code_competition_submission` — kernel→competition; permission-gated

### Dataset
- ✅ `search_datasets`
- ✅ `get_dataset_info`
- ✅ `get_dataset_metadata`
- ✅ `get_dataset_status`
- ✅ `get_dataset_files_summary`
- ✅ `list_dataset_files`
- ✅ `list_dataset_tree_files`
- ✅ `download_dataset`
- ✅ `update_dataset_metadata`
- ✅ `upload_dataset_file`

### Notebook
- ✅ `search_notebooks`
- ✅ `get_notebook_info`
- ✅ `get_notebook_session_status`
- ✅ `create_notebook_session`
- ✅ `cancel_notebook_session`
- ✅ `download_notebook_output`
- ✅ `download_notebook_output_zip`
- ✅ `list_notebook_files`
- ✅ `list_notebook_session_output`
- ✅ `save_notebook`

### Model
- ✅ `list_models`
- ✅ `get_model`
- ✅ `create_model`
- ✅ `update_model`
- ✅ `list_model_variations`
- ✅ `get_model_variation`
- ✅ `update_model_variation`
- ✅ `list_model_variation_versions`
- ✅ `list_model_variation_version_files`
- ✅ `download_model_variation_version`

### Forum
- ✅ `list_forums`
- ✅ `list_forum_topics`
- ✅ `get_forum`
- ✅ `get_forum_topic`

### Hackathon (newer surface — see `modules/kllm/hackathon/`)
- ✅ `get_hackathon_overview` — rules, eligibility, rubric, prizes
- ✅ `list_hackathon_write_ups` — submission roster (paginated)
- ✅ `list_hackathon_tracks` — resolve track id → title
- ✅ `get_hackathon_write_up` — generic invocation error fixed between 2026-04-22 and 2026-05-04; `get_writeup` remains the simpler interface (no `competitionName` arg needed)
- ⚠️  `download_hackathon_write_ups` — host-only; may return CSV header only

### Writeup
- ✅ `get_writeup` — preferred full-body fetch (use over `get_hackathon_write_up`)
- ✅ `get_writeup_by_slug`
- ✅ `get_writeup_by_topic`
- ⚠️  `get_resolved_writeup_links` — host context returns `{}`; participants get role-gated denial

### Benchmark
- ✅ `create_benchmark_task_from_prompt`
- ✅ `get_benchmark_leaderboard` — permission gate lifted between 2026-04-22 and 2026-05-04 (now responds to ordinary KGAT tokens)

### Episode (simulation/agent evaluation)
- 🔬 `get_episode_agent_logs`
- 🔬 `get_episode_replay`
- ✅ `list_submission_episodes`

### Search
- ✅ `search_content` — generic content search

## Usage Patterns

### Search and Download
```
Search datasets matching "titanic" → select best match → download it
```

### Competition Workflow
```
List competitions → join → download data → submit predictions → check leaderboard
```

### Publish Resources
```
Create private dataset with title and license → upload files → verify
```

### Execute Notebook
```
Push notebook code → poll status → retrieve output when complete
```

### Hackathon Writeup Retrieval
```
get_hackathon_overview (rules/rubric) → list_hackathon_tracks (id→title) →
list_hackathon_write_ups (roster) → get_writeup per submission →
get_resolved_writeup_links (host/judge only)
```

Avoid `get_hackathon_write_up` — it returns a generic invocation error even for
valid ids. The `modules/kllm/hackathon/scripts/fetch_writeup.py` script encodes the
correct fallback chain (`get_writeup` → `get_writeup_by_topic` → `get_writeup_by_slug`).

## Official Documentation

- Full tool reference: https://www.kaggle.com/docs/mcp
- Blog announcement: https://www.kaggle.com/blog/kaggles-official-mcp-server
- MCP Protocol spec: https://modelcontextprotocol.io
