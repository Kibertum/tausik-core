"""Парсеры команд `verify` и `receipt`.

Вынесено из project_parser.py: добавление одного флага (--no-tests-expected,
задача verify-no-test-mapped-dead-end) перевело файл через лимит в 400 строк.
Резать по границе команд честнее, чем ужимать help — справка агента и так
единственное место, где он узнаёт о существовании флага.
"""

from __future__ import annotations

from typing import Any


def add_verify_parsers(sub: Any) -> None:
    """Зарегистрировать `verify` и `receipt` на переданном subparsers."""
    vp = sub.add_parser("verify", help="Run scoped quality gates")
    vp.add_argument("--task")
    _scopes = ["lightweight", "standard", "high", "critical", "manual"]
    vp.add_argument("--scope", choices=_scopes, default="manual")
    vp.add_argument(
        "--no-tests-expected",
        action="store_true",
        help=(
            "Declare that the task's files are not expected to map to any test "
            "(docs, config, migrations). Without it an all-skipped run blocks. "
            "The run is recorded with no_tests_declared=1 so closures "
            "with no executed gate stay countable."
        ),
    )

    # --- receipt (v15-receipt-emit-on-verify) ---
    rcpt_p = sub.add_parser("receipt", help="Signed verify receipts (ed25519)")
    rcpt_sub = rcpt_p.add_subparsers(dest="receipt_cmd")
    rs = rcpt_sub.add_parser(
        "show",
        help="Print + re-verify the latest signed receipt",
        epilog="Example: tausik receipt show --task my-task",
    )
    rs.add_argument("--task", help="Latest receipt for this task slug")
    rs.add_argument("--run", type=int, help="Receipt of a specific verification_run id")
    rs.add_argument("--json", action="store_true", help="Print the raw signed envelope")
    re_ = rcpt_sub.add_parser(
        "export",
        help="Export a portable, self-verifiable receipt artifact",
        epilog="Example: tausik receipt export --task my-task",
    )
    re_.add_argument("--task", help="Latest receipt for this task slug")
    re_.add_argument("--run", type=int, help="Receipt of a specific verification_run id")
    re_.add_argument("--out", help="Output path (default .tausik/receipts/<task>-<sha8>.json)")
    re_.add_argument("--stdout", action="store_true", help="Print artifact instead of writing")
    rv = rcpt_sub.add_parser(
        "verify",
        help="Verify an exported receipt file offline (no DB/keystore)",
        epilog="Example: tausik receipt verify .tausik/receipts/my-task-abc12345.json",
    )
    rv.add_argument("file", help="Path to a tausik-receipt-export/v1 JSON file")
    rv.add_argument("--pub", help="Override key: 'ed25519:<64 hex>' from `tausik key show`")
