"""Generated docs constants (version + MCP counts) stay aligned with code."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from gen_doc_constants import build_constants_doc, output_json_path, run_main  # noqa: E402
from mcp_tool_counts import count_mcp_tool_totals  # noqa: E402


def test_build_constants_matches_tool_totals():
    d = build_constants_doc(REPO)
    n_p, n_b, n_r = count_mcp_tool_totals(REPO)
    assert isinstance(d["tausik_version"], str) and d["tausik_version"]
    assert d["mcp_project_tools"] == n_p
    assert d["mcp_brain_tools"] == n_b
    assert d["mcp_rag_tools"] == n_r
    assert d["mcp_main_tools"] == n_p + n_b
    assert d["mcp_tools_with_optional_rag"] == n_p + n_b + n_r


def test_constants_json_file_matches_live():
    """Committed ``constants.json`` must match generator (regression guard)."""
    path = output_json_path(REPO)
    if not path.is_file():
        pytest.skip(f"missing {path} — run python scripts/gen_doc_constants.py")
    import json

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == build_constants_doc(REPO)


def test_run_main_check_fails_on_payload_drift(monkeypatch: pytest.MonkeyPatch):
    import gen_doc_constants as g

    path = output_json_path(REPO)
    if not path.is_file():
        pytest.skip("constants.json not generated yet")

    def _fake(_root: Path) -> dict[str, object]:
        return {"schema_version": 99999, "tausik_version": "0.0.0"}

    monkeypatch.setattr(g, "build_constants_doc", _fake)
    assert run_main(REPO, check=True) == 1
