"""phase_2_competition.py must reject zip members that escape the destination dir.

Kaggle is the source of competition zips, but our threat model treats
external content as untrusted. A malicious or malformed zip could carry
member names like `../../../../../tmp/pwn` and `extractall` would happily
write outside the intended directory ("zip slip", CVE-2018-1000544 family).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "scripts"))

PHASE_2 = REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "scripts" / "phase_2_competition.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("phase_2_competition", PHASE_2)
    mod = importlib.util.module_from_spec(spec)
    # Module imports `badge_tracker` and `utils` from sibling files — sys.path was set above.
    spec.loader.exec_module(mod)
    return mod


def _build_zip(path: Path, members: dict[str, bytes]) -> Path:
    """Create a zip file with the given member name → content mapping."""
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


def test_safe_extract_accepts_normal_member_names(tmp_path):
    mod = _load_module()
    zf = _build_zip(tmp_path / "ok.zip", {
        "submission.csv": b"id,target\n1,0\n",
        "subdir/file.txt": b"hello",
    })
    dest = tmp_path / "extracted"
    dest.mkdir()
    mod._safe_extract(zf, dest)
    assert (dest / "submission.csv").exists()
    assert (dest / "subdir" / "file.txt").exists()


def test_safe_extract_rejects_path_traversal_with_dotdot(tmp_path):
    mod = _load_module()
    zf = _build_zip(tmp_path / "evil.zip", {
        "../escape.txt": b"pwn",
    })
    dest = tmp_path / "extracted"
    dest.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        mod._safe_extract(zf, dest)
    assert not (tmp_path / "escape.txt").exists(), "file escaped destination!"


def test_safe_extract_rejects_absolute_path_member(tmp_path):
    mod = _load_module()
    target = tmp_path / "outside"
    zf = _build_zip(tmp_path / "evil2.zip", {
        f"{target}/pwn.txt": b"pwn",
    })
    dest = tmp_path / "extracted"
    dest.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        mod._safe_extract(zf, dest)
    assert not target.exists()


def test_safe_extract_rejects_deep_traversal(tmp_path):
    mod = _load_module()
    zf = _build_zip(tmp_path / "deep.zip", {
        "subdir/../../escape.txt": b"pwn",
    })
    dest = tmp_path / "extracted"
    dest.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        mod._safe_extract(zf, dest)
    assert not (tmp_path / "escape.txt").exists()
