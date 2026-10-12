"""Ratchet: memory and the working tree stay clean, measured from git-tracked material.

MEASURED BEFORE (session #277): 6 stale file refs, 1 orphan module, 6 DB backups
holding 508 MiB of which 3 were unmanaged. MEASURED AFTER: 0, 0, and 3 managed with
0 unmanaged. The thresholds in `tausik/gates.json` are the AFTER numbers — taken
before the sweep they would have frozen the rubbish in place, which is the negative
case the task named.

THREE OF THOSE FOUR FINDINGS WERE DETECTOR BLINDNESS, not wrong records: the orphan
scan could not see a module imported by name-as-string, and the stale-file scan had
no notion of a path cited as history. A threshold over a blind detector is a zero
that means nothing, so every measure here is paired with a proof that it still goes
red — the fix must not have been "stop looking".

Each measure reads material that git carries, so the number is the same on a fresh
clone: `tausik/memory/*.md` is the projection of exactly the LIVE memory rows (the
exporter deletes the file of an archived one), and `.tausik/` is absent there, where
zero unmanaged backups is the truth rather than a skipped check.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

_GATES = _REPO / "tausik" / "gates.json"

#: This file measures whole trees, so a scoped run that touches any of them must
#: include it: `scripts/` for the orphan scan, `tausik/memory/` for stale refs.
CROSSCUTTING_SCOPE = ["scripts/", "tausik/memory/"]


def _ratchet() -> dict:
    return json.loads(_GATES.read_text(encoding="utf-8"))["repo_hygiene"]


def _memory_bodies() -> list[tuple[str, str]]:
    """(file name, body after the frontmatter) for every live memory projection."""
    out = []
    for path in sorted((_REPO / "tausik" / "memory").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        out.append((path.name, parts[2] if len(parts) == 3 else text))
    return out


def _stale_refs() -> list[str]:
    """Stale-file findings over the projection, via the LINT's own code path.

    `find_lint_candidates` rather than a private re-derivation: a second copy of
    this rule is how the gate and the command drift into two answers, which is
    the class of defect memory #682 was written about.
    """
    from memory_cleanup import find_lint_candidates
    from service_knowledge_hygiene import git_ignore_probe

    bodies = _memory_bodies()
    rows = [{"id": i, "title": name, "content": body} for i, (name, body) in enumerate(bodies)]
    ignored = git_ignore_probe(str(_REPO))
    findings = find_lint_candidates(rows, [], lambda p: (_REPO / p).exists(), lambda p: ignored(p))
    return [f"{f['title']}: {f['reason']}" for f in findings if f["kind"] == "stale_file"]


def test_stale_memory_refs_within_the_ratchet():
    """A record naming a path that vanished sends the reader to a file that is not there.

    EQUALITY, not "at most": a threshold sitting above the measurement is slack nobody
    declared, and slack is where the next 508 MiB goes. So the debt counters fail both
    when the debt grows and when someone raises the number to make the debt fit.
    """
    found = _stale_refs()
    assert len(found) == _ratchet()["stale_memory_refs"], "\n".join(found) or "lower the threshold"


def test_a_stale_ref_is_still_caught_and_a_historical_citation_is_not():
    """The zero above must come from clean records, not from a detector that stopped.

    Both halves matter. Without the first, the sweep could have been done by widening
    the escape hatch until nothing matched; without the second, every correct deletion
    reopens the register, because a record that says "X was removed" cannot stop
    naming X.
    """
    from memory_cleanup import _extract_paths

    gone = "scripts/gate_that_was_deleted.py"
    assert _extract_paths(f"the fix lives in {gone}") == [gone]
    assert _extract_paths(f"{gone} (удалён в a6f614a2)") == []
    assert _extract_paths(f"{gone} (удалён)") == [gone], "a removal claim needs its commit"


def test_orphan_modules_within_the_ratchet():
    """A module in scripts/ that nothing imports and no document names is dead weight."""
    import audit_orphan_files

    found = audit_orphan_files.collect_orphans(_REPO)
    assert len(found) == _ratchet()["orphan_modules"], found or "lower the threshold"


def test_the_orphan_scan_sees_an_import_by_name(tmp_path):
    """The blindness that produced the only orphan finding, as a test.

    `project_parser_answers` was reached solely through `__import__("…")` from two
    modules, so the AST walk saw no reference and called a live CLI module an orphan.
    A COMPUTED name is deliberately still invisible: it names no single module, and
    claiming one would trade this false positive for a false negative.
    """
    from audit_orphan_files import _imports_in

    src = tmp_path / "probe.py"
    src.write_text(
        'import os\n__import__("static_target")\n'
        'importlib.import_module("other_target")\n'
        '__import__(f"computed_{kind}")\n',
        encoding="utf-8",
    )
    seen = _imports_in(src)
    assert {"os", "static_target", "other_target"} <= seen
    assert not any(name.startswith("computed") for name in seen), seen


def test_db_backups_within_the_ratchet():
    """Backups accumulated to 508 MiB because half of them were outside every rule."""
    from cmd_db import list_backups, unmanaged_backups

    node = _ratchet()["db_backups"]
    tausik_dir = str(_REPO / ".tausik")
    unmanaged = unmanaged_backups(tausik_dir)
    assert len(unmanaged) == node["unmanaged"], [os.path.basename(p) for p in unmanaged]
    # `managed_keep` is a POLICY CAP, not a debt baseline, so this one is "at most":
    # a fresh clone holds no backups at all, and zero there is correct rather than
    # slack. What the cap forbids is a fourth snapshot outliving the prune.
    managed = len(list_backups(tausik_dir)) - len(unmanaged)
    assert managed <= node["managed_keep"], f"{managed} managed backups kept"


@pytest.fixture
def backup_dir(tmp_path):
    """Six backups in the shape the sweep found: three managed, three made by hand."""
    for name in (
        "tausik.db.bak.v64",
        "tausik.db.bak.v65",
        "tausik.db.bak.v9",
        "tausik.db.bak.pre-redact-263",
        "tausik.db.bak.20260924T073736-before-leak-cleanup",
        "tausik.db.bak.20260924T074400-before-redact",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")
    return str(tmp_path)


def test_a_hand_made_backup_is_named_unmanaged(backup_dir):
    from cmd_db import unmanaged_backups

    names = sorted(os.path.basename(p) for p in unmanaged_backups(backup_dir))
    assert names == [
        "tausik.db.bak.20260924T073736-before-leak-cleanup",
        "tausik.db.bak.20260924T074400-before-redact",
        "tausik.db.bak.pre-redact-263",
    ]


def test_prune_keeps_managed_by_version_and_drops_the_unmanaged(backup_dir):
    """The old ranking was by mtime over ALL backups, which was exactly backwards.

    Written in one directory, the hand-made files are the newest, so mtime order kept
    the three nobody manages and deleted the migration snapshots the prune exists to
    tidy. Version order also matters on its own: `v9` sorts after `v65` as a string.
    """
    from cmd_db import prune_backups

    result = prune_backups(backup_dir, keep=2)
    assert sorted(os.path.basename(p) for p in result["kept"]) == [
        "tausik.db.bak.v64",
        "tausik.db.bak.v65",
    ]
    assert len(result["deleted"]) == 4 and not result["errors"]
    assert sorted(os.listdir(backup_dir)) == ["tausik.db.bak.v64", "tausik.db.bak.v65"]


def test_dry_run_reports_the_same_list_and_removes_nothing(backup_dir):
    """A command that destroys hundreds of megabytes can be asked first."""
    from cmd_db import prune_backups

    before = sorted(os.listdir(backup_dir))
    preview = prune_backups(backup_dir, keep=2, dry_run=True)
    assert len(preview["deleted"]) == 4
    assert sorted(os.listdir(backup_dir)) == before
    assert sorted(preview["deleted"]) == sorted(prune_backups(backup_dir, keep=2)["deleted"])


def test_every_threshold_is_declared():
    """A ratchet that can be removed by deleting a key is not a ratchet."""
    node = _ratchet()
    assert isinstance(node["stale_memory_refs"], int)
    assert isinstance(node["orphan_modules"], int)
    assert isinstance(node["db_backups"]["managed_keep"], int)
    assert isinstance(node["db_backups"]["unmanaged"], int)
