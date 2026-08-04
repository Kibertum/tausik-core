"""Class public-surface gate (filesize-mro-exempt-mcp).

The line gate cannot see a god-object assembled from mixins: every mixin stays
under the line cap while the class they compose does not. These pin that the new
unit catches exactly that, and — just as important — that it does NOT fire on
shapes that merely look big (many private helpers, a long file with small
classes), because a gate with false positives is a gate that gets disabled.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import gate_class_surface as gcs  # noqa: E402
import gate_filesize  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "harness/", "bootstrap/"]

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tree(tmp_path, files: dict[str, str]) -> str:
    """Write {relative path: source} under tmp_path/scripts and return the root."""
    for rel, src in files.items():
        p = tmp_path / "scripts" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src, encoding="utf-8")
    return str(tmp_path)


# --- AC1: the new unit ------------------------------------------------------


def test_god_class_built_from_small_mixins_is_caught(tmp_path):
    """THE POINT: each mixin is tiny, the composed class is not."""
    src_files, bases = {}, []
    for i in range(4):  # four mixins of 10 public methods each, in separate files
        body = "\n".join(f"    def op_{i}_{j}(self): ..." for j in range(10))
        src_files[f"mixin_{i}.py"] = f"class Mixin{i}:\n{body}\n"
        bases.append(f"Mixin{i}")
    src_files["god.py"] = "class God(" + ", ".join(bases) + "):\n    def extra(self): ...\n"
    root = _tree(tmp_path, src_files)

    ranked, errors, ambiguous = gcs.measure(root)
    assert errors == [] and ambiguous == 0
    surface = {name: size for name, size, _p in ranked}
    assert surface["God"] == 41, surface  # 4x10 inherited + 1 own
    for i in range(4):
        assert surface[f"Mixin{i}"] == 10  # every FILE looks perfectly healthy


def test_private_members_do_not_count(tmp_path):
    """NEGATIVE-1: the cap is on the public CONTRACT, not internal complexity."""
    body = "\n".join(f"    def _helper_{j}(self): ..." for j in range(50))
    root = _tree(tmp_path, {"quiet.py": f"class Quiet:\n{body}\n    def run(self): ...\n"})
    ranked, _errors, _amb = gcs.measure(root)
    assert dict((n, s) for n, s, _ in ranked)["Quiet"] == 1


def test_unparseable_file_fails_loudly_and_is_not_silently_skipped(tmp_path):
    """NEGATIVE-2: a measurer that skips what it cannot read overstates coverage."""
    root = _tree(tmp_path, {"broken.py": "class Oops(:\n", "fine.py": "class Fine:\n    pass\n"})
    ranked, errors, _amb = gcs.measure(root)
    assert any("broken.py" in e and "SyntaxError" in e for e in errors), errors
    assert any(n == "Fine" for n, _s, _p in ranked)  # the readable file still measured


def test_gate_reports_parse_failure_as_a_failure(monkeypatch):
    """An unreadable file must RED the gate, not appear as a footnote on a pass."""
    monkeypatch.setattr(gcs, "measure", lambda *a, **k: ([], ["x.py: SyntaxError: bad"], 0))
    ok, msg = gcs.run_class_surface_gate({"max_public_members": 60}, [])
    assert ok is False
    assert "Could not measure every file" in msg and "x.py" in msg


def test_same_class_name_in_two_modules_measures_both(tmp_path):
    """Keying by name alone silently DROPPED one — the under-reporting this gate exists to stop."""
    root = _tree(
        tmp_path,
        {
            "a.py": "class Dup:\n    def only_a(self): ...\n",
            "b.py": "class Dup:\n" + "\n".join(f"    def m{j}(self): ..." for j in range(7)) + "\n",
        },
    )
    ranked, errors, _amb = gcs.measure(root)
    dups = sorted(s for n, s, _p in ranked if n == "Dup")
    assert dups == [1, 7], f"both Dup classes must be measured, got {dups}"
    assert errors == []


def test_ambiguous_base_is_left_unresolved_not_guessed(tmp_path):
    """Picking one by directory order would make the number depend on listing order."""
    root = _tree(
        tmp_path,
        {
            "a.py": "class Amb:\n    def from_a(self): ...\n",
            "b.py": "class Amb:\n    def from_b(self): ...\n",
            "c.py": "class Child(Amb):\n    def own(self): ...\n",
        },
    )
    ranked, _errors, ambiguous = gcs.measure(root)
    assert ambiguous >= 1
    assert dict((n, s) for n, s, _p in ranked)["Child"] == 1  # lower bound, not a guess


def test_diamond_inheritance_terminates_and_counts_once(tmp_path):
    root = _tree(
        tmp_path,
        {
            "d.py": (
                "class Base:\n    def shared(self): ...\n"
                "class L(Base):\n    def l_only(self): ...\n"
                "class R(Base):\n    def r_only(self): ...\n"
                "class Bottom(L, R):\n    pass\n"
            )
        },
    )
    ranked, errors, _amb = gcs.measure(root)
    assert errors == []
    assert dict((n, s) for n, s, _p in ranked)["Bottom"] == 3  # shared counted once


def test_override_does_not_double_count(tmp_path):
    root = _tree(
        tmp_path,
        {"o.py": "class P:\n    def run(self): ...\nclass C(P):\n    def run(self): ...\n"},
    )
    assert dict((n, s) for n, s, _p in gcs.measure(root)[0])["C"] == 1


# --- AC3: repo-wide + ratchet ----------------------------------------------


def test_gate_is_repo_wide_and_ignores_the_files_argument():
    """A per-file gate never sees a class that drifted through its BASES."""
    ok_empty, msg_empty = gcs.run_class_surface_gate({"max_public_members": 60}, [])
    ok_bogus, msg_bogus = gcs.run_class_surface_gate(
        {"max_public_members": 60}, ["does/not/exist.py"]
    )
    assert (ok_empty, msg_empty) == (ok_bogus, msg_bogus)
    assert "classes across" in msg_empty


def test_live_repo_passes_with_the_committed_baseline():
    ok, msg = gcs.run_class_surface_gate({"max_public_members": 60}, [])
    assert ok, msg


def test_repo_root_resolves_the_same_from_the_deployed_copy():
    """Gates RUN from .claude/scripts/, where dirname-twice lands on `.claude/`.

    That directory has a scripts/ mirror but no tausik/gates.json and no harness/,
    so the gate measured the mirror and lost its ratchet baseline — failing on the
    two classes the baseline exists to hold, on every single close. The root must
    be .git-anchored so both invocations agree.
    """
    deployed = os.path.join(_REPO, ".claude", "scripts", "gate_class_surface.py")
    if not os.path.isfile(deployed):
        pytest.skip("no deployed copy in this tree")
    import importlib.util

    spec = importlib.util.spec_from_file_location("gcs_deployed", deployed)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert os.path.normcase(mod._repo_root()) == os.path.normcase(_REPO)
    assert sorted(mod._load_config().get("baseline", {})) == sorted(
        gcs._load_config().get("baseline", {})
    )
    assert mod.run_class_surface_gate({"max_public_members": 60}, [])[0] is True


def test_baselined_class_fails_when_it_grows(monkeypatch):
    """The ratchet only turns down: a baselined class that GROWS is a regression."""
    monkeypatch.setattr(gcs, "_load_config", lambda: {"baseline": {"Big": 100}})
    monkeypatch.setattr(gcs, "measure", lambda *a, **k: ([("Big", 101, "x.py")], [], 0))
    ok, msg = gcs.run_class_surface_gate({"max_public_members": 60}, [])
    assert ok is False and "grew to 101" in msg

    monkeypatch.setattr(gcs, "measure", lambda *a, **k: ([("Big", 100, "x.py")], [], 0))
    assert gcs.run_class_surface_gate({"max_public_members": 60}, [])[0] is True


def test_new_god_class_is_blocked_outright_not_baselined(monkeypatch):
    monkeypatch.setattr(gcs, "_load_config", lambda: {"baseline": {"Big": 100}})
    monkeypatch.setattr(gcs, "measure", lambda *a, **k: ([("Fresh", 61, "y.py")], [], 0))
    ok, msg = gcs.run_class_surface_gate({"max_public_members": 60}, [])
    assert ok is False and "Fresh exposes 61" in msg


def test_committed_baseline_matches_reality_and_only_ratchets_down():
    """A baseline larger than the truth is a licence to grow back up to it."""
    with open(os.path.join(_REPO, "tausik", "gates.json"), encoding="utf-8") as fh:
        baseline = json.load(fh)["class_surface"]["baseline"]
    ranked, _errors, _amb = gcs.measure()
    actual = {name: size for name, size, _p in ranked}
    for name, allowed in baseline.items():
        assert name in actual, f"baselined class {name} no longer exists — drop the entry"
        assert actual[name] <= allowed, f"{name} grew: {actual[name]} > baseline {allowed}"
        assert actual[name] == allowed, (
            f"{name} is now {actual[name]} but the baseline still says {allowed} — "
            "tighten the baseline so it cannot grow back"
        )


# --- AC2: the blanket mcp/ exemption is gone --------------------------------


def test_blanket_mcp_tree_exemption_is_removed():
    dirs, _names = gate_filesize._resolve_exempts()
    assert "harness/claude/mcp/" not in dirs, (
        "the source MCP tree must be measured — a whole-tree exemption also covers "
        "every file added to it later"
    )
    assert ".claude/mcp/" in dirs  # generated mirror stays exempt (source is measured)


def test_oversized_non_dispatch_file_under_mcp_is_caught(tmp_path):
    """NEGATIVE: only the NAMED files are exempt, not anything living under mcp/."""
    p = tmp_path / "harness" / "claude" / "mcp" / "project" / "newcomer.py"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join(f"x = {i}" for i in range(600)), encoding="utf-8")
    ok, msg = gate_filesize.run_filesize_gate({"max_lines": 500}, [str(p)])
    assert ok is False and "newcomer.py" in msg


def _committed_filesize_config() -> dict:
    with open(os.path.join(_REPO, "tausik", "gates.json"), encoding="utf-8") as fh:
        return json.load(fh)["filesize"]


# Derived from the registry, NOT restated here (convention #339). A hardcoded
# copy of this list is what broke when mcp-handlers-god-module-split retired the
# handlers.py exemption: the registry said one thing, the test asserted another,
# and the test failed for the retirement it was supposed to be indifferent to.
# Deriving it means removing an exemption needs no test edit, while ADDING one
# still has to bring a reason with it.
_NAMED_EXEMPT_FILES = _committed_filesize_config().get("exempt_files") or []


@pytest.mark.parametrize("rel", _NAMED_EXEMPT_FILES, ids=_NAMED_EXEMPT_FILES)
def test_named_exempt_files_are_exempt_and_documented(rel):
    assert rel in gate_filesize._resolve_exempt_files()
    reasons = _committed_filesize_config()["_exempt_files_reasons"]
    assert rel in reasons and len(reasons[rel]) > 80, (
        "every named exemption must carry a reason; a temporary one must name the "
        "task that retires it"
    )


def test_no_reason_documents_an_exemption_that_no_longer_exists():
    """Retiring an exemption must take its reason with it.

    An orphaned reason reads as a live exemption to anyone auditing the file —
    which is the whole point of requiring reasons in the first place.
    """
    cfg = _committed_filesize_config()
    orphaned = sorted(set(cfg["_exempt_files_reasons"]) - set(cfg.get("exempt_files") or []))
    assert not orphaned, f"reason kept for a file that is no longer exempt: {orphaned}"
