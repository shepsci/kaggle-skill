# Security Policy

## Reporting Security Issues

Please report suspected vulnerabilities privately through GitHub Security
Advisories when available, or open a GitHub issue that asks the maintainer to
start a private security discussion. Do not include secrets, exploit payloads,
or private Kaggle data in public issues.

General support questions can be filed at:

```text
https://github.com/shepsci/kaggle-skill/issues
```

## Secret Handling

`kaggle-skill` never requires users to paste credentials into chat. Kaggle
credentials are read from standard local locations such as
`KAGGLE_API_TOKEN`, `~/.kaggle/access_token`, or legacy
`~/.kaggle/kaggle.json`. The tests enforce credential redaction for checker
scripts and plugin setup paths.

If a Kaggle token is exposed, revoke and regenerate it from:

```text
https://www.kaggle.com/settings
```

## Review Notes

The plugin can perform both read-only and account-modifying Kaggle workflows.
Externally visible actions such as competition submissions, dataset/model or
notebook publishing, benchmark task creation, and badge collection require
explicit user intent. When a dry-run command exists, use it before making
changes.

The bundled MCP configuration connects directly to Kaggle's HTTPS MCP endpoint
with the user's `KAGGLE_API_TOKEN` bearer token. The plugin does not collect,
proxy, or store the token outside the user's local environment.
