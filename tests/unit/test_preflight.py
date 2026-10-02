"""Unit tests for skills/kaggle/shared/preflight.py."""

from __future__ import annotations

import pytest

from shared import preflight


def _tree(root, names):
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    return root


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        ".env.local",
        "prod.env",
        "kaggle.json",
        "access_token",
        "access_token.txt",
        "credentials.json",
        ".netrc",
        "id_rsa",
        "id_ed25519",
        "server.pem",
        "cert.p12",
        "cert.pfx",
        "nested/deeper/.env",
    ],
)
def test_credential_like_files_are_found(tmp_path, name):
    assert preflight.find_secret_files(_tree(tmp_path, ["train.csv", name])) == [name]


@pytest.mark.parametrize(
    "name",
    [
        ".env.example",
        ".env.sample",
        ".env.template",
        "environment.yml",
        "tokens.csv",
        "access_token_stats.csv",
        "README.md",
        ".git/config.pem",
        "vendor/lib/.git/kaggle.json",
        ".cache/kaggle.json",
        ".huggingface/credentials.json",
    ],
)
def test_ordinary_files_and_folders_the_uploaders_skip_are_not_flagged(tmp_path, name):
    assert preflight.find_secret_files(_tree(tmp_path, [name])) == []


@pytest.mark.parametrize("name", ["vendor/.cache/kaggle.json", "a/b/.huggingface/.env"])
def test_cache_folders_below_the_top_are_uploaded_so_they_are_checked(tmp_path, name):
    """The uploaders leave out `.cache` and `.huggingface` only at the top of the folder."""
    assert preflight.find_secret_files(_tree(tmp_path, [name])) == [name]


def test_check_exit_codes(tmp_path, capsys, monkeypatch):
    clean = _tree(tmp_path / "clean", ["train.csv"])
    leaky = _tree(tmp_path / "leaky", ["train.csv", ".env", "sub/kaggle.json"])
    assert preflight.check(clean) == 0
    assert preflight.check(tmp_path / "missing") == 2
    assert preflight.check(leaky) == 5
    err = capsys.readouterr().err
    assert ".env" in err and "sub/kaggle.json" in err
    assert "<untrusted-content-" in err, "file names can come from a Kaggle download"

    monkeypatch.setenv("KAGGLE_PUBLISH_ALLOW_SECRETS", "1")
    assert preflight.check(leaky) == 0
    assert "uploading despite" in capsys.readouterr().err


def test_main_usage(tmp_path, capsys):
    assert preflight.main(["--help"]) == 0
    assert preflight.main([]) == 2
    assert preflight.main([str(_tree(tmp_path, ["a.csv"]))]) == 0
