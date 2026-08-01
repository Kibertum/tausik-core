"""The git projection tracks the DB after ANY mutation — property, not call sites.

`state-git-triggers` shipped with the export wired into three places by hand, and
the prose said "task done / decide / memory add". Eighteen of the ~20 mutating
service methods never exported: a decision recorded WITH a task_slug — the common
case — reached the DB and never `tausik/`. Nothing caught it because a periodic
full `tausik state export` rebuilt the tree, so `status` reported no divergence.

Asserting "method X calls auto_export" would repeat the original mistake at test
level: it can only check the call sites someone remembered to list. The property
below is indifferent to how the export happens —

    after any sequence of mutations, with NO manual command in between,
    the files on disk equal build_tree(db) byte for byte

— so a new mutator that forgets to project fails here, and a refactor that moves
the export somewhere else does not.

WHY THIS FILE WAS REWRITTEN (projection-property-test-cannot-reach-cascades).
The first version declared that property and then checked ONE hand-written
sequence, five functions long, in registry order. Three live projection defects
walked past it green, and none of them was bad luck:

  * the sequence closed the story BEFORE any task in it started, so the
    `story["status"] == "open"` branch of `_cascade_start` never ran;
  * every delete in it was a LEAF (a childless epic, a childless story, and the
    epics ran first), so `ON DELETE CASCADE` never fired;
  * the invariant was sampled once per mutator GROUP, so "the projection fell
    behind and caught up" was indistinguishable from "it never fell behind";
  * the coverage ratchet counted FIVE ENTITY KINDS, which one trivial mutator per
    kind satisfies while whole write paths stay untouched.

So the sequence is now GENERATED (fixed seeds, varying order and nesting, deletes
that take children with them), the invariant is sampled after EVERY SINGLE
mutation, and the ratchet counts WRITE PATHS discovered at the write layer.
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any, Callable

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import project_config  # noqa: E402
import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import build_tree  # noqa: E402
from state_import import ENTITY_DIRS  # noqa: E402
from tausik_utils import ServiceError, utcnow_iso  # noqa: E402


def _mem_id(message: str) -> int:
    """`memory_add` returns a human message, not the row id — pull it back out."""
    m = re.search(r"#(\d+)", message)
    assert m, f"unexpected memory_add message: {message!r}"
    return int(m.group(1))


# --- the write layer, as an observation point --------------------------------


_WRITE_RE = re.compile(
    r"""^\s*(?:
          (?P<ins>INSERT(?:\s+OR\s+\w+)?|REPLACE)\s+INTO
        | (?P<upd>UPDATE)(?:\s+OR\s+\w+)?
        | (?P<del>DELETE)\s+FROM
      )\s+["'`\[]?(?P<table>[A-Za-z_][A-Za-z0-9_]*)""",
    re.IGNORECASE | re.VERBOSE,
)
_READ_RE = re.compile(r"\b(?:FROM|JOIN)\s+[\"'`\[]?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
_IS_SELECT = re.compile(r"^\s*(?:WITH|SELECT)\b", re.IGNORECASE)


class _SqlTap:
    """Every statement SQLite actually runs, split into write paths and read set.

    This is the WRITE LAYER used as an observation point, and that is precisely
    what separates it from the approach dead-ended in #355. That one scanned a
    function BODY for literal DML, so a write issued by a helper the function
    calls was invisible — and in this backend nearly every write goes through
    such a helper (`_ex`, `_ins`, `_update`, `_delete_projected`), which is why
    the scan found almost nothing. A trace callback sits BELOW the helper: it
    sees the statement that reached SQLite no matter who composed it, so the
    helper stops being a blind spot and becomes the single place to look.

    Blind spot named honestly: `ON DELETE CASCADE` is performed by SQLite itself
    and is NOT a statement, so it never appears here. Cascades are covered by the
    invariant (which compares the whole tree), not by this ratchet.
    """

    __slots__ = ("writes", "reads", "on")

    def __init__(self) -> None:
        self.writes: set[tuple[str, str]] = set()
        self.reads: set[str] = set()
        self.on = True

    def __call__(self, sql: str) -> None:
        if not self.on:
            return
        m = _WRITE_RE.match(sql)
        if m:
            verb = "INSERT" if m.group("ins") else "UPDATE" if m.group("upd") else "DELETE"
            self.writes.add((m.group("table").lower(), verb))
            return
        if _IS_SELECT.match(sql):
            self.reads.update(t.lower() for t in _READ_RE.findall(sql))


@pytest.fixture
def tap(svc):
    t = _SqlTap()
    svc.be._conn.set_trace_callback(t)
    yield t
    svc.be._conn.set_trace_callback(None)


@pytest.fixture
def svc(tmp_path, monkeypatch):
    # Hermetic: `task_start` and friends resolve `.tausik/` from the ambient cwd
    # for best-effort telemetry. Point that at the temp project so a property run
    # of a few hundred mutations cannot write into the real one.
    monkeypatch.setattr(project_config, "find_tausik_dir", lambda *_a, **_kw: str(tmp_path))
    s = ProjectService(SQLiteBackend(str(tmp_path / "proj.db")))
    yield s
    s.be.close()


def _tree_of(handle: Any) -> str:
    """The projection dir a service (or the exporter's backend view) writes into."""
    return os.path.join(os.path.dirname(os.path.abspath(str(handle.be.db_path))), "tausik")


@pytest.fixture
def root(monkeypatch, svc):
    """Auto-export on, tree root derived PER SERVICE inside the tmp dir.

    Keyed on the handle rather than pinned to one path so a test may drive
    several isolated projects at once — the real `_tree_root` behaves the same
    way, and pinning it would have silently pointed every service at one tree.
    """
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", _tree_of)
    return _tree_of(svc)


def _read_tree(root: str) -> dict[str, str]:
    """Every projection file on disk, keyed like build_tree's dict."""
    out: dict[str, str] = {}
    for kind in ENTITY_DIRS:
        d = os.path.join(root, kind)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(d, name), encoding="utf-8", newline="") as fh:
                out[f"{kind}/{name}"] = fh.read()
    return out


