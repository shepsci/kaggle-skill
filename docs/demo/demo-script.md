# Demo Script for the README Screencast

The asciinema cast in the README is recorded from a real Claude Code session
running through the steps below. Re-record after material UX changes.

## Goal of the demo (≤90 seconds)

Show, in this order:

1. Install kaggle-skill from the marketplace (one command).
2. Ask Claude to set up Kaggle credentials.
3. Ask Claude to summarize a competition's overview pages.
4. Ask Claude to pull every writeup from a hackathon.

Total runtime target: 60-90s. Anything longer loses viewers.

## Setup before recording

```bash
# Fresh Claude Code session, no previous kaggle plugin installed.
# Have your KGAT token ready in clipboard if you need to paste it.
# Make sure terminal is at least 100 cols × 30 rows for legibility.
asciinema --version  # confirm asciinema is installed
```

## Recording commands (paste-able)

```bash
# 1. Open Claude Code, then:
/plugin marketplace add shepsci/claude-marketplace
# (wait ~2s for confirmation)

/plugin install kaggle-skill@shepsci
# (wait ~3s for install confirmation)

# 2. Ask in plain English:
> "set up my Kaggle credentials"
# Claude walks through token generation and verifies
# Pause ~5s on the success message

# 3. Competition overview demo:
> "summarize the rules and evaluation metric for the titanic competition"
# Claude calls list_competition_pages, reads rules + evaluation pages,
# and gives a concise summary
# Pause ~8s on the summary output

# 4. Hackathon demo:
> "pull every writeup from kaggle-measuring-agi and group by track"
# Claude calls list_hackathon_tracks + list_hackathon_write_ups,
# resolves track ids, prints grouped counts
# Pause ~5s on the output
```

## Recording with asciinema

```bash
cd ~/work/kaggle-skill
asciinema rec docs/demo/install-and-demo.cast \
  --title "kaggle-skill v2.1.0 — install + demo" \
  --idle-time-limit 1.5 \
  --rows 30 --cols 100
# Run the demo, then Ctrl+D to finish
asciinema upload docs/demo/install-and-demo.cast
# Note the resulting URL — it goes in the README badge below.
```

## Recording with vhs (alternative — produces GIF/MP4 directly)

vhs is sometimes easier than asciinema for embedding in GitHub READMEs since
GitHub renders MP4/GIF natively. Use the [demo.tape](demo.tape) file:

```bash
cd ~/work/kaggle-skill/docs/demo
vhs demo.tape
# Outputs install-and-demo.gif in this directory
```

## Updating the README embed

The README currently references `https://asciinema.org/a/PLACEHOLDER`. After
upload, replace `PLACEHOLDER` with the cast id (e.g., `123456`) in:

- `README.md` — the asciicast badge link near the top
