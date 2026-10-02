# Setup

Account walkthrough, credential checks, and network checks.

## Check what is configured

```bash
python3 modules/setup/scripts/check_all_credentials.py
python3 modules/setup/scripts/check_all_credentials.py --verify
bash modules/setup/scripts/network_check.sh
```

The checker looks where the Kaggle CLI looks, in the same order: API token,
legacy key, then OAuth login. It only reads. `--verify` runs `kaggle quota`,
which needs a signed-in account, and reports the account. That is the way to
tell a working credential from a revoked one. `--json` prints the report for a
program.

Exit status: 0 when a credential is found (and accepted, with `--verify`),
1 otherwise.

Public reads work with no credential at all, so a missing credential is not
always a problem. See `SKILL.md` for which workflows need one.

## Get a credential

```bash
kaggle auth login
```

or an API token from "Generate New Token" at kaggle.com/settings, stored in
`~/.kaggle/access_token` or exported as `KAGGLE_API_TOKEN`. The walkthrough is
in [kaggle-setup.md](references/kaggle-setup.md).

Never print a credential or the contents of a credential file.

## Save environment credentials to disk

```bash
bash modules/setup/scripts/setup_env.sh
```

Writes `KAGGLE_API_TOKEN` to `~/.kaggle/access_token` (or the legacy pair to
`kaggle.json`) with owner-only permissions. It never replaces an existing
file, installs nothing, and is not run automatically. Run it with `bash`; do
not `source` it.

A `.env` file is read only when `KAGGLE_ENV_FILE` names it, and only its
`KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, and `KAGGLE_CONFIG_DIR`
lines are used.
