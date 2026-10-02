# Setup

What is installed, which credential is configured, and whether Kaggle can be
reached.

## Start here

```bash
python3 scripts/kaggle_skill.py doctor
python3 scripts/kaggle_skill.py doctor --verify
```

`doctor` reports the Python version, the `kaggle` and `kagglehub` packages,
the Kaggle CLI, the credential that would be used, and whether Kaggle's three
hosts and its MCP server answer. It ends with what works now:

- public reads need only Python and the network;
- reads on the account need an API token or an OAuth login;
- downloads, submissions and notebooks need the Kaggle CLI and a credential;
- publishing a dataset or model uses kagglehub by default (an API token or a
  legacy key), or the Kaggle CLI with `--via cli`.

It only reads and prints no credential value. `--verify` also asks Kaggle
whether the credential is accepted. Exit status: 0 every host and the MCP
server answer, 1 one of them does not, 2 with `--verify` when the credential
is rejected.

## Install what is missing

```bash
python3 -m pip install "kaggle>=2.2.4" "kagglehub>=1.0.2"
```

The agent runs commands with the `python3` on its PATH. Install the packages
for that Python. Nothing is installed automatically.

## Credentials in detail

```bash
python3 scripts/kaggle_skill.py credentials
python3 scripts/kaggle_skill.py credentials --verify
```

The checker looks where the Kaggle CLI looks, in the same order: API token,
legacy key, then OAuth login. `--verify` runs `kaggle quota`, which needs a
signed-in account: that is the way to tell a working credential from a
revoked one. `--json` prints the report for a program. Exit status: 0 when a
credential is found (and accepted, with `--verify`), 2 otherwise.

A missing credential is not always a problem: see "Credentials" in
`SKILL.md` for what needs one.

## Get a credential

```bash
kaggle auth login
```

or an API token from "Generate New Token" at kaggle.com/settings, stored in
`~/.kaggle/access_token` or exported as `KAGGLE_API_TOKEN`. The walkthrough is
in [kaggle-setup.md](references/kaggle-setup.md).

A legacy key (`kaggle.json`) works for the Kaggle CLI and kagglehub. The
commands that read the account through Kaggle's MCP server (`status`,
`leaderboard`, `competitions`, `details`, `watch`, `episodes`, `writeups`)
need a token or an OAuth login. kagglehub does not use an OAuth login: with
only a login, publish with `--via cli`.

Never print a credential or the contents of a credential file.

## Save environment credentials to disk

```bash
python3 scripts/kaggle_skill.py save-credentials          # dry run
python3 scripts/kaggle_skill.py save-credentials --yes
```

Writes `KAGGLE_API_TOKEN` to `~/.kaggle/access_token` (or the legacy pair to
`kaggle.json`) readable by the owner alone. It never replaces an existing
file, never prints the value, and does nothing without `--yes`. Run it only
when the user wants the credential stored on disk.

A `.env` file is read only when `KAGGLE_ENV_FILE` names it, and only its
`KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, `KAGGLE_CONFIG_DIR`, and
`KAGGLE_MCP_TOKEN` lines are used.