def _assert_tracks(svc, root: str, note: str) -> None:
    expected, _ = build_tree(svc)
    actual = _read_tree(root)
    missing = sorted(set(expected) - set(actual))
    ghosts = sorted(set(actual) - set(expected))
    assert not missing, f"{note}: the DB has rows the tree lacks: {missing}"
    assert not ghosts, f"{note}: the tree has files the DB lacks: {ghosts}"
    differing = sorted(k for k in expected if expected[k] != actual[k])
    assert not differing, f"{note}: content diverged for {differing}"


# --- the generated mutation sequence -----------------------------------------
# A world model tracks just enough state to keep every operation legal, and each
# step is chosen from the operations whose preconditions currently hold. Order,
# nesting depth and WHICH entity an operation lands on all vary with the seed, so
# no single shape (the leaf-only deletes of the old script, say) can be baked in.


class _World:
    """Live entities, as the generator believes them to be after each step."""

    def __init__(self, rnd, tag: str = "a") -> None:
        self.rnd = rnd
        self.tag = tag  # slug namespace: several runs may share one database
        self.n = 0
        self.epics: dict[str, str] = {}  # slug -> status
        self.stories: dict[str, list] = {}  # slug -> [epic_slug, status]
        self.tasks: dict[str, dict] = {}  # slug -> {story, status, planned}
        self.mem: list[int] = []
        self.dec: list[int] = []
        self.edges: list[dict] = []  # {id, src, rel} — `supersedes` retires others
        self.shapes: set[str] = set()  # hard shapes this run actually reached

    def uid(self, prefix: str) -> str:
        self.n += 1
        return f"{prefix}{self.tag}-{self.n}"

    def children_of_epic(self, e: str) -> list[str]:
        return sorted(s for s, v in self.stories.items() if v[0] == e)

    def children_of_story(self, s: str) -> list[str]:
        return sorted(t for t, v in self.tasks.items() if v["story"] == s)

    def drop_story(self, s: str) -> None:
        for t in self.children_of_story(s):
            self.tasks.pop(t, None)
        self.stories.pop(s, None)

    def drop_epic(self, e: str) -> None:
        for s in self.children_of_epic(e):
            self.drop_story(s)
        self.epics.pop(e, None)

    def pick(self, items):
        return self.rnd.choice(sorted(items))

    def tasks_where(self, **kw) -> list[str]:
        return sorted(
            t for t, v in self.tasks.items() if all(v.get(k) == val for k, val in kw.items())
        )


