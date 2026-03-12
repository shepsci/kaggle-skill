# kagglehub API Reference

> Official source: https://github.com/Kaggle/kagglehub
> PyPI: https://pypi.org/project/kagglehub/
> Current version: 1.0.0 (Feb 2026). Requires Python >= 3.10.

## Installation

```bash
uv pip install kagglehub                    # Base
uv pip install kagglehub[pandas-datasets]   # + Pandas adapter
uv pip install kagglehub[polars-datasets]   # + Polars adapter
uv pip install kagglehub[hf-datasets]       # + Hugging Face adapter
uv pip install kagglehub[signing]           # + Sigstore model signing
```

## Authentication

```python
import kagglehub

# Option 1: Interactive login
kagglehub.login()

# Option 2: Programmatic
from kagglehub.config import set_kaggle_credentials, set_kaggle_api_token
set_kaggle_credentials(username="...", api_key="...")
set_kaggle_api_token(api_token="...")

# Check who is logged in
kagglehub.whoami()  # Returns: {'username': '...'}
```

**Auth methods (checked in order):**
1. `KAGGLE_API_TOKEN` env var (new style)
2. `~/.kaggle/access_token` file
3. Google Colab secret `KAGGLE_API_TOKEN`
4. `KAGGLE_USERNAME` + `KAGGLE_KEY` env vars (legacy)
5. `~/.kaggle/kaggle.json` file (legacy)
6. Google Colab secrets `KAGGLE_USERNAME` + `KAGGLE_KEY` (legacy)

Inside Kaggle notebooks, authentication is automatic.

## All Functions

### dataset_download()

```python
kagglehub.dataset_download(
    handle: str,               # "owner/dataset" or "owner/dataset/versions/N"
    path: str | None = None,   # specific file within dataset
    force_download: bool = False,
    output_dir: str | None = None,  # custom dir (bypasses cache)
) -> str  # returns local path
```

### dataset_upload()

```python
kagglehub.dataset_upload(
    handle: str,                  # "owner/dataset" (no version)
    local_dataset_dir: str,
    version_notes: str = "",
    ignore_patterns: list[str] | str | None = None,
) -> None
```

Creates dataset if new; creates new version if exists. Default ignore: `.git/`, `.cache/`, `.huggingface/`.

**Note:** Unlike `model_upload()`, `dataset_upload()` does NOT accept a `license_name` parameter.

### dataset_load()

```python
kagglehub.dataset_load(
    adapter: KaggleDatasetAdapter,  # PANDAS, POLARS, or HUGGING_FACE
    handle: str,
    path: str,                      # file within dataset
    pandas_kwargs: Any = None,      # passed to pandas read_* method
    sql_query: str | None = None,   # for SQLite files
    hf_kwargs: Any = None,          # passed to Dataset.from_pandas()
    polars_frame_type: PolarsFrameType | None = None,  # LAZY_FRAME or DATA_FRAME
    polars_kwargs: Any = None,
) -> DataFrame | LazyFrame | Dataset
```

**Adapters:**
| Adapter | Returns | Install Extra |
|---------|---------|---------------|
| `KaggleDatasetAdapter.PANDAS` | pandas DataFrame | `[pandas-datasets]` |
| `KaggleDatasetAdapter.POLARS` | polars LazyFrame (default) or DataFrame | `[polars-datasets]` |
| `KaggleDatasetAdapter.HUGGING_FACE` | HF Dataset (via pandas) | `[hf-datasets]` |

**Supported formats:** CSV, TSV, JSON, JSONL, XML, Parquet, Feather, SQLite, Excel.

### model_download()

```python
kagglehub.model_download(
    handle: str,               # "owner/model/framework/variation" or with /version
    path: str | None = None,   # specific file
    force_download: bool = False,
    output_dir: str | None = None,
) -> str
```

### model_upload()

```python
kagglehub.model_upload(
    handle: str,                  # "owner/model/framework/variation" (no version)
    local_model_dir: str,
    license_name: str | None = None,  # e.g. "Apache 2.0"
    version_notes: str = "",
    ignore_patterns: list[str] | str | None = None,
    sigstore: bool = False,       # requires kagglehub[signing]
) -> None
```

### competition_download()

```python
kagglehub.competition_download(
    handle: str,               # competition slug
    path: str | None = None,
    force_download: bool = False,
    output_dir: str | None = None,
) -> str
```

### notebook_output_download()

```python
kagglehub.notebook_output_download(
    handle: str,               # "owner/notebook-slug"
    path: str | None = None,
    force_download: bool = False,
    output_dir: str | None = None,
) -> str
```

### login() / whoami()

```python
kagglehub.login(validate_credentials: bool = True) -> None
kagglehub.whoami(verbose: bool = True) -> dict  # {'username': '...'}
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `KAGGLE_API_TOKEN` | API token (new style) | — |
| `KAGGLE_USERNAME` | Legacy username | — |
| `KAGGLE_KEY` | Legacy API key | — |
| `KAGGLEHUB_CACHE` | Cache folder | `~/.cache/kagglehub/` |
| `KAGGLE_CONFIG_DIR` | Credentials folder | `~/.kaggle/` |
| `KAGGLEHUB_VERBOSITY` | Log level (debug/info/warning/error/critical) | `info` |

## Not Supported

- No kernel/notebook push, status, or output operations
- No competition submit
- No competition registration
- No benchmark operations
