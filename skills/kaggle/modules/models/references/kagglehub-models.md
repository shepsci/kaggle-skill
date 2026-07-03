# kagglehub Model Reference

Official source: https://github.com/Kaggle/kagglehub

## Install

```bash
uv pip install kagglehub
uv pip install kagglehub[signing]
```

## Authentication

kagglehub checks `KAGGLE_API_TOKEN`, `~/.kaggle/access_token`, Colab secrets,
legacy `KAGGLE_USERNAME` plus `KAGGLE_KEY`, and `~/.kaggle/kaggle.json`.
Inside Kaggle notebooks, authentication is automatic.

## model_download()

```python
kagglehub.model_download(
    handle: str,               # "owner/model/framework/variation" or with /version
    path: str | None = None,   # optional file within the version
    force_download: bool = False,
    output_dir: str | None = None,
) -> str
```

## model_upload()

```python
kagglehub.model_upload(
    handle: str,                  # "owner/model/framework/variation"
    local_model_dir: str,
    license_name: str | None = None,
    version_notes: str = "",
    ignore_patterns: list[str] | str | None = None,
    sigstore: bool = False,
) -> None
```

Use `sigstore=True` only when `kagglehub[signing]` is installed and the user
has explicitly asked for signed publishing.
