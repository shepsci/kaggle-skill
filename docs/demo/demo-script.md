# What the demos run

The demos in this folder are built by `tools/build_casts.py`, version 3.1.0
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
  "title": "kaggle-skill - ask about a competition",
  "recorded": "2026-10-02",
  "agent": "Claude Code 2.1.286 (claude-opus-5-5)",
  "agent_short": "Claude",
  "question": "the question, as the person typed it",
  "steps": [
    {"command": "the command as the agent ran it", "output": "the start of what it printed", "show_lines": 12}
  ],
  "answer": "the agent's answer, as it gave it",
  "answer_show_lines": 24
}
```

The three in this folder were recorded with these questions:

| File | Question | Run in |
|---|---|---|
| `agent-brief` | What's the deadline and the metric of kaggle.com/competitions/arc-prize-2026-arc-agi-3? | An empty folder |
| `agent-submit` | Submit ./submission.csv to the Titanic competition on Kaggle. | A folder with `submission.csv` and `downloads/titanic/gender_submission.csv` |
| `agent-solutions` | What did the top three teams of Kaggle's ARC Prize 2025 do? A few lines each. | An empty folder |

To record one:

```bash
python3 tools/record_session.py agent-brief "the question, as a person would type it"
python3 tools/record_session.py agent-submit "Submit ./submission.csv ..." --workdir ~/demo --show-lines 24
python3 tools/build_casts.py agent-brief agent-submit --readme
```

`record_session.py` starts a real Claude Code session (`claude -p`) with this
checkout loaded as the plugin, lets the agent run the skill's commands, and
writes the question, each command, and the agent's answer into the file
without rewording them. The session:

- runs on your Claude Code subscription. The tool refuses to start when an
  API key is set or the sign-in is not a subscription;
- cannot write to Kaggle: `KAGGLE_SKILL_READ_ONLY=1` is set, and the skill's
  commands see no Kaggle credential, because they run with an empty home
  folder. `--with-credential` keeps yours; read the file before committing
  it then, because the output can hold details of your account;
- has Kaggle's MCP servers switched off, so the agent uses the skill's
  commands.

Only the lines a demo shows are kept from each command's output, with a count
of the rest: ten by default (`--show-lines`), and six for `writeup`, `topic`,
`pages` and `hackathon`, whose output is someone's text. The skill's folder,
the working folder and the session's scratch folder are shortened in the
paths. `--answer-lines N` makes the GIF show the first N lines of a long
answer; the file keeps the whole answer. `--stream PATH` also saves the
whole event stream, for looking into a run, and `--from-stream PATH` builds
the session file from it again without starting a session; keep that file
out of the repository.

## Before committing a demo

```bash
python3 -m pytest tests/manifest/test_docs_freshness.py tests/manifest/test_demo_gifs_animated.py -q
```
