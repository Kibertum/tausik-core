"""Strict JUnit evidence parser for release qualification."""

from __future__ import annotations

import hashlib
import json
from typing import Callable, Mapping, Sequence
import xml.etree.ElementTree as ET


EXACT_MATRIX_TESTS = (
    *(
        f"test_published_objects_are_exact_commit_and_tree_pins[v1.{minor}]"
        for minor in (
            "11.7",
            "11.8",
            "11.9",
            "11.10",
            "11.11",
            "11.12",
            "11.13",
            "12.0",
            "13.0",
        )
    ),
    "test_tampered_tree_pin_refuses_before_materialization",
    "test_anonymous_publication_remote_matches_immutable_observation",
    *(
        f"test_publication_attestation_fails_closed[{case}]"
        for case in ("missing", "mismatch", "duplicate")
    ),
    "test_journey_refuses_when_installed_session_start_registration_is_missing[codex-SessionStart]",
    "test_journey_refuses_when_installed_session_start_registration_is_missing[cursor-sessionStart]",
    "test_real_bootstrap_subprocess_skips_markerless_foreign_agents",
    *(
        f"test_host_consumer_completes_clean_or_upgraded_journey[{host}-{tag}]"
        for host in ("codex", "cursor")
        for tag in (
            "clean-current",
            "v1.11.7",
            "v1.11.8",
            "v1.11.9",
            "v1.11.10",
            "v1.11.11",
            "v1.11.12",
            "v1.11.13",
            "v1.12.0",
            "v1.13.0",
        )
    ),
    "test_1118_corrupt_maintenance_upgrade_refuses_without_losing_records",
)
WINDOWS_NATIVE_TEST = (
    "test_windows_native_cursor_upgrade_executes_registered_session_start_after_reload"
)
EXACT_WINDOWS_TESTS = (*EXACT_MATRIX_TESTS, WINDOWS_NATIVE_TEST)
FULL_LANE_MINIMUM_CASES = 13_880
FULL_LANE_MINIMUM_PASSES = 13_800
FULL_LANE_MAXIMUM_SKIPS = 120


class JunitEvidenceError(ValueError):
    """The matrix report does not prove the required journeys."""


def failure_summary(report: bytes, *, limit: int = 5) -> str:
    """Return bounded failing-test identities from an untrusted diagnostic report."""

    try:
        cases = ET.fromstring(report).findall(".//testcase")
    except ET.ParseError as exc:
        raise JunitEvidenceError("CI lane diagnostic JUnit report is malformed") from exc
    failures: list[str] = []
    for case in cases:
        outcome = case.find("failure")
        if outcome is None:
            outcome = case.find("error")
        if outcome is None:
            continue
        identity = ".".join(
            part for part in (case.get("classname", ""), case.get("name", "")) if part
        )
        message = " ".join(str(outcome.get("message", "")).split())[:300]
        failures.append(f"{identity}: {message}" if message else identity)
    if not failures:
        return "no failing testcase was present in JUnit"
    suffix = f" (+{len(failures) - limit} more)" if len(failures) > limit else ""
    return "; ".join(failures[:limit]) + suffix


def validate_matrix_report(report: bytes) -> list[ET.Element]:
    """Require the exact all-passing matrix test identity set."""

    try:
        document = ET.fromstring(report)
    except ET.ParseError as exc:
        raise JunitEvidenceError("qualification matrix JUnit report is malformed") from exc
    cases = document.findall(".//testcase")
    names = [str(case.get("name", "")) for case in cases]
    if len(cases) != len(EXACT_MATRIX_TESTS) or sorted(names) != sorted(EXACT_MATRIX_TESTS):
        raise JunitEvidenceError("qualification matrix did not execute the exact test count")
    if any(
        case.find("failure") is not None
        or case.find("error") is not None
        or case.find("skipped") is not None
        for case in cases
    ):
        raise JunitEvidenceError("qualification matrix contains a non-passing test")
    return cases


