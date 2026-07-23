"""doctor-hardcodes-claude-dir — `tausik doctor` on a non-Claude install.

`scripts/ide_utils.py` is a complete IDE abstraction (7 profiles, directory and
skills resolution) with almost no callers, while `.claude` appeared as a literal
throughout the engine. The consequence was not cosmetic: `project_cli_doctor`
looked for `.claude/mcp/project/server.py` and `.claude/skills/`, so on a
Cursor / Qwen / Kilo / OpenCode install — where bootstrap deploys `.cursor/`,
`.qwen/`, `.kilo/` — a perfectly healthy project reported FAIL and exited 1,
breaking any CI that ran the health check.

A health check that fails healthy projects is worse than no health check: it
teaches people to ignore it.

Coverage:
  - the profile resolvers return the detected IDE's directory, not `.claude`;
  - the "not deployed" message names the profile that IS present, instead of
    advising a bootstrap re-run that would do exactly the same thing;
  - scanners skip every profile directory, derived from the registry;
  - a lint that fails when a new `.claude` literal appears in the engine.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import ide_utils  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"


@pytest.fixture
def cursor_project(tmp_path, monkeypatch):
    """A project bootstrapped for Cursor only — no `.claude/` anywhere."""
    monkeypatch.delenv("TAUSIK_IDE", raising=False)
    (tmp_path / ".cursor" / "mcp" / "project").mkdir(parents=True)
    (tmp_path / ".cursor" / "mcp" / "project" / "server.py").write_text(
        "# server", encoding="utf-8"
    )
    (tmp_path / ".cursor" / "skills" / "start").mkdir(parents=True)
    return tmp_path


class TestProfileResolution:
    def test_cursor_project_resolves_to_cursor(self, cursor_project):
        ide, config_dir = ide_utils.resolve_profile(str(cursor_project))
        assert (ide, config_dir) == ("cursor", ".cursor")

    def test_claude_project_still_resolves_to_claude(self, tmp_path, monkeypatch):
        """Regression guard: the common path must not move."""
        monkeypatch.delenv("TAUSIK_IDE", raising=False)
        (tmp_path / ".claude").mkdir()
        assert ide_utils.resolve_profile(str(tmp_path)) == ("claude", ".claude")

    def test_mcp_path_follows_the_detected_profile(self, cursor_project):
        _, config_dir = ide_utils.resolve_profile(str(cursor_project))
        server = os.path.join(str(cursor_project), config_dir, "mcp", "project", "server.py")
        # The exact check `doctor` performs — it must find the real file.
        assert os.path.isfile(server)

    def test_skills_dir_follows_the_detected_profile(self, cursor_project):
        skills = ide_utils.get_skills_dir(str(cursor_project), "cursor")
        assert os.path.isdir(skills)
        assert ".claude" not in skills


class TestMissingProfileHint:
    def test_names_the_profile_that_is_deployed(self, cursor_project):
        """'re-run bootstrap' is useless advice when bootstrap already ran and
        targeted a different IDE — the same command repeats the same result."""
        hint = ide_utils.missing_profile_hint(str(cursor_project), "claude")
        assert "cursor" in hint
        assert "TAUSIK_IDE=cursor" in hint

    def test_falls_back_to_bootstrap_when_nothing_is_deployed(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TAUSIK_IDE", raising=False)
        hint = ide_utils.missing_profile_hint(str(tmp_path), "claude")
        assert "re-run bootstrap" in hint

    def test_does_not_name_the_profile_being_reported(self, tmp_path, monkeypatch):
        """A hint that says "claude is missing, but claude is deployed" is noise."""
        monkeypatch.delenv("TAUSIK_IDE", raising=False)
        (tmp_path / ".claude").mkdir()
        assert ide_utils.other_deployed_profile(str(tmp_path), "claude") is None


class TestProfileDirsAreRegistryDerived:
    def test_every_registered_profile_is_listed(self):
        dirs = ide_utils.all_profile_dirs()
        for config in ide_utils.IDE_REGISTRY.values():
            assert config["config_dir"] in dirs

    @pytest.mark.parametrize("module_name,attr", [("snippet_detect", "_SKIP_DIRS")])
    def test_scanners_skip_every_profile_not_just_claude(self, module_name, attr):
        """Hand-listed skip-sets named `.claude` (and sometimes `.cursor`), so
        scanners walked a deployed copy of the engine on the other profiles."""
        import importlib

        skip = getattr(importlib.import_module(module_name), attr)
        assert ide_utils.all_profile_dirs() <= set(skip)

    def test_aidd_deny_dirs_skip_every_profile(self):
        import project_cli_aidd_autogen

        assert ide_utils.all_profile_dirs() <= set(project_cli_aidd_autogen._DENY_DIRS)


class TestNoNewClaudeLiterals:
    """The lint that stops this class of defect from creeping back.

    Every exemption is named with its reason. A file that genuinely needs the
    literal (Claude-specific interop, or a documented fallback) is listed here
    deliberately; anything else must go through `ide_utils`.
    """

    # path -> why the literal is legitimate there
    _ALLOWED = {
        "ide_utils.py": "owns the registry — this is where the literal belongs",
        "service_doctor_caveman.py": "reads .claude/settings.json; Claude-specific by design",
        "service_doctor_drift.py": "builds the expected CLAUDE.md body for the claude profile",
        "project_cli_skill.py": "documented fallback when ide_utils is unimportable",
        "project_cli.py": "documented fallback when ide_utils is unimportable",
        "service_roles.py": "DEPLOYED_ROLES_DIR_REL is the last-resort fallback constant",
        "hooks/session_start.py": "documented fallback when the hook cannot locate its profile",
        "hooks/session_metrics.py": (
            "~/.claude/projects is Claude Code's own transcript store in the user's HOME, "
            "not a project profile; the deployed-script path is covered by "
            "engine-claude-literals-followup"
        ),
        "audit_orphan_files.py": (
            "ignore-globs for the deployed Claude profile; generalising them is "
            "engine-claude-literals-followup"
        ),
        "gate_filesize.py": (
            "the .claude/mcp/ exemption the architecture audit flagged as hiding a "
            "1289-line module — owned by l26-filesize-gate-revisit, not this task"
        ),
        "project_cli_extra.py": (
            "CLAUDE.md lookup candidates; generalising to get_rules_file changes "
            "behaviour for AGENTS.md/.cursorrules — engine-claude-literals-followup"
        ),
        # The following reference ~/.claude in the user's HOME — Claude Code's
        # own auto-memory store, a Claude-specific feature with no .cursor/.qwen
        # equivalent. This is NOT a project profile directory, so ide_utils does
        # not apply; the tightened regex correctly reaches them and they are
        # exempt on the merits, not by oversight.
        "hooks/memory_pretool_block.py": "guards ~/.claude/**/memory/ (Claude auto-memory in HOME)",
        "service_knowledge_aggregates.py": "documents the ~/.claude/*/memory/ auto-memory policy",
        "service_replay.py": "already IDE-agnostic — lists /.claude/, /.cursor/, /.qwen/ together",
    }
    # `.claude` bounded by a quote or a path separator on EITHER side. The
    # first cut anchored only on the opening quote, so `.claude` anywhere but
    # the start of its literal — `"harness/.claude/foo"`, `"a/b/.claude"` —
    # slipped through the very lint meant to make a new literal fail the build
    # (adversarial review, s130-review-fixes). A dotted attribute like
    # `x.claude` is not preceded by quote-or-separator, so real code is not a
    # false positive.
    _LITERAL = re.compile(r"""(?:["']|[/\\])\.claude(?:["']|[/\\])""")

    def test_no_unexempted_claude_literal_in_scripts(self):
        offenders = []
        for path in sorted(_SCRIPTS.rglob("*.py")):
            rel = path.relative_to(_SCRIPTS).as_posix()
            if rel in self._ALLOWED or path.name in self._ALLOWED:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if self._LITERAL.search(line):
                    offenders.append(f"{rel}:{n}: {line.strip()}")
        assert not offenders, (
            "hardcoded IDE profile directory — use ide_utils (detect_ide / get_ide_dir / "
            "get_skills_dir / all_profile_dirs) so the engine works on all 7 supported "
            "IDEs, or add the file to _ALLOWED with a reason:\n  " + "\n  ".join(offenders)
        )

    def test_the_lint_would_catch_a_new_literal(self, tmp_path, monkeypatch):
        """Fail-then-pass: prove the matcher fires rather than trivially passing."""
        assert self._LITERAL.search('x = os.path.join(project_dir, ".claude", "mcp")')
        assert self._LITERAL.search("p = '.claude/skills'")
        assert not self._LITERAL.search("# .claude is mentioned in prose only")

    def test_lint_catches_claude_anywhere_in_the_literal(self):
        """The gap adversarial review found: the first regex anchored on the
        opening quote, so `.claude` not at the start of its string slipped
        past — `os.path.join(root, "harness/.claude/foo")` evaded the lint the
        doctor task built to forbid exactly that."""
        assert self._LITERAL.search('"harness/.claude/foo"')
        assert self._LITERAL.search('"some/path/.claude"')
        assert self._LITERAL.search("x = os.path.join(base, 'legacy/.claude/mcp')")
        # A dotted attribute is not a path literal — must not be a false positive.
        assert not self._LITERAL.search("obj.claude = 1")
        assert not self._LITERAL.search("self.claudemd_path")

    def test_allowlist_has_no_stale_entries(self):
        """An exemption for a file that no longer contains the literal is a
        lie about the codebase — it would silently cover a future addition."""
        stale = []
        for name in self._ALLOWED:
            candidate = _SCRIPTS / name
            if not candidate.exists():
                stale.append(f"{name} (file is gone)")
                continue
            if not self._LITERAL.search(candidate.read_text(encoding="utf-8", errors="replace")):
                stale.append(f"{name} (no literal left — drop the exemption)")
        assert not stale, "stale entries in _ALLOWED: " + ", ".join(stale)
