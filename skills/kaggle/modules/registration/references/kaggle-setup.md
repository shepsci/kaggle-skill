# Kaggle Account & API Setup Guide

Step-by-step instructions for creating a Kaggle account, generating API credentials, and configuring them for use with any OpenClaw-compatible agent (Claude Code, gemini-cli, Cursor, etc.).

## 1. Create a Kaggle Account

1. Go to [https://www.kaggle.com/account/login](https://www.kaggle.com/account/login)
2. Click **Register** (or sign in with Google/GitHub if you prefer)
3. Fill in:
   - **Email**: your email address
   - **Password**: choose a strong password
   - **Username**: choose a username (this becomes your Kaggle handle, e.g., `yourname`)
4. Click **Create Account**
5. Verify your email by clicking the link Kaggle sends you

### Persona Verification (Required for Some Features)

Kaggle requires phone verification to:
- Submit to competitions
- Use GPU/TPU accelerators
- Download some restricted datasets

To verify:
1. Go to [https://www.kaggle.com/settings](https://www.kaggle.com/settings)
2. Under **Phone Verification**, click **Verify**
3. Enter your phone number and the SMS code

## 2. Generate Your API Credentials

### Primary: API Token (Recommended)

| Credential | Variable | How to Get |
|-----------|----------|------------|
| API Token | `KAGGLE_API_TOKEN` | "Generate New Token" button under "API Tokens (Recommended)" |

1. Go to [https://www.kaggle.com/settings](https://www.kaggle.com/settings)
2. Scroll to the **API** section
3. Under **API Tokens (Recommended)**, click **Generate New Token**
4. Name the token (e.g., "claude-code") and copy the generated value
5. This single token works with kaggle CLI (>= 1.8.0), kagglehub (>= 0.4.1), and MCP Server

**Note:** Creating a new token does not expire existing tokens or legacy keys. You can create multiple named tokens for different tools/projects.

### Optional: Legacy API Key

| Credential | Variables | How to Get |
|-----------|-----------|------------|
| Legacy Key | `KAGGLE_USERNAME` + `KAGGLE_KEY` | "Create Legacy API Key" under "Legacy API Credentials" |

Only needed for older tool versions (kaggle CLI < 1.8.0, kagglehub < 0.4.1):

1. Go to [https://www.kaggle.com/settings](https://www.kaggle.com/settings)
2. Under **Legacy API Credentials**, click **Create Legacy API Key**
3. A `kaggle.json` file downloads containing `{"username":"...","key":"..."}`

**Warning:** Creating a legacy key expires any existing legacy keys.

## 3. Install Your Credentials

### Method 1: Access Token File (Recommended)

Save your API token to the Kaggle config directory:

```bash
mkdir -p ~/.kaggle
echo '<your_token>' > ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
```

### Method 2: Environment Variable

```bash
export KAGGLE_API_TOKEN='<your_token>'
```

Or add to your shell profile (`~/.zshrc`, `~/.bashrc`) for persistence.

### Method 3: .env File (Project-Level)

Create a `.env` file in your project root:

```
KAGGLE_API_TOKEN=<your_token>
```

**Important**: Add `.env` to your `.gitignore`:
```bash
echo ".env" >> .gitignore
```

Secure the file:
```bash
chmod 600 .env
```

### Method 4: kaggle.json File (Legacy)

If you created a legacy API key, place the downloaded `kaggle.json`:

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

Note: `kaggle.json` only stores username + legacy key. For the API token, use Methods 1-3.

## 4. Verify Your Setup

### Using the Registration Checker

```bash
python3 modules/registration/scripts/check_registration.py
```

Expected output when credentials are configured:
```
[OK] KAGGLE_API_TOKEN: ****abcd (from access_token file)
[OK] KAGGLE_USERNAME: your_username (from kaggle.json)
[OK] KAGGLE_KEY: ****wxyz (from kaggle.json) [legacy]

All credentials found. You're ready to go!
```

### Manual Verification

```bash
# Test with kaggle CLI
kaggle datasets list --search "titanic" --page-size 1

# Test with kagglehub
python3 -c "import kagglehub; print(kagglehub.whoami())"
```

## 5. Credential Priority Order

When multiple credential sources exist, they are checked in this order:

| Priority | Source | Used By |
|----------|--------|----------|
| 1 | `KAGGLE_API_TOKEN` env var | CLI, kagglehub, MCP |
| 2 | `~/.kaggle/access_token` file | CLI, kagglehub |
| 3 | Google Colab secret `KAGGLE_API_TOKEN` | kagglehub |
| 4 | `KAGGLE_USERNAME` + `KAGGLE_KEY` env vars | CLI, kagglehub (legacy) |
| 5 | `~/.kaggle/kaggle.json` file | CLI, kagglehub (legacy) |

## 6. Common Misconfigurations

| Issue | Fix |
|-------|-----|
| `KAGGLE_TOKEN` set instead of `KAGGLE_API_TOKEN` | Rename to `KAGGLE_API_TOKEN` |
| Only legacy `kaggle.json` (no API token) | Generate a new token at kaggle.com/settings |
| Credentials in env but no file | Run `setup_env.sh` to auto-create access_token/kaggle.json |
| Old kaggle CLI (< 1.8.0) doesn't recognize new tokens | Upgrade: `pip install --upgrade kaggle` or use legacy key |
| Old kagglehub (< 0.4.1) doesn't recognize new tokens | Upgrade: `pip install --upgrade kagglehub` or use legacy key |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `kaggle: command not found` | Run `pip install kaggle` or check install location with `pip show kaggle` |
| `401 Unauthenticated` | Check that credentials exist and are correct |
| `403 Forbidden` on competition | Accept competition rules at kaggle.com |
| `403 Forbidden` on model | Accept model license at kaggle.com |
| `kaggle.json permissions warning` | Run `chmod 600 ~/.kaggle/kaggle.json` |
| MCP "Unauthenticated" | Use API token (from "Generate New Token") as Bearer token |
| `HTTP 429 Too Many Requests` | Dynamic rate limiting — wait a few minutes and retry |
