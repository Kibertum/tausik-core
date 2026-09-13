"""One call answers what grep-then-read answered in two.

symbol-index-answers-with-the-definition-not-the-address. Derived from Graft
(github.com/trailhq/Graft): its deterministic half builds a symbol graph with no
model involved and answers with the SOURCE inlined, so nothing is opened
afterwards. Graft is TypeScript on tree-sitter; this is Python on `ast`.

MEASURED BEFORE BUILDING (session #233, eight transcripts). Counting by tool NAME
said code navigation was 9.6% of tool result payload and the idea was not worth
carrying. Counting by what the commands actually DO said otherwise: inside Bash —
75.3% of the payload — `grep/sed/find/ls` is 49.2%, i.e. 37.1% of everything, at
1,192 calls averaging 1,501 characters. Real total: about 47%. The first count
missed half the reconnaissance because here it wears the name `Bash`, which is
decision #335's lesson arriving somewhere new.

MEASURED AFTER BUILDING, on 25 random function definitions of >= 8 lines:

    grep + sed (2 calls)        30,517 chars
    symbol, no callers (1 call) 29,442 chars   -3.5%
    symbol, with callers        34,686 chars  +13.7%

So the saving is in CALLS — half of them — and not in the size of an answer.
That is the honest result and it is the one that matters here: a call re-sends
the whole conversation, and this project's own baseline puts a call at 266,645
context tokens (decision #338). The extra 13.7% buys the caller list, which
would otherwise be a third call.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import symbol_answer as sa  # noqa: E402
import symbol_index as si  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "mod.py").write_text(
        textwrap.dedent(
            '''
            """A module."""


            def target(a, b=2):
                """Does a thing."""
                return a + b


            class Holder:
                def method(self):
                    return target(1)


            def caller():
                return target(3, b=4)
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    return tmp_path


class TestTheIndexIsBuiltFromTheTree:
    def test_it_finds_functions_classes_and_methods(self, tree):
        kinds = {(s.name, s.kind) for s in si.build_index(tree, roots=("scripts",))}
        assert ("target", "function") in kinds
        assert ("Holder", "class") in kinds
        assert ("method", "method") in kinds

    def test_a_method_carries_its_class(self, tree):
        method = next(s for s in si.build_index(tree, roots=("scripts",)) if s.name == "method")
        assert method.parent == "Holder"
        assert method.qualname == "Holder.method"

    def test_the_signature_is_the_source_line_not_a_rewrite(self, tree):
        """`ast.unparse` normalises defaults and annotations; a reader comparing
        the answer with the file would then find two different sentences."""
        target = next(s for s in si.build_index(tree, roots=("scripts",)) if s.name == "target")
        assert target.signature == "def target(a, b=2)"

    def test_sources_are_parsed_and_never_imported(self, tree):
        """AC9. Importing would EXECUTE module-level code from every file."""
        (tree / "scripts" / "explodes.py").write_text(
            "raise SystemExit('module-level code ran')\n", encoding="utf-8"
        )
        si.build_index(tree, roots=("scripts",))  # must not raise

    def test_a_file_that_does_not_parse_is_skipped_and_reported(self, tree):
        (tree / "scripts" / "broken.py").write_text("def (:\n", encoding="utf-8")
        names = {s.name for s in si.build_index(tree, roots=("scripts",))}
        assert "target" in names, "one broken file must not cost the whole index"
        assert "scripts/broken.py" in si.unparsable(tree, roots=("scripts",)), (
            "a file that could not be read must be nameable — otherwise 'could not "
            "read' reaches a caller as 'does not exist'"
        )

    def test_an_oversized_file_is_skipped(self, tree, monkeypatch):
        monkeypatch.setattr(si, "MAX_SOURCE_BYTES", 50)
        assert si.build_index(tree, roots=("scripts",)) == []

    def test_it_does_not_follow_a_link_out_of_the_tree(self, tmp_path, tree):
        outside = tmp_path.parent / "outside_tree"
        outside.mkdir(exist_ok=True)
        (outside / "secret.py").write_text("def outside_symbol():\n    pass\n", encoding="utf-8")
        link = tree / "scripts" / "linked.py"
        try:
            link.symlink_to(outside / "secret.py")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable on this machine")
        names = {s.name for s in si.build_index(tree, roots=("scripts",))}
        assert "outside_symbol" not in names


class TestTheAnswerCarriesTheDefinition:
    def test_it_inlines_the_body_so_no_read_follows(self, tree):
        out = sa.answer(tree, "target", roots=("scripts",))
        assert "def target(a, b=2)" in out
        assert "return a + b" in out, "the answer gives a location and not the code"
        assert "scripts/mod.py:" in out

    def test_it_lists_who_calls_it(self, tree):
        out = sa.answer(tree, "target", roots=("scripts",))
        assert "called from:" in out
        assert "scripts/mod.py:" in out.split("called from:")[1]

    @pytest.mark.parametrize(
        "query,expected",
        [
            pytest.param("caller", "called from: nothing in the indexed tree", id="no_callers"),
            pytest.param("target", "called from: scripts/mod.py:", id="has_callers"),
        ],
    )
    def test_the_caller_line_is_always_present_and_says_which_case(self, tree, query, expected):
        """Omitting the line when nobody calls it would leave the reader unable
        to tell 'nothing calls this' from 'the scan did not run'."""
        assert expected in sa.answer(tree, query, roots=("scripts",))

    def test_an_exact_name_is_not_diluted_by_substring_matches(self, tree):
        (tree / "scripts" / "more.py").write_text(
            "def target_helper():\n    pass\n", encoding="utf-8"
        )
        out = sa.answer(tree, "target", roots=("scripts",))
        assert "target_helper" not in out.split("called from:")[0]


class TestTheAnswerIsBoundedAndSaysSo:
    def test_a_long_definition_is_cut_and_the_cut_is_named(self, tree):
        body = "\n".join(f"    x = {i}" for i in range(120))
        (tree / "scripts" / "long.py").write_text(f"def enormous():\n{body}\n", encoding="utf-8")
        out = sa.answer(tree, "enormous", roots=("scripts",), max_lines=10)
        assert "more line(s)" in out, (
            "the body was cut without saying so — a silent truncation teaches the "
            "reader to open the file anyway, which costs both"
        )
        assert "scripts/long.py:1" in out

    def test_a_short_definition_is_not_marked_as_cut(self, tree):
        out = sa.answer(tree, "target", roots=("scripts",), max_lines=50)
        assert "more line(s)" not in out


class TestAnUnknownSymbolIsAbsenceNotEmptiness:
    def test_it_says_what_was_looked_for(self, tree):
        out = sa.answer(tree, "no_such_thing", roots=("scripts",))
        assert "no symbol named" in out and "no_such_thing" in out

    def test_it_offers_the_nearest_names(self, tree):
        """A typo is the common case, and the nearest names turn a dead end into
        the next query.

        The query has to actually MISS: `targ` is a legitimate substring match
        and rightly returns the definition itself, which is better than a
        suggestion. `targx` is the near miss.
        """
        out = sa.answer(tree, "targx", roots=("scripts",))
        assert "nearest names" in out and "target" in out

    def test_it_never_returns_an_empty_string(self, tree):
        """An empty answer is indistinguishable from a broken index, and the
        reader goes back to grepping — which is the cost this removes."""
        assert sa.answer(tree, "zzzz_nothing", roots=("scripts",)).strip()


class TestTheIndexIsDerivedFromTheTreeNotStored:
    """AC7. A hand-maintained symbol registry rots; this one cannot, because it
    is rebuilt from the source every time it is asked."""

    def test_a_new_definition_appears_without_any_rebuild_step(self, tree):
        # NOT "the name is absent from the text": the refusal quotes the query
        # back, so that assertion was false about a correct answer.
        assert "no symbol named" in sa.answer(tree, "brand_new", roots=("scripts",))
        (tree / "scripts" / "later.py").write_text(
            "def brand_new():\n    return 1\n", encoding="utf-8"
        )
        out = sa.answer(tree, "brand_new", roots=("scripts",))
        assert "def brand_new" in out

    def test_a_deleted_definition_disappears(self, tree):
        (tree / "scripts" / "mod.py").write_text("x = 1\n", encoding="utf-8")
        assert "no symbol named" in sa.answer(tree, "target", roots=("scripts",))


class TestItRunsOnThisRepositoryAndThroughTheCLI:
    def test_the_real_tree_indexes(self):
        symbols = si.build_index(_REPO)
        assert len(symbols) > 5000, f"only {len(symbols)} symbols — roots wrong?"

    def test_the_cli_answers(self, tmp_path):
        """The subject end to end: the command a reader actually types.

        The CLI boots a service and creates `.tausik/tausik.db` where it stands;
        run at the repo root that left a database behind in every clean clone
        and woke the controls that are dormant without one — over an empty
        store, red or skipped by run order (conftest, session #203; caught by
        name in session #254). TAUSIK_DIR sends the state to tmp; the CODE it
        indexes is still this repository.
        """
        (tmp_path / ".tausik").mkdir()
        result = subprocess.run(
            [sys.executable, str(_REPO / "scripts" / "project.py"), "symbol", "tags_unmoved"],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            env={
                **__import__("os").environ,
                "PYTHONUTF8": "1",
                "TAUSIK_DIR": str(tmp_path / ".tausik"),
            },
        )
        assert result.returncode == 0, result.stderr
        assert "def tags_unmoved" in result.stdout
        assert "publication_scope.py:" in result.stdout


class TestTheRefusalDescribesTheSearchThatHappened:
    def test_it_names_the_roots_it_actually_looked_in(self, tree):
        """It named the DEFAULT roots while searching the ones passed in — telling
        the reader a search happened where it did not. Found by a test of the
        neighbouring behaviour, which is where this kind of slip surfaces."""
        out = sa.answer(tree, "nothing_here", roots=("scripts",))
        assert "scripts" in out
        assert "bootstrap" not in out and "harness" not in out
