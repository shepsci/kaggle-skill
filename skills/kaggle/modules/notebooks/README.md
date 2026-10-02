# Notebooks

Publishing notebooks, running them on Kaggle, waiting for the run, and
downloading the output.

```bash
bash modules/notebooks/scripts/cli_publish.sh ./notebook-dir
bash modules/notebooks/scripts/cli_execute.sh ./notebook-dir username/kernel-slug ./output 3600
bash modules/notebooks/scripts/poll_kernel.sh username/kernel-slug ./output 30 3600
```

- `cli_publish.sh` pushes the folder. Pushing also starts a run.
- `cli_execute.sh` pushes, waits for the run, and downloads the output. The
  last argument is the longest time to wait, in seconds.
- `poll_kernel.sh` waits for a run that already started: output folder,
  seconds between checks, longest time to wait.

The folder needs `kernel-metadata.json` (`kaggle kernels init -p <dir>` writes
a template). Its `id` must be the `username/kernel-slug` you pass.

Before a push, confirm with the user: the notebook's visibility, its data
sources, whether it uses a GPU, and the expected run time. A GPU run uses the
account's weekly quota (`kaggle quota`), and only two GPU runs can be active
at once.

## What the scripts check

- A push that the CLI rejects ("Kernel push error") stops the script. The CLI
  itself exits with 0 in that case.
- The status is read from the quoted word in the CLI's status line, so a
  notebook whose name contains "complete" or "error" is not misread.
- Output is downloaded only after the file names are checked: a name that
  would land outside the output folder stops the download (exit status 5).
- The notebook folder is checked for credential files before the push
  (exit status 5).

## Exit status

| Code | Meaning |
|---|---|
| 0 | Output downloaded |
| 1 | The push failed, or the run failed or was cancelled |
| 2 | Wrong arguments |
| 4 | The status or the output listing could not be read |
| 5 | Refused for safety |
| 124 | Still running after the longest wait. Run `poll_kernel.sh` to keep waiting |
