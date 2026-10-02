# Privacy Policy

**kaggle-skill**: agent skill and plugin

*Last updated: 2026-10-02*

## Summary

The skill collects no data. It has no analytics, telemetry, or usage
reporting. Credentials and downloaded data stay on your machine, and requests
go from your machine to Kaggle.

## Credentials

The skill reads Kaggle credentials from the places the Kaggle CLI uses:

- `KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, and `KAGGLE_KEY` in the environment
- `~/.kaggle/access_token` (API token)
- `~/.kaggle/kaggle.json` (legacy key)
- `~/.kaggle/credentials.json` (OAuth login from `kaggle auth login`)

A `.env` file is read only when `KAGGLE_ENV_FILE` names it, and only its
credential lines (`KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`,
`KAGGLE_CONFIG_DIR`).

Credentials are sent only to `www.kaggle.com` and `api.kaggle.com`. They are
not logged, printed, or placed on a command line. One command,
`save-credentials`, writes a credential to disk, and only when you run it
with `--yes`: it copies the value from your environment to `~/.kaggle` with
owner-only permissions. `doctor` and `credentials` only read.

The bundled MCP server entry contains a URL and, for Claude Code, a public
OAuth client ID. It contains no credential. Signing in to it is handled by
your agent, not by this skill.

## Network requests

The skill's own commands connect to:

| Host | For |
|---|---|
| `www.kaggle.com` | The MCP server (competition facts and pages, discussions, your submissions and quota), leaderboard data, and writeup previews |
| `api.kaggle.com` | The Kaggle CLI and `kagglehub` |
| `storage.googleapis.com` | Dataset, model, and competition file downloads, through the Kaggle tools |

Writeup previews are fetched without a credential, and only from
`www.kaggle.com`: a writeup link that points anywhere else is not followed.

Installing the Python packages contacts PyPI. Installing the plugin contacts
GitHub. Those are done by `pip` and by your agent.

The skill does not limit what your agent itself can reach. An agent that
reads a Kaggle page may decide to open a link in it; that is governed by your
agent's own permissions.

## What Kaggle receives

Requests made with your credential are tied to your Kaggle account and are
subject to Kaggle's terms and privacy policy:

- https://www.kaggle.com/terms
- https://www.kaggle.com/privacy

Submissions, uploads, notebook runs, and badge activity change your Kaggle
account. The skill asks the agent to get your go-ahead before any of them,
and its submission, publish and notebook commands do nothing until `--yes` is
given.

## Data on your machine

Downloads, reports, and the badge progress file are stored where you run the
commands. Two commands keep a local record in `./.kaggle-skill/`, in the
folder you run them from:

- `submit` and `watch` add lines to `ledger.jsonl`: the competition, the
  submission file's name, size and SHA-256, your message, the score you
  expected, and the score Kaggle reported.
- `leaderboard` saves a snapshot of the public leaderboard, which holds team
  names and scores, so that the next run can say what moved.

These files are yours. They are not uploaded, and you can delete them at any
time. `KAGGLE_SKILL_DIR` moves the folder.

Nothing is uploaded unless you ask for a publish or a submission, and each of
those is a dry run until you confirm. The publish commands refuse a folder
that contains a credential file.

## Children

The skill is not directed at children under 13.

## Changes

Changes to this policy appear in this file, with the date at the top.

## Contact

Open an issue at https://github.com/shepsci/kaggle-skill/issues.
