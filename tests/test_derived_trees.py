"""Generated trees are declared once and every reader uses that declaration.

complexity-proxy-counts-state-projection (github#76). The complexity detector
counted tausik/ projection files as behaviour: 9 of 10 and 23 of 26 declared
files in two real closes were projection, so diligent journaling read as an
understated task and false detections went to the supervision log.
"""

from __future__ import annotations

from pathlib import Path

import complexity_understatement as cu
import derived_trees

_ROOT = Path(__file__).resolve().parents[1]
REAL_CLOSE = [f"tausik/tasks/t{i}.md" for i in range(22)] + [
    ".gitattributes",
    "tests/test_x.py",
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
]


def test_the_projection_is_not_behaviour():
    """The 26-path close of tausik-tree-gitattributes-lf: no understatement now."""
    assert cu.behaviour_bearing_files(REAL_CLOSE) == [".gitattributes", "tests/test_x.py"]
    assert cu.understatement("simple", REAL_CLOSE) is None


def test_the_detector_is_not_blind():
    """NEGATIVE: nine real code files still warn; thresholds are untouched."""
    u = cu.understatement("simple", [f"scripts/s{i}.py" for i in range(9)])
    assert u is not None and u["implied"] != "simple"


class _Events:
    def __init__(self):
        self.calls = []

    def event_add(self, *args):
        self.calls.append(args)


def test_no_false_detection_reaches_the_supervision_log():
    be = _Events()
    assert cu.warn_if_understated(be, "t", "simple", REAL_CLOSE) == ""
    assert be.calls == []


def test_config_files_in_tausik_stay_behaviour_bearing():
    assert cu.behaviour_bearing_files(["tausik/gates.json", "tausik/policy.json"]) == [
        "tausik/gates.json",
        "tausik/policy.json",
    ]


def test_every_reader_takes_the_layout_from_the_one_source():
    """A hand list in a reader is how the tausik/ tree leaked; none may return."""
    assert cu._GENERATED_DIRS == derived_trees.relative_dirs()
    for rel in ("scripts/state_triggers.py", "scripts/gen_doc_constants.py"):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert "derived_trees" in text, rel
    assert '"tausik")' not in (_ROOT / "scripts/state_triggers.py").read_text(encoding="utf-8")
