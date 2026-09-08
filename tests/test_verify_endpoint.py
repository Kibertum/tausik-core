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
import time

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


#: How long a server gets to start answering before the test gives up on it.
#: A DEADLINE with a condition, never a fixed pause: a `sleep` long enough to be
#: safe is wasted on every run and still a race on a loaded machine.
_READY_TIMEOUT_S = 10.0


def _wait_until_serving(httpd, timeout: float = _READY_TIMEOUT_S) -> None:
    """Block until the server ANSWERS, or fail the test saying it never did.

    `serve_forever` runs in another thread and the listening socket exists
    before that loop starts, so a client can connect to a server that is not yet
    accepting. Waiting on the socket's existence proves nothing; this waits on a
    completed request.

    Loud on failure (never a skip, never a hang): a server that did not come up
    must be distinguishable from an endpoint that answered wrongly, which is the
    whole subject of the tests below.
    """
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection(
                "127.0.0.1", httpd.server_address[1], timeout=1
            )
            conn.request("GET", "/healthz-probe-not-a-real-route")
            conn.getresponse().read()
            conn.close()
            return
        except (OSError, http.client.HTTPException) as exc:
            # BOTH families. `BadStatusLine` and `RemoteDisconnected` come from
            # `http.client`, not from `socket`, and only one of them is an
            # OSError — a probe that caught only OSError would let the other
            # escape and turn a not-yet-ready server into a fixture ERROR
            # rather than another attempt. Measured: one full-suite run in
            # seven produced 19 errors, one per test in this file.
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(0.01)
    raise AssertionError(
        f"the verify endpoint never began answering within {timeout:.0f}s "
        f"(last attempt: {last or 'no error recorded'})"
    )


@pytest.fixture
def server(keyed_project):
    httpd = make_server(keyed_project, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    _wait_until_serving(httpd)
    try:
        yield httpd, keyed_project
    finally:
        # `shutdown` asks the loop to stop and WAITS for it, so the socket is
        # closed only once no handler is still writing to a client. Closing
        # first would abort an in-flight response, which is the shape of failure
        # this file was flaking with.
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=_READY_TIMEOUT_S)


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
        # The same wait as the fixture, for the same reason: this server is
        # built by hand and would otherwise carry the race the fixture no
        # longer has. Two places starting a server, one of them careful, is how
        # a fixed race comes back.
        _wait_until_serving(httpd)
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
            thread.join(timeout=_READY_TIMEOUT_S)


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


class TestTheEndpointDoesNotShareItsPort:
    """MEASURED (session #235): with the stock `ThreadingHTTPServer`, two
    servers bound the SAME port and both succeeded. `http.server` sets
    `allow_reuse_address = 1`, and on Windows `SO_REUSEADDR` permits binding an
    address that is ACTIVELY in use rather than merely lingering in TIME_WAIT.

    Beyond the tests: `tausik serve` binds 8765 to answer receipt-verification
    requests, and a port any other local process may join is a port whose
    answers cannot be relied on.
    """

    def test_a_second_server_cannot_take_the_same_port(self, keyed_project):
        first = make_server(keyed_project, port=0)
        port = first.server_address[1]
        try:
            with pytest.raises(OSError) as caught:
                make_server(keyed_project, port=port)
            assert caught.value.errno in (48, 98, 10048), (
                f"bind failed for an unexpected reason: {caught.value!r}"
            )
        finally:
            first.server_close()

    def test_posix_keeps_the_flag_and_windows_does_not(self):
        """Turning the flag off everywhere would break restart-after-TIME_WAIT
        on POSIX — a real regression to fix a problem that platform lacks."""
        from verify_endpoint import _VerifyServer

        assert _VerifyServer.allow_reuse_address is (sys.platform != "win32")


class TestTheReadinessWaitIsAConditionNotAPause:
    """AC3 and AC4: the fixture waits for the server to ANSWER, and a server
    that never comes up fails the test loudly instead of hanging or skipping."""

    def test_a_server_that_never_answers_fails_with_a_named_reason(self):
        class _Never:
            server_address = ("127.0.0.1", 1)  # nothing listens on port 1

        with pytest.raises(AssertionError) as caught:
            _wait_until_serving(_Never(), timeout=0.3)
        message = str(caught.value)
        assert "never began answering" in message
        assert "last attempt" in message

    def test_it_returns_as_soon_as_the_server_answers(self, keyed_project):
        httpd = make_server(keyed_project, port=0)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            started = time.monotonic()
            _wait_until_serving(httpd)
            assert time.monotonic() - started < _READY_TIMEOUT_S / 2, (
                "the wait behaved like a fixed pause rather than a condition"
            )
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=_READY_TIMEOUT_S)
