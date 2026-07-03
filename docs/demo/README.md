# Screencasts

Short terminal casts are kept here as replayable `.cast` files. They are clean
source recordings with deterministic output, no terminal control sequences, and
human-readable pacing. Upload a fresh public copy only after replaying the
committed source locally and confirming it still looks correct.

## Watch Order

| Cast | What It Shows | Source |
|---|---|---|
| Claude install and first workflow | Marketplace install, credential verification, Titanic overview, recent writeups | [install-and-demo.cast](install-and-demo.cast) |
| Antigravity CLI install | Recommended `agy` path with `npx skills add shepsci/kaggle-skill` | [antigravity-install.cast](antigravity-install.cast) |
| Antigravity MCP config | `.agents/mcp_config.json`, `/mcp`, and `serverUrl` for the Kaggle MCP server | [mcp-config.cast](mcp-config.cast) |
| Competition briefing | Credential check plus `list_competition_pages` for a concise competition brief | [competition-brief.cast](competition-brief.cast) |
| Hackathon writeups | Overview, writeup roster, and one writeup fetch with untrusted-content markers | [hackathon-writeups.cast](hackathon-writeups.cast) |
| Codex install | Codex repo marketplace install path | [codex-install.cast](codex-install.cast) |

Replay any source cast with:

```bash
asciinema play docs/demo/competition-brief.cast
```

## Recording Notes

- Record with an authenticated asciinema CLI so public uploads are retained.
- Keep each cast focused on one workflow and under about 90 seconds.
- Re-record or hand-clean any cast that includes terminal escape/control
  sequences from progress spinners, cursor movement, or alternate screens.
- Prefer redacted, deterministic output over long live API payloads.
- Do not print tokens, credential file names, `kaggle.json`, or environment
  assignments that include secrets.
- Re-run `python3 -m pytest tests/manifest/test_docs_freshness.py -q` before
  committing any cast.

See [demo-script.md](demo-script.md) for the main README demo command sequence
and cast-specific recording plans.
