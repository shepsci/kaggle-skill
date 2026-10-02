# Distribution

Where `kaggle-skill` is published, what each place serves, and how a release
is made. Current version: 3.0.0.

The project is independent and unofficial. It is not affiliated with,
endorsed by, or sponsored by Kaggle or Google. It is not listed in OpenAI's
plugin directory, and its submission to Anthropic's is in review; it does
not claim to be listed in either.

## Where it is published

| Channel | Source | Install |
|---|---|---|
| This repository, as a Claude Code marketplace | `.claude-plugin/marketplace.json` | `/plugin marketplace add shepsci/kaggle-skill`, then `/plugin install kaggle@shepsci` |
| This repository, as a Codex marketplace | `.agents/plugins/marketplace.json`, `.codex-plugin/plugin.json` | `codex plugin marketplace add shepsci/kaggle-skill --ref main`, then `codex plugin add kaggle@shepsci` |
| skills.sh | Reads `skills/kaggle/` from this repository | `npx skills add shepsci/kaggle-skill` |
| ClawHub | Published by hand from a `git archive` of `skills/kaggle/` | `clawhub install kaggle` |
| Agent Plugins format | Root `plugin.json` | For hosts that read that format |

The plugin and the skill are both named `kaggle`; the selector is
`kaggle@shepsci`.

## Releasing

1. Raise the version in every manifest: `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`,
   `plugin.json`, `pyproject.toml`, and `metadata.version` in
   `skills/kaggle/SKILL.md`. Claude Code keeps serving its cached copy until
   the version string changes, so a change that ships under the old version
   never reaches installed users. `tools/check_release.py` fails when that
   would happen.
2. Add the entry to `CHANGELOG.md`.
3. Run the checks:

   ```bash
   python3 -m pytest -q
   ruff check . && ruff format --check .
   claude plugin validate .claude-plugin/plugin.json --strict
   claude plugin validate .claude-plugin/marketplace.json --strict
   agentskills validate skills/kaggle
   ```

   `claude plugin validate .` checks only `marketplace.json` when one exists.
   Validate `plugin.json` by its own path.
4. Run the read-only live tests with a credential. They are not run in CI:

   ```bash
   python3 -m pytest --run-live tests/integration -q
   ```

5. Merge, tag `v<version>`, and publish the GitHub release.
6. Publish to ClawHub, then read its scan. Publish from an export of the tag,
   never from a working checkout, so that an untracked file cannot be
   uploaded:

   ```bash
   git archive v<version> skills/kaggle | tar -x -C /tmp/kaggle-release
   clawhub skill publish /tmp/kaggle-release/skills/kaggle --slug kaggle --name "Kaggle" --version <version>
   ```

## The plugin-only build

The repository root is the plugin root, so an install from `main` also
carries the tests, the tools and the demo media. `tools/build_plugin.py`
writes the plugin alone, about 100 files:

```bash
python3 tools/build_plugin.py /tmp/kaggle-plugin
claude plugin validate /tmp/kaggle-plugin/.claude-plugin/plugin.json --strict
```

CI builds and validates it on every pull request. Publishing that folder as a
branch, and pointing the Claude directory's tracked branch at it, gives the
directory a smaller thing to scan without a new submission. The directory
does not allow the branch to change while a submission is in review, and a
different folder in the same branch would need a new submission, so this is a
step for after the review.

## ClawHub

ClawHub publishes every skill under MIT-0. The copy there is MIT-0; this
repository stays MIT through `LICENSE`. The frontmatter keeps ClawHub's
fields under `metadata.openclaw`, with `KAGGLE_API_TOKEN` as an optional
variable, because a token file or an OAuth login works as well.

Publishing is done by hand. It is not done from CI, which would need a stored
token.

## Claude directory

Submission goes through the developer portal at
https://claude.ai/directory/manage, from this GitHub repository. The older
Console form is retired.

Before submitting, run the portal's **Validate** step and read the
[pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist).
Points that matter for this plugin:

- **The name.** The portal can hold a name that matches a well-known brand.
  The plan is to keep `kaggle` unless the portal blocks or holds it. If it
  does, rename to `kaggle-skill` and add a `renames` entry to
  `.claude-plugin/marketplace.json`, so that existing `kaggle@shepsci`
  installs follow.
- **Credentials.** The bundled MCP entry holds a URL and a public OAuth
  client ID, and no credential. A plugin that reads a credential from the
  user's environment and sends it to a server is held for review; the
  supported way to store a token is a `userConfig` entry with
  `sensitive: true`.
- **The MCP server.** The plugin points at Kaggle's server, which this project
  does not run.
- **No symlinks** in the plugin folder.

There is no separate "verified" application. `claude-plugins-official` is for
partners.

## OpenAI directory

Not planned. OpenAI's guidelines exclude plugins that mainly connect to a
third party's service unofficially, and a plugin with an MCP server must show
control of the server's domain. Codex users install from this repository.

## Checks that run by themselves

- **Every pull request**: the offline tests on Python 3.11 to 3.14, `ruff`,
  the skill and plugin validators, the plugin-only build, and the version
  rule.
- **Weekly**: Kaggle's MCP tool list, the Kaggle packages on PyPI, the Kaggle
  CLI's command tree, and Kaggle's answer to an OAuth client registration are
  compared with the snapshots in `tests/fixtures/`. A difference opens an
  issue. To refresh a snapshot:

  ```bash
  python3 tools/mcp_snapshot.py --update
  python3 tools/cli_snapshot.py --update
  python3 tools/check_pins.py --update
  python3 tools/check_oauth_registration.py --update
  ```

  The last check matters for sign-in: `.mcp.json` names the client ID that
  Kaggle gives to Claude Code. If Kaggle changes how it answers, check the
  sign-in again before changing the entry.

None of these needs a secret.
