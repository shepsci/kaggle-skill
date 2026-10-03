# Models

Model downloads and publishing.

A model has variations (one per framework and size), and each variation has
numbered versions. A handle is `owner/model/framework/variation`, with the
version as an optional fifth part.

## Download

```bash
python3 scripts/kaggle_skill.py model-download owner/model/framework/variation
python3 scripts/kaggle_skill.py model-download owner/model/framework/variation/3 ./model
python3 scripts/kaggle_skill.py model-download owner/model/framework/variation/3 ./model --via cli
```

- By default kagglehub downloads. The four-part handle fetches the latest
  version, or a specific one when you add the number. A public model needs no
  credential.
- The folder must be new or empty: kagglehub deletes what is in a folder when
  it downloads into it, so a folder with files in it is refused (exit status
  5).
- `--via cli` uses the Kaggle CLI and needs the version number. To see the
  versions: `kaggle models variations versions list owner/model/framework/variation`.
  It leaves the archive as downloaded (`.tar.gz`): Kaggle CLI 2.2.4 extracts
  tar files without a path check, so it is not asked to.
- kagglehub 1.0.2 saves the files of a small model under the names the server
  sends, without checking that they stay inside the folder. Download models
  from owners you trust, or use `--via cli`, which keeps the archive packed.

## Publish

```bash
python3 scripts/kaggle_skill.py model-publish owner/model/framework/variation ./model --notes "Version notes"
python3 scripts/kaggle_skill.py model-publish owner/model/framework/variation ./model --notes "Version notes" --yes
python3 scripts/kaggle_skill.py model-publish owner/model/framework/variation ./model --via cli --yes
```

Without `--yes` nothing is uploaded: the command prints what it would do and
stops. Publishing changes the account, so get the user's go-ahead before
`--yes`.

- The command stops with exit status 5 if the folder holds a credential file.
- By default kagglehub uploads: it creates the model and the variation if
  they are new and adds a version if they exist. `--license "Apache 2.0"`
  sets the licence.
- `--via cli` needs `model-metadata.json` and `model-instance-metadata.json`
  in the folder (`kaggle models init -p <dir>` and
  `kaggle models variations init -p <dir>` write templates). It creates only
  what does not exist yet: the model, the variation (which uploads the files
  as version 1), or a new version of an existing variation. Subfolders are
  uploaded as zip archives.
- New models are private.

The scripts are `scripts/model_download.py` and `scripts/model_publish.py`.

## References

- [kagglehub-models.md](references/kagglehub-models.md)
