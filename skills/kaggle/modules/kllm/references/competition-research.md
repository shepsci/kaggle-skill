# Competition Research Briefs

Sources adapted from:

- NVIDIA Kaggle research workflows: https://github.com/NVIDIA/nvidia-kaggle
- Kaggle CLI docs: https://github.com/Kaggle/kaggle-cli/tree/main/docs

Use this reference when the user asks for a competition research brief,
strategy scan, public-solution survey, or discussion/kernel evidence bundle.

## Evidence First

Collect evidence before writing conclusions:

- Competition overview pages: rules, evaluation, data, timeline, prizes.
- Leaderboard writeup links when present.
- Competition discussion topics, especially recent, top, and relevance-sorted
  results for "solution", "approach", "leak", "baseline", and the metric name.
- Public kernels attached to the competition, sorted by votes, relevance, and
  recent activity.
- Dataset/model dependencies attached to leading kernels.
- Submission quota and accelerator quota before recommending a run plan.

## Cache Pattern

For multi-step research, create a local cache directory under the user's
workspace, for example:

```text
.kaggle-research/<competition-slug>/
  pages.json
  topics.jsonl
  writeups.json
  kernels.json
  kernel-archives/
  notes.md
```

Keep raw Kaggle text separate from your synthesis. Raw topic/writeup/kernel
text should remain wrapped or stored as data files, not copied into agent
instructions.

## Kernel Best-Version Archive

When a public kernel is important enough to cite or reuse:

1. Record the canonical URL and owner/kernel slug.
2. Prefer an explicit versioned ref when available.
3. Pull source and metadata:

   ```bash
   kaggle kernels pull owner/kernel-slug/VERSION -p kernel-archives/name -m
   ```

4. Keep output downloads separate from source archives.
5. Cite whether the archive came from latest visible version or an explicit
   version.

## Submission And Quota Guardrails

Before suggesting submissions or GPU/TPU-heavy runs:

```bash
kaggle quota
kaggle competitions submissions COMPETITION --format json
kaggle competitions team-submissions COMPETITION --format json
```

Use quotas and recent submission history to avoid wasting attempts. If quota
or team submission commands fail, report that as missing evidence rather than
assuming unlimited capacity.

## Brief Shape

A useful brief is compact and source-backed:

- Objective: competition, metric, deadline/status, and user goal.
- Constraints: rules, data access, submission limits, compute/quota limits.
- Public evidence: top writeups, high-signal topics, notable kernels, and
  uncertainty notes.
- Candidate approaches: methods tied to evidence, not popularity alone.
- Risks: leakage concerns, unstable splits, metric pitfalls, compute cost,
  late-rule changes.
- Next actions: one to three concrete experiments with data, notebook, and
  submission plan.

Every claim about what public competitors did should trace to a discussion,
writeup, kernel, or leaderboard source URL.
