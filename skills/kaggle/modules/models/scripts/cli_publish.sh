#!/usr/bin/env bash
# Publish a private model with the kaggle CLI.
#
# Usage:
#   bash cli_publish.sh <model-dir> <owner/model/framework/variation> [version-notes]
#
# A Kaggle model has three levels, and the CLI creates them one at a time:
#   1. the model               (model-metadata.json,          kaggle models create)
#   2. a variation of it       (model-instance-metadata.json, kaggle models variations create)
#   3. versions of a variation (kaggle models variations versions create)
#
# This script looks up what already exists and runs only the missing steps.
# Creating a variation uploads the files as its first version, so a new
# version is created only when the variation is already there.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_publish.sh <model-dir> <owner/model/framework/variation> [version-notes]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 2 ]]; then
    usage >&2
    exit 2
fi

DIR="$1"
MODEL_HANDLE="$2"
NOTES="${3:-Upload via kaggle-cli}"
PART='[A-Za-z0-9][A-Za-z0-9._-]*'

if [[ ! "${MODEL_HANDLE}" =~ ^${PART}/${PART}/${PART}/${PART}$ ]]; then
    echo "[FAIL] model handle is not in the expected form" >&2
    echo "       expected owner/model/framework/variation" >&2
    exit 2
fi
MODEL_REF="$(printf '%s' "${MODEL_HANDLE}" | cut -d/ -f1-2)"

if [ ! -f "${DIR}/model-metadata.json" ]; then
    echo "No model-metadata.json in ${DIR}; writing a template."
    kaggle_run models.init models init -p "${DIR}"
    echo "Edit ${DIR}/model-metadata.json, then run this script again."
    exit 1
fi
if [ ! -f "${DIR}/model-instance-metadata.json" ]; then
    echo "No model-instance-metadata.json in ${DIR}; writing a template."
    kaggle_run models.variations.init models variations init -p "${DIR}"
    echo "Edit ${DIR}/model-instance-metadata.json, then run this script again."
    exit 1
fi

preflight_upload "${DIR}"

LOOKUP_DIR="$(mktemp -d)"
trap 'rm -rf "${LOOKUP_DIR}"' EXIT

# `models get` without -p prints the model and exits 0 when it exists. With -p,
# kaggle 2.2.4 crashes while writing the metadata file of an existing model.
if kaggle_raw models get "${MODEL_REF}" >/dev/null 2>&1; then
    echo "--- Model ${MODEL_REF} exists ---"
else
    echo "--- Creating model ${MODEL_REF} ---"
    kaggle_run models.create models create -p "${DIR}"
fi

if kaggle_raw models variations get "${MODEL_HANDLE}" -p "${LOOKUP_DIR}" >/dev/null 2>&1; then
    echo "--- Variation exists; uploading a new version ---"
    # --dir-mode zip uploads subfolders too; the default skips them.
    kaggle_run models.versions.create models variations versions create "${MODEL_HANDLE}" \
        -p "${DIR}" "--version-notes=${NOTES}" --dir-mode zip
else
    echo "--- Creating variation ${MODEL_HANDLE} (uploads the files as version 1) ---"
    kaggle_run models.variations.create models variations create -p "${DIR}" --dir-mode zip
fi

echo "Model files uploaded. The model is private unless its metadata says otherwise."
