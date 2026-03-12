# kaggle-cli Command Reference

> Official source: https://github.com/Kaggle/kaggle-cli
> Docs: https://www.kaggle.com/docs/api
> Requires Python 3.11+

## Installation

```bash
uv pip install kaggle
```

## Authentication

**Option 1:** `export KAGGLE_API_TOKEN=xxx` (new style)
**Option 2:** `~/.kaggle/access_token` file
**Option 3:** `~/.kaggle/kaggle.json` with `{"username":"...","key":"..."}` + `chmod 600`
**Option 4:** `KAGGLE_USERNAME` + `KAGGLE_KEY` env vars (legacy)

## Competitions

```bash
kaggle competitions list [options]
  --group general|entered|inClass
  --category all|featured|research|recruitment|gettingStarted|masters|playground
  --sort-by grouped|prize|earliestDeadline|latestDeadline|numberOfTeams|recentlyCreated
  -p PAGE  -s SEARCH  -v (csv)

kaggle competitions files COMPETITION
  -v (csv)  -q  --page-token TOKEN  --page-size N

kaggle competitions download COMPETITION
  -f FILE  -p PATH  -w  -o (force)  -q

kaggle competitions submit COMPETITION -f FILE -m MESSAGE
  -k KERNEL  -v VERSION  -q  --sandbox

kaggle competitions submissions COMPETITION
  -v (csv)  -q

kaggle competitions leaderboard COMPETITION
  -s (show)  -d (download)  -p PATH  -v (csv)  -q
```

**Note:** No CLI command to "join" a competition. Accept rules at `kaggle.com/c/COMP/rules`.

## Datasets

```bash
kaggle datasets list [options]
  --sort-by hottest|votes|updated|active
  --file-type all|csv|sqlite|json|bigQuery
  --license all|cc|gpl|odb|other
  --tags TAG_IDS  -s SEARCH  -m (mine)  --user USER
  -p PAGE  -v (csv)  --max-size BYTES  --min-size BYTES

kaggle datasets files OWNER/DATASET
  -v (csv)  --page-token TOKEN  --page-size N

kaggle datasets download OWNER/DATASET
  -f FILE  -p PATH  -w  --unzip  -o (force)  -q

kaggle datasets init -p DIRECTORY

kaggle datasets create -p DIRECTORY
  -u (public)  -q  -t (keep-tabular)  -r skip|zip|tar

kaggle datasets version -p DIRECTORY -m "NOTES"
  -q  -t  -r skip|zip|tar  -d (delete-old-versions)

kaggle datasets metadata OWNER/DATASET [-p PATH] [--update]
kaggle datasets status OWNER/DATASET
kaggle datasets delete OWNER/DATASET [-y]
```

### dataset-metadata.json

```json
{
  "title": "My Dataset",
  "id": "username/my-dataset",
  "licenses": [{"name": "CC0-1.0"}],
  "subtitle": "20-80 chars (optional)",
  "keywords": ["tag1", "tag2"],
  "resources": [
    {"path": "file.csv", "description": "Description",
     "schema": {"fields": [{"name": "col", "type": "string"}]}}
  ]
}
```

**Licenses:** CC0-1.0, CC-BY-SA-3.0, CC-BY-SA-4.0, CC-BY-NC-SA-4.0, GPL-2.0, ODbL-1.0, DbCL-1.0, CC-BY-4.0, CC-BY-NC-4.0, Apache-2.0, GPL-3.0, and others.

## Kernels (Notebooks)

