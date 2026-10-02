# kagglehub Model Reference

Official source: https://github.com/Kaggle/kagglehub

## Install

```bash
python3 -m pip install "kagglehub>=1.0.2"
python3 -m pip install "kagglehub[signing]>=1.0.2"
```

Use 1.0.2 or later: earlier releases extracted tar archives without a path
check. Signatures below are from 1.0.2.

## Authentication

kagglehub checks `KAGGLE_API_TOKEN`, `~/.kaggle/access_token`, Colab secrets,
legacy `KAGGLE_USERNAME` plus `KAGGLE_KEY`, and `~/.kaggle/kaggle.json`.
Inside Kaggle notebooks, authentication is automatic. Public models download
without a credential; some need their license accepted on kaggle.com first.

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

The four-part handle downloads the latest version; add `/<number>` for a
specific one. An upload creates the model and the variation if they are new,
and a new version if they exist. New models are private.

Everything in the folder is uploaded except what `ignore_patterns` matches.
The skill's `model-publish` command refuses a folder that holds a credential
file.

Use `sigstore=True` only when `kagglehub[signing]` is installed and the user
has explicitly asked for signed publishing.
