"""Tests for the setup scripts: the credential checker, setup_env.sh, network_check.sh."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
from conftest import write_stub

CHECKER = "skills/kaggle/modules/setup/scripts/check_all_credentials.py"
SETUP_ENV = "skills/kaggle/modules/setup/scripts/setup_env.sh"
NETWORK_CHECK = "skills/kaggle/modules/setup/scripts/network_check.sh"

TOKEN = "KGAT_0123456789abcdef0123456789abcdef"


def _kaggle_dir() -> Path:
    path = Path.home() / ".kaggle"
    path.mkdir(exist_ok=True)
    return path


def _snapshot(root: Path) -> dict[str, tuple[int, int, bytes]]:
    """Path -> (mode, mtime_ns, content) for every file under ``root``."""
    return {
        str(p.relative_to(root)): (p.stat().st_mode, p.stat().st_mtime_ns, p.read_bytes())
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# ── check_all_credentials.py ─────────────────────────────────────────────────


def test_checker_reports_nothing_found_and_how_to_fix_it(run_script):
    result = run_script(CHECKER)
    assert result.returncode == 1
    assert "No Kaggle credentials found" in result.stdout
    assert "kaggle auth login" in result.stdout


def test_checker_finds_each_kind_in_the_order_the_cli_uses(run_script):
    home = _kaggle_dir()
    (home / "credentials.json").write_text(
        json.dumps({"refresh_token": "KGRT_x", "username": "dave"})
    )
    (home / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k" * 32}))
    (home / "access_token").write_text(TOKEN)
    for name in ("credentials.json", "kaggle.json", "access_token"):
        (home / name).chmod(0o600)
    result = run_script(CHECKER, "--json")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert [c["kind"] for c in report["credentials"]] == ["api_token", "legacy_key", "oauth"]
    assert report["active"] == {"kind": "api_token", "source": "~/.kaggle/access_token"}
    assert report["warnings"] == []
    assert report["verified"] is None


def test_oauth_login_alone_counts_as_configured(run_script):
    (_kaggle_dir() / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    (_kaggle_dir() / "credentials.json").chmod(0o600)
    result = run_script(CHECKER)
    assert result.returncode == 0
    assert "[OK] OAuth login: found" in result.stdout


def test_kgat_token_is_labelled_as_the_current_token_type(run_script):
    result = run_script(CHECKER, env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0
    assert "[OK] API token: found (from KAGGLE_API_TOKEN)" in result.stdout
    assert "Legacy" not in result.stdout


@pytest.mark.parametrize("args", [(), ("--json",), ("--verify",), ("--verify", "--json")])
def test_checker_never_prints_a_secret(args, run_script, stub_kaggle):
    stub_kaggle('echo "- username: erin"\n')
    key = "f" * 32
    (_kaggle_dir() / "kaggle.json").write_text(json.dumps({"username": "bob", "key": key}))
    result = run_script(CHECKER, *args, env={"KAGGLE_API_TOKEN": TOKEN})
    assert TOKEN not in result.stdout + result.stderr
    assert key not in result.stdout + result.stderr


def test_checker_changes_nothing_on_disk(run_script):
    """A check must not write. Earlier versions copied a token into ~/.kaggle."""
    home = _kaggle_dir()
    (home / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k" * 32}))
    Path(".env").write_text(f"KAGGLE_API_TOKEN={TOKEN}\n")
    before_home, before_cwd = _snapshot(Path.home()), _snapshot(Path.cwd())
    for args in ((), ("--json",)):
        run_script(CHECKER, *args, env={"KAGGLE_API_TOKEN": TOKEN})
    assert _snapshot(Path.home()) == before_home
    assert _snapshot(Path.cwd()) == before_cwd
    assert not (home / "access_token").exists()


def test_checker_ignores_dotenv_files_it_was_not_pointed_at(run_script):
    Path(".env").write_text(f"KAGGLE_API_TOKEN={TOKEN}\n")
    assert run_script(CHECKER).returncode == 1

    named = Path("kaggle.env")
    named.write_text(f"KAGGLE_API_TOKEN={TOKEN}\nHTTPS_PROXY=http://evil.example\n")
    result = run_script(CHECKER, "--json", env={"KAGGLE_ENV_FILE": str(named.resolve())})
    assert result.returncode == 0
    assert json.loads(result.stdout)["active"]["source"] == "KAGGLE_API_TOKEN"


def test_checker_warns_about_readable_credential_files_and_dead_variables(run_script):
    token_file = _kaggle_dir() / "access_token"
    token_file.write_text(TOKEN)
    token_file.chmod(0o644)
    result = run_script(CHECKER, env={"KAGGLE_TOKEN": "something"})
    assert result.returncode == 0
    assert "readable by other users (mode 644)" in result.stdout
    assert "KAGGLE_TOKEN is set, but no Kaggle tool reads it" in result.stdout


def test_found_is_not_reported_as_accepted(run_script):
    result = run_script(CHECKER, env={"KAGGLE_API_TOKEN": TOKEN})
    assert "Found is not the same as accepted" in result.stdout
    assert "Verified" not in result.stdout


def test_verify_reports_the_account_kaggle_accepted(run_script, stub_kaggle):
    stub_kaggle('case "$1" in config) echo "- username: erin" ;; esac\n')
    result = run_script(CHECKER, "--verify", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0
    assert "[OK] Verified: Kaggle accepted the credential as erin." in result.stdout


def test_verify_fails_for_a_revoked_legacy_key_that_config_view_still_accepts(
    run_script, stub_kaggle
):
    """`kaggle config view` does not contact the server for a legacy key."""
    (_kaggle_dir() / "kaggle.json").write_text(json.dumps({"username": "bob", "key": "k" * 32}))
    (_kaggle_dir() / "kaggle.json").chmod(0o600)
    stub_kaggle(
        'case "$1" in\n'
        '  config) echo "- username: bob" ;;\n'
        '  quota) echo "Authentication required to call the Kaggle API."; exit 1 ;;\n'
        "esac\n"
    )
    result = run_script(CHECKER, "--verify")
    assert result.returncode == 1
    assert "[FAIL] Kaggle did not accept what is configured." in result.stdout
    assert "Verified" not in result.stdout


def test_verify_fails_when_the_cli_cannot_sign_in(run_script, stub_kaggle):
    stub_kaggle('echo "401 Unauthorized" >&2\nexit 1\n')
    result = run_script(CHECKER, "--verify", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 1
    assert "[FAIL] Kaggle did not accept what is configured." in result.stdout


def test_token_that_looks_like_another_kind_is_pointed_out(run_script):
    result = run_script(CHECKER, env={"KAGGLE_API_TOKEN": "KGRT_refresh_token_value"})
    assert "looks like: OAuth refresh token" in result.stdout


# ── setup_env.sh ─────────────────────────────────────────────────────────────


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_setup_env_saves_the_token_with_private_permissions(run_script):
    result = run_script(SETUP_ENV, env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0, result.stderr
    token_file = Path.home() / ".kaggle" / "access_token"
    assert token_file.read_text() == TOKEN
    assert _mode(token_file) == 0o600
    assert _mode(token_file.parent) == 0o700
    assert TOKEN not in result.stdout + result.stderr


def test_setup_env_never_overwrites_an_existing_file(run_script):
    token_file = _kaggle_dir() / "access_token"
    token_file.write_text("KGAT_existing")
    result = run_script(SETUP_ENV, env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0
    assert token_file.read_text() == "KGAT_existing"
    assert "left unchanged" in result.stdout


def test_setup_env_writes_valid_legacy_json(run_script):
    result = run_script(SETUP_ENV, env={"KAGGLE_USERNAME": "alice", "KAGGLE_KEY": "e" * 32})
    assert result.returncode == 0, result.stderr
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    assert json.loads(kaggle_json.read_text()) == {"username": "alice", "key": "e" * 32}
    assert _mode(kaggle_json) == 0o600
    assert "e" * 32 not in result.stdout + result.stderr


def test_setup_env_refuses_values_that_would_break_the_json(run_script):
    result = run_script(SETUP_ENV, env={"KAGGLE_USERNAME": 'al"ice', "KAGGLE_KEY": "k"})
    assert result.returncode == 1
    assert not (Path.home() / ".kaggle" / "kaggle.json").exists()


def test_setup_env_with_nothing_configured_writes_nothing(run_script):
    result = run_script(SETUP_ENV)
    assert result.returncode == 0
    assert "kaggle auth login" in result.stdout
    assert not (Path.home() / ".kaggle").exists()


def test_setup_env_parses_the_env_file_and_never_runs_it(run_script, tmp_path):
    marker = tmp_path / "pwned"
    env_file = tmp_path / "kaggle.env"
    env_file.write_text(
        f"touch {marker}\n"
        f"KAGGLE_USERNAME=$(touch {marker})\n"
        f"PATH=/nonexistent\n"
        f"export KAGGLE_API_TOKEN='{TOKEN}'\n"
    )
    result = run_script(SETUP_ENV, env={"KAGGLE_ENV_FILE": str(env_file)})
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert (Path.home() / ".kaggle" / "access_token").read_text() == TOKEN


def test_setup_env_does_not_store_a_path_as_if_it_were_the_token(run_script, tmp_path):
    """KAGGLE_API_TOKEN may name a token file. The path itself is not a token."""
    token_file = tmp_path / "my-token"
    token_file.write_text(TOKEN)
    result = run_script(SETUP_ENV, env={"KAGGLE_API_TOKEN": str(token_file)})
    assert result.returncode == 0
    assert "names a token file" in result.stdout
    assert not (Path.home() / ".kaggle" / "access_token").exists()


def test_setup_env_reads_an_env_file_with_windows_line_ends(run_script, tmp_path):
    env_file = tmp_path / "kaggle.env"
    env_file.write_bytes(
        f'KAGGLE_API_TOKEN="{TOKEN}"\r\nKAGGLE_API_ENVIRONMENT=LOCALHOST\r\n'.encode()
    )
    result = run_script(SETUP_ENV, env={"KAGGLE_ENV_FILE": str(env_file)})
    assert result.returncode == 0, result.stderr
    assert (Path.home() / ".kaggle" / "access_token").read_text() == TOKEN


def test_setup_env_ignores_a_dotenv_it_was_not_pointed_at(run_script):
    Path(".env").write_text(f"KAGGLE_API_TOKEN={TOKEN}\n")
    result = run_script(SETUP_ENV)
    assert result.returncode == 0
    assert not (Path.home() / ".kaggle").exists()


def test_sourcing_setup_env_is_refused_and_leaves_the_shell_alone(repo_root):
    script = repo_root / SETUP_ENV
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{script}"; echo "rc=$?"; echo "still running"; set -o | grep errexit',
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "KAGGLE_API_TOKEN": TOKEN},
        check=False,
    )
    assert "rc=1" in result.stdout
    assert "still running" in result.stdout
    assert "errexit        \toff" in result.stdout or "errexit         off" in result.stdout
    assert "do not source it" in result.stderr
    assert not (Path.home() / ".kaggle").exists()


# ── network_check.sh ─────────────────────────────────────────────────────────


def _stub_curl(hermetic, body: str):
    write_stub(hermetic, "curl", "#!/bin/sh\n" + body)


def test_network_check_passes_when_every_host_answers(run_script, hermetic, tmp_path):
    log = tmp_path / "curl.log"
    _stub_curl(
        hermetic, f'for a in "$@"; do last="$a"; done\necho "$last" >> "{log}"\nprintf 200\n'
    )
    result = run_script(NETWORK_CHECK)
    assert result.returncode == 0
    assert log.read_text().split() == [
        "https://api.kaggle.com",
        "https://www.kaggle.com",
        "https://storage.googleapis.com",
    ]
    assert "All Kaggle endpoints reachable" in result.stdout


def test_any_http_status_counts_as_reachable(run_script, hermetic):
    _stub_curl(hermetic, "printf 404\n")
    assert run_script(NETWORK_CHECK).returncode == 0


def test_network_check_names_dns_and_connection_failures(run_script, hermetic):
    _stub_curl(hermetic, "printf 000\nexit 6\n")
    result = run_script(NETWORK_CHECK)
    assert result.returncode == 1
    assert result.stdout.count("DNS resolution failed") == 3

    _stub_curl(hermetic, "printf 000\nexit 28\n")
    result = run_script(NETWORK_CHECK)
    assert result.returncode == 1
    assert "curl exit 28" in result.stdout
    assert "3 host(s) unreachable" in result.stdout
