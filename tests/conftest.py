"""Shared pytest fixtures and CLI flags for the kaggle-skill test suite.

Offline tests are hermetic: each one gets an empty HOME, a temporary working
directory, no Kaggle variables in the environment, a stub ``kaggle`` on PATH
and no network. Tests marked ``live`` keep the real environment and are
skipped unless ``--run-live`` is given.
"""

from __future__ import annotations

import json
import os
import re
import socket
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SKILL_ROOT = REPO_ROOT / "skills" / "kaggle"

# Make `from shared import ...` work from tests
sys.path.insert(0, str(SKILL_ROOT))

KAGGLE_ENV_VARS = (
    "KAGGLE_API_TOKEN",
    "KAGGLE_MCP_TOKEN",
    "KAGGLE_USERNAME",
    "KAGGLE_KEY",
    "KAGGLE_TOKEN",
    "KAGGLE_CONFIG_DIR",
    "KAGGLE_ENV_FILE",
    "KAGGLE_CLI_BIN",
    "KAGGLE_API_ENVIRONMENT",
    "KAGGLE_PUBLISH_ALLOW_SECRETS",
    "VERBOSE",
    "VERBOSE_OUTPUT",
)

UNEXPECTED_KAGGLE_STUB = """#!/bin/sh
echo "stub kaggle: unexpected call: $*" >&2
exit 97
"""


