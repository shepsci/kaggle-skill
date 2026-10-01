# kagglehub Dataset Reference

Official source: https://github.com/Kaggle/kagglehub

## Install

```bash
python3 -m pip install "kagglehub>=1.0.2"
python3 -m pip install "kagglehub[pandas-datasets]>=1.0.2"
python3 -m pip install "kagglehub[polars-datasets]>=1.0.2"
python3 -m pip install "kagglehub[hf-datasets]>=1.0.2"
```

Use 1.0.2 or later: earlier releases extracted tar archives without a path
check. Signatures below are from 1.0.2.

## Authentication

kagglehub checks these sources in order:

1. `KAGGLE_API_TOKEN`
2. `~/.kaggle/access_token`
3. Colab `KAGGLE_API_TOKEN` secret
4. `KAGGLE_USERNAME` plus `KAGGLE_KEY`
5. `~/.kaggle/kaggle.json`
6. Colab legacy username/key secrets

Inside Kaggle notebooks, authentication is automatic. Public datasets
download without a credential.

## dataset_download()

```python
kagglehub.dataset_download(
    handle: str,               # "owner/dataset" or "owner/dataset/versions/N"
    path: str | None = None,   # optional file within dataset
    force_download: bool = False,
    output_dir: str | None = None,
) -> str
```

## dataset_upload()

```python
kagglehub.dataset_upload(
    handle: str,                  # "owner/dataset"
    local_dataset_dir: str,
    version_notes: str = "",
    ignore_patterns: list[str] | str | None = None,
) -> None
```

Creates a dataset if the handle is new and creates a version when it already
exists. New datasets are private. Unlike model uploads, dataset uploads take no
license argument: passing `license_name` raises `TypeError`.

Everything in the folder is uploaded except what `ignore_patterns` matches.
The skill's `kagglehub_publish.py` refuses a folder that holds a credential
file.

## dataset_load()

```python
kagglehub.dataset_load(
    adapter: KaggleDatasetAdapter,
    handle: str,
    path: str,
    pandas_kwargs: Any = None,
    sql_query: str | None = None,
    hf_kwargs: Any = None,
    polars_frame_type: PolarsFrameType | None = None,
    polars_kwargs: Any = None,
) -> DataFrame | LazyFrame | Dataset
```

| Adapter | Returns | Install Extra |
|---|---|---|
| `KaggleDatasetAdapter.PANDAS` | pandas DataFrame | `[pandas-datasets]` |
| `KaggleDatasetAdapter.POLARS` | polars LazyFrame or DataFrame | `[polars-datasets]` |
| `KaggleDatasetAdapter.HUGGING_FACE` | Hugging Face Dataset | `[hf-datasets]` |

Supported formats include CSV, TSV, JSON, JSONL, XML, Parquet, Feather,
SQLite, Excel.

## Environment Variables

| Variable | Purpose |
|---|---|
| `KAGGLE_API_TOKEN` | API token |
| `KAGGLE_USERNAME` | Legacy username |
| `KAGGLE_KEY` | Legacy API key |
| `KAGGLEHUB_CACHE` | Cache folder |
| `KAGGLE_CONFIG_DIR` | Credentials folder |
| `KAGGLEHUB_VERBOSITY` | Log level |
