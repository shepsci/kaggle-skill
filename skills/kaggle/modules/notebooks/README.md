# Notebooks

Pushing notebooks, running them on Kaggle, waiting for the run, and
downloading the output.

```bash
python3 scripts/kaggle_skill.py notebook-push ./notebook-dir          # dry run
python3 scripts/kaggle_skill.py notebook-run ./notebook-dir --yes
python3 scripts/kaggle_skill.py notebook-wait username/notebook-name --timeout 7200
```

- `notebook-push` pushes the folder as a new version. Pushing also starts a
  run.
- `notebook-run` pushes, waits for the run, and downloads the output.
- `notebook-wait` waits for a run that has already started, then downloads
  its output. `--no-output` only waits.

`--timeout` is the longest wait in seconds (default 3600) and `--interval`
the time between checks (default 30). The output goes to `--out`, by default
`./downloads/<notebook-name>-output`.

The folder needs `kernel-metadata.json` (`kaggle kernels init -p <dir>` writes
a template). The notebook's name is read from its `id`, so the run that is
watched is the one that was pushed.

Without `--yes`, `notebook-push` and `notebook-run` only print what would be
pushed: the notebook, its visibility, whether it uses a GPU, whether the
internet is on, and its competition. Show that to the user before `--yes`. A
GPU run uses the account's weekly hours (`status <competition>` shows them),
and only two GPU runs can be active at once.

## What the commands check

- A push that the CLI rejects ("Kernel push error") stops the command. The
  CLI itself exits with 0 in that case.
- The status is read from the quoted word in the CLI's status line, so a
  notebook whose name contains "complete" or "error" is not misread.
- When a run fails, the last 40 lines of its log are printed, not all of it.
- Output is downloaded only after the file names are checked: a name that
  would land outside the output folder stops the download (exit status 5).
- Kaggle receives only the code file that `kernel-metadata.json` names, with
  the settings in that file. The push stops (exit status 5) when the code
  file is outside the folder or looks like a credential file.
- The dry run shows the accelerator (`enable_gpu`, `enable_tpu` or
  `machine_shape`), the visibility, and the data sources the run attaches.

## Exit status

| Code | Meaning |
|---|---|
| 0 | Output downloaded; or a dry run |
| 1 | The push failed, or the run failed or was cancelled |
| 2 | Wrong arguments, or no credential |
| 4 | The status or the output listing could not be read |
| 5 | Refused for safety |
| 124 | Still running after the longest wait. Run `notebook-wait` to keep waiting |

The scripts are `scripts/notebook_push.py`, `scripts/notebook_run.py` and
`scripts/notebook_wait.py`.
