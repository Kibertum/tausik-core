"""l26-defect-escape-rate — the outcome metric that can falsify "gates work".

Escape rate = share of done closures that a defect_of later pointed at, sliced by
the escaped task's own attributes, plus a risk_score backtest. Read-only; must be
safe on an empty DB and degrade (not crash) when verification_runs is absent.
"""

from __future__ import annotations

import os
import sqlite3
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from conftest import canonical_ddl

from backend_defect_escape import defect_escape_metrics

# verification_runs stays a 2-column FK stub (_STUB_MAX_COLUMNS=2 — allowed by the
# ddl-parity gate); the metric only reads task_slug. tasks MUST be the canonical
# schema (defect-escape-test-hand-ddl-parity), so it comes from canonical_ddl.
_VRUNS_DDL = "CREATE TABLE verification_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, task_slug TEXT)"
_TS = "2026-01-01T00:00:00Z"


def _q_of(conn):
    def q(sql, params=()):
        return conn.execute(sql, params).fetchall()

    return q


def _conn(*, with_vruns: bool = True):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(canonical_ddl("tasks"))
    if with_vruns:
        c.executescript(_VRUNS_DDL)
    return c


def _task(
    c, slug, *, status="done", complexity=None, role=None, tier=None, risk=None, defect_of=None
):
    # canonical tasks requires slug/title/created_at/updated_at NOT NULL (no default).
    c.execute(
        "INSERT INTO tasks (slug,title,status,complexity,role,tier,risk_score,defect_of,"
        "created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (slug, slug, status, complexity, role, tier, risk, defect_of, _TS, _TS),
    )


def _verify(c, slug):
    c.execute("INSERT INTO verification_runs (task_slug) VALUES (?)", (slug,))


class TestEscapeRate:
    def _fixture(self):
        c = _conn()
        # 3 done closures: A clean+verified, B escaped+verified, C escaped+unverified.
        _task(c, "A", complexity="simple", role="dev", tier="light", risk=0.2)
        _task(c, "B", complexity="medium", role="dev", tier="moderate", risk=0.6)
        _task(c, "C", complexity="medium", role="qa", tier="moderate", risk=0.5)
        _verify(c, "A")
        _verify(c, "B")
        # Defects (planning, so they are not counted as done rows) pointing at B and C.
        _task(c, "D", status="planning", defect_of="B")
        _task(c, "E", status="planning", defect_of="C")
        c.commit()
        return defect_escape_metrics(_q_of(c))

    def test_overall(self):
        m = self._fixture()
        assert m["overall"] == {"escaped": 2, "done": 3, "rate_pct": 66.7}

    def test_by_verification(self):
        bv = self._fixture()["by_verification"]
        # Verified: A (clean) + B (escaped) → 1/2. Unverified: C (escaped) → 1/1.
        assert bv["verified"] == {"escaped": 1, "done": 2, "rate_pct": 50.0}
        assert bv["unverified"] == {"escaped": 1, "done": 1, "rate_pct": 100.0}

    def test_slices_keep_the_escaped_identity(self):
        m = self._fixture()
        assert m["by_complexity"]["medium"] == {"escaped": 2, "done": 2, "rate_pct": 100.0}
        assert m["by_complexity"]["simple"]["rate_pct"] == 0
        assert m["by_role"]["qa"]["rate_pct"] == 100.0
        assert m["by_tier"]["moderate"]["escaped"] == 2

    def test_risk_backtest_separates_escaped_from_clean(self):
        bt = self._fixture()["risk_backtest"]
        assert bt["escaped_avg_risk"] == 0.55  # (0.6 + 0.5) / 2
        assert bt["clean_avg_risk"] == 0.2
        assert bt["escaped_n"] == 2 and bt["clean_n"] == 1


class TestStratifiedVerification:
    """investigate-the-verified-vs-unverified-escape: the Simpson cut.

    Within each complexity stratum verified and unverified escape EQUALLY;
    the aggregate still reads "verified escapes more" because verified work
    concentrates in the harder stratum. The metric must expose both views
    or the aggregate gets read as "verify hurts".
    """

    def _simpson(self):
        c = _conn()
        # medium: verified 2/4 escaped, unverified 1/2 escaped — both 50%.
        for slug, escaped in (("mw1", 1), ("mw2", 1), ("mw3", 0), ("mw4", 0)):
            _task(c, slug, complexity="medium", role="dev")
            _verify(c, slug)
            if escaped:
                _task(c, f"d-{slug}", status="planning", defect_of=slug)
        for slug, escaped in (("mu1", 1), ("mu2", 0)):
            _task(c, slug, complexity="medium", role="dev")
            if escaped:
                _task(c, f"d-{slug}", status="planning", defect_of=slug)
        # simple: verified 0/2, unverified 0/6 — both 0%.
        for slug in ("sw1", "sw2"):
            _task(c, slug, complexity="simple", role="dev")
            _verify(c, slug)
        for i in range(6):
            _task(c, f"su{i}", complexity="simple", role="dev")
        c.commit()
        return defect_escape_metrics(_q_of(c))

    def test_equal_within_strata_but_aggregate_reads_verified_worse(self):
        m = self._simpson()
        strat = m["by_complexity_and_verification"]
        assert strat["medium"]["verified"] == {"escaped": 2, "done": 4, "rate_pct": 50.0}
        assert strat["medium"]["unverified"] == {"escaped": 1, "done": 2, "rate_pct": 50.0}
        assert strat["simple"]["verified"] == {"escaped": 0, "done": 2, "rate_pct": 0}
        assert strat["simple"]["unverified"] == {"escaped": 0, "done": 6, "rate_pct": 0}
        # The SAME rows aggregated: verified work concentrates in the harder
        # stratum, so the aggregate flips to "verified escapes more" — the
        # paradox in miniature, held fixed by the stratified cut above.
        bv = m["by_verification"]
        assert (bv["verified"]["escaped"], bv["verified"]["done"]) == (2, 6)
        assert (bv["unverified"]["escaped"], bv["unverified"]["done"]) == (1, 8)
        assert bv["verified"]["rate_pct"] > bv["unverified"]["rate_pct"]

    def test_render_prints_the_stratified_arms(self):
        from render_metrics import _escape_lines

        lines = "\n".join(_escape_lines(self._simpson()))
        assert "medium     : verified 50.0% (2/4) vs unverified 50.0% (1/2)" in lines
        assert "simple     : verified 0.0% (0/2) vs unverified 0.0% (0/6)" in lines


class TestEdges:
    def test_empty_db_is_all_zero_no_crash(self):
        m = defect_escape_metrics(_q_of(_conn()))
        assert m["overall"] == {"escaped": 0, "done": 0, "rate_pct": 0}
        assert m["risk_backtest"]["escaped_avg_risk"] is None
        assert m["by_verification"]["verified"]["rate_pct"] == 0

    def test_null_attributes_bucket_as_unknown(self):
        c = _conn()
        _task(c, "X")  # done, no complexity/role/tier
        c.commit()
        m = defect_escape_metrics(_q_of(c))
        assert "unknown" in m["by_complexity"] and "unknown" in m["by_tier"]

    def test_missing_verification_table_degrades(self):
        # AC5: a partially-migrated DB without verification_runs must not crash;
        # everything is treated as unverified.
        c = _conn(with_vruns=False)
        _task(c, "A", risk=0.3)
        _task(c, "D", status="planning", defect_of="A")
        c.commit()
        m = defect_escape_metrics(_q_of(c))
        assert m["overall"]["escaped"] == 1
        assert m["by_verification"]["verified"]["done"] == 0
        assert m["by_verification"]["unverified"]["done"] == 1
