"""nothing-can-redact-the-memory-the-framework-publishes — striking a line out.

Decision #258: a redaction is an OVERWRITE THAT LEAVES A TRACE, never a deletion.
An append-only journal is evidence precisely because a row cannot be quietly
rewritten; but irrevocability without a paired mechanism means the first
mistakenly-recorded line is permanent, and publishing such a journal publishes
everything that ever landed in it — including what landed there by mistake.

So the contract has two halves, and both are tested here:
  - the sensitive substring is GONE from the database (a redaction that keeps
    the original somewhere is theatre, and the leak simply moved columns);
  - the FACT of the redaction survives, naming the entity, the field, the class
    of thing removed, the reason, the count and the time.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import redact_scope  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from redact_engine import RedactionRequest, apply_redaction, plan_redaction  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

# Opt-out, not an omission: the `os.walk` below traverses a projection this test
# just exported under `tmp_path`, never the repository's own sources. The scoped
# pytest gate has nothing to guard here, and declaring a path prefix would claim
# coverage this file does not provide. Flagged red by
# tests/test_crosscutting_registry.py when the declaration was simply missing.
#
# Written WITHOUT an annotation on purpose: `read_crosscutting_scope` matches
# `ast.Assign` only, so the annotated form `CROSSCUTTING_SCOPE: list[str] = []`
# reads as "declares nothing" — a silent miss, filed separately.
CROSSCUTTING_SCOPE = []

SECRET = "gitlab.internal.example"


@pytest.fixture
def svc(tmp_path):
    """A project carrying the secret in every kind of row a redaction must reach."""
    # The db must sit in a directory literally named `.tausik`, or `_tree_root`
    # declines to resolve a projection root and the export test has nothing to
    # read — the same fail-closed rule the exporter itself applies.
    (tmp_path / ".tausik").mkdir()
    be = SQLiteBackend(str(tmp_path / ".tausik" / "t.db"))
    s = ProjectService(be)
    s.epic_add("e", "E")
    s.story_add("e", "st", "S")
    s.task_add("st", "t", f"Mirror lives at {SECRET}", goal=f"Publish from {SECRET}")
    s.task_update(
        "t",
        acceptance_criteria=(
            f"1. {SECRET} is unreachable\n"
            "2. NEGATIVE: an empty pattern is refused rather than matching everything"
        ),
    )
    s.task_start("t")
    s.task_log("t", f"pushed to {SECRET} and it answered")
    s.memory_add("context", "Where the mirror lives", f"The mirror is {SECRET}, port 443")
    s.decide(f"Publish through {SECRET}", rationale=f"{SECRET} is already reachable")
    return s


def _req(**over):
    base = {
        "pattern": SECRET,
        "label": "internal-host",
        "reason": "the address of a private host must not reach a public repository",
    }
    base.update(over)
    return RedactionRequest(**base)


def _count_rows(svc, table, column):
    """How many rows of `table` still carry SECRET in `column`."""
    return svc.be._conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?", (f"%{SECRET}%",)
    ).fetchone()[0]


class TestRedactionOverwritesAndLeavesATrace:
    def test_marker_replaces_the_text_and_is_visible(self, svc):
        # AC1: an overwrite, not a deletion. The reader must SEE that something
        # stood here — a silently shortened sentence is indistinguishable from a
        # sentence that was always that short.
        apply_redaction(svc, _req())
        row = svc.be._conn.execute("SELECT message FROM task_logs WHERE task_slug='t'").fetchone()
        assert redact_scope.marker("internal-host") in row[0]
        assert SECRET not in row[0]

    def test_every_redaction_has_a_readable_trace(self, svc):
        # AC2: the trace is what makes the change legitimate rather than furtive.
        apply_redaction(svc, _req())
        rows = svc.be._conn.execute(
            "SELECT entity_type, field, label, reason, occurrences, redacted_at "
            "FROM redactions ORDER BY entity_type, field"
        ).fetchall()
        assert rows, "a redaction that leaves no trace is a silent rewrite"
        for entity_type, field, label, reason, occurrences, redacted_at in rows:
            assert entity_type in redact_scope.REDACTABLE_COLUMNS
            assert field in redact_scope.REDACTABLE_COLUMNS[entity_type]
            assert label == "internal-host"
            assert "private host" in reason
            assert occurrences >= 1
            assert redacted_at and redacted_at.endswith("Z")

    def test_it_reaches_the_three_places_the_cli_could_not(self, svc):
        # The whole point: task_logs is append-only, memory has no update, and
        # decisions has neither. Those are exactly the rows measured as
        # unreachable (27 + 15 + 4 of 69 leaking lines).
        assert _count_rows(svc, "task_logs", "message") == 1
        assert _count_rows(svc, "memory", "content") == 1
        assert _count_rows(svc, "decisions", "rationale") == 1
        apply_redaction(svc, _req())
        assert _count_rows(svc, "task_logs", "message") == 0
        assert _count_rows(svc, "memory", "content") == 0
        assert _count_rows(svc, "decisions", "rationale") == 0


class TestScopeIsDeclaredOnceAndDerived:
    def test_every_declared_column_exists_in_the_schema(self, svc):
        # AC3: the map may not rot. A column renamed in the schema and left
        # behind here would silently narrow what a redaction reaches — and the
        # narrowing would show up as a clean run, not as an error.
        for table, columns in redact_scope.REDACTABLE_COLUMNS.items():
            actual = {r[1] for r in svc.be._conn.execute(f"PRAGMA table_info({table})").fetchall()}
            assert actual, f"table {table} does not exist"
            missing = set(columns) - actual
            assert not missing, f"{table}: declared but absent: {sorted(missing)}"

    def test_widening_the_map_widens_the_command(self, svc, monkeypatch):
        # AC3: coverage is READ from the declaration, not repeated beside it.
        # Narrow the map to a single column and the plan must narrow with it.
        monkeypatch.setattr(
            redact_scope, "REDACTABLE_COLUMNS", {"memory": ("content",)}, raising=True
        )
        hits = plan_redaction(svc, _req())
        assert {h.entity_type for h in hits} == {"memory"}
        assert {h.field for h in hits} == {"content"}


class TestDryRunIsTheDefault:
    def test_planning_changes_nothing(self, svc):
        # AC4 (negative): the default invocation must be inert. A command that
        # writes unless told not to gets its irreversible half run by accident.
        hits = plan_redaction(svc, _req())
        assert hits, "the fixture does carry the secret; the plan must see it"
        assert _count_rows(svc, "memory", "content") == 1
        assert _count_rows(svc, "task_logs", "message") == 1
        assert svc.be._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0, (
            "a dry run must not write a trace either"
        )


class TestARedactionCannotBeQuietlyUndone:
    def test_the_original_survives_nowhere_in_the_database(self, svc):
        # AC5 (negative): proof by absence, across EVERY text column of every
        # redactable table — not just the ones we meant to touch. If the original
        # were kept anywhere (a shadow copy, the trace itself), the leak would
        # still be in the database and the redaction would be theatre.
        apply_redaction(svc, _req())
        for table, columns in redact_scope.REDACTABLE_COLUMNS.items():
            for column in columns:
                assert _count_rows(svc, table, column) == 0, f"{table}.{column} kept it"
        trace_text = " ".join(
            str(v)
            for row in svc.be._conn.execute("SELECT * FROM redactions").fetchall()
            for v in row
        )
        assert SECRET not in trace_text, "the trace must name the CLASS, never the value"


class TestIdempotence:
    def test_second_run_finds_nothing_and_adds_no_trace(self, svc):
        # AC6: re-running after a successful pass is a no-op, and must not
        # inflate the trace with rows recording that nothing happened.
        apply_redaction(svc, _req())
        first = svc.be._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0]
        second_result = apply_redaction(svc, _req())
        after = svc.be._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0]
        assert after == first
        assert second_result.occurrences == 0


class TestAPatternThatMatchesNothingIsSaidOutLoud:
    def test_zero_matches_is_a_named_outcome_not_a_silent_success(self, svc):
        # AC7 (negative): "redacted 0 occurrences" and "redacted 12 occurrences"
        # must not be the same answer. A caller who believes a leak exists and
        # gets a clean exit code learns nothing about a mistyped pattern — this
        # is the could-not-run/passed conflation, in a command that writes.
        result = apply_redaction(svc, _req(pattern="a-string-present-nowhere"))
        assert result.occurrences == 0
        assert result.matched is False
        assert "no match" in result.summary.lower()
        hit = apply_redaction(svc, _req())
        assert hit.matched is True
        assert hit.summary != result.summary


class TestProjectionIsRebuiltFromTheRedactedDatabase:
    def test_the_exported_file_carries_the_marker_not_the_secret(self, svc, tmp_path):
        # AC8: the projection is GENERATED. Redacting the database and leaving
        # the tree alone would be undone by the next export; redacting the tree
        # and leaving the database alone would be undone even sooner.
        from state_export import build_tree
        from state_serialize import write_tree

        apply_redaction(svc, _req())
        tree, _warnings = build_tree(svc)
        write_tree(str(tmp_path / "tausik"), tree)
        found = False
        for root, _dirs, files in os.walk(tmp_path):
            for name in files:
                if not name.endswith(".md"):
                    continue
                text = open(os.path.join(root, name), encoding="utf-8", errors="replace").read()
                assert SECRET not in text
                if redact_scope.marker("internal-host") in text:
                    found = True
        assert found, "the exported projection must show the marker"


class TestAnInvalidPatternIsRefusedInWordsNotInAStackTrace:
    """A refusal nobody phrased is indistinguishable from a broken tool.

    `redact` already gets the neighbouring case right: zero matches has its own
    sentence and is not passed off as success (AC7 of the task that built it).
    An unparseable `--regex` had no sentence at all -- `re.compile` raised
    straight through the CLI's handler, which catches ServiceError and
    ValueError, and the caller got seven frames of `re._compiler` internals.
    The answer existed; it was addressed to the author of the command rather
    than to the person running it.
    """

    BAD = "[Dd]:[/\]Work"  # unterminated character set: the backslash escapes `]`

    def test_an_unparseable_regex_raises_a_named_refusal(self, svc):
        # The TYPE is the whole point, not merely "it failed": `main()` prints a
        # traceback for anything outside (ServiceError, ValueError), so asserting
        # a non-zero outcome would have accepted the defect unchanged.
        with pytest.raises(ServiceError):
            plan_redaction(svc, _req(pattern=self.BAD, regex=True))

    def test_the_refusal_carries_the_reason_the_pattern_is_invalid(self, svc):
        with pytest.raises(ServiceError) as excinfo:
            plan_redaction(svc, _req(pattern=self.BAD, regex=True))
        message = str(excinfo.value)
        # re's own words: "unterminated character set at position 5". Repeating
        # "invalid pattern" without them would tell the caller the same thing
        # they already know.
        assert "character set" in message or "position" in message
        assert self.BAD in message

    def test_nothing_is_written_when_the_pattern_will_not_compile(self, svc):
        before = svc.be._conn.execute("SELECT count(*) FROM redactions").fetchone()[0]
        with pytest.raises(ServiceError):
            apply_redaction(svc, _req(pattern=self.BAD, regex=True))
        after = svc.be._conn.execute("SELECT count(*) FROM redactions").fetchone()[0]
        assert after == before

    def test_a_valid_regex_still_works(self, svc):
        """The negative that keeps the fix from closing `--regex` altogether."""
        result = apply_redaction(svc, _req(pattern="gitlab\.internal\.\w+", regex=True))
        assert result.matched is True
        assert result.occurrences > 0

    def test_an_invalid_pattern_is_not_reported_as_zero_matches(self, svc):
        """The conflation next door: "will not compile" is not "found nothing"."""
        empty = apply_redaction(svc, _req(pattern="a-string-present-nowhere"))
        assert empty.matched is False
        with pytest.raises(ServiceError):
            apply_redaction(svc, _req(pattern=self.BAD, regex=True))
