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
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import ide_utils
from service_doctor_drift import profile_provenance_line

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

    def test_recorded_primary_profile_beats_stale_sibling(self, tmp_path, monkeypatch):
        import json

        monkeypatch.delenv("TAUSIK_IDE", raising=False)
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "config.json").write_text(
            json.dumps({"bootstrap": {"primary_ide": "claude"}}), encoding="utf-8"
        )
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


class TestProfileProvenance:
    def _write_config(self, root, *, primary="cursor", project_root=None, targets=None):
        import json

        tausik = root / ".tausik"
        tausik.mkdir(exist_ok=True)
        (tausik / "config.json").write_text(
            json.dumps(
                {
                    "bootstrap": {
                        "primary_ide": primary,
                        "ides": targets or [primary],
                        "project_root": str(project_root or root),
                    }
                }
            ),
            encoding="utf-8",
        )

    def test_configured_profile_and_root_are_accepted(self, tmp_path, monkeypatch):
        source = tmp_path / ".tausik-lib" / "scripts"
        source.mkdir(parents=True)
        (source / "tausik_version.py").write_text('VERSION = "1.11.7"\n', encoding="utf-8")
        scripts = tmp_path / ".cursor" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "project.py").write_text("# project", encoding="utf-8")
        (scripts / "tausik_version.py").write_text('VERSION = "1.11.7"\n', encoding="utf-8")
        self._write_config(tmp_path)
        monkeypatch.setattr("service_doctor_drift.library_source", lambda *_: str(source))
        assert profile_provenance_line(str(tmp_path))[0] == "ok"

    def test_missing_framework_source_is_not_reported_as_version_agreement(
        self, tmp_path, monkeypatch
    ):
        scripts = tmp_path / ".cursor" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "project.py").write_text("# project", encoding="utf-8")
        self._write_config(tmp_path)
        monkeypatch.setattr("service_doctor_drift.library_source", lambda *_: None)

        level, detail = profile_provenance_line(str(tmp_path))

        assert level == "fail"
        assert "source is unavailable" in detail
        assert "version agree" not in detail
        assert detail.count("git','submodule','update','--init','.tausik-lib") == 1
        assert detail.count(".tausik-lib/bootstrap/bootstrap.py") == 1
        assert "&&" not in detail

    @pytest.mark.skipif(shutil.which("powershell") is None, reason="PowerShell unavailable")
    def test_missing_source_repair_parses_in_windows_powershell_51(self, tmp_path, monkeypatch):
        powershell = shutil.which("powershell")
        assert powershell is not None
        scripts = tmp_path / ".cursor" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "project.py").write_text("# project", encoding="utf-8")
        self._write_config(tmp_path)
        monkeypatch.setattr("service_doctor_drift.library_source", lambda *_: None)
        _, detail = profile_provenance_line(str(tmp_path))
        repair = detail.split("repair: ", 1)[1]
        env = os.environ.copy()
        env["TAUSIK_REPAIR_COMMAND"] = repair

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-Command",
                "[scriptblock]::Create($env:TAUSIK_REPAIR_COMMAND) | Out-Null",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("mutation", ["moved_root", "missing_profile", "primary_not_deployed"])
    def test_divergence_fails_with_one_repair_command(self, tmp_path, monkeypatch, mutation):
        scripts = tmp_path / ".cursor" / "scripts"
        if mutation != "missing_profile":
            scripts.mkdir(parents=True)
            (scripts / "project.py").write_text("# project", encoding="utf-8")
        recorded = tmp_path / "old-location" if mutation == "moved_root" else tmp_path
        targets = ["claude"] if mutation == "primary_not_deployed" else None
        self._write_config(tmp_path, project_root=recorded, targets=targets)
        bootstrap = tmp_path / ".tausik-lib" / "bootstrap"
        bootstrap.mkdir(parents=True)
        (bootstrap / "bootstrap.py").write_text("# bootstrap", encoding="utf-8")
        monkeypatch.setattr("service_doctor_drift.library_source", lambda *_: None)

        level, detail = profile_provenance_line(str(tmp_path))

        assert level == "fail"
        assert detail.count("python .tausik-lib/bootstrap/bootstrap.py --ide cursor") == 1

    def test_configured_profile_version_cannot_be_masked_by_newer_sibling(
        self, tmp_path, monkeypatch
    ):
        source = tmp_path / ".tausik-lib" / "scripts"
        source.mkdir(parents=True)
        (source / "tausik_version.py").write_text('VERSION = "1.11.7"\n', encoding="utf-8")
        bootstrap = tmp_path / ".tausik-lib" / "bootstrap"
        bootstrap.mkdir()
        (bootstrap / "bootstrap.py").write_text("# bootstrap", encoding="utf-8")
        cursor = tmp_path / ".cursor" / "scripts"
        cursor.mkdir(parents=True)
        (cursor / "project.py").write_text("# project", encoding="utf-8")
        (cursor / "tausik_version.py").write_text('VERSION = "1.11.6"\n', encoding="utf-8")
        claude = tmp_path / ".claude" / "scripts"
        claude.mkdir(parents=True)
        (claude / "project.py").write_text("# sibling", encoding="utf-8")
        (claude / "tausik_version.py").write_text('VERSION = "1.11.7"\n', encoding="utf-8")
        self._write_config(tmp_path)
        monkeypatch.setattr("service_doctor_drift.library_source", lambda *_: str(source))

        level, detail = profile_provenance_line(str(tmp_path))

        assert level == "fail"
        assert "cursor profile version diverged" in detail
        assert detail.count("python .tausik-lib/bootstrap/bootstrap.py --ide cursor") == 1


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
        "status_view.py": (
            "documented fallback when ide_utils is unimportable — the skill-set "
            "warning moved here from project_cli.py (status-cli-mcp-divergence)"
        ),
        "service_roles.py": "DEPLOYED_ROLES_DIR_REL is the last-resort fallback constant",
        "hooks/session_start.py": "documented fallback when the hook cannot locate its profile",
        "hooks/session_metrics.py": (
            "~/.claude/projects is Claude Code's own transcript store in the user's HOME, "
            "not a project profile, so ide_utils does not apply; the deployed-script "
            "path now self-locates via _common.profile_dir (engine-claude-literals-followup)"
        ),
        "gate_filesize.py": (
            "the .claude/mcp/ exemption the architecture audit flagged as hiding a "
            "1289-line module — owned by l26-filesize-gate-revisit, not this task"
        ),
        "claudemd_state.py": (
            "the main path resolves the onboarding file via ide_utils; the remaining "
            ".claude/CLAUDE.md literal is the documented ide_utils-unimportable fallback. "
            "The exemption MOVED HERE from project_cli_extra.py, which no longer holds a "
            "literal: the lookup was consolidated together with the dynamic-block builder "
            "so the CLI and the MCP handler stop carrying private copies "
            "(mcp-update-claudemd-erases-the-memory-tail). Generalising it to "
            "get_rules_file would change behaviour for AGENTS.md/.cursorrules — a "
            "deliberate no-op (engine-claude-literals-followup)"
        ),
        # The following reference ~/.claude in the user's HOME — Claude Code's
        # own auto-memory store, a Claude-specific feature with no .cursor/.qwen
        # equivalent. This is NOT a project profile directory, so ide_utils does
        # not apply; the tightened regex correctly reaches them and they are
        # exempt on the merits, not by oversight.
        "hooks/memory_pretool_block.py": "guards ~/.claude/**/memory/ (Claude auto-memory in HOME)",
        "memory_sinks.py": (
            "the deny-list names ~/.claude/**/memory/ as ONE foreign sink among nine "
            "hosts' — it is a HOME auto-memory store, not a project profile, and the "
            "IDE-profile carve-out it needs IS derived from ide_utils.IDE_REGISTRY "
            "(tausik_owned_paths)"
        ),
        "gate_memory_route.py": "docstring names ~/.claude/**/memory/ as the gate's documented blind spot",
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