def _op_epic_add(svc, w: _World) -> None:
    e = w.uid("e")
    svc.epic_add(e, f"Эпик {e}")
    w.epics[e] = "open"


def _op_epic_done(svc, w: _World) -> None:
    e = w.pick(w.epics)
    svc.epic_done(e)
    w.epics[e] = "done"


def _op_epic_delete(svc, w: _World) -> None:
    e = w.pick(w.epics)
    if w.children_of_epic(e):
        w.shapes.add("delete-epic-with-stories")
    svc.epic_delete(e)
    w.drop_epic(e)


def _op_story_add(svc, w: _World) -> None:
    e = w.pick(w.epics)
    s = w.uid("s")
    svc.story_add(e, s, f"Стори {s}")
    w.stories[s] = [e, "open"]


def _op_story_done(svc, w: _World) -> None:
    s = w.pick(w.stories)
    svc.story_done(s)
    w.stories[s][1] = "done"


def _op_story_delete(svc, w: _World) -> None:
    s = w.pick(w.stories)
    if w.children_of_story(s):
        w.shapes.add("delete-story-with-tasks")
    svc.story_delete(s)
    w.drop_story(s)


def _op_task_add(svc, w: _World) -> None:
    s = w.pick(w.stories)
    t = w.uid("t")
    svc.task_add(
        s,
        t,
        f"Задача {t}",
        stack="python",
        complexity=w.rnd.choice(["simple", "medium"]),
        goal="Цель задачи",
    )
    w.tasks[t] = {"story": s, "status": "planning", "planned": False, "spec": False}


def _op_task_spec(svc, w: _World) -> None:
    """QG-0 Rules 2 and 6: a task cannot start without AC, scope and a rollback."""
    t = w.pick(w.tasks)
    svc.task_update(
        t,
        acceptance_criteria="AC1. Свойство держится. AC2. Пустое дерево не роняет вызов.",
        scope="scripts/",
        rollback_plan="git revert",
    )
    w.tasks[t]["spec"] = True


def _op_task_budget(svc, w: _World) -> None:
    """The three budget branches — each returns through its own exit."""
    t = w.pick(w.tasks)
    which = w.rnd.choice(["call", "cost", "token"])
    if which == "call":
        svc.task_update(t, call_budget=w.rnd.randint(1, 90))
    elif which == "cost":
        svc.task_update(t, cost_budget_usd=1.25)
    else:
        svc.task_update(t, token_budget=50_000)


def _op_task_budget_rejected(svc, w: _World) -> None:
    """A REFUSED mutation must not leave the tree behind either.

    `task_update` writes three budgets. Validating them one at a time meant a
    rejected third argument exited by exception with the first already in the
    row — the DB changed, the file did not, and the return path that projects was
    never reached. A property that only ever makes LEGAL calls cannot see that:
    the divergence is created by the failure, so the failure has to be part of
    the sequence.

    The refusal VARIES because the first version of this operation only ever
    paired a budget with another budget — the exact combination that had just
    been fixed — so it could not see that the very next validator (ACL) still
    raised after the budget writes had landed. A rejection shape drawn from the
    fix that prompted it tests the fix, not the property.
    """
    t = w.pick(w.tasks)
    bad = w.rnd.choice(
        [
            {"cost_budget_usd": -1.0},  # refused among the budgets
            {"scope_paths": "{not-json"},  # refused by ACL normalization, after them
            {"scope_tools": "{not-json"},
            {"complexity": "gigantic"},  # refused by the enum check
            {"nosuchcolumn": 1},  # refused by the backend's column whitelist
        ]
    )
    with pytest.raises((ServiceError, ValueError)):
        svc.task_update(t, call_budget=7, **bad)


