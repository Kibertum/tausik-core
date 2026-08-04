"""Shared `_block` helper for gate modules.

Lifted out of `service_gates` when `gate_verify_first` was split off: both
modules record blocking failures in the same shape, and having the extracted
policy import it back from `service_gates` would have been circular.

`service_gates` re-exports the name, so existing callers and tests that do
`from service_gates import _block` keep working.
"""

from __future__ import annotations

import re
from typing import Any


def extract_files_from_gate_output(output: str) -> list[str]:
    """Parse `  path/to/file.py:  123 lines` entries out of gate output.

    Shared for the same reason as `_block`: both `service_gates` and the
    extracted `gate_verify_first` build blocking-failure entries with it.
    """
    return re.findall(r"^\s+([^\s:]+):\s+\d+\s+lines", output or "", re.MULTILINE)


def _block(report: dict[str, Any], gate: str, output: str, remediation: str, files=None) -> None:
    """Record a blocking gate failure. Several call sites repeated this dict."""
    report["passed"] = False
    entry = {"gate": gate, "files": list(files or []), "output": output}
    report["blocking_failures"].append({**entry, "remediation": remediation})
