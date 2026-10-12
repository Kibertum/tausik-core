"""An example quoted in prose is not a citation — and a citation is not an example.

Two independent detectors, `memory lint` (stale_file) and `audit evidence`,
made the same mistake for the same reason. Measured in session #209 before the
fix: `audit evidence` reported 25 refs as NEVER_EXISTED of which 13 were
conventional examples and 3 were genuine misses, so the headline over-reported
real rot by a factor of two beside a ROTTED bucket of 22; `memory lint`
reported 7 stale_file findings of which 5 were not stale.

Every test here carries BOTH ends. A detector can always be quieted by turning
it off, so a test that only proves the noise is gone proves nothing: each rule
is pinned by an example it must set aside AND by a real citation it must keep.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from illustrative_paths import (  # noqa: E402
    is_illustrative,
    is_placeholder_basename,
    is_placeholder_member,
    is_runtime_relative,
    split_ref,
    why_illustrative,
)

# Every ref the live corpus put in NEVER_EXISTED that is an example, verbatim.
MEASURED_EXAMPLES = [
    "tests/../scripts/prod.py",
    "tests/foo.py",
    "tests/integration/test_foo.py",
    "tests/test_X.py",
    "tests/test_a.py",
    "tests/test_does_not_exist.py",
    "tests/test_file.py",
    "tests/test_foo.py",
    "tests/test_foo.py::test_bar",
    "tests/test_real.py::test_a",
    "tests/test_x.py",
    "tests/unit/scoped/test_bar.py",
    "tests/x.py",
]

# The refs in the SAME bucket that were genuine misses, and the bare file names
# that are ordinary module names nobody meant as placeholders.
MEASURED_REAL = [
    "tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject",
    "tests/test_knowledge_export.py::TestTheDestinationMustBeLocal",
    "tests/test_app_spa_mount.py",
    "test_brain_runtime.py",
    "test_citation.py",
    "test_dedupe.py",
    "test_dedupe.py::_signature",
    "test_mapped.py",
    "test_notifier.py",
    "test_resolver.py",
    "test_stack_schema.py",
    "test_test_count.py",
]


@pytest.mark.parametrize("ref", MEASURED_EXAMPLES)
def test_every_measured_example_is_recognised(ref):
    assert is_illustrative(ref), ref


@pytest.mark.parametrize("ref", MEASURED_REAL)
def test_no_measured_real_citation_is_swallowed(ref):
    """The negative end. Widening the placeholder list until the noise is gone
    is indistinguishable from switching the detector off."""
    assert not is_illustrative(ref), ref


@pytest.mark.parametrize("ref", MEASURED_EXAMPLES)
def test_every_exclusion_can_say_why(ref):
    """A reader who cannot see the rule cannot tell a correct exclusion from a
    detector that has gone blind."""
    assert why_illustrative(ref)


def test_a_real_citation_has_no_reason():
    assert why_illustrative("tests/test_app_spa_mount.py") is None


# --- the individual rules, each with both ends ---------------------------


@pytest.mark.parametrize(
    "path,expected",
    [
        ("tests/foo.py", True),
        ("tests/test_x.py", True),
        ("x.py", True),
        ("tests/test_does_not_exist.py", True),
        # both ends: real modules whose names merely start the same way
        ("tests/test_files_are_indexed.py", False),
        ("tests/foobar.py", False),
        ("tests/test_names.py", False),
        ("scripts/bazaar.py", False),
    ],
)
def test_placeholder_basename(path, expected):
    assert is_placeholder_basename(path) is expected


@pytest.mark.parametrize(
    "member,expected",
    [
        ("test_a", True),
        ("test_bar", True),
        ("x", True),
        ("TestX::test_a", True),
        # both ends
        ("test_ble001_selected_in_pyproject", False),
        ("TestTheDestinationMustBeLocal", False),
        ("_signature", False),
        ("", False),
    ],
)
def test_placeholder_member(member, expected):
    assert is_placeholder_member(member) is expected


@pytest.mark.parametrize(
    "path,expected",
    [
        ("./probe.sh", True),
        ("tests/../scripts/prod.py", True),
        ("../outside/thing.py", True),
        # both ends
        ("tests/test_x_ray.py", False),
        ("scripts/a.b/c.py", False),
        ("", False),
    ],
)
def test_runtime_relative(path, expected):
    assert is_runtime_relative(path) is expected


def test_a_windows_separator_is_read_as_a_path_separator():
    """The corpus is written on three platforms; a backslash is not a name."""
    assert is_placeholder_basename(r"tests\foo.py")
    assert is_runtime_relative(r"tests\..\scripts\prod.py")


@pytest.mark.parametrize(
    "ref,expected",
    [
        ("a/b.py::C::d", ("a/b.py", "C::d")),
        ("a/b.py", ("a/b.py", "")),
        ("", ("", "")),
    ],
)
def test_split_ref(ref, expected):
    assert split_ref(ref) == expected


# --- one source of truth -------------------------------------------------


def test_neither_detector_keeps_its_own_placeholder_list():
    """AC-1. Two copies of this list is exactly how the two detectors drifted
    apart in the first place, so the duplicate must not come back."""
    for module in ("memory_cleanup.py", "audit_closure_evidence.py"):
        with open(os.path.join(_SCRIPTS, module), encoding="utf-8") as handle:
            text = handle.read()
        assert "_PLACEHOLDER_BASENAME_RE = re.compile" not in text, module
        assert "illustrative_paths" in text, module
