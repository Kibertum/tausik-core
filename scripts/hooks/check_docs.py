"""Doc-constants drift hook (v14-ci-doc-check).

Run by:
  - GitHub Actions `tests.yml` job
  - Optional local pre-commit (developer adds `python scripts/hooks/check_docs.py`
    to ``.git/hooks/pre-commit`` per docs/en/dev-doc-checks.md)

Exits 0 if `docs/_generated/constants.json` is in sync with
`pyproject.toml` + live MCP tool counts. Exits 1 if drift is detected,
with a hint on how to regenerate. Designed to never crash a hook on
external repos: missing ``pyproject.toml`` → exit 0 with a SKIP message
(AC-3 negative: meaningful skip when run outside a TAUSIK checkout).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path | None:
    here = start.resolve()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").is_file():
            return p
    return None


def main(argv: list[str] | None = None) -> int:
    root = _find_repo_root(Path.cwd())
    if root is None:
        # AC-3 negative — friendly skip instead of crash on external clones.
        print(
            "[check_docs] No pyproject.toml found above cwd — skipping doc-constants drift check.",
            file=sys.stderr,
        )
        return 0

    gen = root / "scripts" / "gen_doc_constants.py"
    if not gen.is_file():
        print(
            "[check_docs] gen_doc_constants.py not found — skipping (legacy checkout).",
            file=sys.stderr,
        )
        return 0

    proc = subprocess.run(
        [sys.executable, str(gen), "--check"],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if proc.returncode == 0:
        return 0

    sys.stderr.write(proc.stderr or proc.stdout)
    sys.stderr.write(
        "\n[check_docs] doc-constants drift — run "
        "`python scripts/gen_doc_constants.py` and re-commit.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
