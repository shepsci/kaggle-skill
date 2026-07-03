# Setup

Use this module for Kaggle account walkthroughs, API token setup, credential
checks, and network diagnostics.

## Quick Checks

```bash
python3 modules/setup/scripts/check_all_credentials.py
python3 modules/setup/scripts/check_registration.py
bash modules/setup/scripts/network_check.sh
```

`setup_env.sh` is used by the Claude SessionStart hook and can also be run
manually:

```bash
bash modules/setup/scripts/setup_env.sh
```

It reads `.env` only from the skill root, never from the current working
directory, and never installs packages automatically.

## Credentials

Preferred:

```bash
mkdir -p ~/.kaggle
printf '%s\n' 'YOUR_TOKEN' > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
```

Alternative:

```bash
export KAGGLE_API_TOKEN='YOUR_TOKEN'
```

Legacy `KAGGLE_USERNAME` plus `KAGGLE_KEY` and `~/.kaggle/kaggle.json` remain
supported for older CLI/API paths. Do not print token values or credential file
contents.

## Reference

- [kaggle-setup.md](references/kaggle-setup.md) — full account and credential
  walkthrough.
