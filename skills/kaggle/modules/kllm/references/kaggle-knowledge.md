# Kaggle Platform — Comprehensive Knowledge Reference

> Official documentation: https://www.kaggle.com/docs
>
> This reference summarizes all major Kaggle docs subpages so that any LLM
> using the KLLM skill has expert-level Kaggle knowledge in context.

## Documentation Map

| Page | URL | Summary |
|------|-----|---------|
| Main docs | https://www.kaggle.com/docs | Landing page — links to all sections |
| Competitions | https://www.kaggle.com/docs/competitions | Competition types, formats, submissions, leaderboards, teams, medals |
| Competitions Setup | https://www.kaggle.com/docs/competitions-setup | How to host/configure competitions |
| Datasets | https://www.kaggle.com/docs/datasets | Creating, versioning, downloading, and sharing datasets |
| Notebooks | https://www.kaggle.com/docs/notebooks | Cloud Jupyter environment, hardware, quotas, Docker images |
| Models | https://www.kaggle.com/docs/models | Model hierarchy, frameworks, publishing, downloading |
| API | https://www.kaggle.com/docs/api | Public API / CLI reference |
| MCP Server | https://www.kaggle.com/docs/mcp | MCP endpoint for AI agents |
| Organizations | https://www.kaggle.com/docs/organizations | Organization profiles and member management |
| Packages | https://www.kaggle.com/docs/packages | Pre-installed packages and custom installs |
| TPU | https://www.kaggle.com/docs/tpu | TPU v3-8 usage with TF/PyTorch/JAX |
| Efficient GPU | https://www.kaggle.com/docs/efficient-gpu-usage | GPU tips, mixed precision, gradient checkpointing |

---

## 1. Competitions (https://www.kaggle.com/docs/competitions)

### Competition Types

| Type | Description | Prizes |
|------|-------------|--------|
| **Featured** | High-profile, company-sponsored. Prize pools up to $1M+. | Cash |
| **Research** | Experimental, novel scientific problems. | Usually none |
| **Playground** | Low-stakes learning environment. | Swag / small |
| **Getting Started** | Semi-permanent tutorials (e.g., Titanic, Housing Prices). | None |
| **Community** | User-created competitions. Anyone can host. | Varies |
| **Recruitment** | Corporate challenges; prize is a job interview. | Interview |

### Competition Formats

- **Standard:** Download data → build model locally → upload predictions CSV.
- **Code (Notebook-only):** All submissions from Kaggle Notebooks. Same hardware for all. Runtime limits, possible internet restrictions.
- **Two-Stage:** Stage 2 releases new test data; must submit in Stage 1 to access Stage 2.

### Submissions

- Evaluated by the competition's scoring metric (RMSE, AUC, F1, LogLoss, etc.).
- **Daily limit:** Typically 5/day (varies per competition). Team size does NOT increase this.
- Failed submissions (processing errors) do NOT count against the limit.
- Must accept competition rules before downloading data or submitting.

### Leaderboard System (Dual)

- **Public Leaderboard:** Scores on a subset of test data. Visible during competition.
- **Private Leaderboard:** Scores on the remaining test data. Determines final ranking after deadline. Overfitting risk between public and private.

### Teams

- Max team size varies per competition (defined in rules).
- **Team merging:** Allowed if merger deadline has not passed and merged size ≤ max.
- Teams can only disband if no submissions have been made.
- **Private sharing** of code/data outside teams is prohibited — all sharing must be public.

### Medals & Progression

| Tier | Requirement |
|------|-------------|
| Novice | Register on Kaggle |
| Contributor | Complete profile, verify phone (SMS), engage |
| Expert | 2 Bronze medals |
| Master | 1 Gold + 2 Silver |
| Grandmaster | 5 Gold (at least 1 solo gold) |

Medal thresholds scale with competition size: Gold ≈ top 10 + 0.2%, Silver ≈ top 5%, Bronze ≈ top 10%.

---

## 2. Competitions Setup (https://www.kaggle.com/docs/competitions-setup)

### Creating a Competition

Navigate to https://www.kaggle.com/competitions/new. Types: Community (free, self-service), InClass (educators), Featured/Sponsored (paid).

### Configuration

