"""Not measured and zero are different statements, and the storage now says so.

telemetry-and-pricing-know-one-vendor-only. The task was raised as "on another
model zeros are written". The measurement, taken on this project's own database
in session #231 before anything was designed, refuted that: the zeros were being
written HERE, on this vendor, on this model.

    55,583 usage_events
    55,288 (99.5%)  tokens_input=0, tokens_output=0, model_id=NULL
    55,471          cost_usd=0; NOT ONE row carried NULL
         0          tasks with cost_actual_usd > 0; 669 with exactly 0

`_extract_usage` read `tool_response.usage`, and a TOOL result structurally has
no usage — usage belongs to the model's message. Bash (26,129 rows), Read
(7,385), Edit (6,346) and every MCP tool never carried it. `Agent` is the only
tool that ever did, at 75 rows. So the product asserted 55,471 times that a piece
of work had cost nothing.

WHAT IS ASSERTED HERE is the migration and the write path, on a REAL SQLite
database built and migrated by the real runner — not a mock. The centre of the
file is the pair of directions: absence must become NULL, and a genuine zero must
stay 0. A change that got only the first right would be the same defect wearing
the opposite sign.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"), str(_REPO / "scripts" / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend_migrations_v58 import MIGRATION_V58  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/backend_migrations_v58.py", "scripts/hooks/posttool_usage.py"]

#: The v57 shape, taken FROM THE MIGRATION rather than retyped here. The
#: migration already carries a frozen copy of the old table (it must, so a
#: partial fixture can be brought forward), and copying it a second time into
#: this file would be a fixture that drifts from the thing it tests — which is
#: what `test_ddl_fixture_parity` exists to stop, and it caught this file.
_V57 = MIGRATION_V58[0]

#: Everything after the CREATE: the conversion proper, run once rows are in.
_CONVERSION = MIGRATION_V58[1:]

#: One row of each interesting shape. `id` is pinned so assertions can name them.
_ROWS = [
    # id, model_id, ti, to, total, cost, source, tool_name  -- what it represents
    (1, None, 0, 0, 0, 0.0, "posttool", "Bash"),  # never measured: -> NULL
    (2, None, 0, 0, 0, 0.0, "posttool", "Read"),  # never measured: -> NULL
    (3, "claude-opus-5", 0, 0, 0, 0.0, "posttool", "Agent"),  # a MEASURED zero
    (4, "claude-opus-5", 120, 40, 160, 0.5, "posttool", "Agent"),  # measured
    (5, None, 281, 0, 281, 0.0, "posttool", "Agent"),  # measured, no model
    (6, None, 0, 0, 0, 0.0, "session_record", None),  # not posttool: untouched
    (7, None, 0, 0, 0, 0.0, "manual", None),  # not posttool: untouched
]


@pytest.fixture
def migrated(tmp_path) -> sqlite3.Connection:
    """A v57 database carrying every shape, put through the real migration."""
    conn = sqlite3.connect(tmp_path / "t.db")
    conn.execute(_V57)
    conn.execute("CREATE INDEX idx_usage_events_task ON usage_events(task_slug, recorded_at)")
    conn.executemany(
        "INSERT INTO usage_events(id, model_id, tokens_input, tokens_output, tokens_total,"
        " cost_usd, tool_calls, source, recorded_at, tool_name)"
        " VALUES(?,?,?,?,?,?,1,?, '2026-09-08T00:00:00Z', ?)",
        _ROWS,
    )
    conn.commit()
    for statement in _CONVERSION:
        conn.execute(statement)
    conn.commit()
    return conn


def _row(conn: sqlite3.Connection, row_id: int) -> dict:
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM usage_events WHERE id = ?", (row_id,))
    return dict(cur.fetchone())


class TestTheMigrationRewritesOnlyWhatItCanProve:
    def test_a_row_that_never_measured_anything_becomes_absent(self, migrated):
        for row_id in (1, 2):
            row = _row(migrated, row_id)
            assert row["tokens_input"] is None
            assert row["tokens_output"] is None
            assert row["tokens_total"] is None
            assert row["cost_usd"] is None

    def test_a_measured_zero_stays_zero(self, migrated):
        """AC7, and the direction a careless fix gets wrong. Row 3 names a model,
        so something answered — and its answer was nought. Erasing that would be
        the same crime in the other direction."""
        row = _row(migrated, 3)
        assert row["tokens_input"] == 0
        assert row["tokens_output"] == 0
        assert row["cost_usd"] == 0.0

    def test_measured_numbers_are_untouched(self, migrated):
        row = _row(migrated, 4)
        assert (row["tokens_input"], row["tokens_output"], row["tokens_total"]) == (120, 40, 160)
        assert row["cost_usd"] == 0.5

    def test_a_measured_row_without_a_model_is_still_a_measurement(self, migrated):
        """Row 5 is the real `Agent` shape: 281 tokens and no model id. The
        model being unknown does not make the tokens unknown."""
        row = _row(migrated, 5)
        assert row["tokens_input"] == 281

    @pytest.mark.parametrize("row_id", [6, 7])
    def test_rows_from_other_sources_are_not_touched(self, migrated, row_id):
        """Only `posttool` rows are provably unmeasured. A `manual` zero was
        typed by somebody and a `session_record` zero was rolled up from a
        session; neither is this migration's to reinterpret."""
        row = _row(migrated, row_id)
        assert row["tokens_input"] == 0
        assert row["cost_usd"] == 0.0

    def test_no_row_is_lost_or_gained(self, migrated):
        """AC9(в): the count is checked, not eyeballed."""
        assert migrated.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0] == len(_ROWS)

    def test_ids_survive_the_rebuild(self, migrated):
        ids = [r[0] for r in migrated.execute("SELECT id FROM usage_events ORDER BY id")]
        assert ids == [r[0] for r in _ROWS]