def _op_task_start(svc, w: _World) -> None:
    t = w.pick(w.tasks_where(status="planning", spec=True))
    story = w.tasks[t]["story"]
    if w.stories[story][1] == "open":
        # The cascade branch the old fixed script could never reach: the story was
        # always closed first, so `story["status"] == "open"` was dead code here.
        w.shapes.add("start-task-in-open-story")
    svc.task_start(t)
    w.tasks[t]["status"] = "active"
    if w.stories[story][1] == "open":
        w.stories[story][1] = "active"
    if w.epics.get(w.stories[story][0]) not in ("active", "done"):
        w.epics[w.stories[story][0]] = "active"


def _op_task_log(svc, w: _World) -> None:
    t = w.pick(w.tasks)
    svc.task_log(t, f"шаг {w.n}")


def _op_task_plan(svc, w: _World) -> None:
    t = w.pick(w.tasks)
    svc.task_plan(t, ["шаг один", "шаг два", "шаг три"])
    w.tasks[t]["planned"] = True


def _op_task_step(svc, w: _World) -> None:
    t = w.pick(w.tasks_where(planned=True))
    svc.task_step(t, w.rnd.randint(1, 3))


def _op_task_block(svc, w: _World) -> None:
    t = w.pick(w.tasks_where(status="active"))
    svc.task_block(t, reason="ждём смежника")
    w.tasks[t]["status"] = "blocked"


def _op_task_unblock(svc, w: _World) -> None:
    t = w.pick(w.tasks_where(status="blocked"))
    svc.task_unblock(t)
    w.tasks[t]["status"] = "active"


def _op_task_review(svc, w: _World) -> None:
    t = w.pick(w.tasks_where(status="active"))
    svc.task_review(t)
    w.tasks[t]["status"] = "review"


def _op_task_close(svc, w: _World) -> None:
    """The durable half of `task_done`: the status write plus `_cascade_done`.

    `task_done` itself runs the QG-2 gate stack (pytest, git, the verify cache)
    and cannot run inside a property loop. What it writes to PROJECTED tables is
    exactly this — the task row, then whatever the cascade closes — so the
    projection surface is covered even though the gates are not. Named here
    rather than left out, because "task done" was the headline case of the
    original defect and its absence from the old script was a real hole.
    """
    t = w.pick(w.tasks_where(status="review"))
    svc.be.task_update(t, status="done", completed_at=utcnow_iso())
    svc._cascade_done(t)
    svc._project_task(t)
    w.tasks[t]["status"] = "done"
    story = w.tasks[t]["story"]
    if not [x for x in w.children_of_story(story) if w.tasks[x]["status"] != "done"]:
        w.stories[story][1] = "done"
        epic = w.stories[story][0]
        if not [s for s in w.children_of_epic(epic) if w.stories[s][1] != "done"]:
            w.epics[epic] = "done"


def _op_task_move(svc, w: _World) -> None:
    t = w.pick(w.tasks)
    s = w.pick(w.stories)
    svc.task_move(t, s)
    w.tasks[t]["story"] = s


def _op_task_delete(svc, w: _World) -> None:
    t = w.pick(w.tasks)
    svc.task_delete(t)
    w.tasks.pop(t, None)


def _op_decide(svc, w: _World) -> None:
    """Both branches: linked to a task (the one that used to skip export) and free."""
    linked = w.rnd.random() < 0.5 and bool(w.tasks)
    slug = w.pick(w.tasks) if linked else None
    msg = svc.decide(f"Решение {w.uid('d')}", task_slug=slug, rationale="Основание")
    w.dec.append(_mem_id(msg))
    if linked:
        w.shapes.add("decision-linked-to-task")


def _op_memory_add(svc, w: _World) -> None:
    kind = w.rnd.choice(["pattern", "gotcha", "convention", "context"])
    m = w.uid("m")
    w.mem.append(_mem_id(svc.memory_add(kind, f"Запись {m}", f"Содержимое {m}.")))


def _op_dead_end(svc, w: _World) -> None:
    d = w.uid("de")
    w.mem.append(_mem_id(svc.dead_end(f"Подход {d}", "Не сработал по измеримой причине")))


