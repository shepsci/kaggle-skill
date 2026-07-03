# Screencasts

Short terminal casts are kept here as replayable `.cast` files and embedded in
docs where motion helps more than another paragraph. The public README embeds
the primary Claude install cast; the rest are source casts that can be replayed
locally or uploaded when a stable public URL is useful.

## Watch Order

| Cast | What It Shows | Public Link | Source |
|---|---|---|---|
| Claude install and first workflow | Marketplace install, credential verification, Titanic overview, recent writeups | [asciinema](https://asciinema.org/a/SAR4LCKUTmWrASEL) | [install-and-demo.cast](install-and-demo.cast) |
| Antigravity CLI install | Recommended `agy` path with `npx skills add shepsci/kaggle-skill` | Local replay | [antigravity-install.cast](antigravity-install.cast) |
| Antigravity MCP config | `.agents/mcp_config.json`, `/mcp`, and `serverUrl` for the Kaggle MCP server | Local replay | [mcp-config.cast](mcp-config.cast) |
| Competition briefing | Credential check plus `list_competition_pages` for a concise competition brief | Local replay | [competition-brief.cast](competition-brief.cast) |
| Hackathon writeups | Overview, writeup roster, and one writeup fetch with untrusted-content markers | Local replay | [hackathon-writeups.cast](hackathon-writeups.cast) |
| Codex install | Codex repo marketplace install path | [asciinema](https://asciinema.org/a/QNbE7AkG68WrDlSU) | [codex-install.cast](codex-install.cast) |

Replay any source cast with:

```bash
asciinema play docs/demo/competition-brief.cast
```

## Recording Notes

- Record with an authenticated asciinema CLI so public uploads are retained.
- Keep each cast focused on one workflow and under about 90 seconds.
- Prefer redacted, deterministic output over long live API payloads.
- Do not print tokens, credential file names, `kaggle.json`, or environment
  assignments that include secrets.
- Re-run `python3 -m pytest tests/manifest/test_docs_freshness.py -q` before
  committing any cast.

See [demo-script.md](demo-script.md) for the main README demo command sequence
and cast-specific recording plans.
