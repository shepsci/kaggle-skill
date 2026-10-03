# Security Policy

## Reporting a vulnerability

Report it privately with GitHub's "Report a vulnerability" button on the
repository's Security tab:

https://github.com/shepsci/kaggle-skill/security/advisories/new

If that is not available, open an issue that asks the maintainer to start a
private discussion, without details. Do not put secrets, exploit steps, or
private Kaggle data in a public issue.

Other questions go to https://github.com/shepsci/kaggle-skill/issues.

## What is in scope

- A way for text from Kaggle (a page, a writeup, a forum post, a file name, an
  error message) to leave its untrusted-content block or to be acted on by a
  script.
- A credential that is printed, logged, written somewhere unexpected, or sent
  to a host other than Kaggle.
- A file written outside the folder a download or an extraction was given.
- A script that changes the Kaggle account when it was described as read-only
  or as a dry run.

## How the skill handles credentials

Credentials are never asked for in chat. They are read from the environment
and from `~/.kaggle`, in the Kaggle CLI's own order. The checker only reads.
The MCP client sends the token in a request header from inside the process;
it is not passed to another program. The bundled MCP server entry holds no
credential.

If a Kaggle credential is exposed, revoke it at
https://www.kaggle.com/settings and create a new one.

## Text from Kaggle is untrusted

Scripts print everything that Kaggle hosts or users can write inside a block
whose tag carries a random suffix, so the text cannot close its own block.
`SKILL.md` tells the agent to treat the content as data. This lowers the risk
of instructions hidden in Kaggle content. It does not remove it: an agent can
still be misled. Review what an agent proposes before it submits, publishes,
or runs commands.

## Actions that change the account

Submissions, dataset, model and notebook publishing, benchmark task creation,
and badge phases change the Kaggle account. The skill pre-approves only read
tools (`Read`, `Grep`, `Glob`), so the agent has to ask before it runs a
command. `submit`, `dataset-publish`, `model-publish`, `notebook-push`,
`notebook-run`, `save-credentials` and an account-changing `cli --` command
are dry runs unless `--yes` is given, and `KAGGLE_SKILL_READ_ONLY=1` makes
them refuse. The badge orchestrator has a `--dry-run`; once a phase is
started it does not ask again.

## Known limits in the Kaggle tools

Kaggle CLI 2.2.4 writes notebook output under file names from the server
without a path check, extracts model archives with `--untar` without one, and
prints request headers when `VERBOSE` is set. The skill's scripts check names
first, do not use `--untar`, and clear those variables. Fixes are on the
CLI's main branch and not yet released. `kagglehub` before 1.0.2 extracted
tar archives without a path check; the skill requires 1.0.2.

Two limits remain in `kagglehub` 1.0.2 itself. It saves the files of a small
model under the names the server sends, without a containment check; whether
Kaggle normalises those names is not known. And with an output folder, a
forced download deletes what is in the folder first; the skill's scripts
refuse a folder that is not empty.

## Supported versions

Fixes are made on the latest release.
