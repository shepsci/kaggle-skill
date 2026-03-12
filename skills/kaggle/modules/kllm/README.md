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

For kaggle-cli: same env vars or `~/.kaggle/kaggle.json`.
For MCP Server: pass API key as `Authorization: Bearer <token>` header.

**Important:** API tokens generated at kaggle.com/settings (under "API Tokens
(Recommended)" → "Generate New Token") are the recommended auth method. Legacy
`KGAT_`-prefixed tokens still work but the new token format is preferred.

## Four Methods of Interaction

| Method | Type | Best For |
|--------|------|----------|
| **kagglehub** | Python library (`pip install kagglehub`) | Quick dataset/model download in Python |
| **kaggle-cli** | CLI (`pip install kaggle`) | Full workflow scripting (competitions, notebooks, datasets, models) |
| **Kaggle MCP Server** | Remote endpoint `https://www.kaggle.com/mcp` | AI agent integration (Claude Code, gemini-cli, Cursor, etc.) |
| **Kaggle UI** | Browser via Open Claw Chrome extension | Account setup, verification, visual exploration |

## Capability Matrix

| Task | kagglehub | kaggle-cli | MCP Server | UI |
|------|-----------|------------|------------|-----|
| Download dataset | `dataset_download()` | `kaggle datasets download` | Yes | Yes |
| Download model | `model_download()` | `kaggle models instances versions download` | Yes | Yes |
| Download competition data | `competition_download()` | `kaggle competitions download` | Yes | Yes |
| Download notebook output | `notebook_output_download()` | `kaggle kernels output` | Yes | Yes |
| Load dataset to DataFrame | `dataset_load()` ⚠️ | — | — | — |
| Execute notebook (KKB) | — | `kaggle kernels push/status/output` | Yes | Yes |
| Register for competition | — | — (accept rules via UI) | Yes | Yes |
| Submit to competition | — | `kaggle competitions submit` | Yes | Yes |
| Publish private dataset | `dataset_upload()` | `kaggle datasets create` | Yes | Yes |
| Publish private notebook | — | `kaggle kernels push` | Yes | Yes |
| Publish private model | `model_upload()` | `kaggle models create` | Yes | Yes |
| Register account | — | — | — | UI only |
| Get API tokens | — | — | — | UI only |
| Persona verification | — | — | — | UI only |

## Known Issues

- **`dataset_load()` issues**: Was broken in kagglehub v0.4.3 (404 on `DownloadDataset`).
  May be fixed in kagglehub 1.0.0. If issues persist, use `dataset_download()` then
  `pd.read_csv()` on the cached files.
- **`competitions download` does not support `--unzip`** in kaggle CLI >= 1.8. Only
  `datasets download` supports `--unzip`. Unzip competition data manually after download.
- **Competition-linked datasets** (e.g., `titanic/titanic`) return 403 even with valid
  credentials. Use standalone dataset copies or download via `competitions download`.
- **`competition_download()` 401 in kagglehub** (older versions): May be fixed in
  kagglehub 1.0.0. If issues persist, use `kaggle competitions download` CLI instead.
  For "rules not accepted" errors, navigate to
  `https://www.kaggle.com/competitions/<slug>/rules` in the browser and click accept.
- **MCP Server auth**: Use API tokens from "Generate New Token" at kaggle.com/settings.
  Legacy API keys may not work with all MCP endpoints.
- **Rate limiting**: Kaggle uses dynamic rate limiting. If you get HTTP 429, wait a few
  minutes and retry. Check code for unintended loops or redundant API calls.

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

## References

- [kaggle-knowledge.md](references/kaggle-knowledge.md) — Comprehensive Kaggle platform knowledge
- [kagglehub-reference.md](references/kagglehub-reference.md) — Full kagglehub Python API
- [cli-reference.md](references/cli-reference.md) — Complete kaggle-cli command reference
- [mcp-reference.md](references/mcp-reference.md) — Kaggle MCP server endpoint, auth, and tools
