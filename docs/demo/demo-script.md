# What the demos run

The demos in this folder are built by `tools/build_casts.py`, version 3.0.0
of the skill. Rebuild them after a change to a command or to what it prints.

Everything here reads. Nothing is submitted or published, and no credential
is printed: the demos avoid `doctor` and `credentials`, because their output
names credential files.

Commands are shown as an agent runs them, from the skill folder
(`skills/kaggle/` in this repository).

## competition-brief

```bash
python3 scripts/kaggle_skill.py brief titanic
python3 scripts/kaggle_skill.py pages titanic --page evaluation --max-chars 300
```

No credential is used.

## vesuvius-top-writeups

```bash
python3 scripts/kaggle_skill.py solutions vesuvius-challenge-surface-detection --top 3 --preview
```

No credential is used.

## install-and-demo

```bash
claude plugin marketplace add shepsci/kaggle-skill
claude plugin install kaggle@shepsci
python3 scripts/kaggle_skill.py brief titanic
```

In a session the first two are `/plugin marketplace add shepsci/kaggle-skill`
and `/plugin install kaggle@shepsci`. The builder installs from the local
checkout, in a throwaway config folder, so the first line in the cast reads
`claude plugin marketplace add ./kaggle-skill`.

## codex-install

```bash
codex plugin marketplace add shepsci/kaggle-skill --ref main --json
codex plugin add kaggle@shepsci --json
```

Built from the local checkout in a throwaway `CODEX_HOME`.

## Recorded agent sessions

A session demo is a file in `sessions/`:

```json
{
  "name": "agent-brief",
  "title": "kaggle-skill - an agent answers a question",
  "recorded": "2026-10-02",
  "agent": "Claude Code (Claude Opus 5.5)",
  "agent_short": "Claude",
  "question": "the question, as the person typed it",
  "steps": [
    {"command": "python3 scripts/kaggle_skill.py brief titanic", "output": "what it printed", "show_lines": 10}
  ],
  "answer": "the agent's answer, as it gave it"
}
```

To record one:

```bash
python3 tools/record_session.py agent-brief "the question, as a person would type it"
python3 tools/build_casts.py agent-brief --readme
```

`record_session.py` starts a real Claude Code session (`claude -p`) with this
checkout loaded as the plugin, lets the agent run the skill's commands, and
writes the question, each command with its full output, and the agent's
answer into the file without rewording them. Only the skill's folder and the
working folder are shortened in the paths. The session runs on your Claude
Code subscription; the tool refuses to start when an API key is set or the
sign-in is not a subscription. It runs with `KAGGLE_SKILL_READ_ONLY=1`, so
nothing can be written to Kaggle, and with Kaggle's MCP servers switched off,
so the agent uses the skill's commands.

`show_lines` only limits how many lines of a command's output the GIF shows;
the file keeps all of it. Use a question about public content, and read the
file before committing it: the output can hold details of your account.

## Before committing a demo

```bash
python3 -m pytest tests/manifest/test_docs_freshness.py tests/manifest/test_demo_gifs_animated.py -q
```
