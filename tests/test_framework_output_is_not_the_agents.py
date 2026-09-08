"""What the framework wrote during a close is not the agent's undeclared scope.

MEASURED (session #235, live database): 846 of 2,278 verify runs recorded an
under-declared scope, and in the recent window it is 135 of the last 300 (45%)
and 39 of the last 100 (39%). The top of the undeclared list is not the agent's
work — AGENTS.md 54, CLAUDE.md 54, ROADMAP.md 12 — because `update-claudemd` and
`doc roadmap` run during the close, AFTER the scope was declared. Of those 135,
26 (19%) consisted of nothing else and 39 (29%) were mixed.

THE HALF THAT DECIDES WHETHER THIS IS A FIX OR A COVER-UP: a partly generated
file is subtracted only when the change is provably inside the generated region.
Subtracting `CLAUDE.md` by its NAME would hide the static-part edits session
#233 made on purpose — the same defect with the sign flipped.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import verify_framework_output as fw  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}

_STATIC_HEAD = "# Rules\n\nHand-written guidance lives here.\n\n"
_DYNAMIC_BLOCK = "<!-- DYNAMIC:START -->\n## Current State\nSession: none\n<!-- DYNAMIC:END -->\n"
_STATIC_TAIL = "\nMore hand-written guidance.\n"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "CLAUDE.md").write_text(_STATIC_HEAD + _DYNAMIC_BLOCK + _STATIC_TAIL, encoding="utf-8")
    (root / "ROADMAP.md").write_text("# Roadmap\n\ngenerated\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n- one\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, env=_GIT_ENV, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, env=_GIT_ENV, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=root, env=_GIT_ENV, check=True)
    return root


class TestWhollyGeneratedFilesAreSubtracted:
    """AC1. `doc roadmap` and `gen_doc_constants` own these completely."""

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("ROADMAP.md", id="roadmap"),
            pytest.param("docs/_generated/constants.json", id="constants"),
            pytest.param("docs/_generated/nested/other.json", id="anything_under_generated"),
        ],
    )
    def test_it_leaves_the_agents_list(self, tmp_path, path):
        kept, removed = fw.subtract_framework_output([path], root=str(tmp_path))
        assert kept == []
        assert removed == [path]

    def test_the_removed_path_keeps_the_callers_spelling(self, tmp_path):
        """A message that renames the file it is talking about makes the reader
        look for a second one."""
        kept, removed = fw.subtract_framework_output(["./ROADMAP.md"], root=str(tmp_path))
        assert removed == ["./ROADMAP.md"]
        assert kept == []


class TestAPartlyGeneratedFileIsJudgedByItsDiff:
    """AC2 and AC3, and this pair is the whole point: by the DIFF, never by the
    name. `CLAUDE.md` holds hand-written guidance around a generated block."""

    def test_a_change_inside_the_generated_block_is_subtracted(self, tmp_path):
        root = _repo(tmp_path)
        (root / "CLAUDE.md").write_text(
            _STATIC_HEAD
            + "<!-- DYNAMIC:START -->\n## Current State\nSession: #235\n<!-- DYNAMIC:END -->\n"
            + _STATIC_TAIL,
            encoding="utf-8",
        )
        kept, removed = fw.subtract_framework_output(["CLAUDE.md"], root=str(root))
        assert removed == ["CLAUDE.md"], "the framework's own block was counted against the agent"
        assert kept == []

    def test_a_change_to_the_hand_written_part_is_NOT_subtracted(self, tmp_path):
        """The half that keeps this honest. Session #233 edited exactly this
        region on purpose; hiding it would be the same defect inverted."""
        root = _repo(tmp_path)
        (root / "CLAUDE.md").write_text(
            "# Rules\n\nHand-written guidance lives here, now REWRITTEN.\n\n"
            + _DYNAMIC_BLOCK
            + _STATIC_TAIL,
            encoding="utf-8",
        )
        kept, removed = fw.subtract_framework_output(["CLAUDE.md"], root=str(root))
        assert kept == ["CLAUDE.md"], "a hand-written edit was hidden from the scope check"
        assert removed == []

    def test_a_change_touching_both_regions_is_NOT_subtracted(self, tmp_path):
        root = _repo(tmp_path)
        (root / "CLAUDE.md").write_text(
            "# Rules\n\nREWRITTEN guidance.\n\n"
            + "<!-- DYNAMIC:START -->\n## Current State\nSession: #235\n<!-- DYNAMIC:END -->\n"
            + _STATIC_TAIL,
            encoding="utf-8",
        )
        kept, _removed = fw.subtract_framework_output(["CLAUDE.md"], root=str(root))
        assert kept == ["CLAUDE.md"]


class TestBeingUnableToCheckIsNotPermission:
    """AC4. Decision #334, applied to this module's own uncertainty."""

    def test_a_file_without_the_markers_is_kept(self, tmp_path):
        root = _repo(tmp_path)
        (root / "AGENTS.md").write_text("# Agents\n\nno markers here\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, env=_GIT_ENV, check=True)
        subprocess.run(["git", "commit", "-qm", "add"], cwd=root, env=_GIT_ENV, check=True)
        (root / "AGENTS.md").write_text("# Agents\n\nchanged\n", encoding="utf-8")
        kept, removed = fw.subtract_framework_output(["AGENTS.md"], root=str(root))
        assert kept == ["AGENTS.md"]
        assert removed == []

    def test_outside_a_git_repository_nothing_partly_generated_is_subtracted(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text(
            _STATIC_HEAD + _DYNAMIC_BLOCK + _STATIC_TAIL, encoding="utf-8"
        )
        kept, removed = fw.subtract_framework_output(["CLAUDE.md"], root=str(tmp_path))
        assert kept == ["CLAUDE.md"], "an unreadable diff must not authorise subtraction"
        assert removed == []

    def test_a_file_with_no_pending_diff_is_kept(self, tmp_path):
        """Committed or staged already: this module cannot tell WHICH region
        moved, so it does not get to decide."""
        root = _repo(tmp_path)
        kept, _removed = fw.subtract_framework_output(["CLAUDE.md"], root=str(root))
        assert kept == ["CLAUDE.md"]


class TestNothingBeyondWhatWasNamedIsSubtracted:
    """AC7. The agent writes the changelog; its absence from a declaration is a
    REAL under-declaration and must stay visible."""

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("CHANGELOG.md", id="changelog"),
            pytest.param("CHANGELOG.ru.md", id="changelog_mirror"),
            pytest.param("docs/ru/graph.md", id="a_hand_written_doc"),
            pytest.param("scripts/symbol_index.py", id="code"),
            pytest.param("tausik/tasks/some-other-task.md", id="another_tasks_export"),
        ],
    )
    def test_it_stays_in_the_agents_scope(self, tmp_path, path):
        kept, removed = fw.subtract_framework_output([path], root=str(tmp_path))
        assert kept == [path]
        assert removed == []


class TestTheWholeDescriptionUsesIt:
    """The subtraction has to reach the status a receipt records, not just exist."""

    def test_a_run_whose_only_undeclared_file_is_generated_reads_complete(self, tmp_path):
        import verify_git_diff
        import verify_scope_honesty

        root = _repo(tmp_path)
        (root / "ROADMAP.md").write_text("# Roadmap\n\nregenerated\n", encoding="utf-8")

        original = verify_git_diff.changed_files_since
        try:
            verify_git_diff.changed_files_since = lambda *a, **k: {  # type: ignore[assignment]
                "scripts/thing.py",
                "ROADMAP.md",
            }
            result = verify_scope_honesty.describe_declared_scope(
                ["scripts/thing.py"], "2026-01-01T00:00:00Z", root=str(root)
            )
        finally:
            verify_git_diff.changed_files_since = original  # type: ignore[assignment]

        assert result["status"] == "complete", result
        assert result["undeclared"] == []
