"""CLI handler for `tausik serve` — stateless HTTP verify endpoint."""

from __future__ import annotations

import os
import sys


def cmd_serve(svc, args) -> None:
    from verify_endpoint import serve

    host = getattr(args, "host", None) or "127.0.0.1"
    port = getattr(args, "port", None)
    if port is None:
        port = 8765
    if host != "127.0.0.1" and not getattr(args, "yes_expose", False):
        print(
            f"Refusing to bind {host}: the endpoint has no auth layer. "
            "Re-run with --yes-expose if you really want a non-localhost bind.",
            file=sys.stderr,
        )
        sys.exit(2)
    serve(os.getcwd(), host=host, port=int(port))


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
