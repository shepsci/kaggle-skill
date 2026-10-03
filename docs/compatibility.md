# Compatibility

"Tested" means the install was run on this release; the steps are in the
[install checklist](../tests/e2e/INSTALL_CHECKLIST.md).

| Platform | Status |
|---|---|
| Claude Code | Tested |
| Codex | Tested |
| Antigravity CLI (`agy`) | Last tested on skill version 2.4.0 |
| OpenClaw | Last tested on skill version 2.4.0 |
| Gemini CLI | Not re-tested: it stopped serving individual accounts on 2026-06-18 |
| Cursor, GitHub Copilot, Cline, Amp, Hermes | Compatible |
| Other agents supported by skills.sh | Compatible |

The skill needs Python 3.11 or later; the test suite runs on 3.11, 3.12, 3.13
and 3.14. Public reads use only the standard library. Downloads, submissions,
notebooks and publishing call the Kaggle CLI (`kaggle>=2.2.4`) and `kagglehub`
(`kagglehub>=1.0.2`).

## How this relates to Kaggle's own skills

Kaggle publishes agent skills of its own. Use them for what they cover:

| Kaggle skill | Where | Use it for |
|---|---|---|
| `kaggle-cli` | [Kaggle/kaggle-cli](https://github.com/Kaggle/kaggle-cli/tree/main/skills) | Full command syntax of the Kaggle CLI |
| `write-kaggle-benchmarks` | [Kaggle/kaggle-skills](https://github.com/Kaggle/kaggle-skills) | Writing and running benchmark tasks |
| `kaggle-benchmarks` | [Kaggle/kaggle-benchmarks](https://github.com/Kaggle/kaggle-benchmarks) | The benchmark task library |
| `hackathon-judging` | [Kaggle/kaggle-skills](https://github.com/Kaggle/kaggle-skills) | Hosts who judge hackathon submissions |

This skill covers what sits between them: short answers about a competition,
where you stand in it, checked and recorded submissions, retrieval of
writeups and discussions, text from Kaggle marked as untrusted, and dry runs
before anything that changes the account. It retrieves; it does not judge.
