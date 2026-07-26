"""Tests for doc_drift_scanners — the hardened count patterns + split integrity.

Regression: the hooks-count scanner was adjacency-anchored (`\\b(\\d+)\\s+hooks\\b`),
so `21 real-time hooks` (an adjective between the number and 'hooks') drifted
uncaught — README said 21 while constants said 22. The pattern now tolerates an
optional real-time qualifier and the RU singular 'хук'. It must still ignore
fenced illustrative numbers and not false-positive on 'stack-scoped' prose.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doc_drift_scanners import (  # noqa: E402
    CROSS_FILE_SCAN_TARGETS,
    scan_code_counts,
    write_cross_file_fixes,
)

_PAYLOAD = {"hooks_count": 22}


def _write_readme(tmp_path, body: str):
    # scan_code_counts walks CROSS_FILE_SCAN_TARGETS by name under repo_root.
    assert "README.md" in CROSS_FILE_SCAN_TARGETS
    (tmp_path / "README.md").write_text(body, encoding="utf-8")


class TestHooksCountHardening:
    def test_flags_real_time_hooks_between_words(self, tmp_path):
        _write_readme(tmp_path, "- **21 real-time hooks** — task gate and more.\n")
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("hooks" in m and "21" in m for m in msgs), msgs

    def test_flags_ru_hyphenated_singular(self, tmp_path):
        _write_readme(tmp_path, "- **21 real-time-хук** — task gate.\n")
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("21" in m for m in msgs), msgs

    def test_in_sync_count_is_clean(self, tmp_path):
        _write_readme(tmp_path, "- **22 real-time hooks** — task gate.\n")
        assert scan_code_counts(tmp_path, _PAYLOAD) == []

    def test_ignores_fenced_illustrative_number(self, tmp_path):
        _write_readme(tmp_path, "```\n21 real-time hooks in this example\n```\n")
        assert scan_code_counts(tmp_path, _PAYLOAD) == []

    def test_no_false_positive_on_stack_prose(self, tmp_path):
        _write_readme(tmp_path, "TAUSIK has stack-scoped gates and 5 stack guides.\n")
        # 'hooks' pattern must not fire; 'stacks' plural pattern must not catch
        # the singular 'stack guides'.
        msgs = scan_code_counts(tmp_path, {"hooks_count": 22, "stacks_count": 25})
        assert msgs == [], msgs


class TestRolesCount:
    """roles_count closes the blind spot that let architecture.md keep '5 roles'
    after devops landed as the sixth built-in role."""

    _ROLES = {"roles_count": 6}

    def test_flags_stale_english_roles(self, tmp_path):
        _write_readme(tmp_path, "TAUSIK ships 5 roles out of the box.\n")
        msgs = scan_code_counts(tmp_path, self._ROLES)
        assert any("roles" in m and "5" in m for m in msgs), msgs

    def test_flags_stale_russian_roles(self, tmp_path):
        _write_readme(tmp_path, "Фреймворк несёт 5 ролей по умолчанию.\n")
        msgs = scan_code_counts(tmp_path, self._ROLES)
        assert any("5" in m for m in msgs), msgs

    def test_in_sync_count_is_clean(self, tmp_path):
        _write_readme(tmp_path, "Six built-in profiles: 6 roles, 6 ролей.\n")
        assert scan_code_counts(tmp_path, self._ROLES) == []

    def test_ignores_fenced_roles_tree_comment(self, tmp_path):
        # This is exactly the architecture.md shape: a stale count inside a fence.
        _write_readme(tmp_path, "```\nroles/  # 5 roles (developer, architect)\n```\n")
        assert scan_code_counts(tmp_path, self._ROLES) == []

    def test_no_false_positive_on_role_scoped_prose(self, tmp_path):
        _write_readme(tmp_path, "Gates are 6 role-scoped and the CLI has 3 role verbs.\n")
        assert scan_code_counts(tmp_path, self._ROLES) == []


class TestAutoFixerReExport:
    """write_cross_file_fixes is re-exported from doc_drift_scanners and repairs
    the hardened hooks pattern, but never inside a fenced block."""

    def test_fixes_real_time_hooks_and_is_idempotent(self, tmp_path):
        _write_readme(tmp_path, "- **21 real-time hooks** — task gate.\n")
        changed = write_cross_file_fixes(tmp_path, _PAYLOAD)
        assert changed == ["README.md"]
        assert "22 real-time hooks" in (tmp_path / "README.md").read_text(encoding="utf-8")
        assert write_cross_file_fixes(tmp_path, _PAYLOAD) == [], "second run is a no-op"

    def test_does_not_touch_fenced_numbers(self, tmp_path):
        _write_readme(tmp_path, "```\n21 real-time hooks\n```\n")
        assert write_cross_file_fixes(tmp_path, _PAYLOAD) == []