class TestTheConstraintsAreNotRelaxedByAccident:
    @pytest.mark.parametrize(
        "values",
        [
            pytest.param("-1, 0, 0, 0", id="negative_input_tokens"),
            pytest.param("0, -1, 0, 0", id="negative_output_tokens"),
            pytest.param("0, 0, 0, -0.5", id="negative_cost"),
        ],
    )
    def test_nonsense_is_still_refused(self, migrated, values):
        """AC9(а). Allowing NULL is not an excuse to stop rejecting nonsense —
        relaxing one constraint must not quietly relax its neighbour."""
        with pytest.raises(sqlite3.IntegrityError):
            migrated.execute(
                "INSERT INTO usage_events(tokens_input, tokens_output, tokens_total,"
                f" cost_usd, source, recorded_at) VALUES({values}, 'manual', 'x')"
            )

    def test_null_is_now_accepted(self, migrated):
        migrated.execute(
            "INSERT INTO usage_events(tokens_input, tokens_output, tokens_total,"
            " cost_usd, source, recorded_at) VALUES(NULL, NULL, NULL, NULL, 'posttool', 'x')"
        )

    def test_the_indexes_survive_the_table_swap(self, migrated):
        names = {
            r[0]
            for r in migrated.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='usage_events'"
            )
        }
        assert {
            "idx_usage_events_session",
            "idx_usage_events_task",
            "idx_usage_events_tool",
        } <= names


class TestTheHonestRollupFallsOutOfTheStorage:
    """Why nullable columns rather than a flag: SQL already means this."""

    def test_a_slice_with_no_measurement_sums_to_absence(self, migrated):
        total = migrated.execute(
            "SELECT SUM(tokens_total) FROM usage_events WHERE tool_name IN ('Bash','Read')"
        ).fetchone()[0]
        assert total is None, "a sum over nothing measured must be absent, not 0"

    def test_a_slice_with_measurements_sums_over_exactly_those(self, migrated):
        total = migrated.execute(
            "SELECT SUM(tokens_total) FROM usage_events WHERE tool_name = 'Agent'"
        ).fetchone()[0]
        assert total == 0 + 160 + 281

    def test_a_slice_of_only_measured_zeros_sums_to_zero_not_absence(self, migrated):
        total = migrated.execute(
            "SELECT SUM(tokens_total) FROM usage_events WHERE id = 3"
        ).fetchone()[0]
        assert total == 0


class TestTheExtractorReadsShapesAndAdmitsWhenItCannot:
    def _extract(self, payload):
        import posttool_usage

        return posttool_usage._extract_usage(payload)

    def test_the_shape_that_never_carried_usage_yields_absence(self):
        """Every ordinary tool. This is the 99.5%."""
        assert self._extract({"tool_name": "Bash", "tool_response": "ok"}) == (None, None, None)
        assert self._extract({}) == (None, None, None)

    @pytest.mark.parametrize(
        "payload",
        [
            {"tool_response": {"usage": {"input_tokens": 7, "output_tokens": 3}}},
            {"tool_response": {"message": {"usage": {"input_tokens": 7, "output_tokens": 3}}}},
            {"usage": {"input_tokens": 7, "output_tokens": 3}},
            {"message": {"usage": {"input_tokens": 7, "output_tokens": 3}}},
        ],
    )
    def test_every_known_shape_is_still_read(self, payload):
        """AC3, the second direction: teaching it to admit ignorance must not
        cost it the shapes it already understood."""
        assert self._extract(payload)[:2] == (7, 3)

    def test_a_real_zero_in_the_payload_is_a_measurement(self):
        got = self._extract({"tool_response": {"usage": {"input_tokens": 0, "output_tokens": 0}}})
        assert got[:2] == (0, 0), "a payload that says zero HAS answered"

    def test_a_usage_dict_with_nothing_readable_is_absence(self):
        """The dict was there and said nothing about tokens. Reporting 0 would
        launder an unparseable payload into a number."""
        assert self._extract({"tool_response": {"usage": {"speed": "fast"}}})[:2] == (None, None)

    def test_an_unreadable_token_value_does_not_become_zero(self):
        got = self._extract({"tool_response": {"usage": {"input_tokens": "many"}}})
        assert got[:2] == (None, None)

    def test_one_measured_side_is_kept_and_the_total_does_not_invent_the_other(self):
        import posttool_usage

        got = self._extract({"tool_response": {"usage": {"input_tokens": 9}}})
        assert got[:2] == (9, None)
        assert posttool_usage._total_or_none(9, None) == 9
        assert posttool_usage._total_or_none(None, None) is None

    def test_the_model_is_found_in_every_shape_it_lives_in(self):
        for payload in (
            {"tool_response": {"model": "m"}},
            {"tool_response": {"message": {"model": "m"}}},
            {"model": "m"},
            {"message": {"model": "m"}},
        ):
            assert self._extract(payload)[2] == "m"

    def test_a_blank_model_is_absent_rather_than_an_empty_string(self):
        assert self._extract({"tool_response": {"model": "   "}})[2] is None
