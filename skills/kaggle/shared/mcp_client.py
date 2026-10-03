"""JSON-RPC client for the Kaggle MCP server (https://www.kaggle.com/mcp).

Used by the scripts and by the test suite. Facts about the server this client
is built around:

- Every tool except ``authorize`` takes its arguments as ``{"request": {...}}``
  with camelCase keys.
- Responses arrive as ``text/event-stream`` (``data: {...}`` lines). The client
  must accept both ``application/json`` and ``text/event-stream``.
- A failed tool call is HTTP 200 with ``result.isError: true`` and a short
  message. Success is never inferred from the message text.
- Public read tools answer without credentials, and an invalid bearer is
  treated as anonymous.

Only the standard library is used, so the public reads work on a Python with
no packages installed.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import credentials, net, script, untrusted  # noqa: E402

MCP_ENDPOINT = "https://www.kaggle.com/mcp"
MAX_RETRIES = 2
MAX_RETRY_WAIT = 30.0
_REQUEST_ID = 1


def resolve_token() -> str:
    """Bearer token for the MCP server, or ``""`` for anonymous calls."""
    return credentials.bearer_token()


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"error": {"message": message, **extra}}


def _parse_body(text: str, content_type: str, request_id: int) -> dict[str, Any]:
    """Pick the JSON-RPC response out of an event stream or a plain JSON body."""
    candidates: list[dict[str, Any]] = []
    if "text/event-stream" in content_type or text.lstrip().startswith(("event:", "data:")):
        for line in text.splitlines():
            if not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except ValueError:
                continue
            if isinstance(obj, dict):
                candidates.append(obj)
    else:
        try:
            obj = json.loads(text)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            candidates.append(obj)

    for obj in candidates:
        if obj.get("id") == request_id and ("result" in obj or "error" in obj):
            return obj
    for obj in candidates:
        if "result" in obj or "error" in obj:
            return obj
    return {"raw": text[:300]}


def _retry_wait(response: Any, attempt: int) -> float:
    header = response.headers.get("Retry-After", "") or ""
    try:
        wait = float(header)
    except ValueError:
        wait = 2.0 * (attempt + 1)
    return max(0.0, min(wait, MAX_RETRY_WAIT))


def _post(payload: dict[str, Any], token: str, timeout: float, endpoint: str) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")

    for attempt in range(MAX_RETRIES + 1):
        try:
            # net.request never follows a redirect, so the token stays with this host.
            response = net.request("POST", endpoint, headers=headers, data=body, timeout=timeout)
        except net.RequestError as exc:
            if exc.kind == "timeout":
                return _error("timeout")
            if exc.kind == "certificate":
                return _error("certificate check failed", hint=net.CERTIFICATE_HINT)
            return _error(f"connection failed: {exc.detail}")
        except ValueError:
            return _error("the MCP endpoint is not an https URL")
        if response.status == 429 and attempt < MAX_RETRIES:
            time.sleep(_retry_wait(response, attempt))
            continue
        if response.status != 200:
            return _error(
                f"HTTP {response.status}",
                http_status=response.status,
                body=response.text[:300],
            )
        return _parse_body(
            response.text, response.headers.get("Content-Type", "") or "", payload["id"]
        )
    return _error("HTTP 429", http_status=429)


def mcp_call(
    tool: str,
    arguments: dict[str, Any],
    token: str = "",
    timeout: float = 30,
    endpoint: str = MCP_ENDPOINT,
) -> dict[str, Any]:
    """Call one MCP tool. Returns the parsed JSON-RPC response.

    Never raises for network or server failures: those come back as
    ``{"error": {"message": ...}}``. An empty ``token`` makes an anonymous call.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
        "id": _REQUEST_ID,
    }
    return _post(payload, token, timeout, endpoint)


def mcp_list_tools(
    token: str = "", timeout: float = 30, endpoint: str = MCP_ENDPOINT
) -> dict[str, Any]:
    """Call ``tools/list``. Works without a token."""
    payload = {"jsonrpc": "2.0", "method": "tools/list", "id": _REQUEST_ID}
    return _post(payload, token, timeout, endpoint)


def extract_text(resp: dict[str, Any]) -> str:
    """The first text block of a response, or ``""``."""
    result = resp.get("result")
    if not isinstance(result, dict):
        return ""
    content = result.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                return item["text"]
    return ""


def extract_json(resp: dict[str, Any]) -> dict[str, Any] | list[Any] | None:
    """The first text block parsed as JSON, or None."""
    text = extract_text(resp)
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def is_error(resp: dict[str, Any]) -> bool:
    """True when the server or the transport reported a failure."""
    if "raw" in resp or resp.get("error"):
        return True
    result = resp.get("result")
    return isinstance(result, dict) and bool(result.get("isError"))


def error_message(resp: dict[str, Any]) -> str:
    """The failure text of a response, or ``""`` when it succeeded."""
    if "raw" in resp:
        return "unparseable response"
    error = resp.get("error")
    if error:
        if isinstance(error, dict):
            return str(error.get("message") or "unknown error")
        return str(error)
    result = resp.get("result")
    if isinstance(result, dict) and result.get("isError"):
        return extract_text(resp) or "tool reported an error"
    return ""