```bash
kaggle kernels list [options]
  -m (mine)  -p PAGE  --page-size N  -s SEARCH  -v (csv)
  --parent OWNER/KERNEL  --competition SLUG  --dataset OWNER/DATASET
  --user USER  --language all|python|r|sqlite|julia
  --kernel-type all|script|notebook
  --output-type all|visualizations|data
  --sort-by hotness|commentCount|dateCreated|dateRun|relevance|viewCount|voteCount

kaggle kernels files OWNER/KERNEL
  -v (csv)  --page-token TOKEN  --page-size N

kaggle kernels init -p DIRECTORY

kaggle kernels push -p DIRECTORY
  --accelerator ACCELERATOR_ID  -t TIMEOUT_SECONDS

kaggle kernels pull OWNER/KERNEL
  -p PATH  -w  -m (metadata)

kaggle kernels output OWNER/KERNEL
  -p PATH  -w  -o (force)  -q  --file-pattern REGEX

kaggle kernels status OWNER/KERNEL
kaggle kernels delete OWNER/KERNEL [-y]
```

### kernel-metadata.json

```json
{
  "id": "username/kernel-slug",
  "title": "Kernel Title",
  "code_file": "notebook.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": false,
  "enable_internet": true,
  "dataset_sources": ["owner/dataset"],
  "competition_sources": ["competition-slug"],
  "kernel_sources": ["owner/kernel"],
  "model_sources": ["owner/model/framework/variation/version"]
}
```

### Available Accelerators

NvidiaTeslaP100, NvidiaTeslaT4, NvidiaTeslaT4Highmem, NvidiaTeslaA100, NvidiaL4, NvidiaL4X1, NvidiaH100, NvidiaRtxPro6000, TpuV38, Tpu1VmV38, TpuV5E8, TpuV6E8.

## Models

```bash
kaggle models list [--owner OWNER] [--sort-by hotness|downloadCount|voteCount|notebookCount|createTime] [-s SEARCH] [--page-size N] [-v (csv)]
kaggle models get OWNER/MODEL
kaggle models init -p DIRECTORY
kaggle models create -p DIRECTORY
kaggle models update -p DIRECTORY
kaggle models delete OWNER/MODEL [-y]
```

### model-metadata.json

```json
{
  "ownerSlug": "username",
  "title": "Model Title",
  "slug": "model-slug",
  "isPrivate": true,
  "description": "Model card markdown",
  "licenseName": "Apache 2.0"
}
```

## Model Variations (Instances)

The CLI uses `models instances` as the primary command; `models variations` is accepted as an alias.

```bash
kaggle models instances init -p DIRECTORY
kaggle models instances create -p DIRECTORY [-q] [-r skip|zip|tar]
kaggle models instances get OWNER/MODEL/FRAMEWORK/VARIATION -p PATH
kaggle models instances files OWNER/MODEL/FRAMEWORK/VARIATION [-v] [--page-size N]
kaggle models instances update -p DIRECTORY
kaggle models instances delete OWNER/MODEL/FRAMEWORK/VARIATION [-y]
```

### model-instance-metadata.json

```json
{
  "ownerSlug": "username",
  "modelSlug": "model-slug",
  "instanceSlug": "variation-slug",
  "framework": "pyTorch",
  "overview": "Short description",
  "usage": "Usage markdown with ${VERSION_NUMBER}, ${VARIATION_SLUG}, ${FRAMEWORK}, ${PATH}",
  "licenseName": "Apache 2.0",
  "fineTunable": false,
  "trainingData": []
}
```

## Model Variation Versions

The CLI uses `models instances versions` as the primary command; `models variations versions` is accepted as an alias.

```bash
kaggle models instances versions create OWNER/MODEL/FRAMEWORK/VARIATION -p DIRECTORY -n "NOTES" [-q] [-r skip|zip|tar]
kaggle models instances versions download OWNER/MODEL/FRAMEWORK/VARIATION/VERSION [-p PATH] [--untar|--unzip] [-f] [-q]
kaggle models instances versions files OWNER/MODEL/FRAMEWORK/VARIATION/VERSION [-v] [--page-size N]
kaggle models instances versions delete OWNER/MODEL/FRAMEWORK/VARIATION/VERSION [-y]
```

## Config

```bash
kaggle config view
kaggle config set -n {competition|path|proxy} -v VALUE
kaggle config unset -n {competition|path|proxy}
```