- **Overview/Description:** Problem statement, goals, evaluation criteria, timeline.
- **Data:** Upload train.csv, test.csv, sample_submission.csv. For code competitions, data at `/kaggle/input/`.
- **Evaluation Metric:** The heart of the competition. Choose metric (RMSE, AUC, F1, etc.), upload solution file, set public/private split ratio. Custom metrics supported.
- **Scoring & Team Settings:** Max team size, daily submission limit, final submission selection.
- **Access:** Anyone / only with link / restricted email list (e.g., `@school.edu`).
- **Code Competition Toggle:** "Enable Notebooks and Models" — all submissions via Kaggle Notebooks.

### Public/Private Split

The solution file is split into public (shown during competition) and private (final ranking). Hosts can set the ratio or use a "Usage" column with "Private"/"Public" values.

---

## 3. Datasets (https://www.kaggle.com/docs/datasets)

### Creating Datasets

- **Web UI:** Datasets → New Dataset → drag-and-drop → set title, license, visibility.
- **CLI:** `kaggle datasets init -p dir` → edit metadata → `kaggle datasets create -p dir --dir-mode zip`.
- **kagglehub:** `kagglehub.dataset_upload("user/slug", "./dir", license_name="CC0-1.0")`.
- Sources: local files, remote URLs, GitHub repos, notebook outputs. Cannot mix source types.

### Metadata (`dataset-metadata.json`)

Follows Data Package spec. Required fields: `title`, `id` (`username/slug`), `licenses`. Optional: `subtitle` (20-80 chars), `keywords` (existing Kaggle tags), `resources` (file descriptions + schemas).

### Versioning

`kaggle datasets version -p dir -m "message"` — the `id` in metadata must match existing dataset.

### Size Limits

| Limit | Value |
|-------|-------|
| Public dataset | 100 GB |
| Private storage quota | ~107 GB per account |
| API per-file upload | ~2 GB (fixed in CLI v1.3.7) |

### Available Licenses

CC0-1.0, CC-BY-SA-3.0, CC-BY-SA-4.0, CC-BY-NC-SA-4.0, GPL-2.0, ODbL-1.0, DbCL-1.0, CC-BY-4.0, CC-BY-NC-4.0, Apache-2.0, GPL-3.0, and others.

### Progression

Expert: 3 Bronze. Master: 1 Gold + 4 Silver. Grandmaster: 5 Gold + 5 Silver.

---

## 4. Notebooks (https://www.kaggle.com/docs/notebooks)

### Hardware

| Resource | CPU | GPU |
|----------|-----|-----|
| CPU Cores | 4 | 4 |
| RAM | ~16 GB | ~29 GB |
| Disk (`/kaggle/working`) | 20 GB | 20 GB |

### Accelerators

| Accelerator | Best For |
|-------------|----------|
| None (CPU) | Data preprocessing, simple tasks |
| GPU P100 (16 GB VRAM) | Smaller models, PyTorch, experimentation |
| GPU T4 x2 (16 GB each) | Multi-GPU, fine-tuning BERT/ResNet |
| TPU VM v3-8 | Large Transformers, vision/NLP at scale |

Enable via Settings → Accelerator dropdown.

### Quotas

| Resource | Limit |
|----------|-------|
| GPU weekly | 30 hours/week |
| TPU weekly | 20 hours/week |
| CPU session | 12 hours max |
| GPU session | 12 hours max |
| TPU session | 9 hours max |
| Disk | 20 GB (`/kaggle/working`) |

Phone (SMS) verification required for GPU/TPU access.

### Languages & Docker

- **Python:** Docker image `kaggle/python` (GitHub: Kaggle/docker-python).
- **R:** Docker image `kaggle/rstats` (GitHub: Kaggle/docker-rstats).
- Kernel types: `notebook` (Jupyter) or `script` (standalone).

### Custom Packages

- **With internet:** `!pip install <package>` in a cell.
- **Without internet (offline competitions):** Download `.whl` files locally, upload as dataset, install from `/kaggle/input/`: `!pip install --no-index --find-links /kaggle/input/wheels/ package`.

### Saving

- **Auto-save:** Edits saved to draft automatically.
- **Save & Run All (Commit):** Runs all cells, saves output, creates a version.
- Only `/kaggle/working` persists. Content outside is lost on session end.
- Collaborators cannot edit simultaneously (unlike Google Colab).

### Data Access

- Competition data at `/kaggle/input/`.
- Attach datasets, models, or notebook outputs via "Add Data" sidebar.

### Progression

Expert: 5 Bronze. Master: 10 Silver. Grandmaster: 15 Gold.

---

## 5. Models (https://www.kaggle.com/docs/models)