def classify_result(resp: dict[str, Any]) -> str:
    """Classify a response: ok | empty | unauthenticated | error: <msg> | parse_fail.

    The decision uses the response structure only (JSON-RPC ``error`` and
    ``result.isError``). Payload text is never searched for error words, so a
    writeup that mentions "server error" is still ``ok``.
    """
    if "raw" in resp:
        return "parse_fail"
    if is_error(resp):
        message = error_message(resp)
        if message.strip().lower().startswith("unauthenticated"):
            return "unauthenticated"
        return f"error: {message[:100]}"
    result = resp.get("result")
    if not result:
        return "empty"
    return "ok"


# Wordings the server uses when the account or its role may not do something:
# "Permission 'kernels.get' was denied", "Only hosts, judges, or teammates of
# this hackathon can request writeups."
_DENIAL_RE = re.compile(
    r"permission|denied|forbidden|not authori[sz]ed|not allowed|\bonly\b.+\bcan\b",
    re.IGNORECASE,
)


def is_denied(resp: dict[str, Any]) -> bool:
    """True when the failure is a permission or role denial rather than not-found."""
    return is_error(resp) and bool(_DENIAL_RE.search(error_message(resp)))


# Hints this module attaches to a failure it detected itself.
LOCAL_HINTS = frozenset({net.CERTIFICATE_HINT})
EXIT_FAILED = script.EXIT_FAILED
EXIT_NO_CREDENTIAL = script.EXIT_NO_CREDENTIAL
EXIT_DENIED = script.EXIT_DENIED


@dataclass
class Result:
    """One tool call, reduced to what a script needs."""

    tool: str
    status: str  # ok | empty | unauthenticated | error: <message> | parse_fail
    response: dict[str, Any]
    had_token: bool

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def text(self) -> str:
        return extract_text(self.response)

    @property
    def data(self) -> Any:
        """The answer parsed as JSON, or None."""
        return extract_json(self.response)

    @property
    def denied(self) -> bool:
        return is_denied(self.response)

    def fail(self, **attrs: Any) -> int:
        """Report the failure on standard error and return the exit code."""
        return print_failure(self.response, tool=self.tool, had_token=self.had_token, **attrs)


def request(
    tool: str,
    request: dict[str, Any] | None = None,
    *,
    token: str | None = None,
    timeout: float = 30,
) -> Result:
    """Call a tool with ``{"request": {...}}`` arguments and classify the answer.

    ``token=None`` uses the configured credential, if any; ``token=""`` makes
    an anonymous call.
    """
    if token is None:
        token = resolve_token()
    response = mcp_call(tool, {"request": request or {}}, token=token, timeout=timeout)
    return Result(tool, classify_result(response), response, bool(token))


LEGACY_KEY_HINT = (
    "       The credential is a legacy API key (kaggle.json). Kaggle's MCP server takes an\n"
    '       API token or an OAuth login: create a token with "Generate New Token" at\n'
    "       https://www.kaggle.com/settings, or run `kaggle auth login`."
)


def _only_legacy_key() -> bool:
    kinds = {cred.kind for cred in credentials.discover()}
    return kinds == {"legacy_key"}


def print_failure(
    resp: dict[str, Any],
    *,
    tool: str,
    had_token: bool,
    source: str = "kaggle-mcp",
    indent: int | None = None,
    **attrs: Any,
) -> int:
    """Report a failed call on stderr and return the exit code to use.

    The server's text is printed as untrusted data. The exit code tells the
    caller why it failed: 2 when credentials are missing or were not accepted,
    3 when the server denied permission (a role gate), 1 for anything else.
    """
    status = classify_result(resp)
    untrusted.emit_json(
        {"status": status, "response": resp},
        source=source,
        tool=tool,
        stream="stderr",
        indent=indent,
        file=sys.stderr,
        **attrs,
    )
    if status == "unauthenticated":
        if had_token:
            print(
                f"error: {tool}: the configured Kaggle credential was not accepted", file=sys.stderr
            )
            if _only_legacy_key():
                print(LEGACY_KEY_HINT, file=sys.stderr)
        else:
            print(f"error: {tool} needs Kaggle credentials and none were found", file=sys.stderr)
        return EXIT_NO_CREDENTIAL
    if is_denied(resp):
        if had_token:
            print(f"error: {tool}: permission denied for this account or role", file=sys.stderr)
        else:
            print(
                f"error: {tool}: permission denied, and no Kaggle credential was sent; "
                "sign in if this is private",
                file=sys.stderr,
            )
        return EXIT_DENIED
    # Only the skill's own hint is repeated here; a server could send one too.
    hint = resp.get("error", {}).get("hint") if isinstance(resp.get("error"), dict) else None
    known = hint if hint in LOCAL_HINTS else None
    print(f"error: {tool} failed" + (f". {known}" if known else ""), file=sys.stderr)
    return EXIT_FAILED
