# KLLM — Kaggle Interaction Module

Interact with kaggle.com using kagglehub, kaggle-cli, Kaggle MCP Server, or
Kaggle UI. Credentials are in `.env` and `~/.kaggle/kaggle.json` — **never
log or display them**.

## Credentials

**Before any Kaggle operation, run `python3 modules/kllm/scripts/check_credentials.py`** to
verify and auto-configure credentials.

**Auth methods (checked in order by kagglehub):**
1. `KAGGLE_API_TOKEN` env var (new style, preferred)
2. `~/.kaggle/access_token` file
3. `KAGGLE_USERNAME` + `KAGGLE_KEY` env vars (legacy)
4. `~/.kaggle/kaggle.json` with `{"username":"...","key":"..."}` (legacy, chmod 600)

For kaggle-cli: use `kaggle auth login`, the same env vars/token file, or
`~/.kaggle/kaggle.json`.
For MCP Server: pass API key as `Authorization: Bearer <token>` header.

**Important:** API tokens generated at kaggle.com/settings (under "API Tokens
(Recommended)" → "Generate New Token") are the recommended auth method. Legacy
`KGAT_`-prefixed tokens still work but the new token format is preferred.

## Four Methods of Interaction

| Method | Type | Best For |
|--------|------|----------|
| **kagglehub** | Python library (`pip install kagglehub`) | Quick dataset/model download in Python |
| **kaggle-cli** | CLI (`pip install kaggle>=2.2.3`) | Full workflow scripting (competitions, notebooks, datasets, models, forums, benchmarks) |
| **Kaggle MCP Server** | Remote endpoint `https://www.kaggle.com/mcp` | AI agent integration (Claude Code, gemini-cli, Cursor, etc.) |
| **Kaggle UI** | Browser via Open Claw Chrome extension | Account setup, verification, visual exploration |

## Capability Matrix

| Task | kagglehub | kaggle-cli | MCP Server | UI |
|------|-----------|------------|------------|-----|
| Search competitions | — | `kaggle competitions list` | `search_competitions` | Yes |
| Get competition metadata | — | — | `get_competition` | Yes |
| Read competition overview pages (rules / evaluation / data-description / FAQ / prizes / timeline) | — | `kaggle competitions pages` | `list_competition_pages` ([guide](references/competition-overview.md)) | Yes |
| Host competition creation/pages/launch | — | `competitions init/create/pages/launch` | — | Yes |
| List competition data files | — | `kaggle competitions files` | `list_competition_data_files` / `list_competition_data_tree_files` / `get_competition_data_files_summary` | Yes |
| Download competition data | `competition_download()` | `kaggle competitions download` | `download_competition_data_file` / `download_competition_data_files` | Yes |
| Submit to competition | — | `kaggle competitions submit` | `start_competition_submission_upload` → `submit_to_competition` | Yes |
| Submit kernel to code competition | — | `competitions submit -k ... -v ...` | `create_code_competition_submission` 🔒 | Yes |
| List/search submissions | — | `competitions submissions` / `team-submissions` | `search_competition_submissions` / `get_competition_submission` | Yes |
| Read leaderboard | — | `competitions leaderboard` / `leaderboard_writeups.py` | `get_competition_leaderboard` / `download_competition_leaderboard` | Yes |
| Simulation episodes, logs, replay | — | `competitions episodes/logs/replay` | `get_episode_agent_logs` / `get_episode_replay` / `list_submission_episodes` ([guide](hackathon/references/episode-endpoints.md)) | Yes |
| Search datasets | — | `kaggle datasets list` | `search_datasets` | Yes |
| Get dataset info / metadata | — | `datasets metadata/status` | `get_dataset_info` / `get_dataset_metadata` / `get_dataset_files_summary` / `get_dataset_status` | Yes |
| List dataset files | — | `kaggle datasets files` | `list_dataset_files` / `list_dataset_tree_files` | Yes |
| Download dataset | `dataset_download()` | `kaggle datasets download` | `download_dataset` | Yes |
| Upload dataset file / version | `dataset_upload()` | `datasets create/version/metadata --update` | `upload_dataset_file` / `update_dataset_metadata` | Yes |
| Search notebooks | — | `kaggle kernels list` | `search_notebooks` | Yes |
| Get notebook info | — | `kernels files/pull` | `get_notebook_info` / `list_notebook_files` | Yes |
| Execute notebook (KKB) | — | `kernels push/status/output/logs` | `create_notebook_session` → `get_notebook_session_status` → `download_notebook_output[_zip]` | Yes |
| Cancel notebook session | — | — | `cancel_notebook_session` | Yes |
| Save / version notebook | — | `kaggle kernels push` | `save_notebook` | Yes |
| List models | — | `kaggle models list` | `list_models` | Yes |
| Get model + variations + versions | — | `models get` / `instances files` | `get_model` / `list_model_variations` / `get_model_variation` / `list_model_variation_versions` / `list_model_variation_version_files` | Yes |
| Download model variation version | `model_download()` | `models instances versions download` | `download_model_variation_version` | Yes |
| Create / update model + variation | — | `models create/update` / `instances create/update` | `create_model` / `update_model` / `update_model_variation` | Yes |
| Forums and resource topics | — | `forums topics` / `<resource> topics` / `cli_forums.py` | `list_forums` / `list_forum_topics` / `get_forum` / `get_forum_topic` | Yes |
| Hackathon overview | — | `competitions pages` (basic) | `get_hackathon_overview` ([guide](hackathon/references/hackathon-endpoints.md)) | Yes |
| Hackathon writeups (list / fetch / by topic / by slug) | — | forum/topic fallback | `list_hackathon_write_ups` / `get_writeup` / `get_writeup_by_topic` / `get_writeup_by_slug` / `get_resolved_writeup_links` | Yes |
| Hackathon tracks | — | — | `list_hackathon_tracks` | Yes |
| Hackathon writeup CSV export (host/judge) | — | — | `download_hackathon_write_ups` 🔒 | Yes |
| Benchmarks | — | `kaggle benchmarks` / `kaggle b` | `create_benchmark_task_from_prompt` / `get_benchmark_leaderboard` ([guide](hackathon/references/benchmark-endpoints.md)) | Yes |
| Quota | — | `kaggle quota` | — | Yes |
| Authorize / user profile | — | OAuth via `kaggle auth login` | `authorize` / `get_user_profile` | Yes |
| Generic search | — | — | `search_content` | Yes |
| Register account | — | — | — | UI only |
| Get API tokens | — | — | — | UI only |
| Persona verification | — | — | — | UI only |

🔒 = role-gated. See [mcp-reference.md](references/mcp-reference.md) for the
full 70-tool inventory with status flags. Use CLI for scriptable platform
workflows and topics; use MCP where it exposes richer agent-oriented objects
or hackathon-specific writeup bodies.

## Known Issues

- **`dataset_load()` in kagglehub**: was broken in v0.4.3 (404 on
  `DownloadDataset`). The pinned baseline is now 1.0.0; status on 1.0.0 is
  unverified by this skill — if you hit issues, fall back to
  `dataset_download()` + `pd.read_csv()` on the cached files.
- **`competitions download` does not support `--unzip`** in kaggle CLI >= 1.8.
  Only `datasets download` supports `--unzip`. Unzip competition data manually
  after download (or use the bundled `_safe_extract` helper if you'd like
  zip-slip protection — see `skills/kaggle/modules/badge-collector/scripts/phase_2_competition.py`).
- **Competition-linked datasets** (e.g., `titanic/titanic`) return 403 even
  with valid credentials. Use standalone dataset copies or download via
  `competitions download`.
- **`competition_download()` 401 in kagglehub** (older versions): same
  caveat as `dataset_load()` — status on 1.0.0 unverified.
  For "rules not accepted" errors, navigate to
  `https://www.kaggle.com/competitions/<slug>/rules` in the browser and click accept.
- **MCP Server auth**: Use API tokens from "Generate New Token" at
  kaggle.com/settings. Legacy 32-char hex keys still work for many endpoints,
  but the new KGAT-prefixed token is required for the auth-gated endpoints
  (see `KGAT_ONLY_ENDPOINTS` in `tests/test_mcp.py`).
- **Rate limiting**: Kaggle uses dynamic rate limiting. If you get HTTP 429,
  wait a few minutes and retry. Check code for unintended loops or redundant
  API calls.
- **`get_hackathon_write_up`**: was returning generic invocation errors in
  the kmcp-tools 2026-04-22 audit; verified PASS as of the 2026-05-04 retest.
  The hackathon submodule's `fetch_writeup.py` uses `get_writeup` first
  anyway because it has a simpler arg shape.

## Task Workflows

### Download Dataset
```python
import kagglehub
path = kagglehub.dataset_download("owner/dataset-name")
```
```bash
kaggle datasets download owner/dataset-name --path ./data --unzip
```

### Download Model
```python
path = kagglehub.model_download("owner/model/framework/variation")
```

### Execute Notebook on KKB
```bash
kaggle kernels push -p ./notebook-dir
kaggle kernels status username/kernel-slug
kaggle kernels output username/kernel-slug --path ./output
```

See `modules/kllm/scripts/cli_execute.sh` for a complete push-poll-download workflow.

### Competition Submit
```bash
kaggle competitions submit -c competition-name -f submission.csv -m "description"
```

See `modules/kllm/scripts/cli_competition.sh` for a complete competition workflow.

### Read Competition Overview Pages

Before joining or analyzing a competition, pull its overview pages (rules,
evaluation, data description, FAQ, prizes, timeline) via the
CLI or the `list_competition_pages` MCP endpoint:

```bash
kaggle competitions pages titanic --content --format json
```

```bash
# Print every page as JSON
python3 modules/kllm/scripts/list_competition_pages.py --competition titanic

# One-line-per-page summary with key-page detection
python3 modules/kllm/scripts/list_competition_pages.py --competition titanic --summary

# Just the rules / evaluation page content
python3 modules/kllm/scripts/list_competition_pages.py --competition titanic --page rules
python3 modules/kllm/scripts/list_competition_pages.py --competition titanic --page evaluation
```

Works for regular competitions, playground series, AND hackathons. For
hackathon-specific overview content (judge ids, track structure), prefer
`hackathon_overview.py` from the hackathon module which calls
`get_hackathon_overview` instead.

See [references/competition-overview.md](references/competition-overview.md)
for the full endpoint reference, page-name conventions, and recommended
analysis patterns.

### Forums, Discussions, And Writeups

Use the CLI-backed wrapper for global forums and resource topics:

```bash
python3 modules/kllm/scripts/cli_forums.py forum-topics \
  --category competition_write_ups --sort-by recent --format json

python3 modules/kllm/scripts/cli_forums.py resource-topics \
  competitions titanic --sort-by recent --page 1 --format json

python3 modules/kllm/scripts/cli_forums.py resource-topic \
  competitions titanic/12345 --format json
```

For leaderboard solution writeup links:

```bash
python3 modules/kllm/scripts/leaderboard_writeups.py titanic --top-k 20 --pretty
```

For hackathon writeup bodies, stay on the MCP path under `hackathon/scripts/`.
See [references/forums-writeups.md](references/forums-writeups.md).

### Benchmarks CLI

Use `kaggle benchmarks` or `kaggle b` for task creation, model runs, status,
logs, downloads, publishing, and benchmark topics:

```bash
kaggle b init -y
kaggle b t push my-task -f task.py --wait 600
kaggle b t run my-task -m gemini-2.5-pro --wait
kaggle b t status my-task
kaggle b t download my-task --include-source
```

These commands can create Kaggle resources and consume quota, so confirm the
user wants the operation before running the full lifecycle. See
[references/benchmarks-cli.md](references/benchmarks-cli.md).

## Scripts

- `scripts/setup_env.sh` — Auto-configure Kaggle credentials from env vars (creates kaggle.json)
- `scripts/check_credentials.py` — Verify Kaggle credentials are configured (with auto-mapping)
- `scripts/network_check.sh` — Check network reachability to Kaggle API endpoints
- `scripts/poll_kernel.sh <kernel-slug> [output-dir] [poll-interval]` — Poll a KKB kernel for completion
- `scripts/cli_download.sh` — Download datasets and models via kaggle-cli
- `scripts/cli_execute.sh <notebook-dir> <kernel-slug> [output-dir]` — Execute a notebook on KKB
- `scripts/cli_competition.sh <competition> <submission-file> [download-dir]` — Competition workflow
- `scripts/cli_publish.sh <dataset|notebook|model> <dir> [model-handle]` — Publish resources
- `scripts/kagglehub_download.py` — Download datasets and models via kagglehub
- `scripts/kagglehub_publish.py <dataset|model> <handle> <local-dir> [version-notes]` — Publish via kagglehub
- `scripts/list_competition_pages.py --competition <slug> [--summary|--page NAME|--pretty]` — Fetch host-authored overview pages (rules, evaluation, data-description, FAQ, prizes, timeline) via the `list_competition_pages` MCP endpoint
- `scripts/cli_forums.py ...` — Safe wrapper around `kaggle forums topics` and `kaggle <resource> topics`
- `scripts/leaderboard_writeups.py <competition> [--top-k N]` — Discover solution writeup links from leaderboard payloads

## References

- [kaggle-knowledge.md](references/kaggle-knowledge.md) — Comprehensive Kaggle platform knowledge
- [kagglehub-reference.md](references/kagglehub-reference.md) — Full kagglehub Python API
- [cli-reference.md](references/cli-reference.md) — Complete kaggle-cli command reference
- [mcp-reference.md](references/mcp-reference.md) — Kaggle MCP server endpoint, auth, and tools
- [competition-overview.md](references/competition-overview.md) — `list_competition_pages` endpoint, page-name conventions, briefing patterns
- [forums-writeups.md](references/forums-writeups.md) — CLI forums/resource topics, leaderboard solution writeups, and hackathon writeup routing
- [benchmarks-cli.md](references/benchmarks-cli.md) — Current `kaggle benchmarks` command workflow and task-authoring guidance
- [competition-research.md](references/competition-research.md) — Evidence-first competition research brief workflow
