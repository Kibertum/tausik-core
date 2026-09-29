"""A changelog entry per task, in a file only that task writes.

WHY. The continuous-changelog gate asks every closing task for an added line in
`CHANGELOG.md` AND `CHANGELOG.ru.md`, and every entry lands at the head of the same
`[Unreleased]` section. With parallel lanes that conflicts on EVERY closed task in both
languages — always, not occasionally, because everyone writes into the first lines of one
section.

WHAT THESE TESTS GUARD. The gate accepting a second proof must not become the gate
accepting a smaller one. So most of what is below is refusal: an empty fragment, a
half-written one, an unparseable one, and a task with no fragment at all — each has to
leave the close exactly as refused as it was before fragments existed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import changelog_fragments as cf  # noqa: E402

#: This walks `changelog.d/`, so no source edit would ever select it by import.
CROSSCUTTING_SCOPE = ["changelog.d/", "scripts/changelog_fragments.py"]

BOTH = "<!-- lang: en -->\n### Added — a thing\n\n<!-- lang: ru -->\n### Added — a thing\n"


def _tree(tmp_path: Path, fragments: dict[str, str] | None = None) -> Path:
    (tmp_path / cf.FRAGMENT_DIR).mkdir(parents=True, exist_ok=True)
    for name, text in (fragments or {}).items():
        (tmp_path / cf.FRAGMENT_DIR / name).write_text(text, encoding="utf-8")
    for target in cf.TARGETS.values():
        (tmp_path / target).write_text(
            f"# Changelog\n\n{cf.UNRELEASED}\n\n### Older — kept\n", encoding="utf-8"
        )
    return tmp_path


class TestAFragmentSatisfiesTheGate:
    def test_a_fragment_with_both_languages_passes(self, tmp_path):
        """AC-1. The slug names the file, so two lanes cannot write the same path."""
        root = _tree(tmp_path, {"a.md": BOTH})
        ok, why = cf.check(str(root), "a")
        assert ok is True
        assert "en" in why and "ru" in why

    def test_the_fragment_is_named_after_the_task(self, tmp_path):
        """The whole no-conflict property rests on this: a shared name would bring back
        the collision the fragments exist to remove."""
        root = _tree(tmp_path, {"a.md": BOTH})
        assert cf.fragment_path(str(root), "a").endswith(f"{cf.FRAGMENT_DIR}{chr(92)}a.md") or (
            cf.fragment_path(str(root), "a").endswith(f"{cf.FRAGMENT_DIR}/a.md")
        )
        assert cf.check(str(root), "b")[0] is False, "another task's fragment is not this one's"


class TestWhatTheGateStillRefuses:
    @pytest.mark.parametrize(
        ("body", "needle"),
        [
            pytest.param("", "is empty", id="empty"),
            pytest.param("   \n\n  ", "is empty", id="whitespace_only"),
            pytest.param("### Added — a thing\n", "no language marker", id="no_marker"),
            pytest.param("<!-- lang: en -->\n### Added — a thing\n", "ru", id="one_language"),
            pytest.param("<!-- lang: ru -->\n### Only ru\n", "en", id="other_language"),
            pytest.param("<!-- lang: en -->\n\n<!-- lang: ru -->\n", "nothing under", id="hollow"),
        ],
    )
    def test_a_fragment_that_is_not_an_entry_does_not_pass(self, body, needle, tmp_path):
        """NEGATIVE, AC-2 and AC-3. Half a pair is not an entry, and an empty file is the
        compliance theatre the shared-file gate already refused."""
        root = _tree(tmp_path, {"a.md": body})
        ok, why = cf.check(str(root), "a")
        assert ok is False
        assert needle in why

    def test_a_task_with_no_fragment_does_not_pass(self, tmp_path):
        """NEGATIVE, AC-4. The route is additional, not a way past the requirement."""
        root = _tree(tmp_path)
        ok, why = cf.check(str(root), "a")
        assert ok is False and "no fragment" in why

    def test_a_language_written_twice_is_refused(self, tmp_path):
        root = _tree(tmp_path, {"a.md": BOTH + "<!-- lang: en -->\nagain\n"})
        assert cf.check(str(root), "a")[0] is False


class TestAssembly:
    def test_it_folds_every_fragment_into_both_files_and_removes_them(self, tmp_path):
        """AC-5."""
        root = _tree(tmp_path, {"a.md": BOTH, "b.md": BOTH.replace("a thing", "another")})
        said = cf.assemble(str(root), apply=True)
        assert "2 fragment(s)" in said[0]
        for lang, target in cf.TARGETS.items():
            body = (root / target).read_text(encoding="utf-8")
            assert body.count("###") >= 3, f"{lang}: both entries plus what was there"
            assert "### Older — kept" in body, "what was already published stays"
        assert not list((root / cf.FRAGMENT_DIR).glob("*.md")), "fragments are gone"

    def test_a_dry_run_writes_nothing(self, tmp_path):
        root = _tree(tmp_path, {"a.md": BOTH})
        before = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        said = cf.assemble(str(root), apply=False)
        assert "would fold" in " ".join(said)
        assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == before
        assert (root / cf.FRAGMENT_DIR / "a.md").exists()

    def test_running_it_twice_does_not_duplicate(self, tmp_path):
        """AC-5. The fragments are gone after the first fold, so the second has nothing to
        add — which is what makes the command safe to repeat."""
        root = _tree(tmp_path, {"a.md": BOTH})
        cf.assemble(str(root), apply=True)
        first = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        assert cf.assemble(str(root), apply=True) == ["no fragments to assemble"]
        assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == first

    def test_the_order_is_the_slug_order(self, tmp_path):
        """Two assemblies of the same set must agree, or a merge produces a diff nobody
        made."""
        root = _tree(tmp_path, {"b.md": BOTH.replace("a thing", "bee"), "a.md": BOTH})
        cf.assemble(str(root), apply=True)
        body = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        assert body.index("a thing") < body.index("bee")

    @pytest.mark.parametrize(
        ("name", "body"),
        [("a.md", ""), ("a.md", "no marker here")],
        ids=["empty", "unparseable"],
    )
    def test_a_bad_fragment_stops_the_fold_before_anything_is_written(self, name, body, tmp_path):
        """NEGATIVE, AC-6. A half-applied assembly leaves some entries folded and other
        fragments deleted with nothing to show for them — worse than not running."""
        root = _tree(tmp_path, {"good.md": BOTH, name: body})
        before = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        with pytest.raises(cf.MalformedFragment):
            cf.assemble(str(root), apply=True)
        assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == before
        assert (root / cf.FRAGMENT_DIR / "good.md").exists(), "the good one survived too"

    def test_a_changelog_without_the_heading_is_refused(self, tmp_path):
        root = _tree(tmp_path, {"a.md": BOTH})
        (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        with pytest.raises(cf.MalformedFragment) as exc:
            cf.assemble(str(root), apply=True)
        assert "no `## [Unreleased]` heading" in str(exc.value)


class TestTheGateReadsTheFragmentRoute:
    @pytest.mark.parametrize(
        ("needle", "why"),
        [
            pytest.param(
                "from changelog_fragments import check as fragment_check",
                "the gate knows about the second route at all",
                id="imported",
            ),
            pytest.param(
                'fragment_check(root, slug) if root else (False, "")',
                "reading `changelog.d/` wherever the process stands would pass a close on "
                "another checkout's file — the same lesson the preparation step learned",
                id="no_cwd_fallback",
            ),
        ],
    )
    def test_the_gate_reaches_for_the_fragment_in_the_right_way(self, needle, why):
        text = (_REPO / "scripts" / "gate_changelog.py").read_text(encoding="utf-8")
        assert needle in text, why

    def test_the_fragment_is_tried_before_the_git_check(self):
        """Order matters: the fragment is the cheap answer and the git check is the
        fallback, not the other way round."""
        text = (_REPO / "scripts" / "gate_changelog.py").read_text(encoding="utf-8")
        assert text.index("fragment_check") < text.index("files_with_substantive_additions")

    def test_this_task_shipped_its_own_fragment(self):
        """Dogfood: the change that introduced fragments is itself recorded as one —
        as a fragment until the release is assembled, and folded into both changelogs
        after `changelog assemble --apply`, which removes the fragment by design."""
        ok, why = cf.check(str(_REPO), "lanes-changelog-fragments")
        if ok:
            return
        en = (_REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        ru = (_REPO / "CHANGELOG.ru.md").read_text(encoding="utf-8")
        assert "one changelog file per task instead of every task editing" in en, why
        assert "changelog.d/<slug>.md" in ru, why  # the Russian entry names the same path


class TestNoNewDependency:
    def test_the_module_imports_only_the_standard_library(self):
        """AC-8. The project has no runtime dependency and this is not the place to gain
        the first one — towncrier is the pattern, not the package."""
        text = (_REPO / "scripts" / "changelog_fragments.py").read_text(encoding="utf-8")
        imported = {
            line.split()[1].split(".")[0]
            for line in text.splitlines()
            if line.startswith(("import ", "from ")) and "__future__" not in line
        }
        assert imported <= {"os", "re", "typing"}, f"unexpected imports: {imported}"
