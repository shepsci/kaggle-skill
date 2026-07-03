# Notebooks

Use this module for Kaggle notebook publishing, execution on Kaggle Kernel
Backend, polling, and output download.

## Scripts

```bash
bash modules/notebooks/scripts/cli_publish.sh ./notebook-dir
bash modules/notebooks/scripts/cli_execute.sh ./notebook-dir username/kernel-slug ./output
bash modules/notebooks/scripts/poll_kernel.sh username/kernel-slug ./output 30
```

Notebook publish and execution are account-visible writes. Confirm visibility,
kernel slug, attached data sources, and expected runtime before running them.
