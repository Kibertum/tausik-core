"""Generated docs constants (version + MCP counts) stay aligned with code."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from gen_doc_constants import (  # noqa: E402
    CROSS_FILE_SCAN_TARGETS,
    build_constants_doc,
    output_json_path,
    run_main,
    scan_mcp_tool_counts,
    scan_test_counts,
    scan_version_refs,
)
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


# Cross-file version-ref scanner ------------------------------------------


def _seed_cross_file_repo(tmp_path: Path) -> Path:
    """Build a fake repo with the standard scan-target files plus pyproject."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.4.0"\n', encoding="utf-8"
    )
    for rel in CROSS_FILE_SCAN_TARGETS:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_scan_version_refs_clean_when_all_match(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text("# Project\n\nv1.4 ships features X and Y.\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("v1.4.0 release notes.\n", encoding="utf-8")
    assert scan_version_refs(repo, "1.4.0") == []


def test_scan_version_refs_flags_minor_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text("# Project\n\nv1.3 features.\n", encoding="utf-8")
    drifts = scan_version_refs(repo, "1.4.0")
    assert any("README.md:3" in d and "v1.3" in d for d in drifts)


def test_scan_version_refs_flags_patch_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text("\n\nv1.4.5 doc note.\n", encoding="utf-8")
    drifts = scan_version_refs(repo, "1.4.0")
    assert any("v1.4.5" in d for d in drifts)


def test_scan_version_refs_skips_foreign_versions(tmp_path: Path):
    """SENAR / Python / OWASP versions are independent — must NOT be flagged."""
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text(
        "# Project\n\nImplements SENAR v1.3 spec.\n"
        "Requires Python v3.11.0 or newer.\n"
        "Follows OWASP v2.0 guidelines.\n",
        encoding="utf-8",
    )
    assert scan_version_refs(repo, "1.4.0") == []


def test_scan_version_refs_skips_fenced_code_blocks(tmp_path: Path):
    """Refs inside ``` ... ``` are documentation examples, not real version refs."""
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text(
        "# Project\n\n```\nThis README mentions v1.3 in code\n```\n",
        encoding="utf-8",
    )
    assert scan_version_refs(repo, "1.4.0") == []


def test_run_main_check_fails_on_cross_file_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_main(check=True) returns 1 when constants OK but doc refs drift."""
    import gen_doc_constants as g

    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text("v1.3 features\n", encoding="utf-8")
    monkeypatch.setattr(
        g, "build_constants_doc", lambda _root: {"schema_version": 1, "tausik_version": "1.4.0"}
    )
    # Generate constants.json so the first stage of --check passes
    assert run_main(repo, check=False) == 0
    # Now --check should fail because of cross-file scan
    assert run_main(repo, check=True) == 1


def test_run_main_check_passes_with_skip_cross_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--skip-cross-files preserves the legacy behaviour (constants.json only)."""
    import gen_doc_constants as g

    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text("v1.3 features\n", encoding="utf-8")
    monkeypatch.setattr(
        g, "build_constants_doc", lambda _root: {"schema_version": 1, "tausik_version": "1.4.0"}
    )
    assert run_main(repo, check=False) == 0
    assert run_main(repo, check=True, skip_cross_files=True) == 0


# Cross-file MCP tool-count scanner ---------------------------------------


_FAKE_MCP_PAYLOAD: dict[str, object] = {
    "schema_version": 1,
    "tausik_version": "1.4.0",
    "mcp_project_tools": 93,
    "mcp_brain_tools": 7,
    "mcp_main_tools": 100,
    "mcp_rag_tools": 7,
    "mcp_tools_with_optional_rag": 107,
}


def test_scan_mcp_counts_clean_when_all_match(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text(
        "**100 MCP tools** (93 project + 7 brain) — programmatic access.\n",
        encoding="utf-8",
    )
    (repo / "AGENTS.md").write_text(
        "Total: 93 project tools + 7 brain tools = 100.\n",
        encoding="utf-8",
    )
    (repo / "docs/en/mcp.md").write_text(
        "## Shared Brain (`tausik-brain`, 7 tools)\n",
        encoding="utf-8",
    )
    assert scan_mcp_tool_counts(repo, _FAKE_MCP_PAYLOAD) == []


def test_scan_mcp_counts_flags_brain_header_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "docs/en/mcp.md").write_text(
        "## Shared Brain (`tausik-brain`, 6 tools)\n",
        encoding="utf-8",
    )
    drifts = scan_mcp_tool_counts(repo, _FAKE_MCP_PAYLOAD)
    assert any("docs/en/mcp.md:1" in d and "tausik-brain" in d and "found=6" in d for d in drifts)


def test_scan_mcp_counts_flags_project_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "AGENTS.md").write_text(
        "We expose 96 project tools today.\n",
        encoding="utf-8",
    )
    drifts = scan_mcp_tool_counts(repo, _FAKE_MCP_PAYLOAD)
    assert any("AGENTS.md:1" in d and "project count" in d and "found=96" in d for d in drifts)


def test_scan_mcp_counts_flags_pair_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text("Surface: (90 project + 10 brain)\n", encoding="utf-8")
    drifts = scan_mcp_tool_counts(repo, _FAKE_MCP_PAYLOAD)
    assert any("README.md:1" in d and "project+brain pair" in d for d in drifts)


def test_scan_mcp_counts_skips_fenced_code_blocks(tmp_path: Path):
    """Counts inside ``` ... ``` are doc examples, not authoritative refs."""
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text(
        "Counts in code\n\n```\n90 project tools (legacy example)\n```\n",
        encoding="utf-8",
    )
    assert scan_mcp_tool_counts(repo, _FAKE_MCP_PAYLOAD) == []


def test_run_main_check_passes_with_skip_mcp_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--skip-mcp-counts disables only the MCP-counts scan; version-ref check stays on."""
    import gen_doc_constants as g

    repo = _seed_cross_file_repo(tmp_path)
    (repo / "docs/en/mcp.md").write_text(
        "## Shared Brain (`tausik-brain`, 6 tools)\n", encoding="utf-8"
    )
    monkeypatch.setattr(g, "build_constants_doc", lambda _root: dict(_FAKE_MCP_PAYLOAD))
    assert run_main(repo, check=False) == 0
    # Without skip — fails on brain drift
    assert run_main(repo, check=True) == 1
    # With skip-mcp-counts — passes (no version drift in this fixture)
    assert run_main(repo, check=True, skip_mcp_counts=True) == 0


# Cross-file test-count scanner -------------------------------------------


_FAKE_TEST_COUNT_PAYLOAD: dict[str, object] = {
    "schema_version": 1,
    "tausik_version": "1.4.0",
    "test_count": 3050,
}


def test_scan_test_counts_clean_when_all_match(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "AGENTS.md").write_text(
        "Run pytest suite (3050 tests) before merging.\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        "[![3050 tests](https://example.com/badge/tests-3050%20passed-green.svg)](#)\n",
        encoding="utf-8",
    )
    assert scan_test_counts(repo, _FAKE_TEST_COUNT_PAYLOAD) == []


def test_scan_test_counts_flags_pytest_suite_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "AGENTS.md").write_text(
        "tests/             pytest suite (2590 tests)\n",
        encoding="utf-8",
    )
    drifts = scan_test_counts(repo, _FAKE_TEST_COUNT_PAYLOAD)
    assert any(
        "AGENTS.md:1" in d and "pytest suite count" in d and "found=2590" in d for d in drifts
    )


def test_scan_test_counts_flags_badge_drift(tmp_path: Path):
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "README.md").write_text(
        "[![2590 tests](https://example.com/badge/tests-2590%20passed-green.svg)](#)\n",
        encoding="utf-8",
    )
    drifts = scan_test_counts(repo, _FAKE_TEST_COUNT_PAYLOAD)
    # Both badge URL and badge label patterns fire
    assert any("badge URL count" in d and "found=2590" in d for d in drifts)
    assert any("badge label count" in d and "found=2590" in d for d in drifts)


def test_scan_test_counts_skips_fenced_code_blocks(tmp_path: Path):
    """pytest suite (N tests) inside fenced repo-structure blocks is skipped."""
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "AGENTS.md").write_text(
        "Repo layout:\n\n```\ntests/   pytest suite (2590 tests)\n```\n",
        encoding="utf-8",
    )
    assert scan_test_counts(repo, _FAKE_TEST_COUNT_PAYLOAD) == []


def test_scan_test_counts_does_not_flag_illustrative_numbers(tmp_path: Path):
    """Phrases like 'Never add 5 tests' must NOT be flagged — narrow patterns only."""
    repo = _seed_cross_file_repo(tmp_path)
    (repo / "AGENTS.md").write_text(
        "Never add 5 tests where one parametrized test covers the same matrix.\n",
        encoding="utf-8",
    )
    assert scan_test_counts(repo, _FAKE_TEST_COUNT_PAYLOAD) == []


def test_run_main_check_passes_with_skip_test_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--skip-test-count disables only the test-count scan; other scans stay on."""
    import gen_doc_constants as g

    repo = _seed_cross_file_repo(tmp_path)
    (repo / "AGENTS.md").write_text("pytest suite (2590 tests)\n", encoding="utf-8")
    monkeypatch.setattr(g, "build_constants_doc", lambda _root: dict(_FAKE_TEST_COUNT_PAYLOAD))
    assert run_main(repo, check=False) == 0
    assert run_main(repo, check=True) == 1
    assert run_main(repo, check=True, skip_test_count=True) == 0
