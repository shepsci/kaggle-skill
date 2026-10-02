"""Unit tests for skills/kaggle/shared/net.py."""

from __future__ import annotations

import email.message
import io
import ssl
import urllib.error
import urllib.request

import pytest

from shared import net


def _headers(**values: str) -> email.message.Message:
    message = email.message.Message()
    for name, value in values.items():
        message[name.replace("_", "-")] = value
    return message


class FakeStream(io.BytesIO):
    def __init__(self, body: bytes, status: int = 200, **headers: str) -> None:
        super().__init__(body)
        self.status = status
        self.headers = _headers(**headers)


class FakeOpener:
    def __init__(self, result) -> None:
        self.result = result
        self.requests: list[urllib.request.Request] = []

    def open(self, req, timeout=None):
        self.requests.append(req)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


@pytest.mark.parametrize(
    "url",
    [
        "https://www.kaggle.com/competitions/titanic",
        "https://kaggle.com/c/titanic?tab=x",
        "https://WWW.KAGGLE.COM/",
        "https://www.kaggle.com:443/code",
    ],
)
def test_kaggle_urls_are_accepted(url):
    assert net.is_kaggle_url(url)
    assert net.kaggle_url(url).startswith(("https://www.kaggle.com/", "https://kaggle.com/"))


@pytest.mark.parametrize(
    "url",
    [
        "http://www.kaggle.com/x",
        "https://www.kaggle.com.evil.example/x",
        "https://evil.example/www.kaggle.com",
        "https://www.kaggle.com@evil.example/x",
        "https://user:pw@www.kaggle.com/x",
        "https://evil.example\\@www.kaggle.com/x",
        "https://www.kaggle.com:8443/x",
        "https://www.kaggle.com/x\nHost: evil.example",
        "https://www.kaggle.com/a b",
        "//www.kaggle.com/x",
        "file:///etc/passwd",
        "https://[::1]/x",
        "",
    ],
)
def test_other_urls_are_refused(url):
    assert not net.is_kaggle_url(url)
    with pytest.raises(ValueError):
        net.kaggle_url(url)


def test_the_checked_host_is_the_requested_host():
    assert net.kaggle_url("https://kaggle.com/a/b?x=1#frag") == "https://kaggle.com/a/b?x=1"
    assert net.kaggle_url("https://www.kaggle.com") == "https://www.kaggle.com/"


def test_request_refuses_anything_but_https():
    opener = FakeOpener(FakeStream(b""))
    for url in ("http://www.kaggle.com/", "file:///etc/passwd", "https://x/\r\nHeader: 1"):
        with pytest.raises(ValueError):
            net.request("GET", url, opener=opener)
    assert opener.requests == []


def test_request_returns_status_headers_and_decoded_text():
    body = "dash — here".encode()
    opener = FakeOpener(FakeStream(body, content_type="text/html; charset=utf-8"))
    response = net.request("GET", "https://www.kaggle.com/x", opener=opener, timeout=5)
    assert (response.status, response.text) == (200, "dash — here")
    assert response.headers.get("content-type").startswith("text/html")
    assert opener.requests[0].get_method() == "GET"


def test_an_error_status_is_an_answer_not_an_exception():
    error = urllib.error.HTTPError(
        "https://www.kaggle.com/x", 404, "Not Found", _headers(), io.BytesIO(b"gone")
    )
    response = net.request("GET", "https://www.kaggle.com/x", opener=FakeOpener(error))
    assert (response.status, response.text) == (404, "gone")


def test_a_redirect_is_reported_and_never_followed():
    error = urllib.error.HTTPError(
        "https://www.kaggle.com/x",
        302,
        "Found",
        _headers(Location="https://evil.example/steal"),
        io.BytesIO(b""),
    )
    opener = FakeOpener(error)
    response = net.request("GET", "https://www.kaggle.com/x", opener=opener)
    assert response.status == 302
    assert response.location == "https://evil.example/steal"
    assert len(opener.requests) == 1


def test_the_opener_has_no_redirect_follower():
    opener = net.make_opener()
    redirectors = [h for h in opener.handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]
    assert redirectors and all(isinstance(h, net._NoRedirect) for h in redirectors)
    assert redirectors[0].redirect_request(None, None, 302, "Found", {}, "https://x/") is None


@pytest.mark.parametrize(
    "raised, kind, detail",
    [
        (TimeoutError("slow"), "timeout", ""),
        (urllib.error.URLError(TimeoutError("slow")), "timeout", ""),
        (urllib.error.URLError(ssl.SSLCertVerificationError("bad cert")), "certificate", ""),
        (urllib.error.URLError(ConnectionRefusedError("x")), "connection", "ConnectionRefusedError"),
        (ConnectionResetError("secret header value"), "connection", "ConnectionResetError"),
    ],
)
def test_failures_are_named_without_their_message(raised, kind, detail):
    with pytest.raises(net.RequestError) as caught:
        net.request("GET", "https://www.kaggle.com/x", opener=FakeOpener(raised))
    assert (caught.value.kind, caught.value.detail) == (kind, detail)
    assert "secret" not in str(caught.value) and "slow" not in str(caught.value)


def test_cookie_lookup():
    opener = net.make_opener(cookies=True)
    assert net.cookie(opener, "XSRF-TOKEN") == ""
    assert net.cookie(net.make_opener(), "XSRF-TOKEN") == ""
