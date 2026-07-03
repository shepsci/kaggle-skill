# Screencasts

Short terminal casts are kept here as replayable `.cast` files and embedded in
docs where they help more than another paragraph.

## Available Casts

| Cast | Public Link | Source |
|---|---|---|
| Claude install and first workflow | [asciinema](https://asciinema.org/a/SAR4LCKUTmWrASEL) | [install-and-demo.cast](install-and-demo.cast) |
| Codex install | [asciinema](https://asciinema.org/a/QNbE7AkG68WrDlSU) | [codex-install.cast](codex-install.cast) |

## Recording Notes

- Record with an authenticated asciinema CLI so public uploads are retained.
- Keep commands short and deterministic.
- Do not print tokens, credential file names, `kaggle.json`, or environment
  assignments that include secrets.
- Re-run `python3 -m pytest tests/manifest/test_docs_freshness.py -q` before
  committing any cast.

See [demo-script.md](demo-script.md) for the main README demo command sequence.