class Secret(str):
    """A token that shows as ``<redacted>`` in tracebacks and assertion messages.

    pytest prints fixture values with ``repr`` when a test fails. A plain
    string would put the real token in the terminal and in CI logs.
    """

    def __repr__(self) -> str:
        return "'<redacted>'"


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.live (they call Kaggle)",
    )
    parser.addoption(
        "--run-destructive",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.destructive (write to Kaggle account)",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        skip_live = pytest.mark.skip(reason="needs --run-live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
    if not config.getoption("--run-destructive"):
        skip_dest = pytest.mark.skip(reason="needs --run-destructive")
        for item in items:
            if "destructive" in item.keywords:
                item.add_marker(skip_dest)


BLOCK_RE = re.compile(
    r"<untrusted-content-(?P<nonce>[0-9a-f]{8})(?P<attrs>(?: [a-z-]+=\"[^\"]*\")*)>\n"
    r"(?P<body>.*?)\n?</untrusted-content-(?P=nonce)>",
    re.DOTALL,
)


@dataclass
class UntrustedBlock:
    """One block printed by shared/untrusted.py."""

    nonce: str
    attrs: dict[str, str]
    body: str

    def json(self):
        return json.loads(self.body)


def parse_untrusted_blocks(text: str) -> list[UntrustedBlock]:
    """Blocks in ``text``, each matched open tag to its own close tag."""
    return [
        UntrustedBlock(
            nonce=m.group("nonce"),
            attrs=dict(re.findall(r' ([a-z-]+)="([^"]*)"', m.group("attrs"))),
            body=m.group("body"),
        )
        for m in BLOCK_RE.finditer(text)
    ]


def text_outside_blocks(text: str) -> str:
    """What is left of ``text`` after every block is removed."""
    return BLOCK_RE.sub("", text)


def write_stub(directory: Path, name: str, script: str) -> Path:
    """Write an executable stub named ``name`` into ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(script)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture(autouse=True)
def hermetic(request, tmp_path, monkeypatch):
    """Isolate offline tests from the machine and from Kaggle."""
    if "live" in request.keywords or "manual" in request.keywords:
        yield None
        return

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    for var in KAGGLE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    stub_bin = tmp_path / "stub-bin"
    write_stub(stub_bin, "kaggle", UNEXPECTED_KAGGLE_STUB)
    # Shell wrappers call `python3` and `sleep`: use this interpreter, and do not wait.
    write_stub(stub_bin, "python3", f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    write_stub(stub_bin, "sleep", "#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("PATH", f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    def _no_network(*args, **kwargs):
        raise RuntimeError("network access in an offline test; mark it live or mock the call")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    yield stub_bin


@pytest.fixture
def stub_kaggle(hermetic):
    """Install a stub ``kaggle`` for this test: ``stub_kaggle(shell_script_body)``."""

    def _install(body: str) -> Path:
        return write_stub(hermetic, "kaggle", "#!/bin/sh\n" + body)

    return _install


@pytest.fixture
def kaggle_calls(hermetic, tmp_path):
    """Install a stub ``kaggle`` that records its calls.

    ``calls = kaggle_calls(shell_body)`` installs the stub; ``calls()`` returns
    one list of arguments per call. In the body, ``$path`` is the value given
    to ``--path`` or ``-p``, if any.
    """
    log = tmp_path / "kaggle-calls.log"
    prelude = (
        "#!/bin/sh\n"
        f"(IFS='|'; printf '%s\\n' \"$*\") >> \"{log}\"\n"
        'path=""; prev=""\n'
        'for a in "$@"; do\n'
        '  case "$prev" in --path|-p) path="$a" ;; esac\n'
        '  prev="$a"\n'
        "done\n"
    )

    def _install(body: str = ""):
        write_stub(hermetic, "kaggle", prelude + body)

        def _calls() -> list[list[str]]:
            if not log.exists():
                return []
            return [line.split("|") for line in log.read_text().splitlines()]

        return _calls

    return _install


@pytest.fixture
def run_script(repo_root):
    """Run a script from the repository: ``run_script("skills/.../x.sh", "arg")``."""
    import subprocess

    def _run(
        rel_path: str,
        *args: str,
        env: dict | None = None,
        timeout: int = 60,
        stdin: str | None = None,
    ):
        path = repo_root / rel_path
        interpreter = ["bash"] if path.suffix == ".sh" else [sys.executable]
        full_env = dict(os.environ)
        full_env.update(env or {})
        return subprocess.run(
            [*interpreter, str(path), *args],
            capture_output=True,
            text=True,
            env=full_env,
            timeout=timeout,
            input=stdin,
            check=False,
        )

    return _run


@pytest.fixture
def blocks():
    """``blocks(text)`` parses the untrusted-content blocks in ``text``."""
    return parse_untrusted_blocks


@pytest.fixture
def outside():
    """``outside(text)`` returns the part of ``text`` that is not inside a block."""
    return text_outside_blocks


@pytest.fixture
def load_script(repo_root, monkeypatch):
    """Import a script by its path relative to the repository root.

    The script's folder goes first on ``sys.path`` and same-named modules left
    by other tests are set aside, because two script folders each have a
    ``utils.py``.
    """
    import importlib.util

    touched: set[str] = set()
    saved: dict[str, object] = {}

    def _load(rel_path: str):
        path = repo_root / rel_path
        monkeypatch.syspath_prepend(str(path.parent))
        for sibling in path.parent.glob("*.py"):
            name = sibling.stem
            if name in sys.modules and name not in saved and name not in touched:
                saved[name] = sys.modules.pop(name)
            touched.add(name)
        name = "script_" + re.sub(r"[^A-Za-z0-9]", "_", rel_path)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    yield _load
    for name in touched:
        sys.modules.pop(name, None)
    sys.modules.update(saved)


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


def mcp_answer(payload, *, error: bool = False) -> dict:
    """An MCP response whose text is ``payload``: JSON for a dict or list, else the string."""
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": text}], "isError": error},
    }


@pytest.fixture
def fake_mcp(monkeypatch):
    """Answer MCP calls from a table instead of the network.

    ``state = fake_mcp({"get_competition": payload}, token="")`` installs the
    answers. A payload is a dict or list (sent as JSON text), a full response
    dict with a ``result`` or ``error`` key, a list of those to return in turn,
    or a function of the request. A tool with no answer gets "Not found".
    ``state.calls`` records ``(tool, request, token)``.
    """
    from types import SimpleNamespace

    from shared import mcp_client

    state = SimpleNamespace(calls=[], answers={}, token="")

    def _respond(answer, request):
        if callable(answer):
            answer = answer(request)
        if isinstance(answer, dict) and ("result" in answer or "error" in answer):
            return answer
        return mcp_answer(answer)

    def _call(tool, arguments, token="", timeout=30, endpoint=None):
        request = arguments.get("request", arguments) if isinstance(arguments, dict) else {}
        state.calls.append(SimpleNamespace(tool=tool, request=request, token=token))
        if tool not in state.answers:
            return mcp_answer("Not found", error=True)
        answer = state.answers[tool]
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        return _respond(answer, request)

    monkeypatch.setattr(mcp_client, "mcp_call", _call)
    monkeypatch.setattr(mcp_client, "resolve_token", lambda: state.token)

    def _install(answers: dict | None = None, token: str = ""):
        state.answers.update(answers or {})
        state.token = token
        return state

    return _install


@pytest.fixture
def run_main(capsys):
    """Run a loaded script's ``main(argv)``: returns ``(exit code, stdout, stderr)``."""

    def _run(module, *argv: str):
        try:
            code = module.main(list(argv))
        except SystemExit as exc:  # argparse
            code = exc.code
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _run


@pytest.fixture
def kaggle_token() -> Secret:
    """Bearer token from the shared resolver, or skip when none is configured."""
    from shared import credentials

    token = credentials.bearer_token()
    if not token:
        pytest.skip("no Kaggle credential found for live tests")
    return Secret(token)


@pytest.fixture
def kgat_token(kaggle_token: Secret) -> Secret:
    """Older name for ``kaggle_token``."""
    return kaggle_token


@pytest.fixture
def competition_slugs() -> dict:
    return {
        "hackathon": "kaggle-measuring-agi",
        "classic": "titanic",
        "playground": "playground-series-s6e2",
    }