def _op_memory_delete(svc, w: _World) -> None:
    mid = w.rnd.choice(w.mem)
    svc.memory_delete(mid)
    w.mem.remove(mid)


def _op_memory_link(svc, w: _World) -> None:
    a, b = w.rnd.sample(sorted(w.mem), 2)
    # `supersedes` takes the second branch of memory_link: it invalidates the
    # target's own supersedes edges too, so TWO files change from one call.
    rel = w.rnd.choice(["relates_to", "caused_by", "contradicts", "supersedes"])
    eid = _mem_id(svc.memory_link("memory", a, "memory", b, rel))
    if rel == "supersedes":
        w.edges = [e for e in w.edges if not (e["src"] == b and e["rel"] == "supersedes")]
    w.edges.append({"id": eid, "src": a, "rel": rel})


def _op_memory_unlink(svc, w: _World) -> None:
    edge = w.rnd.choice(w.edges)
    svc.memory_unlink(edge["id"])
    w.edges.remove(edge)


def _op_memory_archive(svc, w: _World) -> None:
    """Back-date one entry, then run the retention sweep over it."""
    mid = w.rnd.choice(w.mem)
    svc.be._ex("UPDATE memory SET created_at='2020-01-01T00:00:00Z' WHERE id=?", (mid,))
    svc.memory_archive("30d", confirm=True)
    w.mem.remove(mid)


# (name, precondition, operation). Preconditions keep every generated sequence
# legal without constraining its SHAPE — which is the part that has to vary.
_OPS: tuple[tuple[str, Callable[[_World], bool], Callable[[Any, _World], None]], ...] = (
    ("epic_add", lambda w: len(w.epics) < 4, _op_epic_add),
    ("epic_done", lambda w: bool(w.epics), _op_epic_done),
    ("epic_delete", lambda w: len(w.epics) > 1, _op_epic_delete),
    ("story_add", lambda w: bool(w.epics) and len(w.stories) < 6, _op_story_add),
    ("story_done", lambda w: bool(w.stories), _op_story_done),
    ("story_delete", lambda w: len(w.stories) > 1, _op_story_delete),
    ("task_add", lambda w: bool(w.stories) and len(w.tasks) < 8, _op_task_add),
    ("task_spec", lambda w: bool(w.tasks), _op_task_spec),
    ("task_budget", lambda w: bool(w.tasks), _op_task_budget),
    ("task_budget_rejected", lambda w: bool(w.tasks), _op_task_budget_rejected),
    ("task_start", lambda w: bool(w.tasks_where(status="planning", spec=True)), _op_task_start),
    ("task_log", lambda w: bool(w.tasks), _op_task_log),
    ("task_plan", lambda w: bool(w.tasks), _op_task_plan),
    ("task_step", lambda w: bool(w.tasks_where(planned=True)), _op_task_step),
    ("task_block", lambda w: bool(w.tasks_where(status="active")), _op_task_block),
    ("task_unblock", lambda w: bool(w.tasks_where(status="blocked")), _op_task_unblock),
    ("task_review", lambda w: bool(w.tasks_where(status="active")), _op_task_review),
    ("task_close", lambda w: bool(w.tasks_where(status="review")), _op_task_close),
    ("task_move", lambda w: bool(w.tasks) and bool(w.stories), _op_task_move),
    ("task_delete", lambda w: len(w.tasks) > 1, _op_task_delete),
    ("decide", lambda w: True, _op_decide),
    ("memory_add", lambda w: len(w.mem) < 8, _op_memory_add),
    ("dead_end", lambda w: len(w.mem) < 8, _op_dead_end),
    ("memory_delete", lambda w: len(w.mem) > 2, _op_memory_delete),
    ("memory_link", lambda w: len(w.mem) >= 2, _op_memory_link),
    ("memory_unlink", lambda w: bool(w.edges), _op_memory_unlink),
    ("memory_archive", lambda w: len(w.mem) > 2, _op_memory_archive),
)

