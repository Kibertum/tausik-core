"""Tests for doc_drift_scanners — the hardened count patterns + split integrity.

Regression: the hooks-count scanner was adjacency-anchored (`\\b(\\d+)\\s+hooks\\b`),
so `21 real-time hooks` (an adjective between the number and 'hooks') drifted
uncaught — README said 21 while constants said 22. The pattern now tolerates an
allow-list qualifier (real-time / Python / active / активн…) and the RU singular
'хук', and hooks.md — which hardcodes the count in its header but sat outside
every scan list — is now a CODE_COUNT_EXTRA_TARGET. It must still ignore fenced
illustrative numbers, leave hooks.md's historical version refs alone, and not
false-positive on 'stack-scoped' prose or an unrelated noun before 'hooks'.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doc_drift_common import (  # noqa: E402
    CODE_COUNT_EXTRA_TARGETS,
    VERSION_SCAN_TARGETS,
)
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


def _write_target(tmp_path, rel: str, body: str):
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


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


class TestHooksCountQualifiers:
    """hooks.md phrases the count as '22 Python hooks' / '22 Python-хука' — a
    'Python'/'active'/'активн…' qualifier the old adjacency-only pattern (and even
    the real-time-only broadening) missed. Regression for docs-enforcement-drift-
    matrix: the header drifted to '20 Python hooks / = 21' across 1.8 uncaught."""

    def test_flags_python_hooks_en(self, tmp_path):
        _write_readme(tmp_path, "**20 Python hooks + 1 shell** ship.\n")
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("20" in m and "hooks" in m for m in msgs), msgs

    def test_flags_active_hooks_en(self, tmp_path):
        _write_readme(tmp_path, "21 active hooks are wired.\n")
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("21" in m for m in msgs), msgs

    def test_flags_python_hyphen_hook_ru(self, tmp_path):
        _write_readme(tmp_path, "**20 Python-хука** идут.\n")
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("20" in m for m in msgs), msgs

    def test_flags_active_hook_ru(self, tmp_path):
        _write_readme(tmp_path, "21 активный хук идёт.\n")
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("21" in m for m in msgs), msgs

    def test_in_sync_python_hooks_clean(self, tmp_path):
        _write_readme(tmp_path, "**22 Python hooks + 1 shell** — 23 gates total.\n")
        assert scan_code_counts(tmp_path, _PAYLOAD) == []

    def test_qualifier_is_allowlist_not_greedy(self, tmp_path):
        # An unrelated noun between the number and 'hooks' must NOT be swallowed —
        # the qualifier is an explicit allow-list (real-time/python/active), not \\w+.
        _write_readme(tmp_path, "We ran 5 integration tests before the hooks fire.\n")
        assert scan_code_counts(tmp_path, _PAYLOAD) == []


class TestHooksMdInScanSet:
    """The blindness the task closes: hooks.md hardcodes the hook count in its
    header but was outside every scan list, so scan_code_counts never read it.
    It is now a CODE_COUNT_EXTRA_TARGET — scanned for counts only, never versions
    (its 'v1.4' historical refs must survive)."""

    def test_hooks_md_registered_as_code_count_target(self):
        assert "docs/en/hooks.md" in CODE_COUNT_EXTRA_TARGETS
        assert "docs/ru/hooks.md" in CODE_COUNT_EXTRA_TARGETS

    def test_hooks_md_never_version_scanned(self):
        # Guarantees the version scanner does not trip on hooks.md's "# Hooks (v1.4)"
        # title — code-count and version target sets are disjoint here.
        assert set(CODE_COUNT_EXTRA_TARGETS).isdisjoint(VERSION_SCAN_TARGETS)

    def test_stale_count_in_hooks_md_is_detected(self, tmp_path):
        # NEGATIVE SCENARIO: a stale header in docs/en/hooks.md — with NO stale
        # number anywhere in README — is now caught purely because hooks.md joined
        # the scan set. Before the fix scan_code_counts returned [].
        _write_target(
            tmp_path,
            "docs/en/hooks.md",
            "# Hooks (v1.4)\n\n**20 Python hooks + 1 shell** ship with v1.4.\n",
        )
        _write_target(
            tmp_path,
            "docs/ru/hooks.md",
            "# Хуки\n\n**19 активных хука** идут.\n",
        )
        msgs = scan_code_counts(tmp_path, _PAYLOAD)
        assert any("docs/en/hooks.md" in m and "20" in m for m in msgs), msgs
        assert any("docs/ru/hooks.md" in m and "19" in m for m in msgs), msgs

    def test_in_sync_hooks_md_clean(self, tmp_path):
        _write_target(
            tmp_path,
            "docs/en/hooks.md",
            "# Hooks\n\n**22 Python hooks + 1 shell** — 23 gates total.\n",
        )
        assert scan_code_counts(tmp_path, _PAYLOAD) == []

    def test_autofixer_repairs_hooks_md(self, tmp_path):
        _write_target(
            tmp_path,
            "docs/en/hooks.md",
            "# Hooks (v1.4)\n\n**20 Python hooks + 1 shell** ship with v1.4.\n",
        )
        changed = write_cross_file_fixes(tmp_path, _PAYLOAD)
        assert "docs/en/hooks.md" in changed
        text = (tmp_path / "docs/en/hooks.md").read_text(encoding="utf-8")
        assert "22 Python hooks" in text
        # Version ref in hooks.md is left untouched (code-count target, not version).
        assert "v1.4" in text
        assert write_cross_file_fixes(tmp_path, _PAYLOAD) == [], "second run is a no-op"


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
