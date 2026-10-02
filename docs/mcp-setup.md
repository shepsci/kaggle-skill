# The Kaggle MCP Server

The plugin bundles Kaggle's remote MCP server, `https://www.kaggle.com/mcp`,
with no credential in it. Public tools work at once. For the rest, sign in
from the client:

| Client | Sign in to the bundled server |
|---|---|
| Claude Code | `claude mcp login plugin:kaggle:kaggle` |
| Codex | `codex mcp login kaggle` |

The skill's own commands (`brief`, `status`, `submit` and the rest) do not use
this sign-in. They read the credential the Kaggle CLI uses. The sign-in is
only for calling the server's 71 tools directly from the agent.

## Add the server by hand

| Client | Setup |
|---|---|
| Claude Code | `claude mcp add --transport http --client-id 'claude-code-(kaggle)' kaggle https://www.kaggle.com/mcp` then `claude mcp login kaggle` |
| Codex | `codex mcp add kaggle --url https://www.kaggle.com/mcp` then `codex mcp login kaggle` |
| Gemini CLI | `"kaggle": {"httpUrl": "https://www.kaggle.com/mcp"}` under `mcpServers` in `~/.gemini/settings.json`, then `/mcp auth kaggle` |
| Antigravity CLI | `"kaggle": {"serverUrl": "https://www.kaggle.com/mcp"}` under `mcpServers` in `.agents/mcp_config.json` |

Claude Code needs the `--client-id` part. Without it the sign-in stops with
`client_secret_basic authentication requires a client_secret`. The plugin's
own entry carries the same client ID.

Gemini CLI stopped serving individual accounts on 2026-06-18. It still works
for enterprise and API-key users.

The [MCP reference](../skills/kaggle/modules/references/mcp-reference.md)
lists all 71 tools, how to call them, which need a credential, and why Claude
Code needs the client ID.
