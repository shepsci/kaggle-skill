# kaggle-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-kaggle--skill-blue)](https://skills.sh/shepsci/kaggle-skill/kaggle)
[![ClawHub](https://img.shields.io/badge/ClawHub-kaggle-green)](https://clawhub.ai/skills/kaggle)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/shepsci/kaggle-skill?style=social)](https://github.com/shepsci/kaggle-skill)

`kaggle-skill` is an agent skill and plugin for end-to-end Kaggle work:
credential setup, competition research, dataset/model downloads, notebook
execution, submissions, forums and writeups, benchmark workflows, and badge
collection.

This is an independent, unofficial project. It is not affiliated with,
endorsed by, or sponsored by Kaggle or Google.

The repository name is `kaggle-skill`; the public skill and plugin name is
`kaggle`. It works with agents that support SKILL-style packages, including
Claude Code, Codex, OpenClaw, Antigravity CLI (`agy`), Hermes, Cursor, and 35+
agents via skills.sh. Antigravity CLI is recommended for new installs; Gemini
CLI remains tested for legacy compatibility.

## Demo

Terminal walkthrough: install `kaggle@shepsci`, verify Kaggle credentials
without exposing secrets, summarize Titanic competition pages, and retrieve
recent Kaggle writeup discussions. Replay the committed clean source cast with
`asciinema play docs/demo/install-and-demo.cast`.
More task-focused local screencasts live in the [demo library](docs/demo/README.md).

## Available On

| Platform | Link | Install |
|---|---|---|
| skills.sh | [skills.sh/shepsci/kaggle-skill](https://skills.sh/shepsci/kaggle-skill/kaggle) | `npx skills add shepsci/kaggle-skill` |
| ClawHub | [clawhub.ai/skills/kaggle](https://clawhub.ai/skills/kaggle) | `clawhub install kaggle` |
| Codex self-hosted repo marketplace | [github.com/shepsci/kaggle-skill](https://github.com/shepsci/kaggle-skill) | `codex plugin marketplace add shepsci/kaggle-skill --ref main` then `codex plugin add kaggle@shepsci` |
| Claude Code self-hosted marketplace | [github.com/shepsci/kaggle-skill](https://github.com/shepsci/kaggle-skill) | `/plugin marketplace add shepsci/kaggle-skill` then `/plugin install kaggle@shepsci` |

## What You Can Ask

- "Set up my Kaggle credentials."
- "Summarize the rules and evaluation metric for the Titanic competition."
- "Generate a Kaggle competition landscape report for the last 30 days."
- "Search Kaggle discussion topics about ensembling."
- "Find recent solution writeups for this competition."
- "Pull every writeup from `kaggle-measuring-agi` and group by track."
- "Download this dataset and prepare it for a notebook."
- "Push this notebook to Kaggle Kernels and tell me when it finishes."
- "Initialize a Kaggle benchmark task and run one model."
- "What badges can I still earn through API activity?"

## Documentation

| Need | Start Here |
|---|---|
| Install and first run | [Docs hub](docs/README.md) |
| Choose the right workflow | [Workflow guide](docs/workflows.md) |
| Credential setup | [Registration module](skills/kaggle/modules/registration/README.md) |
| CLI, forums, topics, writeups, notebooks | [KLLM module](skills/kaggle/modules/kllm/README.md) |
| Current Kaggle CLI command surface | [CLI reference](skills/kaggle/modules/kllm/references/cli-reference.md) |
| Forums, discussions, and writeups | [Forums/writeups reference](skills/kaggle/modules/kllm/references/forums-writeups.md) |
| Benchmark task workflows | [Benchmarks reference](skills/kaggle/modules/kllm/references/benchmarks-cli.md) |
| MCP tool inventory | [MCP reference](skills/kaggle/modules/kllm/references/mcp-reference.md) |
| Competition landscape reports | [Competition report module](skills/kaggle/modules/comp-report/README.md) |
| Badge collection | [Badge collector module](skills/kaggle/modules/badge-collector/README.md) |
| Troubleshooting | [Troubleshooting guide](docs/troubleshooting.md) |
| Plugin distribution status | [Codex request packet](docs/distribution/codex-curated-plugin-request.md) and [Claude directory packet](docs/distribution/claude-community-submission.md) |
| Screencasts and demo recording | [Demo library](docs/demo/README.md) |

## Install

### Claude Code

```text
/plugin marketplace add shepsci/kaggle-skill
/plugin install kaggle@shepsci
```

Claude's `marketplace add` command adds a marketplace catalog, not an individual
plugin. `shepsci/kaggle-skill` contains its own `.claude-plugin/marketplace.json`,
so it is the canonical Claude marketplace source for `kaggle`.

### Codex

```bash
codex plugin marketplace add shepsci/kaggle-skill --ref main
codex plugin add kaggle@shepsci
```

### skills.sh

```bash
npx skills add shepsci/kaggle-skill
```

### ClawHub

```bash
clawhub install kaggle
```

### Manual Clone

```bash
git clone https://github.com/shepsci/kaggle-skill.git
cd kaggle-skill
python3 -m pip install \
  "kagglehub>=1.0.0" \
  "kaggle>=2.2.3" \
  "kagglesdk>=0.1.33,<1.0" \
  python-dotenv requests
```

Then copy `skills/kaggle/` into your agent's skills directory if your agent does
not support plugin or marketplace installs.

## Credential Setup

Kaggle's current token flow uses a single token string. Save it in one of these
locations:

```bash
mkdir -p ~/.kaggle
printf '%s\n' 'YOUR_TOKEN' > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
```

or:

```bash
export KAGGLE_API_TOKEN='YOUR_TOKEN'
```

Legacy `~/.kaggle/kaggle.json` credentials still work for many CLI workflows,
but `KAGGLE_API_TOKEN` or `~/.kaggle/access_token` is preferred for MCP-backed
workflows. Verify setup with:

```bash
python3 skills/kaggle/shared/check_all_credentials.py
```

## Quick Examples

### Competition Pages

```bash
python3 skills/kaggle/modules/kllm/scripts/list_competition_pages.py \
  --competition titanic --summary

python3 skills/kaggle/modules/kllm/scripts/list_competition_pages.py \
  --competition titanic --page evaluation
```

### Forums And Topics

```bash
python3 skills/kaggle/modules/kllm/scripts/cli_forums.py forum-topics \
  --category competition_write_ups --sort-by recent --format json

python3 skills/kaggle/modules/kllm/scripts/cli_forums.py resource-topics \
  competitions titanic --sort-by recent --page 1 --format json
```

### Leaderboard Writeup Links

```bash
python3 skills/kaggle/modules/kllm/scripts/leaderboard_writeups.py \
  titanic --top-k 20 --pretty
```

### Hackathon Writeups

```bash
python3 skills/kaggle/modules/kllm/hackathon/scripts/list_writeups.py \
  --competition kaggle-measuring-agi --array

python3 skills/kaggle/modules/kllm/hackathon/scripts/fetch_writeup.py \
  --writeup-id 71617
```

### Benchmark CLI

```bash
kaggle b init -y
kaggle b t push my-task -f task.py --wait 600
kaggle b t run my-task -m gemini-2.5-pro --wait
```

All wrappers that emit Kaggle-supplied text wrap that text in
`<untrusted-content source="..." tool="...">` markers so agents treat external
content as data rather than instructions. The guard is enforced by
`tests/security/test_untrusted_content_wrappers.py`.

## Architecture

The skill is organized around four modules:

| Module | Purpose |
|---|---|
| Registration | Account setup, token storage, credential checks |
| Competition reports | Competition discovery and landscape reporting |
| Kaggle interaction (`kllm`) | Kaggle CLI, kagglehub, MCP, forums, topics, writeups, notebooks, benchmarks |
| Badge collector | API-first badge earning workflows with manual fallbacks where needed |

When installed as a Claude Code plugin, the bundled `.mcp.json` configures the
Kaggle MCP server. The live inventory was verified on 2026-07-03 with 70 tools;
see the [MCP reference](skills/kaggle/modules/kllm/references/mcp-reference.md)
for status notes and role-gated endpoints.

## Distribution Status

The public skill name and plugin name are both `kaggle`.

This repo includes:

- `.codex-plugin/plugin.json` for Codex.
- `.agents/plugins/marketplace.json` for Codex repo marketplace installs.
- `.claude-plugin/plugin.json` for Claude Code.
- `.claude-plugin/marketplace.json` for in-repo Claude marketplace metadata.

Current status:

- `kaggle-skill` is self-hosted and installable from this repository and from
  third-party skill indexes such as skills.sh and ClawHub.
- This project is independent and unofficial. It is not affiliated with,
  endorsed by, or sponsored by Kaggle or Google.
- Claude plugin-directory submission is the first official-listing target.
  Anthropic Verified is a separate discretionary review goal to pursue after
  directory acceptance and usage evidence.
- Codex curated listing depends on OpenAI's official publishing or partner
  review path. The repo marketplace remains the supported Codex install path
  until a curated listing is accepted.
- This repository does not claim Claude official, Anthropic Verified, or
  OpenAI-curated status unless those default catalogs list it.

The plugin selector remains `kaggle@shepsci` for compatibility with existing
installs. If a reviewer requires a less first-party-looking identifier, use the
distribution packets to evaluate a future rename such as `kaggle-workflows`.

The bundled `.mcp.json` configures Kaggle's remote MCP endpoint with a
user-provided bearer token from `KAGGLE_API_TOKEN`. That is documented as a
review consideration in the Claude and Codex distribution packets.

## Security

Security claims are backed by tests in `tests/security/` and `tests/manifest/`.

| Property | Guard |
|---|---|
| No dynamic `eval`, `exec`, `compile`, or `__import__` in scripts | `tests/security/test_no_dynamic_eval.py` |
| Credentials are not echoed to stdout, stderr, or logs | `tests/security/test_no_credential_leakage.py` |
| Kaggle-supplied text is wrapped as untrusted content | `tests/security/test_untrusted_content_wrappers.py` |
| Zip extraction blocks path traversal | `tests/security/test_zip_slip_protection.py` |
| Dataset slugs are validated before shell use | `tests/security/test_dataset_slug_validation.py` |
| SessionStart hook avoids auto-installing packages or sourcing CWD `.env` | `tests/security/test_session_start_hook_safety.py` |
| MCP config uses HTTPS plus env-var token substitution | `tests/manifest/test_mcp_json_valid.py` |

Report security issues through [SECURITY.md](SECURITY.md). General support and
distribution questions can be filed as GitHub issues.

Network egress is limited to Kaggle, Google storage, PyPI, and GitHub domains in
`.claude/settings.json`.

## Compatibility

| Platform | Status |
|---|---|
| Claude Code | Tested |
| OpenClaw | Tested |
| Antigravity CLI (`agy`) | Tested |
| Gemini CLI (legacy) | Tested |
| Codex | Tested |
| Hermes | Compatible |
| Cursor | Compatible |
| GitHub Copilot | Compatible |
| Cline | Compatible |
| Amp | Compatible |
| 35+ agents via skills.sh | Compatible |

## License And Privacy

MIT license. See [LICENSE](LICENSE).

This skill collects no data. Credentials and processing remain local; see
[PRIVACY.md](PRIVACY.md).