# Deterministic by construction: a fixed seed list, `random.Random(seed)`, and
# every choice made over a SORTED collection. A red here is reproducible from the
# seed printed in the failure message — an irreproducible red would be worse than
# no test at all.
_SEEDS = (1, 2, 3, 5, 8, 13)
# Long enough for the DEEP shapes to appear: a story only becomes non-empty
# after epic → story → task, and a task only reaches `active` after it is spec'd
# for QG-0. Short runs stall in the shallow half of the model, which is how the
# old fixed script came to look adequate.
_STEPS = 80


def _run_sequence(svc, root: str, seed: int, steps: int = _STEPS) -> _World:
    """Drive `steps` legal mutations, asserting the invariant after EVERY one."""
    import random

    w = _World(random.Random(seed), tag=f"s{seed}")
    trail: list[str] = []
    for i in range(steps):
        eligible = [(n, op) for n, pre, op in _OPS if pre(w)]
        name, op = w.rnd.choice(eligible)
        op(svc, w)
        trail.append(f"{i + 1}.{name}")
        # After EVERY mutation, not once per group: sampling at the end cannot
        # tell "the projection lagged and caught up" from "it never lagged".
        _assert_tracks(svc, root, f"seed={seed} after {' '.join(trail)}")
    return w


@pytest.mark.parametrize("seed", _SEEDS)
def test_projection_tracks_db_after_every_mutation(svc, root, seed):
    """The load-bearing test: no manual export anywhere in this function."""
    w = _run_sequence(svc, root, seed)
    assert w.n > 0


def test_generated_sequences_reach_the_shapes_the_old_script_could_not(svc, root, tmp_path):
    """The generator is not degenerate: the three dead branches are now live.

    Asserted over the UNION of the seeds rather than per-seed — requiring every
    shape in every run would force the generator back into a fixed script, which
    is the defect being fixed. If a future edit makes one of these unreachable
    again, this fails and says which one.
    """
    seen: set[str] = set()
    for seed in _SEEDS:
        s = ProjectService(SQLiteBackend(str(tmp_path / f"cover{seed}" / "proj.db")))
        try:
            seen |= _run_sequence(s, _tree_of(s), seed).shapes
        finally:
            s.be.close()
    required = {
        "delete-epic-with-stories",  # ON DELETE CASCADE, transitively
        "delete-story-with-tasks",
        "start-task-in-open-story",  # the `status == "open"` cascade branch
        "decision-linked-to-task",  # the original defect's headline case
    }
    assert required <= seen, f"generator no longer reaches: {sorted(required - seen)}"


def test_the_sequence_is_reproducible_from_its_seed(svc, root, tmp_path):
    """Same seed → same trail. An irreproducible red cannot be debugged."""

    def trail(run: str) -> list[str]:
        s = ProjectService(SQLiteBackend(str(tmp_path / run / "proj.db")))
        try:
            import random

            w = _World(random.Random(_SEEDS[0]), tag=run)
            names: list[str] = []
            for _ in range(_STEPS):
                eligible = [(n, op) for n, pre, op in _OPS if pre(w)]
                name, op = w.rnd.choice(eligible)
                op(s, w)
                names.append(name)
            return names
        finally:
            s.be.close()

    assert trail("repro-a") == trail("repro-b")


# --- the ratchet: WRITE PATHS, not entity kinds -------------------------------


def _projection_read_set(svc) -> set[str]:
    """Every table `build_tree` reads — i.e. every table that CAN change the tree.

    Discovered by tracing the real query load of `build_tree`, not listed here:
    `ENTITY_DIRS` names the five projected KINDS and would have missed
    `task_logs` (the task Journal) and `memory_edges` (the `edges:` block)
    entirely — two tables whose rows are projected without owning a directory.
    """
    tap = _SqlTap()
    svc.be._conn.set_trace_callback(tap)
    try:
        build_tree(svc)
    finally:
        svc.be._conn.set_trace_callback(None)
    return tap.reads


