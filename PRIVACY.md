# Privacy Policy

**kaggle-skill** — Claude Code Plugin & Agent Skill

*Last updated: March 12, 2026*

## Summary

This plugin does not collect, store, transmit, or share any personal data. All credentials and data remain on your local machine.

## Data Collection

This plugin collects **no data whatsoever**. There is no analytics, telemetry, tracking, or usage reporting of any kind.

## Credential Storage

Kaggle API credentials are stored locally on your machine in standard locations:

- `~/.kaggle/access_token` (API token)
- `~/.kaggle/kaggle.json` (legacy credentials)
- Environment variables (`KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`)

Credentials are never logged, echoed, transmitted to third parties, or stored anywhere other than these local files. File permissions are set to owner-only (chmod 600).

## Third-Party Services

This plugin makes API calls to **Kaggle** (kaggle.com) on your behalf using your credentials. These calls are subject to Kaggle's own privacy policy and terms of service:

- [Kaggle Terms of Service](https://www.kaggle.com/terms)
- [Kaggle Privacy Policy](https://www.kaggle.com/privacy)

The bundled MCP server configuration connects to `https://www.kaggle.com/mcp` using your API token. This connection is between your machine and Kaggle's servers — no data passes through any intermediary.

Network requests are made only to:
- `api.kaggle.com` — Kaggle API endpoints
- `www.kaggle.com` — Kaggle website and MCP server
- `storage.googleapis.com` — Dataset and model file downloads

## Data Processing

All data processing happens locally on your machine. Downloaded datasets, models, competition data, and generated reports are stored in your local filesystem only.

## Children's Privacy

This plugin is not directed at children under 13 and does not knowingly process data from children.

## Changes to This Policy

Updates to this policy will be reflected in this file and in the plugin's GitHub repository. The "Last updated" date at the top will be revised accordingly.

## Contact

For questions about this privacy policy, open an issue at [github.com/shepsci/kaggle-skill](https://github.com/shepsci/kaggle-skill/issues).
