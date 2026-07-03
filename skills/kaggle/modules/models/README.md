# Models

Use this module for Kaggle model variation downloads and model publishing.

## Scripts

```bash
python3 modules/models/scripts/kagglehub_download.py owner/model/framework/variation
bash modules/models/scripts/cli_download.sh owner/model/framework/variation ./model
python3 modules/models/scripts/kagglehub_publish.py owner/model/framework/variation ./model "Version notes"
bash modules/models/scripts/cli_publish.sh ./model owner/model/framework/variation
```

Publishing creates or updates account-visible model resources and requires
explicit user intent.

## References

- [kagglehub-models.md](references/kagglehub-models.md)
