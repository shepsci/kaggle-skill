# How the Skill Is Built

## Layout

```
skills/kaggle/
  SKILL.md                 what the agent reads first: the commands and the rules
  scripts/kaggle_skill.py  the one entry point; runs a command by name
  modules/<area>/          a README, references, and the scripts of one area
  shared/                  the code every script uses
```

| Module | Purpose |
|---|---|
| `setup` | What is installed, signed in and reachable |
| `competitions` | Research, status, data, submissions, scores, hackathons |
| `datasets` | Dataset download and publishing |
| `models` | Model download and publishing |
| `notebooks` | Notebook push, run, wait, output |
| `discussions` | Forums, topics, solution writeups |
| `benchmarks` | Benchmark task commands |
| `badges` | Badge inventory, dry run, phases |
| `references` | Kaggle CLI, MCP server, and platform references |

`shared/` holds the MCP client and the HTTPS helper (standard library only),
the credential resolver, the Kaggle CLI runner, the printer for untrusted
content, the argument and exit-code helpers, the submission ledger, the upload
check for credential files, and the safe zip extractor.

The repository carries a manifest for each plugin system: `.claude-plugin/`
(Claude Code), `.codex-plugin/` and `.agents/plugins/` (Codex), and a root
`plugin.json` in the Agent Plugins format. `tools/build_plugin.py` writes the
plugin alone, about 100 files, for a plugin-only branch.

## How a command reads Kaggle

| Kind of command | Reads through | Needs |
|---|---|---|
| Public reads: `brief`, `pages`, `solutions`, `writeup`, `topics`, `topic`, `hackathon` | Kaggle's MCP server and web pages, over HTTPS | Python only |
| Reads on the account: `status`, `leaderboard`, `competitions`, `details`, `watch`, `episodes`, `writeups` | Kaggle's MCP server, with a bearer token | An API token or an OAuth login |
| `download`, `submit`, notebooks, `--via cli` | The Kaggle CLI | The `kaggle` package and a credential |
| `dataset-download`, `model-download`, publishing by default | `kagglehub` | The `kagglehub` package; an API token or a legacy key to publish (kagglehub does not use an OAuth login) |

## What the tests hold it to

| Property | Test |
|---|---|
| Text from Kaggle is printed inside a block with a random tag that the text cannot close, and invisible characters are removed or escaped | `tests/security/test_untrusted_content_wrappers.py`, `tests/unit/test_untrusted.py`, and the unit tests of each script |
| Credentials are never printed, never put on a command line, and never sent to a host other than Kaggle; a redirect is never followed with a token | `tests/security/test_no_credential_leakage.py`, `tests/unit/test_net.py` |
| The bundled MCP entries carry no credential | `tests/manifest/test_mcp_json_valid.py` |
| No `eval`, `exec`, shell interpretation, or inline `python -c` | `tests/security/test_no_dynamic_eval.py` |
| Archives and notebook output cannot write outside their folder | `tests/security/test_zip_slip_protection.py`, `tests/unit/test_notebook_scripts.py` |
| Upload folders are checked for credential files and for links that lead outside them; a notebook's code file must be inside its folder | `tests/unit/test_preflight.py`, `tests/unit/test_data_scripts.py`, `tests/unit/test_notebook_scripts.py` |
| Every command that changes the account is a dry run until `--yes`, badge phases included, and the read-only switch refuses it. The `cli` runner lets through only commands it knows to read | `tests/unit/test_script.py`, `tests/unit/test_dispatcher.py`, `tests/unit/test_kaggle_cli.py` |
| Local records are never written through a link | `tests/unit/test_competition_ops.py` |
| `--help` calls nothing and writes nothing | `tests/integration/test_scripts_help.py` |
| Slugs and handles are validated before use | `tests/unit/test_script.py`, `tests/unit/test_data_scripts.py` |
| The skill pre-approves only read tools (`Read`, `Grep`, `Glob`) | `tests/manifest/test_skill_md_frontmatter.py` |

What it does not do: it does not sandbox the agent, and it does not limit
which hosts the agent can reach. Marking text as untrusted lowers the risk
from instructions hidden in Kaggle content; it does not remove it. Review what
an agent proposes before it submits, publishes, or runs a badge phase.
