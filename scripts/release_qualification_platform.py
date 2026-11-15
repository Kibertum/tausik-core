"""Canonical binding for mandatory platform compatibility checks."""

from __future__ import annotations

import re
from typing import Mapping

from release_qualification_git import QualificationError


REQUIRED_LANES = ("lint", "qualification-matrix", "test-full")
REQUIRED_PLATFORM_CHECKS = ("native-windows",)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_lane_results(lanes: Mapping[str, object], snapshot: str) -> dict[str, object]:
    """Require every trusted lane to pass on one exact workflow run and SHA."""
    if set(lanes) != set(REQUIRED_LANES):
        raise QualificationError("lane result set does not match the trusted ratchet")
    normalized: dict[str, object] = {}
    run_ids: set[int] = set()
    for name in REQUIRED_LANES:
        row = lanes[name]
        if not isinstance(row, Mapping):
            raise QualificationError(f"lane {name} result is malformed")
        if row.get("conclusion") != "success" or row.get("sha") != snapshot:
            raise QualificationError(f"lane {name} is not successful on the exact public SHA")
        run_id = row.get("run_id")
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            raise QualificationError(f"lane {name} has no positive run identity")
        report_sha256 = row.get("report_sha256")
        if not isinstance(report_sha256, str) or not _SHA256.fullmatch(report_sha256):
            raise QualificationError(f"lane {name} has no trusted report digest")
        run_ids.add(run_id)
        normalized[name] = {
            "conclusion": "success",
            "report_sha256": report_sha256,
            "run_id": run_id,
            "sha": snapshot,
        }
    if len(run_ids) != 1:
        raise QualificationError("lane results do not belong to one workflow run")
    return normalized


def native_windows_platform_checks(
    snapshot: str, *, conclusion: str, run_id: int, run_attempt: int, workflow_sha: str
) -> dict[str, object]:
    """Bind the native canary to GitHub-owned workflow outcome, not its XML."""
    if conclusion != "success" or workflow_sha != snapshot:
        raise QualificationError("native Windows canary did not succeed on the exact workflow SHA")
    if (
        not isinstance(run_id, int)
        or isinstance(run_id, bool)
        or not isinstance(run_attempt, int)
        or isinstance(run_attempt, bool)
        or run_id <= 0
        or run_attempt <= 0
    ):
        raise QualificationError("native Windows canary has no positive run identity")
    return {
        "native-windows": {
            "candidate_sha": snapshot,
            "evidence_kind": "github-job-result",
            "job": "qualification-windows",
            "run_attempt": run_attempt,
            "run_id": run_id,
            "status": "success",
            "trust_class": "reviewed-candidate-native-canary",
            "workflow_sha": workflow_sha,
        }
    }


def validate_platform_checks(
    checks: Mapping[str, object], snapshot: str, workflow_run_id: int
) -> dict[str, object]:
    """Require the platform canary to belong to the trusted lanes' workflow run."""
    if set(checks) != set(REQUIRED_PLATFORM_CHECKS):
        raise QualificationError("platform check set does not match the trusted ratchet")
    row = checks["native-windows"]
    if not isinstance(row, Mapping):
        raise QualificationError("native Windows platform check is malformed")
    run_attempt = row.get("run_attempt")
    expected = native_windows_platform_checks(
        snapshot,
        conclusion=str(row.get("status", "")),
        run_id=workflow_run_id,
        run_attempt=(
            run_attempt if isinstance(run_attempt, int) and not isinstance(run_attempt, bool) else 0
        ),
        workflow_sha=str(row.get("workflow_sha", "")),
    )
    if dict(row) != expected["native-windows"]:
        raise QualificationError("native Windows platform check is not canonical")
    return expected
