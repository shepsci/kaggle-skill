# Datasets

Dataset downloads, new datasets, and new versions.

## Download

```bash
python3 scripts/kaggle_skill.py dataset-download owner/dataset-name
python3 scripts/kaggle_skill.py dataset-download owner/dataset-name ./data --file train.csv
python3 scripts/kaggle_skill.py dataset-download owner/dataset-name ./data --via cli
```

By default kagglehub downloads. A public dataset needs no credential, the
files go to the kagglehub cache (`~/.cache/kagglehub`) unless you give a
folder, and a version can be named as `owner/name/versions/3`.

The folder must be new or empty. kagglehub deletes what is in a folder when
it downloads into it, so a folder with files in it is refused (exit status
5). With `--file` only that one file is replaced, and only with `--force`.

`--via cli` uses the Kaggle CLI, which needs a credential, downloads into
`./downloads/<owner>-<name>` unless a folder is given, and unpacks the
archive.

## Publish

```bash
python3 scripts/kaggle_skill.py dataset-publish owner/dataset-name ./data --notes "Version notes"
python3 scripts/kaggle_skill.py dataset-publish owner/dataset-name ./data --notes "Version notes" --yes
python3 scripts/kaggle_skill.py dataset-publish owner/dataset-name ./data --via cli --yes
```

Without `--yes` nothing is uploaded: the command prints the dataset, the
number of files and their size, and stops. Publishing changes the account, so
get the user's go-ahead before `--yes`.

- Everything in the folder is uploaded. The command stops with exit status 5
  if the folder holds a credential file such as `.env` or `kaggle.json`, or a
  link to a file or folder outside it (the uploaders follow links).
- By default kagglehub uploads: it creates the dataset if it is new and adds
  a version if it exists.
- `--via cli` needs `dataset-metadata.json` in the folder, and its `id` must
  be the dataset you name. Write a template with
  `kaggle datasets init -p <dir>`. Without `--notes` the dataset is created;
  with `--notes` a version is added.
- New datasets are private.

The scripts are `scripts/dataset_download.py` and `scripts/dataset_publish.py`.

## References

- [kagglehub-datasets.md](references/kagglehub-datasets.md)
