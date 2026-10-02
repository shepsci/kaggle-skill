"""Credentials must never be printed, put on a command line, or sent to another host."""

from __future__ import annotations

import email.message
import io
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from shared import credentials, kaggle_cli, mcp_client

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = "skills/kaggle"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "tests", "__pycache__"}
TOKEN = "KGAT_0123456789abcdef0123456789abcdef"

LEAK_PATTERNS = [
    # echo "$KAGGLE_API_TOKEN" or echo $KAGGLE_KEY
    re.compile(r"echo\s+[^\n|>]*\$\{?(KAGGLE_(API_TOKEN|KEY|MCP_TOKEN)|API_TOKEN|KEY)\}?"),
    # print(token) or print(KAGGLE_API_TOKEN) directly
    re.compile(
        r'print\s*\(\s*(f?["\'][^"\']*\{)?\s*(token|secret|KAGGLE_(API_TOKEN|KEY|MCP_TOKEN))\s*[)}]'
    ),
    # a bearer token handed to another program as an argument
    re.compile(r'["\']Authorization:\s*Bearer'),
]


def _candidate_files() -> list[Path]:
    return sorted(
        path
        for ext in ("*.sh", "*.py")
        for path in REPO_ROOT.rglob(ext)
        if not any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts)
    )


@pytest.mark.parametrize("path", _candidate_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_credential_echo_in_script(path: Path):
    offenders = [
        (number, line.strip())
        for number, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1)
        for pattern in LEAK_PATTERNS
        if pattern.search(line)
    ]
    assert not offenders, f"{path.relative_to(REPO_ROOT)}: possible credential echo at {offenders}"


def test_the_only_printf_of_a_token_writes_to_the_token_file():
    """setup_env.sh stores the token on purpose. Its printf must go to a file, not the terminal."""
    text = (REPO_ROOT / SKILL / "modules/setup/scripts/setup_env.sh").read_text()
    printfs = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("printf") and ("TOKEN" in line or "KEY" in line)
    ]
    assert printfs and all(
        re.search(r'>\s*"\$\{(ACCESS_TOKEN_FILE|KAGGLE_JSON)\}"$', line) for line in printfs
    ), printfs


# ── the token stays inside the process ───────────────────────────────────────


class _Stream(io.BytesIO):
    status = 200

    def __init__(self, body: bytes = b'data: {"result": {}, "id": 1}\n') -> None:
        super().__init__(body)
        self.headers = email.message.Message()
        self.headers["Content-Type"] = "text/event-stream"


def test_mcp_call_does_not_start_a_process_or_put_the_token_in_a_url(monkeypatch):
    seen = []

    def fake_open(self, req, timeout=None):
        seen.append(req)
        return _Stream()

    def forbidden(*args, **kwargs):
        raise AssertionError("no child process may be started for an MCP call")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake_open)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    mcp_client.mcp_call("get_competition", {"request": {"competitionName": "titanic"}}, token=TOKEN)
    (req,) = seen
    assert req.full_url == "https://www.kaggle.com/mcp"
    assert TOKEN not in req.full_url and TOKEN not in req.data.decode()
    assert req.get_header("Authorization") == f"Bearer {TOKEN}"


def test_a_redirect_does_not_carry_the_token_to_another_host(monkeypatch):
    seen = []

    def redirecting_open(self, req, timeout=None):
        seen.append(req.full_url)
        headers = email.message.Message()
        headers["Location"] = "https://evil.example/mcp"
        raise urllib.error.HTTPError(req.full_url, 307, "Temporary Redirect", headers, io.BytesIO())

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", redirecting_open)
    response = mcp_client.mcp_call("authorize", {}, token=TOKEN)
    assert seen == ["https://www.kaggle.com/mcp"], "the redirect must not be followed"
    assert response["error"]["message"] == "HTTP 307"


def test_transport_errors_do_not_echo_request_details(monkeypatch):
    def failing_open(self, req, timeout=None):
        raise ConnectionError(f"failed for headers Authorization: Bearer {TOKEN}")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", failing_open)
    response = mcp_client.mcp_call("authorize", {}, token=TOKEN)
    assert response["error"]["message"] == "connection failed: ConnectionError"
    assert TOKEN not in json.dumps(response)


def test_failure_report_never_contains_the_token(capsys):
    response = {
        "result": {"content": [{"type": "text", "text": "Unauthenticated"}], "isError": True}
    }
    mcp_client.print_failure(response, tool="t", had_token=True)
    captured = capsys.readouterr()
    assert "KGAT_" not in captured.out + captured.err


def test_credential_objects_hide_their_secret(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", TOKEN)
    credential = credentials.resolve()
    assert credential.secret == TOKEN
    for rendered in (repr(credential), str(credential), f"{credential}", repr([credential])):
        assert TOKEN not in rendered


# ── the Kaggle CLI is never asked to print headers ───────────────────────────


def test_cli_runs_without_the_variables_that_print_the_bearer_token(stub_kaggle, monkeypatch):
    stub_kaggle(
        'echo "VERBOSE=[${VERBOSE:-}] VERBOSE_OUTPUT=[${VERBOSE_OUTPUT:-}] '
        'ENV=[${KAGGLE_API_ENVIRONMENT:-}] TOKEN_SET=[${KAGGLE_API_TOKEN:+yes}]"\n'
    )
    monkeypatch.setenv("VERBOSE", "1")
    monkeypatch.setenv("VERBOSE_OUTPUT", "1")
    monkeypatch.setenv("KAGGLE_API_ENVIRONMENT", "LOCALHOST")
    monkeypatch.setenv("KAGGLE_API_TOKEN", TOKEN)
    result = kaggle_cli.run(["config", "view"])
    assert result.stdout.strip() == "VERBOSE=[] VERBOSE_OUTPUT=[] ENV=[] TOKEN_SET=[yes]"


def test_oauth_token_lookup_does_not_print(stub_kaggle, capsys):
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "credentials.json").write_text(json.dumps({"refresh_token": "KGRT_x"}))
    stub_kaggle('[ "$1 $2" = "auth print-access-token" ] && echo "oauth-access-token-value"\n')
    assert credentials.bearer_token() == "oauth-access-token-value"
    captured = capsys.readouterr()
    assert "oauth-access-token-value" not in captured.out + captured.err


# ── bundled configuration ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "manifest",
    [
        ".mcp.json",
        ".codex-plugin/mcp.json",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        ".codex-plugin/plugin.json",
    ],
)
def test_manifests_forward_no_credential(manifest):
    """The bundled MCP entries hold no credential. A header template here would send
    whatever KAGGLE_API_TOKEN holds on every request, including a legacy key or a
    wrong token."""
    text = (REPO_ROOT / manifest).read_text()
    assert "Authorization" not in text
    assert "Bearer" not in text
    assert "${KAGGLE" not in text and "KGAT_" not in text


def test_no_credential_files_are_tracked():
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    forbidden = [
        name
        for name in tracked
        if Path(name).name in {"kaggle.json", "access_token", "credentials.json", ".env"}
        or name.endswith((".pem", ".p12"))
    ]
    assert not forbidden, forbidden
