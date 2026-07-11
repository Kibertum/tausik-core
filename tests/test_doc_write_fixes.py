"""`gen_doc_constants.py --write` must repair exactly what `--check` flags.

The check_docs gate told users to "run gen_doc_constants.py and re-commit", but
the script only rewrote constants.json and left the README badges and prose
alone — so following the advice kept the gate red. These tests pin the fixer.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doc_drift_scanners import (  # noqa: E402
    scan_test_counts,
    write_cross_file_fixes,
)

PAYLOAD = {
    "test_count": 4540,
    "tausik_version": "1.6.0",
    "stacks_count": 25,
    "hooks_count": 21,
    "review_agents_count": 6,
    "mcp_main_tools": 124,
    "mcp_project_tools": 117,
    "mcp_brain_tools": 7,
}


def _readme(tmp_path, body: str) -> None:
    # write_cross_file_fixes walks CROSS_FILE_SCAN_TARGETS by name under repo_root.
    (tmp_path / "README.md").write_text(body, encoding="utf-8")


class TestWriteFixesCounts:
    def test_fixes_badge_bold_and_url(self, tmp_path):
        _readme(
            tmp_path,
            "[![1234 tests](https://x/badge/tests-1234-brightgreen.svg)](#p)\n"
            "- **1234 tests** — most-tested part.\n",
        )
        changed = write_cross_file_fixes(tmp_path, PAYLOAD)
        assert changed == ["README.md"]
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "tests-4540-brightgreen" in text
        assert "![4540 tests]" in text
        assert "**4540 tests**" in text
        assert "1234" not in text

    def test_fixes_russian_forms(self, tmp_path):
        _readme(
            tmp_path,
            "[![1234 тестов](https://x/badge/tests-1234-brightgreen.svg)](#p)\n"
            "- **1234 тестов** — ядро.\n",
        )
        write_cross_file_fixes(tmp_path, PAYLOAD)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "![4540 тестов]" in text
        assert "**4540 тестов**" in text
        assert "1234" not in text

    def test_never_touches_fenced_examples(self, tmp_path):
        _readme(
            tmp_path,
            "![1234 tests](https://x/badge/tests-1234-brightgreen.svg)\n"
            "```\n"
            "example badge: tests-999-brightgreen, ![999 tests], **999 tests**\n"
            "```\n",
        )
        write_cross_file_fixes(tmp_path, PAYLOAD)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "tests-999-brightgreen" in text, "fenced example must be preserved"
        assert "![999 tests]" in text
        assert "tests-4540-brightgreen" in text, "the real badge must be fixed"

    def test_idempotent(self, tmp_path):
        _readme(tmp_path, "![1234 tests](https://x/tests-1234-brightgreen.svg)\n")
        assert write_cross_file_fixes(tmp_path, PAYLOAD) == ["README.md"]
        assert write_cross_file_fixes(tmp_path, PAYLOAD) == [], "second run is a no-op"

    def test_in_sync_file_is_not_rewritten(self, tmp_path):
        _readme(tmp_path, "![4540 tests](https://x/tests-4540-brightgreen.svg)\n")
        assert write_cross_file_fixes(tmp_path, PAYLOAD) == []


class TestWriteFixesVersion:
    def test_fixes_current_version_ref(self, tmp_path):
        _readme(tmp_path, "[![v1.5.0](https://x/version-v1.5.0-blue.svg)](#r)\n")
        write_cross_file_fixes(tmp_path, PAYLOAD)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "v1.6.0" in text
        assert "v1.5.0" not in text

    def test_preserves_ref_precision(self, tmp_path):
        _readme(tmp_path, "See v1.5 and v1.5.0 here.\n")
        write_cross_file_fixes(tmp_path, PAYLOAD)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "v1.6 " in text and "v1.6.0" in text  # two-part stays two-part

    def test_foreign_version_untouched(self, tmp_path):
        _readme(tmp_path, "Implements SENAR v1.3 and needs Python v3.11.\n")
        write_cross_file_fixes(tmp_path, PAYLOAD)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "SENAR v1.3" in text
        assert "Python v3.11" in text


def test_writer_closes_every_gap_the_scanner_reports(tmp_path):
    """The core contract: after the writer, the matching scanner finds nothing.

    Any test-count form the scanner can flag, the writer must be able to fix —
    otherwise the gate's advice would leave the file red on that form.
    """
    _readme(
        tmp_path,
        "[![1111 tests](https://x/tests-1111-brightgreen.svg)]\n"
        "[![2222 тестов](https://x/tests-2222-brightgreen.svg)]\n"
        "- **3333 tests** / **4444 тестов**\n",
    )
    write_cross_file_fixes(tmp_path, PAYLOAD)
    assert scan_test_counts(tmp_path, PAYLOAD) == []
