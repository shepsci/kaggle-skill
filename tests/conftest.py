"""Shared pytest fixtures and CLI flags for the kaggle-skill test suite."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Make `from shared.mcp_client import ...` work from tests
import sys

sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))


def pytest_addoption(parser):
    parser.addoption(
        "--run-live", action="store_true", default=False,
        help="Run tests marked @pytest.mark.live (require KAGGLE_API_TOKEN)",
    )
    parser.addoption(
        "--run-destructive", action="store_true", default=False,
        help="Run tests marked @pytest.mark.destructive (write to Kaggle account)",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        skip_live = pytest.mark.skip(reason="needs --run-live and KAGGLE_API_TOKEN")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
    if not config.getoption("--run-destructive"):
        skip_dest = pytest.mark.skip(reason="needs --run-destructive")
        for item in items:
            if "destructive" in item.keywords:
                item.add_marker(skip_dest)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def mcp_response(fixtures_dir: Path):
    """Load a canned MCP JSON-RPC response by name (without .json)."""
    def _load(name: str) -> dict:
        return json.loads((fixtures_dir / "mcp_responses" / f"{name}.json").read_text())
    return _load


@pytest.fixture
def tmp_kaggle_home(tmp_path, monkeypatch) -> Path:
    """Synthesize ~/.kaggle/ with a valid kaggle.json under a tmp HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    return tmp_path


@pytest.fixture
def kgat_token() -> str:
    """KGAT token from env, ~/.kaggle/access_token, or skip if absent.

    Mirrors the credential-discovery order in shared.mcp_client.resolve_token:
    explicit MCP override → KGAT env → access_token file. Env vars never need
    to be set for tests if the token lives in the documented file location.
    """
    from shared.mcp_client import resolve_token  # noqa: WPS433

    tok = resolve_token()
    if not tok.startswith("KGAT_"):
        pytest.skip(
            "KGAT_-prefixed token not found in KAGGLE_MCP_TOKEN, "
            "KAGGLE_API_TOKEN, or ~/.kaggle/access_token"
        )
    return tok


@pytest.fixture
def legacy_key() -> str:
    """Legacy 32-char hex key from env, or skip if absent."""
    key = os.getenv("KAGGLE_KEY", "")
    if not key or key.startswith("KGAT_"):
        pytest.skip("KAGGLE_KEY (legacy hex) not set")
    return key


@pytest.fixture
def competition_slugs() -> dict:
    return {
        "hackathon": "kaggle-measuring-agi",
        "classic": "titanic",
        "playground": "playground-series-s6e2",
    }
