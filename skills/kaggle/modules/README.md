# Kaggle Modules

One folder per kind of task. Every command is run through the entry point,
`python3 scripts/kaggle_skill.py <command>`; each is also a script in its
module's `scripts/` folder.

| Need | Module | Commands |
|---|---|---|
| What is installed, signed in, reachable | [setup](setup/README.md) | `doctor`, `credentials`, `save-credentials` |
| Research and run a competition; hackathons | [competitions](competitions/README.md) | `brief`, `pages`, `competitions`, `details`, `status`, `leaderboard`, `download`, `validate`, `submit`, `watch`, `ledger`, `episodes`, `hackathon`, `writeups`, `writeup` |
| Dataset download or publishing | [datasets](datasets/README.md) | `dataset-download`, `dataset-publish` |
| Model download or publishing | [models](models/README.md) | `model-download`, `model-publish` |
| Notebook push, run, wait, output | [notebooks](notebooks/README.md) | `notebook-push`, `notebook-run`, `notebook-wait` |
| Forums, topics, solution writeups | [discussions](discussions/README.md) | `forums`, `topics`, `topic`, `solutions`, `discussions` |
| Benchmark task commands | [benchmarks](benchmarks/README.md) | `cli -- benchmarks ...` |
| Badge inventory, dry run, phases | [badges](badges/README.md) | `badges` |
| Kaggle CLI, MCP server, and platform references | [references](references/README.md) | `cli -- <kaggle arguments>` |

## Routing notes

- Public pages, writeups and discussions need no credential and no installed
  package. Run `doctor` before anything on the user's account, and before any
  write.
- `competitions/` covers standard competitions, code competitions,
  simulations and hackathons.
- `datasets/` and `models/` use kagglehub by default and the Kaggle CLI with
  `--via cli`.
- Use `discussions/` whenever forum, topic, or writeup text will be read.
- Read `benchmarks/` before a command that creates a task or uses quota.
- Use `badges/` only after a dry run and the user's go-ahead.

## Shared code

`../shared/` holds what every script uses: the MCP client and the HTTPS
helper (standard library only), the credential resolver, the Kaggle CLI
runner, the untrusted-content printer, the argument and exit-code helpers,
the submission ledger, the upload check for credential files, and the safe
zip extractor. Scripts print Kaggle-supplied text through
`shared/untrusted.py`; see "Reading the output" in `SKILL.md`.
