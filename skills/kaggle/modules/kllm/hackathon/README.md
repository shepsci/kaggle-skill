# Hackathon Module

Retrieve hackathon overview pages, enumerate writeup submissions, and fetch
full writeup bodies from Kaggle's MCP hackathon endpoints. Built around the
documented endpoint behavior from the [shepsci/kmcp-tools](https://github.com/shepsci/kmcp-tools)
2026-04-22 audit (which sweeps the live `https://www.kaggle.com/mcp` server
and records exactly which tools work, which fail, and which are role-gated).

## When to use

Reach for this module when:

- The user asks about a Kaggle hackathon, AGI/cognitive evaluation, or writeup
  collection (e.g., `kaggle-measuring-agi`, `meta-kaggle-hackathon`).
- You need rules / eligibility / rubric extracted from the hackathon overview.
- You need a complete roster of submissions for downstream evaluation or analysis.
- You need full writeup bodies with project links resolved.

## Prerequisites

- `KAGGLE_API_TOKEN` in environment, or a token at `~/.kaggle/access_token`.
  KGAT-prefixed tokens are required for many hackathon endpoints.
- The competition slug (e.g., `kaggle-measuring-agi`).
- Host or judge access if you need `download_hackathon_write_ups` or
  `get_resolved_writeup_links`. Both endpoints are role-gated.

Run the credential checker first if anything is unset:

```bash
python3 ../../shared/check_all_credentials.py
```

## Endpoint order

This is the working endpoint sequence — see
[references/hackathon-endpoints.md](references/hackathon-endpoints.md) for the
full taxonomy of which endpoints succeed, which fail, and why.

1. `get_hackathon_overview` — rules, eligibility, rubric, prizes
2. `list_hackathon_tracks` — resolve numeric track ids → titles
3. `list_hackathon_write_ups` — paginated submission roster
4. `get_writeup` — full body for each submission (preferred path)
5. `get_writeup_by_topic` / `get_writeup_by_slug` — fallbacks when id missing
6. `get_resolved_writeup_links` — host-only enrichment pass

`get_hackathon_write_up` was broken in the 2026-04-22 audit (generic
invocation error in both host and participant contexts) and verified
**recovered** in the 2026-05-04 retest. `fetch_writeup.py` still uses
`get_writeup` first because it has a simpler arg shape (just `writeUpId`,
no `competitionName` required) — but the wrapper endpoint is now also viable
if you have both args.

## Scripts

```bash
# Step 1 — pull rules, rubric, eligibility
python3 scripts/hackathon_overview.py --competition kaggle-measuring-agi

# Step 2 — enumerate submissions
python3 scripts/list_writeups.py --competition kaggle-measuring-agi

# Step 3 — fetch full body for one submission (id from step 2)
python3 scripts/fetch_writeup.py --writeup-id 123456
python3 scripts/fetch_writeup.py --topic-id 789012      # fallback
python3 scripts/fetch_writeup.py --competition kaggle-measuring-agi --slug my-team-writeup
```

All three scripts share the same auth resolution (env → `~/.kaggle/access_token`
→ `~/.kaggle/kaggle.json`) via `skills/kaggle/shared/mcp_client.py`.

## Role-aware behavior

Hosts and judges see more than participants. Each script preserves
permission-denial responses verbatim as evidence rather than silently dropping
them — see the role-specific guidance in
[references/hackathon-endpoints.md](references/hackathon-endpoints.md).

## Related references

- [hackathon-endpoints.md](references/hackathon-endpoints.md) — full retrieval
  workflow, role guidance, anti-patterns
- [benchmark-endpoints.md](references/benchmark-endpoints.md) — `create_benchmark_task_from_prompt`,
  `get_benchmark_leaderboard`
- [episode-endpoints.md](references/episode-endpoints.md) — agent simulation
  episodes (logs, replays, submission listing)
