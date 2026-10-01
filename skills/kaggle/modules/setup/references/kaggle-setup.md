# Kaggle Account and Credential Setup

How to create a Kaggle account, get a credential, and check that it works.
The same credential serves the Kaggle CLI, `kagglehub`, and the MCP server.

## 1. Create an account

1. Go to https://www.kaggle.com/account/login and choose **Register**, or
   sign in with Google.
2. Pick a username. It becomes your handle in every dataset, model, and
   notebook address.
3. Confirm your email from the message Kaggle sends.

### Phone verification

Kaggle asks for a phone number before it lets an account use GPU, TPU, or
internet access in notebooks. Do it at https://www.kaggle.com/settings under
**Phone Verification**. Some competitions also ask for identity verification
on the website before submissions or prizes. Neither step has an API.

## 2. Choose a credential

Public competitions pages, datasets, models, and notebooks can be read with no
credential. You need one for private data, submissions, publishing, and your
own account data.

| Credential | Good for | How to get it |
|---|---|---|
| OAuth login | Interactive use on your own machine | `kaggle auth login` |
| API token | Scripts, servers, MCP clients | **Generate New Token** at https://www.kaggle.com/settings |
| Legacy key | Old tools only | **Create Legacy API Key** at the same page |

### OAuth login

```bash
kaggle auth login
```

A browser opens, you approve, and the CLI stores the login in
`~/.kaggle/credentials.json`. Use `--no-launch-browser` on a machine without
one.

### API token

1. Go to https://www.kaggle.com/settings and find the **API** section.
2. Choose **Generate New Token**, name it, and copy the value. It starts with
   `KGAT_`.
3. Store it in a file only you can read. This form keeps the token out of your
   shell history: run it, paste the token, press Enter, then Ctrl-D.

```bash
mkdir -p ~/.kaggle && chmod 700 ~/.kaggle
(umask 077 && cat > ~/.kaggle/access_token)
```

Or export it from your shell profile:

```bash
export KAGGLE_API_TOKEN="paste-the-token-here"
```

Creating a new token does not cancel your other tokens. Make one per tool so
that you can revoke them one at a time.

### Legacy key

`kaggle.json` holds a username and a 32-character key for the older API.
Creating a new legacy key cancels the previous one.

```bash
mkdir -p ~/.kaggle && chmod 700 ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

### A `.env` file

The skill reads a `.env` file only when you name it, and only its
`KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, and `KAGGLE_CONFIG_DIR`
lines:

```bash
export KAGGLE_ENV_FILE="$HOME/.config/kaggle.env"
```

A `.env` in the working directory is not read. Keep such a file out of version
control and out of any folder you publish as a dataset or model.

## 3. Check the setup

```bash
python3 modules/setup/scripts/check_all_credentials.py --verify
```

Sample output:

```
[OK] API token: found (from ~/.kaggle/access_token)
[OK] OAuth login: found (from ~/.kaggle/credentials.json, user: your_username)

The Kaggle CLI will try the API token from ~/.kaggle/access_token first.
[OK] Verified: Kaggle accepted the credential as your_username.
```

Without `--verify` the checker only lists what it finds. A credential that was
revoked still shows as found, so use `--verify` when something fails. The
checker never writes a file and never prints a credential. `--json` prints the
same report for a program to read.

To check by hand:

```bash
kaggle config view
kaggle quota
bash modules/setup/scripts/network_check.sh
```

`kaggle config view` prints the account name. For a legacy key or an OAuth
login it does not contact Kaggle, so it also passes for a revoked key.
`kaggle quota` needs a signed-in account: it fails with "Authentication
required" when Kaggle no longer accepts the credential.

## 4. Order of use

When more than one credential is present, the Kaggle CLI uses the first that
works:

| Order | Source |
|---|---|
| 1 | `KAGGLE_API_TOKEN` (the token, or the path of a file that holds it) |
| 2 | `~/.kaggle/access_token` |
| 3 | `KAGGLE_USERNAME` + `KAGGLE_KEY` |
| 4 | `kaggle.json` in `KAGGLE_CONFIG_DIR` or `~/.kaggle` |
| 5 | OAuth login in `~/.kaggle/credentials.json` |

For the MCP server the skill's scripts send the API token if there is one,
then the OAuth access token.

## 5. Saving environment credentials to disk

```bash
bash modules/setup/scripts/setup_env.sh
```

This writes `KAGGLE_API_TOKEN` to `~/.kaggle/access_token`, or
`KAGGLE_USERNAME` and `KAGGLE_KEY` to `~/.kaggle/kaggle.json`, readable only
by you. It never replaces a file that exists. Run it with `bash`; do not
`source` it. Nothing runs it automatically.

## 6. Common problems

| Problem | What to do |
|---|---|
| `kaggle: command not found` | `python3 -m pip install "kaggle>=2.2.4"`, then open a new shell |
| `KAGGLE_TOKEN` is set | No Kaggle tool reads it. Use `KAGGLE_API_TOKEN` |
| Credential found but calls fail | Run the checker with `--verify`; the credential may be revoked |
| 401 or `Unauthenticated` | No credential reached the server. For MCP, sign in from the client or send an API token |
| 403 on a competition | Accept the competition's rules on kaggle.com |
| 403 on a model | Accept the model's license on kaggle.com |
| Permission warning on `kaggle.json` | `chmod 600 ~/.kaggle/kaggle.json` |
| 429 Too Many Requests | Wait a few minutes and retry with fewer calls |
| Token appears in output | A variable named `VERBOSE` or `VERBOSE_OUTPUT` is set. Unset it and make a new token |

## 7. If a credential leaks

Revoke it at https://www.kaggle.com/settings (or `kaggle auth revoke` for an
OAuth login), create a new one, and check recent activity on the account.
Never paste a credential into a chat, an issue, or a notebook.
