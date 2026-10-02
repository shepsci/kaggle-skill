"""Tests for the setup scripts: the credential checker, save_credentials.py, doctor.py."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from shared import net

CHECKER = "skills/kaggle/modules/setup/scripts/check_all_credentials.py"
SAVE = "skills/kaggle/modules/setup/scripts/save_credentials.py"
DOCTOR = "skills/kaggle/modules/setup/scripts/doctor.py"

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
    assert result.returncode == 2
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
    assert run_script(CHECKER).returncode == 2

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
    assert result.returncode == 2
    assert "[FAIL] Kaggle did not accept what is configured." in result.stdout
    assert "Verified" not in result.stdout


def test_verify_fails_when_the_cli_cannot_sign_in(run_script, stub_kaggle):
    stub_kaggle('echo "401 Unauthorized" >&2\nexit 1\n')
    result = run_script(CHECKER, "--verify", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 2
    assert "[FAIL] Kaggle did not accept what is configured." in result.stdout


def test_token_that_looks_like_another_kind_is_pointed_out(run_script):
    result = run_script(CHECKER, env={"KAGGLE_API_TOKEN": "KGRT_refresh_token_value"})
    assert "looks like: OAuth refresh token" in result.stdout


# ── save_credentials.py ──────────────────────────────────────────────────────


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_saving_is_a_dry_run_that_never_shows_the_value(run_script):
    result = run_script(SAVE, env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Dry run. Nothing was sent to disk.")
    assert "from:   KAGGLE_API_TOKEN" in result.stdout
    assert "/.kaggle/access_token (mode 600)" in result.stdout
    assert TOKEN not in result.stdout + result.stderr
    assert not (Path.home() / ".kaggle").exists()


def test_help_writes_nothing_even_with_a_token_in_the_environment(run_script):
    result = run_script(SAVE, "--help", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0 and "usage" in result.stdout.lower()
    assert not (Path.home() / ".kaggle").exists()


def test_yes_saves_the_token_with_private_permissions(run_script):
    result = run_script(SAVE, "--yes", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0, result.stderr
    token_file = Path.home() / ".kaggle" / "access_token"
    assert token_file.read_text() == TOKEN
    assert _mode(token_file) == 0o600
    assert _mode(token_file.parent) == 0o700
    assert TOKEN not in result.stdout + result.stderr


def test_an_existing_file_is_never_overwritten(run_script):
    token_file = _kaggle_dir() / "access_token"
    token_file.write_text("KGAT_existing")
    result = run_script(SAVE, "--yes", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0
    assert token_file.read_text() == "KGAT_existing"
    assert "left unchanged" in result.stdout


def test_a_legacy_key_is_saved_as_valid_json(run_script):
    env = {"KAGGLE_USERNAME": 'al"ice\\', "KAGGLE_KEY": "e" * 32}
    result = run_script(SAVE, "--yes", env=env)
    assert result.returncode == 0, result.stderr
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    assert json.loads(kaggle_json.read_text()) == {"username": 'al"ice\\', "key": "e" * 32}
    assert _mode(kaggle_json) == 0o600
    assert "e" * 32 not in result.stdout + result.stderr


def test_with_nothing_configured_nothing_is_written(run_script):
    result = run_script(SAVE, "--yes")
    assert result.returncode == 0
    assert "kaggle auth login" in result.stdout
    assert not (Path.home() / ".kaggle").exists()


def test_the_env_file_is_parsed_and_never_run(run_script, tmp_path):
    marker = tmp_path / "pwned"
    env_file = tmp_path / "kaggle.env"
    env_file.write_bytes(
        (
            f"touch {marker}\r\n"
            f"KAGGLE_USERNAME=$(touch {marker})\r\n"
            "PATH=/nonexistent\r\n"
            "KAGGLE_API_ENVIRONMENT=LOCALHOST\r\n"
            f"export KAGGLE_API_TOKEN='{TOKEN}'\r\n"
        ).encode()
    )
    result = run_script(SAVE, "--yes", env={"KAGGLE_ENV_FILE": str(env_file)})
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert (Path.home() / ".kaggle" / "access_token").read_text() == TOKEN


def test_a_path_is_not_stored_as_if_it_were_the_token(run_script, tmp_path):
    """KAGGLE_API_TOKEN may name a token file. The path itself is not a token."""
    token_file = tmp_path / "my-token"
    token_file.write_text(TOKEN)
    result = run_script(SAVE, "--yes", env={"KAGGLE_API_TOKEN": str(token_file)})
    assert result.returncode == 0
    assert "names a token file" in result.stdout
    assert not (Path.home() / ".kaggle" / "access_token").exists()


def test_a_dotenv_it_was_not_pointed_at_is_ignored(run_script):
    Path(".env").write_text(f"KAGGLE_API_TOKEN={TOKEN}\n")
    result = run_script(SAVE, "--yes")
    assert result.returncode == 0
    assert not (Path.home() / ".kaggle").exists()


def test_the_read_only_switch_refuses_to_store_a_credential(run_script):
    env = {"KAGGLE_API_TOKEN": TOKEN, "KAGGLE_SKILL_READ_ONLY": "1"}
    result = run_script(SAVE, "--yes", env=env)
    assert result.returncode == 5 and result.stdout.startswith("Refused:")
    assert not (Path.home() / ".kaggle").exists()


# ── doctor.py ────────────────────────────────────────────────────────────────


@pytest.fixture
def doctor(load_script, monkeypatch):
    module = load_script(DOCTOR)
    monkeypatch.setattr(module, "package_version", {"kaggle": "2.2.4", "kagglehub": "1.0.2"}.get)

    def reachable(method, url, **kwargs):
        return net.Response(200, {}, "", url)

    monkeypatch.setattr(net, "request", reachable)
    monkeypatch.setattr(
        module.mcp_client, "mcp_list_tools", lambda **kw: {"result": {"tools": [{}] * 71}}
    )
    return module


def test_doctor_with_everything_in_place(doctor, run_main, monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", TOKEN)
    code, out, err = run_main(doctor)
    assert code == 0 and err == "" and TOKEN not in out
    for expected in (
        "kaggle package",
        "API token from KAGGLE_API_TOKEN",
        "found; add --verify to ask Kaggle",
        "Kaggle MCP server",
        "71 tools",
        "yes  public reads",
        "yes  reads on your account",
        "yes  downloads, submissions, notebooks, publishing",
        "yes  dataset and model downloads with kagglehub",
    ):
        assert expected in out, expected


def test_doctor_on_a_bare_machine_says_what_still_works(doctor, run_main, monkeypatch):
    monkeypatch.setattr(doctor, "package_version", lambda name: None)
    monkeypatch.setattr(doctor.kaggle_cli, "installed", lambda: False)
    code, out, _ = run_main(doctor)
    assert code == 0, "public reads work, so this is not a failure"
    assert "not installed: python3 -m pip install 'kaggle>=2.2.4'" in out
    assert "not installed: python3 -m pip install 'kagglehub>=1.0.2'" in out
    assert "none found" in out
    assert "yes  public reads" in out
    assert "no   reads on your account" in out
    assert "no   downloads, submissions" in out
    assert "No credential: sign in with `kaggle auth login`" in out


def test_doctor_explains_a_legacy_key(doctor, run_main, monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "alice")
    monkeypatch.setenv("KAGGLE_KEY", "e" * 32)
    code, out, _ = run_main(doctor)
    assert code == 0 and "e" * 32 not in out
    assert "legacy API key from KAGGLE_USERNAME + KAGGLE_KEY" in out
    assert "no   reads on your account" in out
    assert "yes  downloads, submissions" in out
    assert "The credential is a legacy API key." in out


def test_doctor_reports_an_unreachable_host(doctor, run_main, monkeypatch):
    def unreachable(method, url, **kwargs):
        if "api.kaggle.com" in url:
            raise net.RequestError("connection", "gaierror")
        return net.Response(200, {}, "", url)

    monkeypatch.setattr(net, "request", unreachable)
    monkeypatch.setattr(
        doctor.mcp_client, "mcp_list_tools", lambda **kw: {"error": {"message": "x"}}
    )
    code, out, _ = run_main(doctor)
    assert code == 1
    assert "NOT reachable (gaierror)" in out and "no   public reads" in out
    assert "allow outbound HTTPS" in out


def test_doctor_points_out_a_certificate_problem(doctor, run_main, monkeypatch):
    def failing(method, url, **kwargs):
        raise net.RequestError("certificate")

    monkeypatch.setattr(net, "request", failing)
    out = run_main(doctor)[1]
    assert "NOT reachable (certificate)" in out and "certifi" in out


def test_doctor_verify_and_json(doctor, run_main, monkeypatch, stub_kaggle):
    monkeypatch.setenv("KAGGLE_API_TOKEN", TOKEN)
    stub_kaggle(
        'case "$1" in\n  config) echo "- username: alice" ;;\n  quota) echo "GPU 1h" ;;\nesac\n'
    )
    code, out, _ = run_main(doctor, "--verify", "--skip-network")
    assert code == 0 and "accepted by Kaggle as alice" in out
    assert "www.kaggle.com" not in out, "--skip-network contacts nobody"

    stub_kaggle('echo "Authentication required to call the Kaggle API." >&2\nexit 1\n')
    code, out, _ = run_main(doctor, "--verify", "--skip-network", "--json")
    report = json.loads(out)
    assert code == 2 and report["verified"] is False
    assert report["works"]["account_reads"] is False and TOKEN not in out


def test_doctor_reads_and_changes_nothing(run_script):
    home = Path.home()
    before = sorted(str(p) for p in home.rglob("*"))
    result = run_script(DOCTOR, "--skip-network", env={"KAGGLE_API_TOKEN": TOKEN})
    assert result.returncode == 0, result.stderr
    assert sorted(str(p) for p in home.rglob("*")) == before
    assert TOKEN not in result.stdout + result.stderr
