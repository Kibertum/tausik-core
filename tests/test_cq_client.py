"""Tests for scripts/cq_client.py — CqClient HTTP client."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from cq_client import CqClient, get_cq_client


# ---------------------------------------------------------------------------
# URL scheme validation
# ---------------------------------------------------------------------------


class TestEndpointValidation:
    def test_http_endpoint_accepted(self):
        client = CqClient(endpoint="http://localhost:8742")
        assert client.endpoint == "http://localhost:8742"

    def test_https_endpoint_accepted(self):
        client = CqClient(endpoint="https://cq.example.com/")
        assert client.endpoint == "https://cq.example.com"

    def test_file_scheme_raises(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            CqClient(endpoint="file:///etc/passwd")

    def test_ftp_scheme_raises(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            CqClient(endpoint="ftp://evil.com/data")

    def test_empty_scheme_raises(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            CqClient(endpoint="no-scheme-at-all")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(data: object) -> MagicMock:
    """Create a mock urllib response that behaves as a context manager."""
    body = json.dumps(data).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# Connection-error graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @patch("cq_client.urllib.request.urlopen")
    def test_query_returns_empty_on_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        client = CqClient()
        result = client.query(domains=["testing"])
        assert result == []

    @patch("cq_client.urllib.request.urlopen")
    def test_propose_returns_none_on_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        client = CqClient()
        result = client.propose(domains=["testing"], summary="some insight")
        assert result is None

    @patch("cq_client.urllib.request.urlopen")
    def test_health_returns_false_on_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        client = CqClient()
        result = client.health()
        assert result is False


# ---------------------------------------------------------------------------
# _request URL building
# ---------------------------------------------------------------------------


class TestRequestBuildsCorrectURL:
    @patch("cq_client.urllib.request.urlopen")
    def test_url_with_params(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"ok": True})
        client = CqClient(endpoint="http://localhost:9000")
        client._request("GET", "/search", params={"q": "hello", "limit": 10})

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url.startswith("http://localhost:9000/search?")
        assert "q=hello" in req.full_url
        assert "limit=10" in req.full_url

    @patch("cq_client.urllib.request.urlopen")
    def test_url_with_list_params(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([])
        client = CqClient(endpoint="http://localhost:9000")
        client._request("GET", "/query", params={"domain": ["a", "b"]})

        req = mock_urlopen.call_args[0][0]
        assert "domain=a" in req.full_url
        assert "domain=b" in req.full_url

    @patch("cq_client.urllib.request.urlopen")
    def test_url_without_params(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"status": "ok"})
        client = CqClient(endpoint="http://localhost:9000")
        client._request("GET", "/health")

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://localhost:9000/health"


# ---------------------------------------------------------------------------
# Authorization header
# ---------------------------------------------------------------------------


class TestAuthorizationHeader:
    @patch("cq_client.urllib.request.urlopen")
    def test_bearer_token_sent(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"ok": True})
        client = CqClient(endpoint="http://localhost:9000", api_key="secret-token")
        client._request("GET", "/health")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer secret-token"

    @patch("cq_client.urllib.request.urlopen")
    def test_no_auth_header_without_key(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"ok": True})
        client = CqClient(endpoint="http://localhost:9000")
        client._request("GET", "/health")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") is None


# ---------------------------------------------------------------------------
# get_cq_client factory
# ---------------------------------------------------------------------------


class TestGetCqClient:
    def test_returns_none_without_config(self):
        assert get_cq_client({}) is None

    def test_returns_none_with_empty_endpoint(self):
        assert get_cq_client({"cq": {"endpoint": ""}}) is None

    def test_returns_client_with_valid_config(self):
        client = get_cq_client(
            {"cq": {"endpoint": "http://localhost:8742", "api_key": "k"}}
        )
        assert isinstance(client, CqClient)
        assert client.api_key == "k"


# ---------------------------------------------------------------------------
# confirm() method
# ---------------------------------------------------------------------------


class TestConfirm:
    @patch("cq_client.urllib.request.urlopen")
    def test_confirm_calls_correct_url(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"id": "u1", "confidence": 0.9})
        client = CqClient(endpoint="http://localhost:9000")
        result = client.confirm("u1")

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://localhost:9000/confirm/u1"
        assert req.get_method() == "POST"
        assert result == {"id": "u1", "confidence": 0.9}

    @patch("cq_client.urllib.request.urlopen")
    def test_confirm_encodes_special_chars_in_unit_id(self, mock_urlopen):
        mock_urlopen.return_value = _make_response({"id": "a/b c", "confidence": 0.5})
        client = CqClient(endpoint="http://localhost:9000")
        client.confirm("a/b c")

        req = mock_urlopen.call_args[0][0]
        assert "/confirm/a%2Fb%20c" in req.full_url

    @patch("cq_client.urllib.request.urlopen")
    def test_confirm_returns_none_on_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        client = CqClient()
        result = client.confirm("u1")
        assert result is None