# A write path the projected surface can be reached by, which NO ProjectService
# method issues. Each is excluded WITH its reason and the exclusion is checked
# both ways (see the ratchet): if one becomes reachable, the equality below
# fails and the entry must go. Forgetting to ADD an entry is the safe direction
# — it makes the test red, never green.
_UNREACHABLE: dict[tuple[str, str], str] = {
    ("task_logs", "UPDATE"): "the journal is append-only; nothing rewrites a log line",
    ("task_logs", "DELETE"): "removed only by ON DELETE CASCADE, which SQLite runs itself",
    ("decisions", "UPDATE"): "no service method edits a recorded decision",
    ("decisions", "DELETE"): (
        "only `brain_move` deletes one, straight through `_ex` with no projection "
        "— see task brain-move-deletes-leave-ghost-projection"
    ),
    ("memory_edges", "DELETE"): "edges are soft-invalidated (`valid_to`), never deleted",
}


def test_write_path_ratchet_counts_paths_not_kinds(svc, root, tap):
    """Every write path into the projected surface is exercised — exactly.

    The old ratchet compared five entity KINDS against `ENTITY_DIRS`, which one
    trivial mutator per kind satisfied while whole paths stayed dark. The set
    here is derived from the write layer at runtime: the tables `build_tree`
    reads, crossed with the three DML verbs, minus the paths documented above as
    unreachable. Equality, not containment — so a table that gains a delete path,
    or a sixth projected kind, or an exclusion that stops being true, all fail.
    """
    for seed in _SEEDS:
        _run_sequence(svc, root, seed)
    tap.on = False
    universe = {(t, v) for t in _projection_read_set(svc) for v in ("INSERT", "UPDATE", "DELETE")}
    bogus = sorted(set(_UNREACHABLE) - universe)
    assert not bogus, f"exclusion names a path outside the projected surface: {bogus}"
    expected = universe - set(_UNREACHABLE)
    covered = tap.writes & universe
    assert covered == expected, (
        f"uncovered write paths: {sorted(expected - covered)}; "
        f"paths declared unreachable but observed: {sorted(covered - expected)}"
    )


def test_registry_has_not_collapsed(svc):
    """Guard against a degenerate pass: an empty registry would make both green."""
    assert len(ENTITY_DIRS) >= 5
    assert "decisions" in ENTITY_DIRS and "tasks" in ENTITY_DIRS
    reads = _projection_read_set(svc)
    assert set(ENTITY_DIRS) <= reads, "a projected kind whose table build_tree never reads"
    assert {"task_logs", "memory_edges"} <= reads


def test_the_property_run_stays_affordable(svc, root):
    """One seed, wall-clock. 6500 tests cannot each cost a minute."""
    t0 = time.monotonic()
    _run_sequence(svc, root, _SEEDS[0])
    assert time.monotonic() - t0 < 30.0


# --- the two behaviours the property depends on ------------------------------


def test_delete_removes_the_projection_file(svc, root):
    svc.epic_add("e", "Эпик")
    svc.story_add("e", "s", "Стори")
    svc.task_add("s", "temp", "Временная", goal="Цель")
    path = os.path.join(root, "tasks", "temp.md")
    assert os.path.isfile(path)
    svc.task_delete("temp")
    assert not os.path.exists(path), "a deleted task left a ghost file behind"


def test_archived_memory_leaves_the_projection(svc, root):
    mid = _mem_id(svc.memory_add("context", "Старая запись", "Уедет в архив"))
    slug = svc.be.memory_get(mid)["slug"]
    path = os.path.join(root, "memory", f"{slug}.md")
    assert os.path.isfile(path)
    svc.be._ex("UPDATE memory SET created_at='2020-01-01T00:00:00Z' WHERE id=?", (mid,))
    svc.memory_archive("30d", confirm=True)
    assert not os.path.exists(path), "archived memory is excluded from the projection"


def test_export_failure_does_not_roll_back_the_write(svc, root, monkeypatch):
    """Fail-open (gotcha #271): the DB write is the truth, the file is best-effort."""

    def _boom(*_a, **_kw):
        raise RuntimeError("serializer exploded")

    monkeypatch.setattr("state_export.export_one", _boom)
    svc.epic_add("survivor", "Эпик переживает падение экспорта")
    assert svc.be.epic_get("survivor") is not None
    assert not os.path.exists(os.path.join(root, "epics", "survivor.md"))
