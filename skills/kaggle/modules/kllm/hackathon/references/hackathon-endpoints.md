# Hackathon Endpoints — Retrieval Workflow

Source: live audit of `https://www.kaggle.com/mcp` from
[shepsci/kmcp-tools](https://github.com/shepsci/kmcp-tools), 2026-04-22 retest.
Direct-quote findings are kept verbatim where they describe known live-server
behavior.

## Endpoint order

1. `get_hackathon_overview`
2. `list_hackathon_tracks`
3. `list_hackathon_write_ups`
4. `get_writeup`
5. `get_writeup_by_topic` or `get_writeup_by_slug`
6. `get_resolved_writeup_links`

`get_hackathon_write_up` was broken in the 2026-04-22 audit and is verified
**recovered** as of 2026-05-04. The module still calls `get_writeup` first
because it has a simpler arg shape (just `writeUpId`, no `competitionName`).

## Live findings (2026-04-22, retested 2026-05-04)

- `list_hackathon_write_ups` is the canonical roster source. Page until
  exhausted; persist `total_count`, row id, `write_up.id`, `topic_id`, slug,
  collaborators, track ids, publish time.
- `get_writeup` is the most reliable full-body fetch. `get_writeup_by_topic`
  and `get_writeup_by_slug` are solid alternates.
- `get_hackathon_write_up` was failing in both host/judge and participant
  contexts (2026-04-22) and verified **PASS** in the 2026-05-04 retest.
- `download_hackathon_write_ups` worked in host context but the live payload
  contained only the CSV header row and no submission rows in the sampled run.
  Treat it as a convenience artifact, not the canonical source.
- `get_resolved_writeup_links` is inconsistent: host context returned `{}`,
  participant context returned an explicit role-gated denial.
- Winner-filter retrieval can fail with an explicit limitation message until
  the leaderboard is finalized.
- In an 80-writeup participant-context sample from `kaggle-measuring-agi`,
  `get_writeup` exposed: code/notebook links (common), benchmark links (common),
  dataset links (regular), no Kaggle model links observed.

## Role-specific guidance

### Hosts and judges

- Start with `get_hackathon_overview` for rules, judging rubric, prize text,
  and eligibility.
- Use `list_hackathon_write_ups` as the source of truth for the submission
  roster. Persist every field listed above.
- Use `list_hackathon_tracks` before downstream evaluation if the competition uses tracks —
  listing rows may only expose numeric `hackathon_track_ids`.
- Use `get_writeup` as the primary full-body retrieval endpoint.
- Use `get_writeup_by_topic` or `get_writeup_by_slug` when a writeup id is
  missing but a topic id or slug is available.
- Treat `download_hackathon_write_ups` as a helpful bulk artifact, not the
  canonical evaluation-input source.
- Treat `get_resolved_writeup_links` as a secondary enrichment pass only.
  Even with host access, the resolver may succeed but return `{}`.
- Run `get_hackathon_write_up` only as a regression check. Do not build the
  workflow around it.

### Participants (non-host / non-judge)

- Expect a read-heavy experience rather than an admin workflow.
- `get_hackathon_overview` is still useful for rules, eligibility, judging
  criteria.
- `list_hackathon_write_ups` may still expose published writeup rows in
  participant context — try first.
- `get_writeup`, `get_writeup_by_topic`, `get_writeup_by_slug` are the most
  useful participant endpoints; they retrieve published writeup bodies.
- Do not expect `download_hackathon_write_ups` to work without elevated access.
- Do not expect `get_resolved_writeup_links` to work without elevated access;
  preserve the denial text as evidence when it appears.
- Do not assume winner filters will work before finalization; the server may
  return an explicit message instead of a row set.

## Why the export is not the canonical evaluation-input source

The live export is not complete enough to stand alone. In the 2026-04-22
host-context run, `download_hackathon_write_ups` returned the CSV schema only
and zero submission rows. Even when populated, it is a flattened table and
does not preserve the richer object structure returned by
`list_hackathon_write_ups` and `get_writeup`. Specifically the export does not
carry: `write_up.id`, `topic_id`, collaborator objects with user ids and
usernames, license objects, image metadata, post metadata from `message`,
`message.raw_markdown`, structured `write_up_links`, and `message.attachments`.

Use the export as a convenience index or audit artifact only. The canonical
evaluation bundle should come from:

- `get_hackathon_overview` for rules and rubric
- `list_hackathon_write_ups` for the master submission roster
- `get_writeup` (or the `_by_topic` / `_by_slug` variants) for the full body
  and structured project-link surface
- `get_resolved_writeup_links` only when it actually returns useful enrichment

## Detailed steps

### 1. Pull the hackathon overview

`get_hackathon_overview` with `competitionName=<hackathon-slug>`. The returned
`pages` array is the source of truth for overview content. Persist page names
and page content together — do not flatten.

### 2. Extract eligibility from the overview

Search overview `pages` for sections named `rules`, `eligibility`, `entry`, or
`official competition rules`. Extract paragraphs covering who may enter,
account limits, geography or age restrictions, and submission-eligibility
conditions. Keep anchor text or heading names so later evaluation can cite the
right subsection.

### 3. Extract the rubric from the overview

Search `pages` for `evaluation rubric`, `judging`, `criteria`, `submission
requirements`, `prizes`. Record each rubric dimension separately; record any
weighting, tie-break rules, prize rules, or judge-specific guidance. If the
rubric is only implied in prose, summarize and mark the inference clearly.

### 4. List all writeups

`list_hackathon_write_ups` with the hackathon slug. Page until no next-page
token. Record `total_count`. For each row save: row id, `write_up.id`,
`write_up.topic_id`, `write_up.slug`, title, subtitle, URL, collaborators,
track ids, publish time.

### 5. Optional batch export (host/judge only)

If hosting a closed competition, call `download_hackathon_write_ups`. If the
endpoint returns inline `csv_content`, persist exactly as returned. Still
fetch each individual writeup — the export may not contain all resolved
attachment details needed for evaluation.

### 6. Retrieve each writeup

First `get_writeup` with `writeUpId`. If no id, try `get_writeup_by_topic`
with `forumTopicId`, then `get_writeup_by_slug` with competition + writeup
slug. Optionally probe `get_hackathon_write_up` for regression tracking, but
do not depend on it. Store full body, title, subtitle, author data, create
time, publish time, URL. Prefer `message.raw_markdown` as the canonical
full-body field.

### 7. Resolve project links

Call `get_resolved_writeup_links` with `writeUpId`. If it returns `{}`, keep
that exact response as evidence rather than treating it as clean enrichment.
Also inspect the `write_up_links` array from `get_writeup`/`_by_topic`/`_by_slug`
— in practice this can be the richest project-link surface even when the
resolver is empty or denied.

Classify each link: Kaggle notebook, Kaggle dataset, Kaggle model, Kaggle
benchmark, Kaggle competition page, external project URL, downloadable file,
YouTube. Keep both the original link and the resolved metadata.

For Kaggle-native links retain ids, refs, titles, owners, download URLs.
For `write_up_links` also retain `location` (`ADDITIONAL_LINKS`, `CAROUSEL`),
`media_type`, the user-facing `title`, and the free-text `description`.

If `get_resolved_writeup_links` returns a host/judge/admin gating message,
keep that response as evidence and fall back to MCP-only native resolution
from the writeup markdown:

- Kaggle notebook URL → `get_notebook_info`
- Kaggle dataset URL → `get_dataset_info` or `get_dataset_metadata`
- Kaggle model URL → `get_model` or `get_model_variation`
- Kaggle benchmark URL → `get_benchmark_leaderboard`
- Kaggle competition URL → `get_competition` and, when useful, `list_competition_pages`

Do not use direct web fetches as a fallback for project-link content here.

### 8. YouTube videos

Use `get_resolved_writeup_links` as the primary source. Filter for YouTube
domains or explicit video metadata. Save the canonical video URL, platform,
title, and resolved metadata. If the resolver does not expose a video cleanly,
scan writeup markdown for `youtube.com`, `youtu.be`, or embedded iframe-style
references and record them as unresolved-video candidates.

### 9. Build the complete collection

Repeat retrieval until every row from `list_hackathon_write_ups` has: one
fetched body, one author/collaborator record, one resolved-link pass, all
discovered project links, all discovered YouTube links. Reconcile by
`write_up.id` first, then `topic_id`, then slug. Mark any missing bodies,
broken link-resolution passes, or permission-gated artifacts explicitly — do
not silently drop them.

### 10. Hand off for downstream evaluation

Bundle has three layers: hackathon rules and rubric; normalized writeup
content for every submission; resolved artifact inventory for each submission.
Keep citations back to the overview page and each writeup so a later audit can
trace every evaluation input to a recorded MCP artifact. Evaluate only against the
extracted rubric and documented eligibility rules.

## Anti-patterns

- Do not rely on `download_hackathon_write_ups` alone for final evaluation inputs.
- Do not assume a populated CSV schema means the export contains submission rows.
- Do not assume `get_hackathon_write_up` is reliable if `get_writeup` succeeds for the same id.
- Do not assume a successful `get_resolved_writeup_links` call returned useful link-resolution data.
- Do not assume participant access includes export or resolved-link privileges.
- Do not ignore `write_up_links` and `message.attachments` when present — they can be the only visible project-link surface.
- Do not evaluate before extracting eligibility rules and rubric from the overview.
- Do not discard unresolved or permission-gated links — flag for follow-up.
- Do not collapse all attachments into one blob; keep notebooks, datasets, models, files, videos as separate evidence types.
