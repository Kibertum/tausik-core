"""Runnable reference client from docs/{en,ru}/no-sdk-verify.md.

This file IS the documented working example (v15-nosdk-docs-example):
a pure-stdlib http.client integration with `tausik serve`, exercised
against a live endpoint. If the doc's code drifts from reality, this
breaks.
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
from verify_endpoint import make_server  # noqa: E402


# --- the documented client (kept in sync with no-sdk-verify.md) -------------


class CiExit(SystemExit):
    """The doc's client calls sys.exit(msg); tests capture it as this."""


def submit_gates(host: str, port: int, task_slug: str, gates: list[dict]) -> dict:
    conn = http.client.HTTPConnection(host, port, timeout=30)
    conn.request(
        "POST",
        "/verify",
        body=json.dumps({"task_slug": task_slug, "gates": gates}),
        headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    data = json.loads(resp.read())
    if resp.status == 503:
        raise CiExit(f"endpoint has no signing key: {data['error']}")
    if resp.status != 200:
        raise CiExit(f"verify request rejected ({resp.status}): {data['error']}")
    return data


def ci_main(host: str, port: int, receipt_path: str) -> int:
    """The doc's __main__ flow: submit, persist receipt, exit 1 on red."""
    result = submit_gates(
        host,
        port,
        "ci-build-42",
        [{"name": "pytest", "passed": True, "severity": "block"}],
    )
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(result["envelope"], f)
    return 0 if result["passed"] else 1


# --- live-endpoint exercise --------------------------------------------------


@pytest.fixture
def server(tmp_path):
    project = str(tmp_path)
    crypto_keys.init_keys(project)
    httpd = make_server(project, port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield "127.0.0.1", httpd.server_address[1], project
    httpd.shutdown()
    httpd.server_close()


class TestDocumentedExample:
    def test_green_ci_flow_exits_zero_and_writes_receipt(self, server, tmp_path):
        host, port, project = server
        receipt_path = str(tmp_path / "receipt.json")
        assert ci_main(host, port, receipt_path) == 0
        # the persisted receipt re-verifies through the endpoint, as in the doc
        envelope = json.loads(open(receipt_path, encoding="utf-8").read())
        conn = http.client.HTTPConnection(host, port, timeout=30)
        conn.request("POST", "/receipt/verify", body=json.dumps(envelope), headers={})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        assert resp.status == 200 and data["valid"] is True

    def test_red_verdict_exits_one(self, server):
        host, port, _ = server
        result = submit_gates(
            host,
            port,
            "ci-red",
            [{"name": "pytest", "passed": False, "severity": "block"}],
        )
        assert result["passed"] is False
        assert (0 if result["passed"] else 1) == 1  # the doc's exit line

    def test_rejected_request_exits_with_message(self, server):
        host, port, _ = server
        with pytest.raises(CiExit, match="rejected \\(400\\)"):
            submit_gates(host, port, "", [])

    def test_keyless_endpoint_exits_with_hint(self, tmp_path):
        httpd = make_server(str(tmp_path / "keyless"), port=0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            with pytest.raises(CiExit, match="no signing key"):
                submit_gates(
                    "127.0.0.1",
                    httpd.server_address[1],
                    "t",
                    [{"name": "pytest", "passed": True, "severity": "block"}],
                )
        finally:
            httpd.shutdown()
            httpd.server_close()
