"""Tests for Notion REST client (stdlib-only).

All tests use injected urlopen/clock/sleep — no real network I/O.
"""

import io
import json
import os
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_notion_client as bnc  # noqa: E402


# --- Helpers -----------------------------------------------------------


class _FakeResponse:
    def __init__(self, status: int = 200, body: dict | bytes | None = None):
        self.status = status
        if isinstance(body, (bytes, bytearray)):
            self._bytes = bytes(body)
        elif body is None:
            self._bytes = b""
        else:
            self._bytes = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._bytes


class _FakeHTTPError(urllib.error.HTTPError):
    def __init__(
        self,
        url: str,
        code: int,
        body: dict | None = None,
        headers: dict | None = None,
    ):
        payload = json.dumps(body or {}).encode("utf-8")
        from email.message import Message

        hdrs = Message()
        for k, v in (headers or {}).items():
            hdrs[k] = v
        super().__init__(url, code, f"HTTP {code}", hdrs, io.BytesIO(payload))


class _Recorder:
    """Captures requests and replays a queued sequence of responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[dict] = []

    def __call__(self, req, timeout=None):
        body = None
        if req.data:
            body = json.loads(req.data.decode("utf-8"))
        self.requests.append(
            {
                "method": req.get_method(),
                "url": req.get_full_url(),
                "headers": dict(req.header_items()),
                "body": body,
                "timeout": timeout,
            }
        )
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


class _ClockSleep:
    def __init__(self):
        self.t = 1000.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def _client(responses, *, throttle_ms: int = 350, max_retries: int = 5):
    cs = _ClockSleep()
    opener = _Recorder(responses)
    client = bnc.NotionClient(
        "secret_token",
        throttle_ms=throttle_ms,
        max_retries=max_retries,
        urlopen=opener,
        clock=cs.clock,
        sleep=cs.sleep,
    )
    return client, opener, cs


# --- Constructor -------------------------------------------------------


def test_token_required():
    with pytest.raises(ValueError):
        bnc.NotionClient("")


def test_token_must_be_string():
    with pytest.raises(ValueError):
        bnc.NotionClient(None)  # type: ignore[arg-type]


# --- Happy path --------------------------------------------------------


def test_pages_create_sends_expected_request():
    client, rec, _ = _client([_FakeResponse(200, {"id": "page-xxx"})])
    out = client.pages_create(
        parent={"database_id": "db-1"},
        properties={"Name": {"title": [{"text": {"content": "Hi"}}]}},
    )
    assert out == {"id": "page-xxx"}
    req = rec.requests[0]
    assert req["method"] == "POST"
    assert req["url"] == "https://api.notion.com/v1/pages"
    assert req["headers"]["Authorization"] == "Bearer secret_token"
    assert req["headers"]["Notion-version"] == bnc.DEFAULT_VERSION
    assert req["headers"]["Content-type"] == "application/json"
    assert req["body"]["parent"] == {"database_id": "db-1"}


def test_pages_create_with_children():
    client, rec, _ = _client([_FakeResponse(200, {"id": "p"})])
    client.pages_create(
        parent={"database_id": "db"},
        properties={},
        children=[{"type": "paragraph"}],
    )
    assert rec.requests[0]["body"]["children"] == [{"type": "paragraph"}]


def test_pages_retrieve_is_get_without_body():
    client, rec, _ = _client([_FakeResponse(200, {"id": "p1"})])
    client.pages_retrieve("p1")
    req = rec.requests[0]
    assert req["method"] == "GET"
    assert req["url"].endswith("/pages/p1")
    assert req["body"] is None


def test_pages_update_is_patch():
    client, rec, _ = _client([_FakeResponse(200, {"id": "p1"})])
    client.pages_update("p1", archived=True)
    req = rec.requests[0]
    assert req["method"] == "PATCH"
    assert req["body"] == {"archived": True}


def test_databases_query_is_post():
    client, rec, _ = _client([_FakeResponse(200, {"results": [], "has_more": False})])
    client.databases_query(
        "db-1", filter={"property": "Name"}, sorts=[{"timestamp": "created_time"}]
    )
    req = rec.requests[0]
    assert req["method"] == "POST"
    assert req["url"].endswith("/databases/db-1/query")
    assert req["body"]["filter"] == {"property": "Name"}


def test_search_is_post():
    client, rec, _ = _client([_FakeResponse(200, {"results": []})])
    client.search(query="hello")
    assert rec.requests[0]["url"].endswith("/search")
    assert rec.requests[0]["body"] == {"query": "hello"}


def test_empty_body_returns_empty_dict():
    client, _, _ = _client([_FakeResponse(200, b"")])
    assert client.pages_retrieve("p1") == {}


# --- Pagination --------------------------------------------------------


def test_iter_database_query_follows_cursor():
    responses = [
        _FakeResponse(
            200,
            {
                "results": [{"id": "a"}, {"id": "b"}],
                "has_more": True,
                "next_cursor": "cur-1",
            },
        ),
        _FakeResponse(
            200,
            {
                "results": [{"id": "c"}],
                "has_more": False,
                "next_cursor": None,
            },
        ),
    ]
    client, rec, _ = _client(responses)
    rows = list(client.iter_database_query("db-1", page_size=50))
    assert [r["id"] for r in rows] == ["a", "b", "c"]
    assert len(rec.requests) == 2
    # Second request must carry cursor from first response
    assert rec.requests[1]["body"]["start_cursor"] == "cur-1"


def test_iter_stops_when_cursor_missing_despite_has_more():
    responses = [
        _FakeResponse(
            200,
            {
                "results": [{"id": "x"}],
                "has_more": True,
                "next_cursor": None,
            },
        ),
    ]
    client, _, _ = _client(responses)
    rows = list(client.iter_database_query("db"))
    assert [r["id"] for r in rows] == ["x"]


# --- Errors: not retried -----------------------------------------------


def test_401_raises_auth_error_without_retry():
    client, rec, cs = _client(
        [_FakeHTTPError("u", 401, body={"message": "unauthorized"})]
    )
    with pytest.raises(bnc.NotionAuthError) as ei:
        client.pages_retrieve("p1")
    assert ei.value.status == 401
    assert ei.value.body["message"] == "unauthorized"
    assert len(rec.requests) == 1
    assert cs.sleeps == []


def test_403_raises_auth_error():
    client, _, _ = _client([_FakeHTTPError("u", 403)])
    with pytest.raises(bnc.NotionAuthError):
        client.pages_retrieve("p1")


def test_404_raises_not_found_error_without_retry():
    client, rec, _ = _client([_FakeHTTPError("u", 404)])
    with pytest.raises(bnc.NotionNotFoundError):
        client.pages_retrieve("missing")
    assert len(rec.requests) == 1


def test_400_raises_generic_notion_error_without_retry():
    client, rec, _ = _client(
        [_FakeHTTPError("u", 400, body={"message": "bad request"})]
    )
    with pytest.raises(bnc.NotionError) as ei:
        client.pages_retrieve("p1")
    assert not isinstance(
        ei.value,
        (
            bnc.NotionAuthError,
            bnc.NotionNotFoundError,
            bnc.NotionRateLimitError,
            bnc.NotionServerError,
        ),
    )
    assert ei.value.status == 400
    assert len(rec.requests) == 1


# --- Errors: retry logic ----------------------------------------------


def test_429_retries_with_retry_after_header():
    responses = [
        _FakeHTTPError("u", 429, headers={"Retry-After": "2"}),
        _FakeResponse(200, {"id": "p1"}),
    ]
    client, rec, cs = _client(responses)
    out = client.pages_retrieve("p1")
    assert out == {"id": "p1"}
    assert len(rec.requests) == 2
    assert cs.sleeps == [2.0]


def test_429_retries_with_exponential_backoff_when_no_header():
    responses = [
        _FakeHTTPError("u", 429),
        _FakeHTTPError("u", 429),
        _FakeResponse(200, {"id": "p1"}),
    ]
    client, rec, cs = _client(responses)
    client.pages_retrieve("p1")
    assert len(rec.requests) == 3
    # Two backoffs recorded, each within jitter bounds of 2^attempt
    assert len(cs.sleeps) == 2
    for attempt, delay in enumerate(cs.sleeps):
        base = 2.0**attempt
        assert delay >= max(0.1, base * 0.8)
        assert delay <= base * 1.2 + 0.1


def test_500_retries_and_succeeds():
    responses = [
        _FakeHTTPError("u", 500),
        _FakeHTTPError("u", 503),
        _FakeResponse(200, {"results": []}),
    ]
    client, rec, _ = _client(responses)
    client.databases_query("db-1")
    assert len(rec.requests) == 3


def test_429_retries_exhausted_raises_rate_limit_error():
    responses = [_FakeHTTPError("u", 429) for _ in range(6)]
    client, rec, _ = _client(responses, max_retries=5)
    with pytest.raises(bnc.NotionRateLimitError) as ei:
        client.pages_retrieve("p1")
    assert ei.value.status == 429
    assert len(rec.requests) == 6


def test_5xx_retries_exhausted_raises_server_error():
    responses = [_FakeHTTPError("u", 502) for _ in range(6)]
    client, _, _ = _client(responses, max_retries=5)
    with pytest.raises(bnc.NotionServerError):
        client.pages_retrieve("p1")


def test_network_error_is_retried_and_bubbles_up():
    responses = [
        urllib.error.URLError("connection refused"),
        urllib.error.URLError("connection refused"),
        _FakeResponse(200, {"id": "p1"}),
    ]
    client, rec, cs = _client(responses)
    client.pages_retrieve("p1")
    assert len(rec.requests) == 3
    assert len(cs.sleeps) == 2


def test_network_error_retries_exhausted_raises_notion_error():
    responses = [urllib.error.URLError("boom") for _ in range(6)]
    client, _, _ = _client(responses, max_retries=5)
    with pytest.raises(bnc.NotionError):
        client.pages_retrieve("p1")


def test_retry_after_non_numeric_falls_back_to_backoff():
    responses = [
        _FakeHTTPError("u", 429, headers={"Retry-After": "tomorrow"}),
        _FakeResponse(200, {"id": "p1"}),
    ]
    client, _, cs = _client(responses)
    client.pages_retrieve("p1")
    # Fell back to exponential (attempt=0 → base=1.0, 0.8..1.2)
    assert 0.1 <= cs.sleeps[0] <= 1.3


# --- Throttle ----------------------------------------------------------


def test_first_write_does_not_sleep():
    client, _, cs = _client([_FakeResponse(200, {"id": "p1"})])
    client.pages_create(parent={"database_id": "d"}, properties={})
    assert cs.sleeps == []


def test_second_write_sleeps_to_honor_throttle():
    client, _, cs = _client(
        [
            _FakeResponse(200, {"id": "p1"}),
            _FakeResponse(200, {"id": "p2"}),
        ],
        throttle_ms=350,
    )
    client.pages_create(parent={"database_id": "d"}, properties={})
    client.pages_create(parent={"database_id": "d"}, properties={})
    # Second call must have slept ≈ 0.35s (no clock advance between calls)
    assert len(cs.sleeps) == 1
    assert 0.3 <= cs.sleeps[0] <= 0.4


def test_reads_do_not_throttle():
    client, _, cs = _client(
        [
            _FakeResponse(200, {}),
            _FakeResponse(200, {}),
            _FakeResponse(200, {}),
        ],
    )
    for _ in range(3):
        client.pages_retrieve("p")
    assert cs.sleeps == []
