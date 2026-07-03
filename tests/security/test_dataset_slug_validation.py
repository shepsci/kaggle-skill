"""cli_download.sh must reject dataset slugs that aren't owner/name with safe characters.

Without validation, a slug like `../foo/bar` or one containing shell
metacharacters could create files outside ./downloads/ or trigger unintended
behavior in kaggle-cli's --unzip step.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_DOWNLOAD = REPO_ROOT / "skills" / "kaggle" / "modules" / "datasets" / "scripts" / "cli_download.sh"


@pytest.mark.parametrize("bad_slug", [
    "../foo/bar",
    "foo/../bar",
    "foo/bar; rm -rf /tmp",
    "$(whoami)/dataset",
    "owner/dataset name with spaces",
    "owner|dataset",
    "owner",          # missing /
    "owner/",         # empty name
    "/dataset",       # empty owner
    "owner/dataset/extra",  # too many slashes
])
def test_cli_download_rejects_bad_slug(bad_slug):
    result = subprocess.run(
        ["bash", str(CLI_DOWNLOAD), bad_slug],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0, (
        f"slug {bad_slug!r} was accepted (rc=0). stdout={result.stdout!r} "
        f"stderr={result.stderr!r}. Validation in cli_download.sh is too permissive."
    )
    assert "not in the expected" in result.stderr or "not in the expected" in result.stdout


def test_cli_download_accepts_canonical_slug_form_in_validation_only():
    """A valid slug should pass the regex check (we don't actually invoke kaggle here).

    We don't want to hit the network or wait for kaggle-cli — kill the script
    fast and just confirm the validator did not reject the slug.
    """
    try:
        result = subprocess.run(
            ["bash", str(CLI_DOWNLOAD), "kaggle/meta-kaggle"],
            capture_output=True, text=True, timeout=2,
        )
        stderr = result.stderr
    except subprocess.TimeoutExpired as e:
        # Timing out is fine — it means the script got past the validator and
        # was waiting on kaggle-cli/network. The validator only fires
        # synchronously near the top.
        stderr = (e.stderr or b"").decode(errors="replace")

    assert "not in the expected" not in stderr, (
        f"valid slug 'kaggle/meta-kaggle' was rejected by the validator: {stderr}"
    )
