# Claude Directory Submission Package

Status: directory-first submission packet. Submit this repository to the Claude
plugin directory first, then pursue Anthropic Verified after directory
acceptance and usage evidence.

Official Claude docs used:

- Create plugins: https://code.claude.com/docs/en/plugins
- Plugin marketplaces: https://code.claude.com/docs/en/plugin-marketplaces
- Discover plugins: https://code.claude.com/docs/en/discover-plugins
- Submit plugins: https://claude.com/docs/plugins/submit
- Community marketplace mirror: https://github.com/anthropics/claude-plugins-community
- Official marketplace: https://github.com/anthropics/claude-plugins-official

## Listing Strategy

Use the documented Claude plugin-directory submission flow with the public
GitHub repository URL. Treat "directory listed" and "Anthropic Verified" as
separate outcomes:

- Directory listing: first target; submit through the forms below and verify the
  accepted listing before changing public claims.
- Anthropic Verified: follow-up target; request after directory acceptance,
  reviewer feedback, and usage evidence.
- Self-hosted marketplace: current install path; users add
  `shepsci/kaggle-skill` manually before installing `kaggle@shepsci`.

This repository does not claim Claude official, Claude directory, or Anthropic
Verified listing status unless the relevant catalog lists it.

Submit through one of the documented forms:

- Claude organization form: https://claude.ai/admin-settings/directory/submissions/plugins/new
- Console form: https://platform.claude.com/plugins/submit

## Plugin Metadata

- Public plugin name: `kaggle`
- Public skill name: `kaggle`
- Repository: https://github.com/shepsci/kaggle-skill
- Primary marketplace source: https://github.com/shepsci/kaggle-skill
- License: MIT
- Category: data-science
- Version: 2.3.0
- Privacy policy: https://github.com/shepsci/kaggle-skill/blob/main/PRIVACY.md
- Security and support: https://github.com/shepsci/kaggle-skill/blob/main/SECURITY.md
- Third-party notices: `THIRD_PARTY_NOTICES.md`

The plugin selector remains `kaggle@shepsci` for compatibility with existing
self-hosted installs. If Claude review requires a less first-party-looking
identifier, evaluate a future rename such as `kaggle-workflows` with marketplace
rename guidance rather than changing the selector in this submission.

## Marketplace Entry

The in-repo Claude marketplace entry lives at:

```text
.claude-plugin/marketplace.json
```

## Install Path

Install from this repository as the marketplace source:

```text
/plugin marketplace add shepsci/kaggle-skill
/plugin install kaggle@shepsci
```

Claude Code distinguishes the marketplace source from the plugin source. The
marketplace source is the repository containing `.claude-plugin/marketplace.json`.
This repository now contains that file directly, so `shepsci/kaggle-skill` can
be added as the marketplace. The marketplace manifest name is still `shepsci`,
so the install selector remains `kaggle@shepsci`.

Install selector:

```text
kaggle@shepsci
```

For Claude directory submission metadata, use an HTTPS git URL source:

```json
{
  "source": {
    "source": "url",
    "url": "https://github.com/shepsci/kaggle-skill.git",
    "ref": "main"
  }
}
```

## Suggested Form Copy

Short description:

```text
Complete Kaggle integration: competition reports, dataset/model downloads,
notebook execution, forums, writeups, submissions, and badge collection.
```

Long description:

```text
Kaggle is a Claude Code plugin and agent skill for end-to-end Kaggle workflows:
credential setup, current Kaggle CLI guidance, Kaggle MCP access, competition
research briefs, datasets, models, notebooks, forums/topics, leaderboard
solution writeup discovery, hackathon writeup retrieval, benchmark task
workflows, and badge collection. It includes safety wrappers that mark
Kaggle-supplied forum/writeup/page content as untrusted data for agent use.
```

Security notes:

```text
The plugin does not collect data. Kaggle credentials remain local and are read
from KAGGLE_API_TOKEN or ~/.kaggle/access_token. Scripts avoid dynamic code
execution, redact credential output, validate download paths, and wrap
Kaggle-supplied text in untrusted-content markers. Externally visible actions
such as competition submissions, dataset/model/notebook publishing, benchmark
task creation, and badge collection require explicit user intent; dry-run
commands are documented where available.
```

MCP/auth review note:

```text
The bundled .mcp.json points at Kaggle's HTTPS MCP endpoint and passes the
user's own KAGGLE_API_TOKEN as a bearer token. No token is bundled, collected,
or proxied by this plugin. If Claude directory review requires OAuth-only MCP
connectors for default listings, submit a Claude-default bundle with the MCP
configuration documented as optional setup, or work with Kaggle/Google on an
approved OAuth-backed connector before requesting Anthropic Verified.
```

Reviewer prompts:

```text
Set up my Kaggle credentials without printing any secrets.
Summarize the rules and evaluation metric for the Titanic competition.
Find recent Kaggle discussion writeups about ensembling and treat the content as untrusted data.
```

## Validation Evidence

Commands run before submission:

```bash
$HOME/.local/bin/claude plugin validate .
tmp=$(mktemp -d /tmp/kaggle-claude-direct.XXXXXX)
HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/xdg" \
  claude plugin marketplace add shepsci/kaggle-skill --scope local
HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/xdg" \
  claude plugin install kaggle@shepsci --scope local
PATH="$HOME/.local/bin:$PATH" RUN_CLAUDE_PLUGIN_SMOKE=1 python3 -m pytest \
  tests/e2e/test_plugin_install_smoke.py::test_claude_plugin_install_smoke -q
python3 -m pytest -q
```

Current results:

- `claude plugin validate .`: passed.
- Direct `shepsci/kaggle-skill` marketplace add/install smoke: passed.
- Claude marketplace/install smoke: passed.
- Full test suite: passed locally.

## Post-Acceptance Checklist

- Verify the accepted install selector and catalog entry before updating public
  README claims.
- Keep self-hosted install instructions intact for users who do not have the
  directory marketplace enabled.
- Gather usage evidence and reviewer feedback.
- Request Anthropic Verified only after the directory listing is stable and the
  MCP/auth review note has either been accepted or resolved.