### Hierarchy

```
Model → Framework → Variation → Version
```

Handle format: `owner/model/framework/variation` (e.g., `google/gemma/transformers/2b`).
Notebook path: `/kaggle/input/<model_slug>/<framework>/<variation>/<version>/`.

### Supported Frameworks

tensorFlow1, tensorFlow2, tfLite, tfJs, pyTorch, jax, coral, Keras.

### Publishing Models

1. **Web UI:** Models → New Model → fill metadata → upload files.
2. **kagglehub:** `kagglehub.model_upload("user/model/framework/variation", "./dir", license_name="Apache 2.0")`.
3. **CLI:** `kaggle models init` → `kaggle models create` → `kaggle models variations versions create`.
4. **KerasHub:** `keras_hub.upload_preset(uri="kaggle://user/model/Keras/variation", preset_dir="./dir")`.

### Metadata Files

- `model-metadata.json`: ownerSlug, title, slug, isPrivate, description (model card markdown), licenseName.
- `model-instance-metadata.json`: ownerSlug, modelSlug, instanceSlug, framework, overview, usage, licenseName, fineTunable, trainingData, modelInstanceType, baseModelInstance.

### Template Variables (for usage docs)

`${VERSION_NUMBER}`, `${VARIATION_SLUG}`, `${FRAMEWORK}`, `${PATH}`, `${FILEPATH}`, `${URL}`.

### Model Instance Types

- **Base Model:** Original standalone model.
- **Internal Variant:** Derived from another Kaggle model.
- **External Variant:** Derived from a model hosted elsewhere.

---

## 6. API / CLI (https://www.kaggle.com/docs/api, https://github.com/Kaggle/kaggle-cli)

### Installation

```bash
pip install kaggle    # Requires Python 3.11+
```

### Authentication

1. **Env var:** `export KAGGLE_API_TOKEN=xxx` (recommended) or `KAGGLE_USERNAME`/`KAGGLE_KEY` (legacy).
2. **Token file:** `~/.kaggle/access_token` (recommended file-based method).
3. **Legacy JSON:** `~/.kaggle/kaggle.json` with `{"username":"...","key":"..."}`. Must be `chmod 600`.

