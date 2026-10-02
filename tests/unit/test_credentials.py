"""Unit tests for skills/kaggle/shared/credentials.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shared import credentials


def _kaggle_dir() -> Path:
    path = Path.home() / ".kaggle"
    path.mkdir(exist_ok=True)
    return path


def test_nothing_configured_resolves_to_none():
    assert credentials.discover() == []
    assert credentials.resolve() is None
    assert credentials.bearer_token() == ""


def test_env_token_wins_over_the_token_file(monkeypatch):
    (_kaggle_dir() / "access_token").write_text("KGAT_from_file\n")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_from_env")
    cred = credentials.resolve()
    assert (cred.kind, cred.source, cred.secret) == (
        "api_token",
        "KAGGLE_API_TOKEN",
        "KGAT_from_env",
    )


def test_env_token_may_be_a_path_to_a_file(tmp_path, monkeypatch):
    token_file = tmp_path / "token.txt"
    token_file.write_text("KGAT_in_named_file\n")
    monkeypatch.setenv("KAGGLE_API_TOKEN", str(token_file))
    assert credentials.bearer_token() == "KGAT_in_named_file"


def test_token_file_and_txt_variant_are_found():
    (_kaggle_dir() / "access_token.txt").write_text("KGAT_txt")
    assert credentials.resolve().source == "~/.kaggle/access_token.txt"
    (_kaggle_dir() / "access_token").write_text("KGAT_plain")
    assert credentials.resolve().source == "~/.kaggle/access_token"


def test_token_does_not_need_a_kgat_prefix(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "CfDJ8-oauth-access-token")
    assert credentials.bearer_token() == "CfDJ8-oauth-access-token"


def test_legacy_key_from_env_and_from_kaggle_json(monkeypatch):
    (_kaggle_dir() / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k" * 32}))
    cred = credentials.resolve()
    assert (cred.kind, cred.source, cred.username) == ("legacy_key", "kaggle.json", "bob")
    monkeypatch.setenv("KAGGLE_USERNAME", "alice")
    monkeypatch.setenv("KAGGLE_KEY", "e" * 32)
    cred = credentials.resolve()
    assert (cred.source, cred.username) == ("KAGGLE_USERNAME + KAGGLE_KEY", "alice")


def test_kaggle_config_dir_is_honoured(tmp_path, monkeypatch):
    config = tmp_path / "cfg"
    config.mkdir()
    (config / "kaggle.json").write_text(json.dumps({"username": "carol", "key": "x"}))
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(config))
    assert credentials.resolve().username == "carol"


def test_malformed_kaggle_json_is_ignored():
    (_kaggle_dir() / "kaggle.json").write_text("not json")
    assert credentials.resolve() is None


def test_oauth_login_is_detected():
    (_kaggle_dir() / "credentials.json").write_text(
        json.dumps({"refresh_token": "KGRT_x", "username": "dave"})
    )
    cred = credentials.resolve()
    assert (cred.kind, cred.username, cred.secret) == ("oauth", "dave", "")


def test_discovery_order_matches_the_cli():
    home = _kaggle_dir()
    (home / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    (home / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k"}))
    (home / "access_token").write_text("KGAT_file")
    assert [c.kind for c in credentials.discover()] == ["api_token", "legacy_key", "oauth"]


def test_oauth_token_is_the_last_line_when_the_cli_prints_warnings_first(stub_kaggle):
    """Sending the whole output as a header would fail, and the error would quote the token."""
    (_kaggle_dir() / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    stub_kaggle(
        'echo "Warning: Looks like you are using an outdated version"\n'
        'echo "Warning: Your Kaggle API key is readable by other users on this system!"\n'
        'echo "oauth-access-token"\n'
    )
    assert credentials.bearer_token() == "oauth-access-token"


def test_cli_output_that_is_not_a_token_is_not_used(stub_kaggle):
    (_kaggle_dir() / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    stub_kaggle('echo "You must log in to Kaggle to print an access token."\n')
    assert credentials.oauth_access_token() == ""
    stub_kaggle('echo "token-then-nothing"\nexit 1\n')
    assert credentials.oauth_access_token() == ""


@pytest.mark.parametrize("value", ["two words", "line\nbreak", "tab\there", "", "caf\u00e9"])
def test_values_that_cannot_be_a_header_are_not_tokens(value, monkeypatch):
    assert credentials.usable_bearer(value) == ""
    monkeypatch.setenv("KAGGLE_MCP_TOKEN", value)
    assert credentials.bearer_token() == ""


def test_a_token_file_with_extra_lines_is_skipped_not_sent():
    (_kaggle_dir() / "access_token").write_text("KGAT_first\nsecond line pasted by mistake\n")
    assert credentials.bearer_token() == ""


def test_oauth_bearer_comes_from_the_cli(stub_kaggle):
    (_kaggle_dir() / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    stub_kaggle('[ "$1 $2" = "auth print-access-token" ] && echo "oauth-access-token"\n')
    assert credentials.bearer_token() == "oauth-access-token"


def test_oauth_token_is_preferred_to_the_legacy_key_as_a_bearer(stub_kaggle):
    home = _kaggle_dir()
    (home / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k" * 32}))
    (home / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    stub_kaggle('[ "$1 $2" = "auth print-access-token" ] && echo "oauth-access-token"\n')
    assert credentials.bearer_token() == "oauth-access-token"
    # The CLI itself still tries the legacy key first.
    assert credentials.resolve().kind == "legacy_key"


def test_legacy_key_is_the_last_resort_bearer(stub_kaggle):
    home = _kaggle_dir()
    (home / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k" * 32}))
    assert credentials.bearer_token() == "k" * 32
    (home / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    stub_kaggle("exit 1\n")
    assert credentials.bearer_token() == "k" * 32, "falls back when the CLI gives no token"


def test_mcp_token_override_wins(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_normal")
    monkeypatch.setenv("KAGGLE_MCP_TOKEN", "override")
    assert credentials.bearer_token() == "override"


def test_repr_never_shows_the_secret(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_super_secret_value")
    assert "KGAT_super_secret_value" not in repr(credentials.resolve())
    assert "KGAT_super_secret_value" not in str(credentials.discover())


def test_describe_token():
    assert credentials.describe_token("KGAT_abc") == "API token"
    assert credentials.describe_token("KGRT_abc") == "OAuth refresh token"
    assert credentials.describe_token("0123456789abcdef0123456789abcdef") == "legacy API key"
    assert credentials.describe_token("CfDJ8xyz") == "token"


def test_verify_needs_a_call_that_the_server_checks(stub_kaggle, tmp_path):
    """`config view` passes for a revoked legacy key; `quota` does not."""
    log = tmp_path / "calls"
    stub_kaggle(
        f'echo "$*" >> "{log}"\n'
        'case "$1" in\n'
        '  config) echo "- username: erin" ;;\n'
        "  quota) exit 0 ;;\n"
        "esac\n"
    )
    assert credentials.verify() == (True, "erin")
    assert log.read_text().splitlines() == ["config view", "quota"]


def test_verify_fails_for_a_key_the_server_no_longer_accepts(stub_kaggle):
    stub_kaggle(
        'case "$1" in\n'
        '  config) echo "- username: erin" ;;\n'
        '  quota) echo "Authentication required to call the Kaggle API."; exit 1 ;;\n'
        "esac\n"
    )
    assert credentials.verify() == (False, "")


def test_verify_fails_when_the_cli_cannot_authenticate(stub_kaggle):
    stub_kaggle('echo "Authentication required to call the Kaggle API."\nexit 1\n')
    assert credentials.verify() == (False, "")


def test_username_prefers_env_then_json_then_cli(stub_kaggle, monkeypatch):
    stub_kaggle('echo "- username: from-cli"\n')
    (_kaggle_dir() / "access_token").write_text("KGAT_x")
    assert credentials.username() == "from-cli"
    (_kaggle_dir() / "kaggle.json").write_text(json.dumps({"username": "from-json", "key": "k"}))
    assert credentials.username() == "from-json"
    monkeypatch.setenv("KAGGLE_USERNAME", "from-env")
    assert credentials.username() == "from-env"


def test_env_file_loads_only_kaggle_keys_without_overriding(tmp_path, monkeypatch):
    env_file = tmp_path / "kaggle.env"
    env_file.write_text(
        "# comment\n"
        'export KAGGLE_USERNAME="alice"\n'
        "KAGGLE_KEY='abc'\n"
        "KAGGLE_API_TOKEN=KGAT_from_file\n"
        "HTTPS_PROXY=http://evil.example:8080\n"
        "REQUESTS_CA_BUNDLE=/tmp/evil.pem\n"
        "PATH=/nonexistent\n"
        "KAGGLE_API_ENVIRONMENT=LOCALHOST\n"
        "KAGGLE_CLI_BIN=/tmp/not-kaggle\n"
        "KAGGLE_PUBLISH_ALLOW_SECRETS=1\n"
    )
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_already_set")
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    import os

    path_before = os.environ["PATH"]
    loaded = credentials.load_env_file(env_file)
    assert sorted(loaded) == ["KAGGLE_KEY", "KAGGLE_USERNAME"]
    assert os.environ["KAGGLE_USERNAME"] == "alice"
    assert os.environ["KAGGLE_KEY"] == "abc"
    assert os.environ["KAGGLE_API_TOKEN"] == "KGAT_already_set"
    assert "HTTPS_PROXY" not in os.environ and "REQUESTS_CA_BUNDLE" not in os.environ
    for name in ("KAGGLE_API_ENVIRONMENT", "KAGGLE_CLI_BIN", "KAGGLE_PUBLISH_ALLOW_SECRETS"):
        assert name not in os.environ, f"{name} must not be taken from an env file"
    assert os.environ["PATH"] == path_before


def test_no_env_file_is_read_unless_named(tmp_path, monkeypatch):
    # A .env in the working directory and in HOME must both be ignored.
    Path(".env").write_text("KAGGLE_API_TOKEN=KGAT_cwd\n")
    (Path.home() / ".env").write_text("KAGGLE_API_TOKEN=KGAT_home\n")
    assert credentials.load_configured_env_file() == []
    assert credentials.bearer_token() == ""
    named = tmp_path / "named.env"
    named.write_text("KAGGLE_API_TOKEN=KGAT_named\n")
    monkeypatch.setenv("KAGGLE_ENV_FILE", str(named))
    assert credentials.load_configured_env_file() == ["KAGGLE_API_TOKEN"]
    assert credentials.bearer_token() == "KGAT_named"
