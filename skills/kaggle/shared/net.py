"""HTTPS requests with the standard library.

(The module is not called ``http``: some files in this folder are run as
scripts, which puts the folder first on the import path, and a file of that
name would then hide the standard library's ``http`` package.)

The public reads this skill makes (the Kaggle MCP server, writeup pages) have
to work on a Python with nothing installed, so they use ``urllib`` and not
``requests``.

Rules kept here:

- Only ``https`` URLs are requested.
- A redirect is never followed. The caller sees the 3xx answer and decides, so
  a bearer token is never carried to another host.
- Certificates are always verified.
- The text of a library exception is never passed on. It can quote a header.
"""

from __future__ import annotations

import http.client
import http.cookiejar
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

KAGGLE_HOSTS = frozenset({"www.kaggle.com", "kaggle.com"})
MAX_BODY_BYTES = 50 * 1024 * 1024
REDIRECT_STATUSES = (301, 302, 303, 307, 308)
CERTIFICATE_HINT = (
    "Python could not verify the server's certificate. On macOS with a python.org "
    "install, run 'Install Certificates.command' from the Python folder, or install "
    "certifi: python3 -m pip install certifi"
)

_UNSAFE_URL_RE = re.compile(r"[\x00-\x20\x7f\\]")


class RequestError(OSError):
    """The request did not get an answer.

    ``kind`` is ``timeout``, ``certificate`` or ``connection``. ``detail`` is
    the name of the underlying exception type, never its message.
    """

    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(kind if not detail else f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


@dataclass
class Response:
    status: int
    headers: Any  # an email.message.Message: .get(name, default) ignores case
    text: str
    url: str

    def json(self) -> Any:
        return json.loads(self.text)

    @property
    def location(self) -> str:
        """The redirect target, or ``""`` when this is not a redirect."""
        if self.status not in REDIRECT_STATUSES:
            return ""
        target = self.headers.get("Location", "") or ""
        return urllib.parse.urljoin(self.url, target) if target else ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, D102
        return None


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    try:
        import certifi  # present whenever the kaggle package is installed

        context.load_verify_locations(certifi.where())
    except (ImportError, OSError):
        pass
    return context


def make_opener(*, cookies: bool = False) -> urllib.request.OpenerDirector:
    """An opener that does not follow redirects. ``cookies`` keeps a cookie jar."""
    handlers: list[Any] = [_NoRedirect(), urllib.request.HTTPSHandler(context=_ssl_context())]
    if cookies:
        jar = http.cookiejar.CookieJar()
        handlers.append(urllib.request.HTTPCookieProcessor(jar))
    opener = urllib.request.build_opener(*handlers)
    opener.cookie_jar = jar if cookies else None  # type: ignore[attr-defined]
    return opener


def cookie(opener: urllib.request.OpenerDirector, name: str) -> str:
    """The value of a cookie the opener holds, or ``""``."""
    jar = getattr(opener, "cookie_jar", None)
    for item in jar or ():
        if item.name == name:
            return item.value or ""
    return ""


def _read(stream: Any) -> str:
    raw = stream.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        raw = raw[:MAX_BODY_BYTES]
    charset = "utf-8"
    headers = getattr(stream, "headers", None)
    if headers is not None:
        charset = headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float = 30,
    opener: urllib.request.OpenerDirector | None = None,
) -> Response:
    """Send one request and return the answer, whatever its status.

    Raises ValueError for a URL that is not https, and RequestError when no
    answer arrives.
    """
    if not url.lower().startswith("https://") or _UNSAFE_URL_RE.search(url):
        raise ValueError("only https URLs are requested")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)  # noqa: S310
    opener = opener or make_opener()
    try:
        with opener.open(req, timeout=timeout) as stream:
            return Response(stream.status, stream.headers, _read(stream), url)
    except urllib.error.HTTPError as exc:
        # urllib raises for every status it does not handle, 3xx included.
        with exc:
            return Response(exc.code, exc.headers, _read(exc), url)
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            raise RequestError("timeout") from None
        if isinstance(reason, ssl.SSLCertVerificationError):
            raise RequestError("certificate") from None
        raise RequestError("connection", type(reason).__name__) from None
    except TimeoutError:
        raise RequestError("timeout") from None
    except ssl.SSLCertVerificationError:
        raise RequestError("certificate") from None
    except (OSError, http.client.HTTPException) as exc:
        raise RequestError("connection", type(exc).__name__) from None


def kaggle_url(url: str) -> str:
    """Return ``url`` rebuilt from its checked parts.

    Raises ValueError unless it is an https URL on kaggle.com with no user
    name, password or port. What is requested is the rebuilt URL, so the host
    that was checked is the host that is contacted, whatever a parser might
    make of an input such as ``https://evil.example\\@www.kaggle.com/x``.
    """
    if not isinstance(url, str) or _UNSAFE_URL_RE.search(url):
        raise ValueError("not an https kaggle.com URL")
    try:
        parts = urllib.parse.urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        raise ValueError("not an https kaggle.com URL") from None
    if (
        parts.scheme != "https"
        or "@" in parts.netloc
        or port not in (None, 443)
        or host not in KAGGLE_HOSTS
    ):
        raise ValueError("not an https kaggle.com URL")
    path = urllib.parse.quote(parts.path or "/", safe="/%:@-._~!$&'()*+,;=")
    query = urllib.parse.quote(parts.query, safe="/%:@-._~!$&'()*+,;=?")
    return f"https://{host}{path}" + (f"?{query}" if query else "")


def is_kaggle_url(url: str) -> bool:
    """True only for an https URL whose destination is kaggle.com."""
    try:
        kaggle_url(url)
    except ValueError:
        return False
    return True