Generate tokens at [kaggle.com/settings](https://www.kaggle.com/settings):
- **"Generate New Token"** under "API Tokens (Recommended)" → creates named Access tokens.
- **"Create Legacy API Key"** under "Legacy API Credentials" → downloads `kaggle.json` (deprecated).

### Rate Limits

Kaggle uses dynamic rate limiting on both the API and website. If you get HTTP 429
("Too many requests"), wait a few minutes and retry. Check your code for unintended
loops or redundant calls.

### OAuth 2.0 Provider API

Kaggle implements OAuth 2.0 Authorization Code flow with PKCE for third-party apps:

**Endpoints:**
- Discovery: `GET https://www.kaggle.com/.well-known/oauth-authorization-server`
- Authorization: `GET https://www.kaggle.com/api/v1/oauth2/authorize`
- Token: `POST https://www.kaggle.com/api/v1/oauth2/token`
- Introspection: `POST https://www.kaggle.com/api/v1/oauth2/introspect`

**Token formats:** Access tokens use `kagat_` prefix (3-hour expiry). Refresh tokens use `kagrt_` prefix.

**Scopes:** `datasets.get:*`, `datasets.create:*`, `datasets.update:*`, `models.get:*`, `models.download:*`, `kernels.list:*`, `kernels.pull:*`, `kernels.push:*`, `competitions.list:*`, `competitions.submit:*`.

**Roles (bundle permissions):** `datasets.viewer`, `datasets.editor`, `models.viewer`, `resources.admin`.

**Client types:** Public clients (PKCE required, localhost redirect only) and Organization clients (`org:<slug>`, HTTPS redirect allowed). Contact Kaggle team to register clients.

### Command Groups

```
kaggle competitions {list, files, download, submit, submissions, leaderboard}
kaggle datasets     {list, files, download, create, version, init, metadata, status, delete}
kaggle kernels      {list, files, init, push, pull, output, status, delete}
kaggle models       {list, get, init, create, update, delete}
kaggle models variations       {init, create, get, update, delete, files}
kaggle models variations versions {create, download, delete, files}
kaggle config       {view, set, unset}
```

### Key Metadata Files

- **dataset-metadata.json:** title, id, licenses (required). Optional: subtitle, keywords, resources.
- **kernel-metadata.json:** id, title, code_file, language, kernel_type (required). Optional: is_private, enable_gpu, enable_internet, dataset_sources, competition_sources, model_sources.
- **model-metadata.json:** ownerSlug, title, slug, isPrivate, description, licenseName.
- **model-instance-metadata.json:** ownerSlug, modelSlug, instanceSlug, framework, overview, usage, licenseName.

### Available Accelerators (for `kaggle kernels push --accelerator`)

NvidiaTeslaP100, NvidiaTeslaT4, NvidiaTeslaT4Highmem, NvidiaTeslaA100, NvidiaL4, NvidiaL4X1, NvidiaH100, NvidiaRtxPro6000, TpuV38, Tpu1VmV38, TpuV5E8, TpuV6E8.

### Config Options

`kaggle config set -n {competition|path|proxy} -v VALUE`.

---

## 7. MCP Server (https://www.kaggle.com/docs/mcp)

### Endpoint

```
https://www.kaggle.com/mcp
```

Protocol: Streamable HTTP (MCP standard). Auth: API token via `Authorization: Bearer <api_token>` (use token from "Generate New Token" at kaggle.com/settings).

### Client Configuration

**Claude Code (CLI):**
```bash
claude mcp add kaggle --transport http https://www.kaggle.com/mcp \
  --header "Authorization: Bearer <your_api_key>"
```

**Generic MCP client (gemini-cli, Claude Desktop, Cursor, etc.):**
```json
{
  "mcpServers": {
    "kaggle": {
      "url": "https://www.kaggle.com/mcp",
      "headers": {
        "Authorization": "Bearer <your_api_key>"
      }
    }
  }
}
```

### Available Tool Categories

- **Competitions:** list, details, download files, list files, submit, submissions, leaderboard.
- **Datasets:** list, list files, download, metadata, create new, create version, status, init metadata, update metadata.
- **Kernels/Notebooks:** list, list files, output, pull, status, init metadata, push.
- **Models:** list, get, init metadata, create, update, delete. Plus instance (variation) and version subtools.
- **Config:** view, set, unset, path.
- **Auth:** authenticate tool.

Use `tools/list` for discovery of exact tool names.

---

## 8. kagglehub (https://github.com/Kaggle/kagglehub)

### Installation

```bash
pip install kagglehub                           # Base
pip install kagglehub[pandas-datasets]          # + Pandas adapter
pip install kagglehub[polars-datasets]          # + Polars adapter
pip install kagglehub[hf-datasets]              # + Hugging Face adapter
```

Current version: 1.0.0 (Feb 2026). Requires Python ≥ 3.10.

### Authentication

`kagglehub.login()` (interactive), `KAGGLE_API_TOKEN` env var, `~/.kaggle/access_token`, `~/.kaggle/kaggle.json` (legacy), `KAGGLE_USERNAME`/`KAGGLE_KEY` env vars (legacy), Google Colab secrets.

### All Functions

| Function | Purpose |
|----------|---------|
| `kagglehub.login()` | Interactive auth |
| `kagglehub.whoami()` | Show authenticated user |
| `kagglehub.dataset_download(handle, path=, force_download=, output_dir=)` | Download dataset |
| `kagglehub.dataset_upload(handle, local_dataset_dir, version_notes=, license_name=, ignore_patterns=)` | Upload/version dataset |
| `kagglehub.dataset_load(adapter, handle, path, pandas_kwargs=, sql_query=, hf_kwargs=, polars_frame_type=, polars_kwargs=)` | Load dataset into DataFrame |
| `kagglehub.model_download(handle, path=, force_download=, output_dir=)` | Download model |
| `kagglehub.model_upload(handle, local_model_dir, license_name=, version_notes=, ignore_patterns=, sigstore=)` | Upload/version model |
| `kagglehub.competition_download(handle, path=, force_download=, output_dir=)` | Download competition data |
| `kagglehub.notebook_output_download(handle, path=, force_download=, output_dir=)` | Download notebook output |

### Dataset Adapters

| Adapter | Returns | Formats |
|---------|---------|---------|
| `KaggleDatasetAdapter.PANDAS` | DataFrame | CSV, TSV, JSON, JSONL, XML, Parquet, Feather, SQLite, Excel |
| `KaggleDatasetAdapter.POLARS` | LazyFrame/DataFrame | CSV, TSV, JSON, JSONL, Parquet, Feather, SQLite, Excel |
| `KaggleDatasetAdapter.HUGGING_FACE` | HF Dataset | Same as Pandas (built on top) |

### Not Supported

- No kernel/notebook push, status, or output operations.
- No competition submit.
- No competition registration.
- No benchmark operations.

### Environment Variables

`KAGGLE_API_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, `KAGGLEHUB_CACHE` (default `~/.cache/kagglehub/`), `KAGGLE_CONFIG_DIR` (default `~/.kaggle/`), `KAGGLEHUB_VERBOSITY` (debug/info/warning/error/critical).

---

## 9. Organizations (https://www.kaggle.com/docs/organizations)

- Create at https://www.kaggle.com/organizations/new.
- Roles: **Admin** (full control) and **Member** (can contribute under org brand).
- Admins can invite/remove members, manage settings.
- Orgs can publish datasets, notebooks, and competitions under a shared identity.

---

## 10. Packages (https://www.kaggle.com/docs/packages)

- Kaggle notebooks come with hundreds of pre-installed packages.
- Docker images: `kaggle/python` (GitHub: Kaggle/docker-python) and `kaggle/rstats` (GitHub: Kaggle/docker-rstats).
- Package list: `kaggle_requirements.txt` in the docker-python repo.
- Custom packages: `!pip install X` (internet required). Offline: upload wheels as dataset.
- To run locally: `docker pull kaggle/python`.

---

## 11. TPU (https://www.kaggle.com/docs/tpu)

### Hardware

TPU VM v3-8: 4 chips × 2 TensorCore cores = 8 logical TPU devices. Preinstalled: Python 3.10, PyTorch/XLA 2.1.

### Quota

20 hours/week, 9-hour max session.

### TensorFlow

```python
tpu = tf.distribute.cluster_resolver.TPUClusterResolver(tpu="local")
tf.config.experimental_connect_to_cluster(tpu)
tf.tpu.experimental.initialize_tpu_system(tpu)
strategy = tf.distribute.TPUStrategy(tpu)
with strategy.scope():
    model = create_model()
```

### PyTorch (via PyTorch/XLA)

```python
import torch_xla.core.xla_model as xm
device = xm.xla_device()
model = model.to(device)
```

Distributed: use `xmp.spawn()`. Broadcast params from replica 0: `xm.broadcast_master_param(model)`.

### JAX

Native TPU support. Use `bfloat16` (larger range than float16, no loss scaling needed).

---

## 12. Efficient GPU Usage (https://www.kaggle.com/docs/efficient-gpu-usage)

### Hardware

| GPU | VRAM | Best For |
|-----|------|----------|
| NVIDIA Tesla P100 | 16 GB | Training complex models |
| NVIDIA T4 x2 | 16 GB each | Multi-GPU, inference |

### Quota

30 hours/week GPU.

### Tips

1. **Mixed precision:** TF: `mixed_precision.set_global_policy('mixed_float16')`. PyTorch: `torch.cuda.amp.autocast()`.
2. **Batch size:** Powers of 2 (8, 16, 32...). For FP16, multiples of 8.
3. **Gradient accumulation:** Simulate larger batches without extra memory.
4. **Gradient checkpointing:** ~20% slower but large memory savings.
5. **Monitor:** `!nvidia-smi` or `pynvml`.
6. **Data loading:** `num_workers > 0`, `pin_memory=True` in PyTorch DataLoaders.
7. **Only enable GPU when needed** — turn off during exploration/preprocessing.

---

## 13. Progression System (https://www.kaggle.com/progression)

Five tiers across four categories:

| Tier | Competitions | Datasets | Notebooks | Discussions |
|------|-------------|----------|-----------|-------------|
| Novice | Register | Register | Register | Register |
| Contributor | Profile + SMS + engage | Same | Same | Same |
| Expert | 2 Bronze | 3 Bronze | 5 Bronze | 50 Bronze |
| Master | 1 Gold + 2 Silver | 1 Gold + 4 Silver | 10 Silver | 200 total (50 Silver) |
| Grandmaster | 5 Gold (1 solo) | 5 Gold + 5 Silver | 15 Gold | 500 total (50 Gold) |

---

## 14. Persona Identity Verification

Required for prize-eligible competitions. Uses third-party service **Persona**.

1. Navigate to prize competition → verification prompt.
2. Provide government-issued ID (passport/driver's license).
3. Complete selfie verification.
4. Wait for automated processing.

Only available via web UI. No programmatic method exists.
