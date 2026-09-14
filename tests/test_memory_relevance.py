"""Memory is pulled in by what the task is about, and an empty answer says so.

Session #189's measurement: memory #425 (the retired "five names" rule) and
#428 (a signed receipt is not a passing commit) had to be carried into the
prompt by hand, because the recency tail could not have returned them. The
fixture below reproduces those two rows under thirty newer decoys and asks the
relevance path for the task whose declared files name the scoped registry.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import memory_relevance as mr  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

CROSSCUTTING_SCOPE = []  # a fixture store, not the tree


def _svc(tmp_path) -> ProjectService:
    return ProjectService(SQLiteBackend(str(tmp_path / "t.db")))


def _seed_189(be) -> tuple[int, int]:
    """#425 and #428 as they read in the live store, then thirty newer decoys."""
    m425 = be.memory_add(
        "convention",
        "Правило «подмешивай пять имён к любой выборке» ОТМЕНЕНО: теперь тест выбирается по импорту",
        "CROSSCUTTING_SCOPE names the guarded tree; the scoped registry selects by import edge, "
        "the invisible baseline only shrinks (ratchet).",
        tags=["crosscutting", "scoped-tests", "resolver", "ratchet"],
    )
    m428 = be.memory_add(
        "gotcha",
        "Подписанная квитанция verify НЕ означает, что коммит пройдёт: у commit пять гейтов",
        "state_roundtrip and mypy run on commit only; verify certifies the scoped lane.",
        tags=["gates", "verify", "commit", "state-roundtrip", "mypy"],
    )
    for i in range(30):
        be.memory_add(
            "pattern",
            f"Decoy {i}: cost pricing for the Nm context tier suffix",
            "model lookup, telemetry, pricing table, session metrics, nothing about gates",
            tags=["pricing", "telemetry"],
        )
    return m425, m428


def _parity_task(svc: ProjectService) -> str:
    slug = "cross-model-parity-has-no-gate"
    svc.task_add(
        None,
        slug,
        "Кроссмодельность не проверяется ничем: новая возможность может уехать в Claude",
        complexity="medium",
    )
    svc.task_update(
        slug,
        relevant_files=json.dumps(
            [
                "scripts/gate_cross_model_parity.py",
                "scripts/host_mechanisms.py",
                "scripts/gate_registry_scoped.py",
                "tests/test_cross_model_parity_gate.py",
            ]
        ),
    )
    return slug


# --- the measurable criterion -------------------------------------------------


def test_the_parity_task_pulls_425_and_428_from_under_thirty_decoys(tmp_path):
    """The session-#189 criterion: both rows, newer decoys notwithstanding.
    #425 through `scoped` (tag `scoped-tests`) and `registry`; #428 through
    `gate` (tag `gates`). In the live store #428 competes with dozens of other
    gate-tagged rows and ranks below the top eight — the journal records that
    measurement; the fixture pins that the PATH reaches both."""
    svc = _svc(tmp_path)
    try:
        m425, m428 = _seed_189(svc.be)
        slug = _parity_task(svc)
        task = svc.be.task_get_full(slug)
        rel = mr.relevant_memory(svc.be, task, [])
        ids = [row["id"] for row in rel.entries]
        assert m425 in ids and m428 in ids, (ids, rel.terms)
        assert len(ids) <= mr.MAX_ENTRIES
        assert "scoped" in rel.terms and "registry" in rel.terms and "gate" in rel.terms
        assert ids.index(m425) < ids.index(m428), "the tag-exact row outranks the tag-prefix one"
    finally:
        svc.be.close()


def test_the_decoys_do_not_outrank_the_subject_rows(tmp_path):
    """Negative: thirty newer rows about pricing must not crowd the block —
    recency is exactly what this path does NOT rank by."""
    svc = _svc(tmp_path)
    try:
        m425, m428 = _seed_189(svc.be)
        slug = _parity_task(svc)
        rel = mr.relevant_memory(svc.be, svc.be.task_get_full(slug), [])
        assert all(not str(row.get("title", "")).startswith("Decoy") for row in rel.entries[:2])
    finally:
        svc.be.close()


# --- the block on the surfaces -------------------------------------------------


def test_task_start_prints_the_block(tmp_path):
    svc = _svc(tmp_path)
    try:
        m425, _ = _seed_189(svc.be)
        slug = _parity_task(svc)
        svc.task_update(
            slug,
            goal="parity gate",
            acceptance_criteria="AC-1: gate exists. AC-2 (negative): a missing host is reported.",
            scope="scripts/gate_cross_model_parity.py",
            rollback_plan="git revert",
        )
        out = svc.task_start(slug)
        assert "Relevant memory (" in out
        assert f"#{m425}" in out
        resumed = svc.task_start(slug)
        assert "already active" in resumed and f"#{m425}" in resumed, resumed
        shown = svc.task_show(slug)
        assert any(f"#{m425}" in line for line in shown["relevant_memory"])
    finally:
        svc.be.close()


# --- negatives -------------------------------------------------------------------


def test_an_empty_answer_is_named_with_the_terms_tried(tmp_path):
    svc = _svc(tmp_path)
    try:
        svc.task_add(None, "billing-ledger", "Migrate the billing ledger", complexity="simple")
        rel = mr.relevant_memory(svc.be, svc.be.task_get_full("billing-ledger"), [])
        lines = mr.relevance_lines(rel)
        assert lines == [f"Relevant memory: none matched {', '.join(rel.terms)}"]
        assert "billing" in rel.terms and "ledger" in rel.terms
    finally:
        svc.be.close()


def test_a_failing_search_degrades_to_a_named_line_not_a_crash(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    try:
        svc.task_add(None, "billing-ledger", "Migrate the billing ledger", complexity="simple")

        def boom(*_a, **_k):
            raise RuntimeError("fts5 unavailable")

        monkeypatch.setattr(mr, "search_any", boom)
        lines = mr.lines_for_task(svc.be, "billing-ledger")
        assert len(lines) == 1 and lines[0].startswith(
            "Relevant memory: search failed (RuntimeError"
        )
        assert "billing" in lines[0], "the terms tried are still named"
    finally:
        svc.be.close()


def test_a_task_with_no_terms_prints_nothing(tmp_path):
    rel = mr.Relevance([], [], None)
    assert mr.relevance_lines(rel) == []


def test_a_superseded_row_yields_to_its_replacement(tmp_path):
    svc = _svc(tmp_path)
    try:
        old = svc.be.memory_add(
            "convention", "scoped registry rule v1", "old wording", tags=["scoped-tests"]
        )
        new = svc.be.memory_add(
            "convention", "scoped registry rule v2", "new wording", tags=["scoped-tests"]
        )
        svc.memory_link("memory", new, "memory", old, "supersedes")
        slug = _parity_task(svc)
        ids = [
            row["id"] for row in mr.relevant_memory(svc.be, svc.be.task_get_full(slug), []).entries
        ]
        assert new in ids and old not in ids
    finally:
        svc.be.close()


def test_a_term_matching_nothing_does_not_poison_the_query(tmp_path):
    svc = _svc(tmp_path)
    try:
        m425, _ = _seed_189(svc.be)
        rows = mr.search_any(svc.be, ["zzzznothing", "scoped"], n=10)
        assert m425 in [r["id"] for r in rows]
        assert mr.search_any(svc.be, [], n=10) == []
    finally:
        svc.be.close()


def test_json_list_fields_are_parsed(tmp_path):
    terms = mr.task_terms(
        {"title": "x", "slug": "x", "relevant_files": '["scripts/gate_registry_scoped.py"]'}
    )
    assert "scoped" in terms and "registry" in terms
