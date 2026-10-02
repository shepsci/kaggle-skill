# Demos

Short demos of the skill at work. Each has a `.cast` file (asciinema) and a
GIF in `media/`, because GitHub cannot play casts inline.

There are two kinds, and each says which it is:

- **A recorded agent session** is kept as a JSON file in `sessions/`: the
  question a person asked, the commands the agent ran with what they printed,
  and the agent's answer. Rebuilding it runs nothing.
- **A command demo** runs the skill's commands when it is built and keeps
  their output. It shows what an agent runs and what comes back; no agent
  takes part.

In both, colour codes are removed, long output is cut with a line that says
how much was left out, and temporary folder paths are shortened. Nothing else
is edited. The command demos run with no Kaggle credential, so they show what
anyone gets and nothing about an account.

The screen is 48 columns wide. GitHub shrinks an image to a phone's width,
and at 48 columns the type is still about 11 pixels tall.

## A competition on one screen

Command demo.

![A competition on one screen](media/competition-brief.gif)

Source: [competition-brief.cast](competition-brief.cast)

## Solution writeups of the top teams

Command demo.

![Solution writeups of the top teams](media/vesuvius-top-writeups.gif)

Source: [vesuvius-top-writeups.cast](vesuvius-top-writeups.cast)

## Claude Code install and first command

Command demo.

![Claude Code install and first command](media/install-and-demo.gif)

Source: [install-and-demo.cast](install-and-demo.cast)

## Codex install

Command demo.

![Codex install](media/codex-install.gif)

Source: [codex-install.cast](codex-install.cast)

## Replay

```bash
asciinema play docs/demo/competition-brief.cast
```

## Rebuild

```bash
python3 tools/build_casts.py
python3 tools/build_casts.py competition-brief
python3 tools/build_casts.py --gif-only
python3 tools/build_casts.py --readme
```

The builder needs Pillow, and `claude` and `codex` on the PATH for the two
install demos; a demo whose program is missing is skipped. Plugin installs
run in throwaway config folders, from the local checkout, so the demos can be
rebuilt before a release is on GitHub. `--readme` also refreshes the demo
blocks in the repository's README. See [demo-script.md](demo-script.md) for
what each demo runs and how a session is recorded.

After a rebuild, run `python3 -m pytest tests/manifest -q`. The tests check
that no cast contains a credential, a control sequence, or stale paths, and
that each cast is short.
