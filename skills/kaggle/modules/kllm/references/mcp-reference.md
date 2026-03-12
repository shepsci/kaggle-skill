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

## Tool Categories

Use `tools/list` for exact tool names. The server provides tools across these categories:

### Authentication
- `authenticate` — Set Kaggle credentials (username + key)

### Competition Tools
- List available competitions (with search, category, sort, page filters)
- Get competition details (evaluation metric, tags, kernel submission settings)
- Download competition files (specific file or all, with path option)
- List competition files (names, sizes, dates)
- Submit predictions (file path + message)
- List your submissions (scores, status)
- Get leaderboard (team rankings, scores)

### Dataset Tools
- List/search datasets (search, user, license, file type, tags, sort, size filters)
- List files in a dataset
- Download dataset files (to specified path or temp dir)
- Get dataset metadata (JSON format)
- Create new dataset (title, files dir, license, description, private flag)
- Create new version (version notes, convert-to-csv flag, delete-old flag)
- Check dataset status (creation progress, errors)
- Initialize dataset metadata file
- Update dataset metadata

### Kernel/Notebook Tools
- List kernels (search, user, language, type, output type, sort, page)
- List kernel files
- Download kernel output (to specified path)
- Pull kernel code (with optional metadata generation)
- Get kernel status (ref, title, status, error message, has output)
- Initialize kernel metadata (notebook/script, python/r)
- Push kernel (from folder with code + metadata — triggers KKB execution)

### Model Tools
- List models (search, sort, owner, page)
- Get model details
- Initialize model metadata
- Create new model
- Update model
- Delete model
- Get/create/update/delete model instance (variation)
- List model instance files
- Create/download/delete/list-files for model instance version

### Config Tools
- View current config
- Set config value (competition, path, proxy)
- Unset config value

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

## Official Documentation

- Full tool reference: https://www.kaggle.com/docs/mcp
- Blog announcement: https://www.kaggle.com/blog/kaggles-official-mcp-server
- MCP Protocol spec: https://modelcontextprotocol.io
