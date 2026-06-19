"""Tests for scripts/verify_endpoint.py (v15-nosdk-verify-endpoint).

End-to-end over real HTTP (port 0, background thread): verdict + signed
receipt, offline receipt verification, 400/404/503 negatives, no private
key material in any response.
"""

from __future__ import annotations

import http.client
import json
import os
import sys
import threading

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
import crypto_sign  # noqa: E402
from verify_endpoint import make_server  # noqa: E402

_GATES_OK = [
    {"name": "pytest", "passed": True, "severity": "block"},
    {"name": "hadolint", "passed": True, "severity": "warn", "skipped": True},
]


@pytest.fixture
def keyed_project(tmp_path):
    crypto_keys.init_keys(str(tmp_path))
    return str(tmp_path)


@pytest.fixture
def server(keyed_project):
    httpd = make_server(keyed_project, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, keyed_project
    httpd.shutdown()
    httpd.server_close()


def _request(httpd, method, path, payload=None):
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
    try:
        body = json.dumps(payload) if payload is not None else None
        conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        return resp.status, json.loads(resp.read().decode("utf-8"))
    finally:
        conn.close()


class TestVerify:
    def test_green_gates_signed_receipt(self, server):
        httpd, project = server
        status, data = _request(
            httpd, "POST", "/verify", {"task_slug": "ci-task", "gates": _GATES_OK}
        )
        assert status == 200
        assert data["passed"] is True and data["blocking_failed"] == []
        env = data["envelope"]
        assert env["envelope"] == "tausik-signed/v1"
        assert crypto_sign.verify_receipt(env, public=crypto_keys.load_public(project))
        # receipts attest only gates that RAN
        assert [g["name"] for g in env["receipt"]["gates"]] == ["pytest"]

    def test_blocking_failure_fails_verdict(self, server):
        httpd, project = server
        gates = [{"name": "pytest", "passed": False, "severity": "block"}]
        status, data = _request(httpd, "POST", "/verify", {"task_slug": "t", "gates": gates})
        assert status == 200
        assert data["passed"] is False and data["blocking_failed"] == ["pytest"]
        assert crypto_sign.verify_receipt(data["envelope"], public=crypto_keys.load_public(project))

    def test_all_skipped_is_not_a_pass(self, server):
        httpd, _ = server
        gates = [{"name": "pytest", "passed": True, "severity": "block", "skipped": True}]
        status, data = _request(httpd, "POST", "/verify", {"task_slug": "t", "gates": gates})
        assert status == 200
        assert data["passed"] is False and data["all_skipped"] is True

    def test_tampered_envelope_fails_receipt_verify(self, server):
        httpd, _ = server
        _, data = _request(httpd, "POST", "/verify", {"task_slug": "t", "gates": _GATES_OK})
        env = data["envelope"]
        env["receipt"]["passed"] = False
        status, check = _request(httpd, "POST", "/receipt/verify", env)
        assert status == 200 and check["valid"] is False

    def test_receipt_verify_roundtrip(self, server):
        httpd, _ = server
        _, data = _request(httpd, "POST", "/verify", {"task_slug": "t", "gates": _GATES_OK})
        status, check = _request(httpd, "POST", "/receipt/verify", data["envelope"])
        assert status == 200 and check["valid"] is True


class TestNegatives:
    @pytest.mark.parametrize(
        "payload,fragment",
        [
            ({"gates": _GATES_OK}, "task_slug"),
            ({"task_slug": "t"}, "gates"),
            ({"task_slug": "t", "gates": []}, "gates"),
            ({"task_slug": "t", "gates": [{"passed": True}]}, "name"),
            ({"task_slug": "t", "gates": _GATES_OK, "ran_at": "yesterday"}, "ran_at"),
        ],
    )
    def test_bad_input_is_400(self, server, payload, fragment):
        httpd, _ = server
        status, data = _request(httpd, "POST", "/verify", payload)
        assert status == 400
        assert fragment in data["error"]

    def test_invalid_json_is_400(self, server):
        httpd, _ = server
        conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        try:
            conn.request("POST", "/verify", body="{nope", headers={})
            resp = conn.getresponse()
            assert resp.status == 400
        finally:
            conn.close()

    def test_unknown_path_is_404(self, server):
        httpd, _ = server
        assert _request(httpd, "GET", "/nope")[0] == 404
        assert _request(httpd, "POST", "/nope", {})[0] == 404

    def test_no_key_is_503(self, tmp_path):
        httpd = make_server(str(tmp_path / "keyless"), port=0)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            status, data = _request(
                httpd, "POST", "/verify", {"task_slug": "t", "gates": _GATES_OK}
            )
            assert status == 503
            assert "key init" in data["error"]
            assert _request(httpd, "GET", "/key")[0] == 503
        finally:
            httpd.shutdown()
            httpd.server_close()


class TestInfoEndpoints:
    def test_healthz(self, server):
        httpd, _ = server
        status, data = _request(httpd, "GET", "/healthz")
        assert status == 200 and data["ok"] is True

    def test_key_is_public_only(self, server):
        httpd, project = server
        status, data = _request(httpd, "GET", "/key")
        assert status == 200
        assert data["fingerprint"] == crypto_keys.fingerprint(crypto_keys.load_public(project))
        seed_hex = crypto_keys.load_seed(project).hex()
        assert seed_hex not in json.dumps(data)
