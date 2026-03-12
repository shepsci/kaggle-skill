# Registration — Account & Credential Setup

Walk the user through Kaggle account registration, generating API credentials,
and saving them securely. Run the credential checker first to skip steps that
are already complete.

## Credential Check (Always Run First)

Before starting the walkthrough, check what's already configured:

```bash
python3 modules/registration/scripts/check_registration.py
```

This checks for credentials in env vars, `.env` file, `~/.kaggle/access_token`,
and `~/.kaggle/kaggle.json`. If credentials are found, tell the user they're
already set up and no further action is needed.

## Credentials Overview

| Variable | Format | Source | Required? |
|----------|--------|--------|-----------|
| `KAGGLE_API_TOKEN` | Access token string | "Generate New Token" button | **Yes (primary)** |
| `KAGGLE_USERNAME` | Kaggle handle (e.g., `johndoe`) | Account creation | Optional (auto-detected from token) |
| `KAGGLE_KEY` | 32-char hex string | "Create Legacy API Key" button | Optional (legacy fallback) |

**Primary method:** A single API token from "Generate New Token" is all you need.
It works with kaggle CLI (>= 1.8.0), kagglehub (>= 0.4.1), and MCP Server.

**Legacy fallback:** The username + key pair (from `kaggle.json`) is only needed
for older tool versions. The Kaggle Settings UI explicitly labels this as
"Legacy API Credentials".

## Step 1: Create a Kaggle Account

If the user doesn't have a Kaggle account:

1. Direct them to [https://www.kaggle.com/account/login](https://www.kaggle.com/account/login)
2. Click **Register** (or sign in with Google/GitHub)
3. Fill in email, password, and choose a username (this is their `KAGGLE_USERNAME`)
4. Click **Create Account** and verify email

### Phone / Persona Verification (Optional but Recommended)

Required for competition submissions, GPU/TPU access, and restricted datasets:

1. Go to [https://www.kaggle.com/settings](https://www.kaggle.com/settings)
2. Under **Phone Verification**, click **Verify**
3. Enter phone number and SMS code

## Step 2: Generate API Token (Primary)

This is the recommended credential method:

1. Go to [https://www.kaggle.com/settings](https://www.kaggle.com/settings)
2. Scroll to the **API** section
3. Under **API Tokens (Recommended)**, click **Generate New Token**
4. Give the token a name (e.g., "claude-code" or "my-project")
5. Copy the generated token value
6. Ask the user to provide this token

**Note:** Creating a new token does not expire existing tokens or legacy keys.
These tokens are supported by kaggle CLI >= 1.8.0 and kagglehub >= 0.4.1.

## Step 3: Legacy API Key (Optional)

Only needed for older tool versions that don't support the new API tokens:

1. Go to [https://www.kaggle.com/settings](https://www.kaggle.com/settings)
2. Scroll to the **API** section
3. Under **Legacy API Credentials**, click **Create Legacy API Key**
4. A `kaggle.json` file downloads automatically containing:
   ```json
   {"username": "your_username", "key": "your_32_char_hex_key"}
   ```
5. Ask the user for the `username` and `key` values from this file

**Warning:** Creating a legacy key expires any existing legacy keys. It does
not affect API tokens.

## Step 4: Save Credentials

### Primary: API Token

Set the token as an environment variable and/or save to file:

```bash
# Option A: Save to access_token file (recommended)
mkdir -p ~/.kaggle
echo '<token>' > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token

# Option B: Set as environment variable
export KAGGLE_API_TOKEN=<token>
```

### Optional: .env File (for project-level config)

```bash
cat > .env << 'ENVEOF'
KAGGLE_API_TOKEN=<token>
ENVEOF

chmod 600 .env
```

Also ensure `.env` is in `.gitignore`:

```bash
if ! grep -q '^.env$' .gitignore 2>/dev/null; then
  echo '.env' >> .gitignore
fi
```

### Legacy: kaggle.json (if Step 3 was done)

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

## Step 5: Verify Setup

Run the checker again to confirm everything works:

```bash
python3 modules/registration/scripts/check_registration.py
```

Expected output: credentials show `[OK]`.

## Security Best Practices

- **Never** commit `.env`, `kaggle.json`, or `access_token` to version control
- **Never** echo or print credential values in terminal output
- **Always** add `.env` and `.kaggle/` to `.gitignore`
- Set file permissions: `chmod 600 .env ~/.kaggle/kaggle.json ~/.kaggle/access_token`

## References

- [kaggle-setup.md](references/kaggle-setup.md) — Full step-by-step guide with troubleshooting table