def validate_windows_report(report: bytes) -> list[ET.Element]:
    """Require the cross-host matrix plus the native PowerShell reload canary."""
    try:
        cases = ET.fromstring(report).findall(".//testcase")
    except ET.ParseError as exc:
        raise JunitEvidenceError("Windows qualification JUnit report is malformed") from exc
    names = [str(case.get("name", "")) for case in cases]
    if len(cases) != len(EXACT_WINDOWS_TESTS) or sorted(names) != sorted(EXACT_WINDOWS_TESTS):
        raise JunitEvidenceError("Windows qualification did not execute the exact test count")
    if any(
        case.find("failure") is not None
        or case.find("error") is not None
        or case.find("skipped") is not None
        for case in cases
    ):
        raise JunitEvidenceError("Windows qualification contains a non-passing test")
    return cases


def build_results(
    report: bytes,
    *,
    tag_to_boundary: Mapping[str, str],
    required_scenarios: Sequence[str],
    evidence_hash: Callable[[str, str], str],
) -> dict[str, object]:
    """Return scenario rows only for an exact, all-passing matrix report."""

    cases = validate_matrix_report(report)

    prefix = "test_host_consumer_completes_clean_or_upgraded_journey["
    observed: set[tuple[str, str]] = set()
    for case in cases:
        name = str(case.get("name", ""))
        if not name.startswith(prefix) or not name.endswith("]"):
            continue
        identity = name[len(prefix) : -1]
        host, separator, tag = identity.partition("-")
        if separator and host in {"codex", "cursor"} and tag in tag_to_boundary:
            observed.add((host, tag_to_boundary[tag]))
    expected_journeys = {
        (host, scenario) for host in ("codex", "cursor") for scenario in required_scenarios
    }
    if observed != expected_journeys:
        raise JunitEvidenceError("qualification matrix omitted a required journey scenario")
    codex_scenarios = {scenario for host, scenario in observed if host == "codex"}
    if codex_scenarios != set(required_scenarios):
        raise JunitEvidenceError("Codex did not execute every named lifecycle scenario")
    digest = hashlib.sha256(report).hexdigest()
    return {
        name: {
            "status": "passed",
            "report_sha256": digest,
            "evidence_sha256": evidence_hash(name, digest),
        }
        for name in required_scenarios
    }


def validate_lint_report(report: bytes) -> str:
    """Accept only Ruff's isolated, machine-readable zero-finding result."""

    try:
        findings = json.loads(report)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JunitEvidenceError("lint result report is malformed") from exc
    if findings != []:
        raise JunitEvidenceError("lint result report contains findings")
    return hashlib.sha256(report).hexdigest()


def validate_lane_report(
    report: bytes,
    *,
    minimum_cases: int = FULL_LANE_MINIMUM_CASES,
    minimum_passes: int = FULL_LANE_MINIMUM_PASSES,
    maximum_skips: int = FULL_LANE_MAXIMUM_SKIPS,
) -> str:
    """Refuse empty/collected/skipped suites and return the report digest."""

    try:
        cases = ET.fromstring(report).findall(".//testcase")
    except ET.ParseError as exc:
        raise JunitEvidenceError("CI lane JUnit report is malformed") from exc
    failed = sum(
        case.find("failure") is not None or case.find("error") is not None for case in cases
    )
    skipped = sum(case.find("skipped") is not None for case in cases)
    passed = len(cases) - failed - skipped
    if failed or len(cases) < minimum_cases or passed < minimum_passes or skipped > maximum_skips:
        raise JunitEvidenceError(
            "CI lane did not execute the required passing test floor "
            f"(cases={len(cases)} passed={passed} failed={failed} skipped={skipped}; "
            f"need cases>={minimum_cases} passed>={minimum_passes} "
            f"skipped<={maximum_skips} failed==0)"
        )
    return hashlib.sha256(report).hexdigest()
