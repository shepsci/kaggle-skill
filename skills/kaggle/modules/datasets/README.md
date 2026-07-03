# Datasets

Use this module for Kaggle dataset downloads, metadata initialization, dataset
creation, and dataset version uploads.

## Scripts

```bash
python3 modules/datasets/scripts/kagglehub_download.py owner/dataset-name
bash modules/datasets/scripts/cli_download.sh owner/dataset-name ./data
python3 modules/datasets/scripts/kagglehub_publish.py owner/dataset-name ./data "Version notes"
bash modules/datasets/scripts/cli_publish.sh ./data
```

`cli_download.sh` validates dataset slugs before shell use. Publishing is an
account-visible write and should stay private unless the user asks otherwise.

## References

- [kagglehub-datasets.md](references/kagglehub-datasets.md)
