"""Stateless HTTP verify endpoint (v15-nosdk-verify-endpoint, Sift Lite).

Makes TAUSIK attestation reachable from ANY agent or CI — no MCP, no
hooks, no SDK. Pure stdlib (http.server + json), no DB access:

    POST /verify          {task_slug, gates: [{name, passed, severity,
                           skipped?}], scope?, git_sha?, files_hash?}
                          -> 200 {passed, envelope}   (tausik-signed/v1)
    POST /receipt/verify  envelope OR tausik-receipt-export/v1 artifact
                          -> 200 {valid, detail}
    GET  /key             -> public key + fingerprint (never the seed)
    GET  /healthz         -> {ok: true}

Verdict semantics mirror the local verify pipeline: every non-skipped
gate with severity=block must pass, AND at least one gate must have
actually run (an all-skipped run proves nothing — same rule as
run_gates_with_cache). Receipts attest only gates that ran.

Security posture: binds 127.0.0.1 by default (localhost CI tool, no
auth layer); --host overrides deliberately. The private seed never
leaves crypto_keys; responses carry the public key only.
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MAX_BODY_BYTES = 512 * 1024  # gates lists are small; reject abuse early
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class RequestError(Exception):
    """400-class input problem; message is safe to echo to the client."""


def _utcnow_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_gates(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise RequestError("gates: non-empty list required")
    gates: list[dict[str, Any]] = []
    for i, g in enumerate(raw):
        if not isinstance(g, dict) or not isinstance(g.get("name"), str) or not g["name"]:
            raise RequestError(f"gates[{i}]: object with a non-empty 'name' required")
        gates.append(
            {
                "name": g["name"],
                "passed": bool(g.get("passed", False)),
                "severity": str(g.get("severity", "warn")),
                "skipped": bool(g.get("skipped", False)),
            }
        )
    return gates


def handle_verify(body: dict[str, Any], project_dir: str) -> dict[str, Any]:
    """POST /verify — verdict + signed receipt. Raises RequestError on input."""
    task_slug = body.get("task_slug")
    if not isinstance(task_slug, str) or not task_slug.strip():
        raise RequestError("task_slug: non-empty string required")
    gates = _validate_gates(body.get("gates"))

    ran = [g for g in gates if not g["skipped"]]
    blocking_failed = [g["name"] for g in ran if g["severity"] == "block" and not g["passed"]]
    has_real_pass = any(g["passed"] for g in ran)
    passed = not blocking_failed and has_real_pass

    ran_at = body.get("ran_at") or _utcnow_iso()
    if not isinstance(ran_at, str) or not _ISO_RE.match(ran_at):
        raise RequestError("ran_at: ISO-8601 string required when provided")

    import crypto_keys
    from crypto_receipt import ReceiptError, build_receipt
    from crypto_sign import sign_receipt

    public = crypto_keys.load_public(project_dir)  # KeyError_ -> 503 upstream
    try:
        receipt = build_receipt(
            task_slug=task_slug.strip(),
            git_sha=body.get("git_sha") if isinstance(body.get("git_sha"), str) else None,
            scope=str(body.get("scope") or "manual"),
            gates=[{k: g[k] for k in ("name", "passed", "severity")} for g in ran],
            passed=passed,
            ran_at=ran_at,
            files_hash=(
                body.get("files_hash") if isinstance(body.get("files_hash"), str) else None
            ),
            key_fingerprint=crypto_keys.fingerprint(public),
        )
        envelope = sign_receipt(project_dir, receipt)
    except ReceiptError as e:
        raise RequestError(f"receipt: {e}") from e
    return {
        "passed": passed,
        "blocking_failed": blocking_failed,
        "all_skipped": not ran,
        "envelope": envelope,
    }


def handle_receipt_verify(body: dict[str, Any], project_dir: str) -> dict[str, Any]:
    """POST /receipt/verify — accepts an envelope or an export artifact."""
    if not isinstance(body, dict):
        raise RequestError("JSON object required")
    if body.get("export"):
        from receipt_export import ExportError, verify_export

        try:
            valid, detail = verify_export(body)
        except ExportError as e:
            raise RequestError(str(e)) from e
        return {"valid": valid, "detail": detail}
    if body.get("envelope") == "tausik-signed/v1":
        import crypto_keys
        import crypto_sign

        public = crypto_keys.load_public(project_dir)
        valid = crypto_sign.verify_receipt(body, public=public)
        return {
            "valid": valid,
            "detail": f"checked against the project public key ({crypto_keys.fingerprint(public)})",
        }
    raise RequestError("expected a tausik-signed/v1 envelope or a receipt-export artifact")


def make_handler(project_dir: str) -> type[BaseHTTPRequestHandler]:
    class VerifyHandler(BaseHTTPRequestHandler):
        server_version = "tausik-verify/1"

        def log_message(self, fmt: str, *args: Any) -> None:  # quiet by default
            pass

        def _send(self, code: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError as e:
                raise RequestError("bad Content-Length") from e
            if length <= 0:
                raise RequestError("empty body")
            if length > MAX_BODY_BYTES:
                raise RequestError(f"body exceeds {MAX_BODY_BYTES} bytes")
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                raise RequestError(f"invalid JSON: {e}") from e
            if not isinstance(data, dict):
                raise RequestError("JSON object required")
            return data

        def do_GET(self) -> None:  # noqa: N802 — http.server contract
            if self.path == "/healthz":
                self._send(200, {"ok": True, "service": "tausik-verify"})
                return
            if self.path == "/key":
                import crypto_keys

                try:
                    self._send(200, crypto_keys.key_info(project_dir))
                except crypto_keys.KeyError_ as e:
                    self._send(503, {"error": f"{e}"})
                return
            self._send(404, {"error": f"unknown path {self.path}"})

        def do_POST(self) -> None:  # noqa: N802 — http.server contract
            import crypto_keys

            routes = {"/verify": handle_verify, "/receipt/verify": handle_receipt_verify}
            handler = routes.get(self.path)
            if handler is None:
                self._send(404, {"error": f"unknown path {self.path}"})
                return
            try:
                body = self._read_body()
                self._send(200, handler(body, project_dir))
            except RequestError as e:
                self._send(400, {"error": str(e)})
            except crypto_keys.KeyError_ as e:
                self._send(503, {"error": f"{e} (run `tausik key init` in the project)"})
            except Exception:  # noqa: BLE001 — never leak a traceback to the wire
                self._send(500, {"error": "internal error"})

    return VerifyHandler


def make_server(project_dir: str, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(project_dir))


def serve(project_dir: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = make_server(project_dir, host, port)
    print(f"tausik verify endpoint on http://{host}:{httpd.server_address[1]} (Ctrl+C stops)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
