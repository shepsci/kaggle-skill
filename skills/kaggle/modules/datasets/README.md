# Datasets

Dataset downloads, new datasets, and new versions.

## Download

```bash
python3 modules/datasets/scripts/kagglehub_download.py owner/dataset-name
python3 modules/datasets/scripts/kagglehub_download.py owner/dataset-name --path train.csv --output-dir ./data
bash modules/datasets/scripts/cli_download.sh owner/dataset-name ./data
```

Public datasets need no credential. The kagglehub script downloads to its
cache (`~/.cache/kagglehub`) unless you pass `--output-dir`. The CLI script
checks the slug, lists the files, downloads, and unzips.

`--output-dir` must be a new or empty folder. kagglehub deletes what is in the
folder when it downloads again, so the script refuses a folder with files in
it (exit status 5). With `--path` only that one file is replaced, and only
with `--force`.

## Publish

```bash
python3 modules/datasets/scripts/kagglehub_publish.py owner/dataset-name ./data "Version notes"
bash modules/datasets/scripts/cli_publish.sh ./data
bash modules/datasets/scripts/cli_publish.sh ./data "Version notes"
```

Publishing changes the account, so get the user's go-ahead first.

- Both scripts upload everything in the folder. They stop with exit status 5
  if it holds a credential file such as `.env` or `kaggle.json`.
- The kagglehub script creates the dataset if it is new and adds a version if
  it exists.
- The CLI script needs `dataset-metadata.json` in the folder. Without it the
  script writes a template and stops. With version notes it adds a version;
  without them it creates the dataset.
- New datasets are private.

## References

- [kagglehub-datasets.md](references/kagglehub-datasets.md)
