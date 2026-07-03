# Claude Community Marketplace Submission Package

Status: ready for maintainer submission after the release PR merges.

Official Claude docs used:

- Create plugins: https://code.claude.com/docs/en/plugins
- Plugin marketplaces: https://code.claude.com/docs/en/plugin-marketplaces
- Official/community directory: https://github.com/anthropics/claude-plugins-official

Claude Code documents two public marketplaces:

- `claude-community`: third-party submissions reviewed through the Claude
  submission forms.
- `claude-plugins-official`: a separately curated Anthropic marketplace. The
  docs say there is no application process for official curated inclusion.

This repository does not claim official Anthropic listing. Submit the community
package through one of the documented forms:

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
- Third-party notices: `THIRD_PARTY_NOTICES.md`

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

For Claude community submission metadata, use an HTTPS git URL source:

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
Kaggle-supplied text in untrusted-content markers.
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
