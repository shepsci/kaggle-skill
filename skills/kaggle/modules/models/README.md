# Models

Model downloads and publishing.

A model has variations (one per framework and size), and each variation has
numbered versions. A handle is `owner/model/framework/variation`, with the
version as an optional fifth part.

## Download

```bash
python3 modules/models/scripts/kagglehub_download.py owner/model/framework/variation
python3 modules/models/scripts/kagglehub_download.py owner/model/framework/variation/3 --output-dir ./model
bash modules/models/scripts/cli_download.sh owner/model/framework/variation/3 ./model
```

- The kagglehub script takes the four-part handle and fetches the latest
  version, or a specific one when you add the number.
- The CLI script needs the version number. To see the versions:
  `kaggle models variations versions list owner/model/framework/variation`.
- The CLI script leaves the archive as downloaded (`.tar.gz`). Kaggle CLI
  2.2.4 extracts tar files without a path check, so the script does not ask
  it to.
- For the kagglehub script, `--output-dir` must be a new or empty folder:
  kagglehub deletes what is in the folder when it downloads again, so a folder
  with files in it is refused (exit status 5).
- kagglehub 1.0.2 saves the files of a small model under the names the server
  sends, without checking that they stay inside the folder. Download models
  from owners you trust, or use the CLI script, which keeps the archive
  packed.

## Publish

```bash
python3 modules/models/scripts/kagglehub_publish.py owner/model/framework/variation ./model "Version notes"
bash modules/models/scripts/cli_publish.sh ./model owner/model/framework/variation "Version notes"
```

Publishing changes the account, so get the user's go-ahead first.

- Both scripts stop with exit status 5 if the folder holds a credential file.
- The CLI script needs `model-metadata.json` and
  `model-instance-metadata.json`; it writes a template for whichever is
  missing and stops. It then creates only what does not exist yet: the model,
  the variation (which uploads the files as version 1), or a new version of
  an existing variation. Subfolders are uploaded as zip archives.
- New models are private.

## References

- [kagglehub-models.md](references/kagglehub-models.md)
