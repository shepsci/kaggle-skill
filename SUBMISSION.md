# Official Anthropic Marketplace Submission

This document collects the exact text needed to submit `kaggle-skill` to the
official Anthropic plugin marketplace
([anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official)).

The independent marketplace at
[shepsci/claude-marketplace](https://github.com/shepsci/claude-marketplace) is
already live and lets users install today; submitting to the official
marketplace is the next step for broader discoverability.

## Where to submit

- **Primary form**: https://platform.claude.com/plugins/submit
- **Alternative**: https://claude.ai/settings/plugins/submit

## Submission payload

### Plugin name
```
kaggle-skill
```

### Repository URL
```
https://github.com/shepsci/kaggle-skill
```

### Version
```
2.1.0
```

### One-line description (≤120 chars)
```
Complete Kaggle integration: competition reports, dataset/model downloads, notebook execution, hackathons, and badges.
```

### Long description
```
kaggle-skill is a unified Kaggle integration packaged as a Claude Code plugin.
It bundles the official Kaggle MCP server (66 tools) with five purpose-built
modules:

  • Registration  — account creation, KGAT API token generation, credential
                    storage, multi-source credential discovery
  • Competition   — landscape reports combining the public Kaggle API with
    Reports        Playwright scraping for SPA content
  • Kaggle (kllm) — kagglehub, kaggle-cli, and the bundled MCP server
                    interaction patterns with full reference docs
  • Hackathon     — writeup retrieval, overview/rubric extraction, role-aware
                    grading bundles built around the documented endpoint order
                    from the kmcp-tools 2026-04-22 audit (avoids the broken
                    get_hackathon_write_up endpoint, uses the get_writeup
                    fallback chain instead)
  • Badge         — systematic 5-phase badge collection for ~38 automatable
    Collector      Kaggle badges

The plugin ships with a comprehensive TDD test suite: 128+ no-network unit /
manifest / security tests that run on every commit, plus 30+ live integration
tests that probe all 66 MCP tools when KAGGLE_API_TOKEN is available.

Privacy: no telemetry, no third-party services, no automatic persistence.
Credentials are stored locally with chmod 600. All scraped content is wrapped
in <untrusted-content> boundary markers before agent processing.

Security: all imports are explicit and static — no eval/exec/__import__/
dynamic compile in any script (enforced by tests/security/test_no_dynamic_eval.py).
```

### Keywords / tags
```
kaggle, competitions, datasets, models, notebooks, hackathons, writeups,
machine-learning, data-science, mcp, kagglehub, badges
```

### Author
```
shepsci
```

### License
```
MIT
```

### Homepage
```
https://github.com/shepsci/kaggle-skill
```

### Privacy policy
```
https://github.com/shepsci/kaggle-skill/blob/main/PRIVACY.md
```

### Why include this plugin

```
Kaggle is the dominant platform for ML competitions, datasets, and notebooks.
Until now there has been no first-class Claude Code integration that wraps the
official Kaggle MCP server with curated workflows for the day-to-day Kaggle
tasks (credential setup, competition reports, dataset downloads, notebook
execution, badge progression, hackathon grading). This plugin fills that gap
with a single install and ships with a security posture suitable for the
official catalog (no telemetry, no eval, validated by 128+ tests).
```

### Screenshots / demo

Demo flow that shows end-to-end value (run after install):

```
/plugin install kaggle-skill@shepsci
"set up my Kaggle credentials"
"give me a landscape report of competitions in the last 30 days"
"download the kaggle-measuring-agi hackathon overview and list every writeup"
```

## Pre-submission checklist

- [x] `.claude-plugin/plugin.json` valid (validated by tests/manifest)
- [x] SKILL.md frontmatter valid (validated by tests/manifest)
- [x] `.mcp.json` uses HTTPS + env-var substitution (validated by tests/manifest)
- [x] No `eval`/`exec`/`compile` in scripts (validated by tests/security)
- [x] No credential echo patterns in scripts (validated by tests/security)
- [x] PRIVACY.md present
- [x] LICENSE present (MIT)
- [x] Independent marketplace already live at shepsci/claude-marketplace as
      a fast-publish alternative
- [x] Live MCP coverage documented (66 tools) with KNOWN_FAIL endpoints called
      out and worked around in the hackathon module
- [x] README install section uses the correct two-step
      `marketplace add` → `install @namespace` flow

## After submission

1. Track approval status; respond to review comments inline on the form thread.
2. On approval, the plugin appears in the pre-installed `claude-plugins-official`
   marketplace and `/plugin install kaggle-skill@claude-plugins-official` works
   from a stock Claude Code install.
3. Update the README "Available On" table to add the official marketplace row.
4. Tag the release `v2.1.0` on GitHub once approved.
