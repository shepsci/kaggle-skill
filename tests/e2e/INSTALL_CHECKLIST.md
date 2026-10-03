# Install Checklist

Run this once per release. The automated parts are in
`tests/e2e/test_plugin_install_smoke.py`; everything that needs a real agent
session, a browser, or a Kaggle sign-in is here.

Version under test: `3.1.0`.

## Automated, in throwaway config folders

```bash
RUN_CLAUDE_PLUGIN_SMOKE=1 python3 -m pytest tests/e2e -q -k claude
RUN_CODEX_PLUGIN_SMOKE=1 python3 -m pytest tests/e2e -q -k codex
```

- [ ] Claude Code: `claude plugin validate` passes with `--strict` on
      `.claude-plugin/plugin.json` and on `.claude-plugin/marketplace.json`,
      and `kaggle@shepsci` installs from this checkout.
- [ ] Codex: the marketplace is added and `kaggle@shepsci` installs.

## Claude Code, in a real session

- [ ] `/plugin marketplace add shepsci/kaggle-skill` succeeds.
- [ ] `/plugin install kaggle@shepsci` succeeds, and the Installed tab shows
      `kaggle` at version `3.1.0`.
- [ ] `/mcp` lists the `plugin:kaggle:kaggle` server as connected. Before
      signing in, a public tool works: ask for the rules of the titanic
      competition.
- [ ] `claude mcp login plugin:kaggle:kaggle` completes, and afterwards
      `get_accelerator_quota` answers. If you have a `kaggle` entry of your
      own for the same URL, Claude Code shows it in place of the plugin's;
      sign in to that one.
- [ ] Ask: "what is the metric and deadline of the Kaggle titanic
      competition". The agent asks before running a command, runs
      `kaggle_skill.py brief titanic`, and the answer names its source.
- [ ] Ask: "what did the top teams of the Vesuvius surface detection
      competition do". No credential is shown, and the agent treats the text
      as data.
- [ ] Ask: "check my Kaggle setup". The agent runs `doctor` and reports what
      works now, without printing a credential.
- [ ] Ask it to submit a file to a competition. The agent shows the dry run
      and asks before it adds `--yes`.
- [ ] Loading the skill does not grant Bash: the first command run prompts
      for permission.

## Other distributions

- [ ] `npx skills add shepsci/kaggle-skill` in a temporary folder.
- [ ] `clawhub install kaggle`, after the ClawHub release.
- [ ] `codex plugin marketplace add shepsci/kaggle-skill --ref main`, then
      `codex plugin add kaggle@shepsci`, in a temporary `CODEX_HOME`.
- [ ] Codex: `codex mcp login kaggle` completes.

## Platforms marked "Tested" in docs/compatibility.md

A platform is marked "Tested" only when its line here was run on this
release. `tests/manifest/test_no_false_claims.py` checks that every such
platform has a line.

- Claude Code: the automated install above, on Claude Code 2.1.288.
- Codex: the automated install above, on Codex 0.160.0.

Not re-run on this release, and marked accordingly in docs/compatibility.md:
Antigravity CLI (`agy`), OpenClaw, and Gemini CLI.

## Clean up

- [ ] `/plugin uninstall kaggle@shepsci` removes the plugin.

If a step fails, open an issue with the step, the output with credentials
removed, and the agent's version.
