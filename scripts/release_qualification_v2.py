#!/usr/bin/env python3
"""Canonical release qualification v2 candidate and protected attestation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
from typing import Mapping

import crypto_ed25519 as ed25519
import release_qualification_junit as junit
import release_qualification_ledger as ledger
from hooks.codex_capability import CODEX_SECURITY_ADAPTERS
from release_qualification_git import (
    QualificationError,
    git as _git,
    object_id as _object,
    projection_hashes as _git_projection_hashes,
    version_at as _version_at,
)
from release_qualification_scenario_manifest import (
    ScenarioCurrent as ScenarioCurrent,
    ScenarioManifest as ScenarioManifest,
    ScenarioPublication as ScenarioPublication,
    ScenarioPublished as ScenarioPublished,
    validate_scenario_manifest,
)
from release_qualification_platform import (
    REQUIRED_LANES as REQUIRED_LANES,
    REQUIRED_PLATFORM_CHECKS as REQUIRED_PLATFORM_CHECKS,
    native_windows_platform_checks as native_windows_platform_checks,
    validate_lane_results as _validate_lane_results,
    validate_platform_checks as _validate_platform_checks,
)


SCHEMA = 2
ATTESTATION_SCHEMA = "release-qualification-attestation-v2"
ATTESTATION_TTL = timedelta(minutes=30)
REQUIRED_SCENARIOS = (
    "call-budget-recovery-retirement",
    "clean-current",
    "handoff",
    "lease-and-stop-baseline",
    "lease-completion",
    "obsolete-unbind",
    "post-tool-failure",
    "pre-lease-stop-regression",
    "repeated-stop",
    "terminal-unbind-next-lifecycle",
)
PROJECTION_PATHS = tuple(f"scripts/hooks/{name}" for name in CODEX_SECURITY_ADAPTERS)
SCENARIO_MANIFEST_PATH = "tests/fixtures/codex_upgrade_matrix_v1.json"
SCENARIO_HARNESS_PATH = "tests/test_codex_upgrade_matrix.py"
PINNED_SCENARIO_MANIFEST_SHA256 = "aff62c6d0ab079fc3746959916fa22c443fe87b76efa8f819a33cb05e567c128"
PINNED_SCENARIO_HARNESS_SHA256 = "e4cb6f5e6110b960316ee810e66dd989b39dbef6fe3362bed97217e651ec90d3"
SIGNING_SEED_ENV = "TAUSIK_RELEASE_QUALIFICATION_SIGNING_SEED"
# Provision through a reviewed change that commits only the public key. The
# matching seed belongs exclusively in the protected GitHub environment.
PINNED_PUBLIC_KEY_HEX = "32b34b3fbcab55280b02390bb6b7e529e0720efdaaa5f08b46db69025f2a1bb1"
_VERSION = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_KEYS = {
    "schema",
    "version",
    "development",
    "public_snapshot",
    "verifier_revision",
    "lanes",
    "platform_checks",
    "scenarios",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _projection_hashes(root: Path, commit: str) -> dict[str, str]:
    return _git_projection_hashes(root, commit, PROJECTION_PATHS)


def scenario_evidence_hash(
    root: str | Path, snapshot: str, scenario: str, report_sha256: str
) -> str:
    """Derive scenario evidence from the trusted ratchet and exact public object."""

    if scenario not in REQUIRED_SCENARIOS:
        raise QualificationError(f"scenario {scenario} is outside the trusted ratchet")
    if not _SHA256.fullmatch(report_sha256):
        raise QualificationError("scenario report digest is invalid")
    repo = Path(root).resolve()
    commit = _object(repo, snapshot, "commit")
    manifest = _git(repo, "show", f"{commit}:{SCENARIO_MANIFEST_PATH}", text=False)
    assert isinstance(manifest, bytes)
    manifest_hash = hashlib.sha256(manifest).hexdigest()
    if not secrets.compare_digest(manifest_hash, PINNED_SCENARIO_MANIFEST_SHA256):
        raise QualificationError("scenario manifest does not match the trusted ratchet")
    try:
        document = validate_scenario_manifest(json.loads(manifest))
        published = document["published"]
        current = document["current"]
        boundaries = [current["boundary"], *(row["boundary"] for row in published)]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise QualificationError("scenario manifest is malformed") from exc
    if len(boundaries) != len(set(boundaries)) or set(boundaries) != set(REQUIRED_SCENARIOS):
        raise QualificationError("scenario manifest does not match the trusted ratchet")
    harness = _git(repo, "show", f"{commit}:{SCENARIO_HARNESS_PATH}", text=False)
    assert isinstance(harness, bytes)
    harness_hash = hashlib.sha256(harness).hexdigest()
    if not secrets.compare_digest(harness_hash, PINNED_SCENARIO_HARNESS_SHA256):
        raise QualificationError("scenario harness does not match the trusted semantic ratchet")
    binding = {
        "harness_sha256": harness_hash,
        "manifest_sha256": manifest_hash,
        "public_snapshot_commit": commit,
        "report_sha256": report_sha256,
        "scenario": scenario,
    }
    return hashlib.sha256(canonical_bytes(binding)).hexdigest()


def _validate_scenarios(
    root: Path, scenarios: Mapping[str, object], snapshot: str
) -> dict[str, object]:
    if set(scenarios) != set(REQUIRED_SCENARIOS):
        raise QualificationError("scenario result set does not match the trusted ratchet")
    normalized: dict[str, object] = {}
    for name in REQUIRED_SCENARIOS:
        row = scenarios[name]
        if not isinstance(row, Mapping) or row.get("status") != "passed":
            raise QualificationError(f"scenario {name} did not pass")
        evidence = row.get("evidence_sha256")
        report_sha256 = row.get("report_sha256")
        if not isinstance(report_sha256, str) or not _SHA256.fullmatch(report_sha256):
            raise QualificationError(f"scenario {name} report digest is invalid")
        expected = scenario_evidence_hash(root, snapshot, name, report_sha256)
        if (
            not isinstance(evidence, str)
            or not _SHA256.fullmatch(evidence)
            or not secrets.compare_digest(evidence, expected)
        ):
            raise QualificationError(
                f"scenario {name} evidence is not bound to the exact public snapshot"
            )
        normalized[name] = {
            "evidence_sha256": evidence,
            "report_sha256": report_sha256,
            "status": "passed",
        }
    return normalized


def scenario_results_from_junit(
    root: str | Path, snapshot: str, report: bytes
) -> dict[str, object]:
    """Validate the real pinned matrix report and derive canonical scenario rows."""

    repo = Path(root).resolve()
    commit = _object(repo, snapshot, "commit")
    raw_manifest = _git(repo, "show", f"{commit}:{SCENARIO_MANIFEST_PATH}", text=False)
    assert isinstance(raw_manifest, bytes)
    try:
        manifest = validate_scenario_manifest(json.loads(raw_manifest))
        tag_to_boundary = {row["tag"]: row["boundary"] for row in manifest["published"]}
        tag_to_boundary["clean-current"] = manifest["current"]["boundary"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise QualificationError("scenario manifest is malformed") from exc
    try:
        return junit.build_results(
            report,
            tag_to_boundary=tag_to_boundary,
            required_scenarios=REQUIRED_SCENARIOS,
            evidence_hash=lambda name, digest: scenario_evidence_hash(repo, snapshot, name, digest),
        )
    except junit.JunitEvidenceError as exc:
        raise QualificationError(str(exc)) from exc


def lane_results_from_junit(
    snapshot: str,
    run_id: int,
    *,
    lint_report: bytes,
    matrix_report: bytes,
    full_report: bytes,
) -> dict[str, object]:
    """Build lane claims from protected, machine-readable pytest evidence."""

    try:
        junit.validate_matrix_report(matrix_report)
        reports = {
            "lint": junit.validate_lint_report(lint_report),
            "qualification-matrix": hashlib.sha256(matrix_report).hexdigest(),
            "test-full": junit.validate_lane_report(full_report),
        }
    except junit.JunitEvidenceError as exc:
        raise QualificationError(str(exc)) from exc
    return {
        name: {
            "conclusion": "success",
            "run_id": run_id,
            "sha": snapshot,
            "report_sha256": reports[name],
        }
        for name in REQUIRED_LANES
    }


def build_candidate(
    root: str | Path,
    *,
    version: str,
    development_ref: str,
    public_snapshot_ref: str,
    verifier_ref: str,
    lane_results: Mapping[str, object],
    platform_checks: Mapping[str, object],
    scenario_results: Mapping[str, object],
) -> dict[str, object]:
    """Build the unprivileged claim; this function never reads signing material."""

    if not _VERSION.fullmatch(version):
        raise QualificationError("version must be MAJOR.MINOR.PATCH")
    repo = Path(root).resolve()
    development = _object(repo, development_ref, "commit")
    snapshot = _object(repo, public_snapshot_ref, "commit")
    verifier = _object(repo, verifier_ref, "commit")
    if verifier != snapshot:
        raise QualificationError("verifier revision is not the exact public snapshot")
    versions = {
        _version_at(repo, development, "pyproject.toml", rb'(?m)^version = "([^"]+)"$'),
        _version_at(
            repo, development, "scripts/tausik_version.py", rb'(?m)^__version__ = "([^"]+)"$'
        ),
        _version_at(repo, snapshot, "pyproject.toml", rb'(?m)^version = "([^"]+)"$'),
        _version_at(repo, snapshot, "scripts/tausik_version.py", rb'(?m)^__version__ = "([^"]+)"$'),
    }
    if versions != {version}:
        raise QualificationError("requested version does not match both exact release objects")
    normalized_lanes = _validate_lane_results(lane_results, snapshot)
    workflow_run_id = normalized_lanes[REQUIRED_LANES[0]]["run_id"]  # type: ignore[index]
    assert isinstance(workflow_run_id, int)
    normalized_platform_checks = _validate_platform_checks(
        platform_checks, snapshot, workflow_run_id
    )
    normalized_scenarios = _validate_scenarios(repo, scenario_results, snapshot)
    matrix_digest = normalized_lanes["qualification-matrix"]["report_sha256"]  # type: ignore[index]
    if any(row["report_sha256"] != matrix_digest for row in normalized_scenarios.values()):  # type: ignore[index]
        raise QualificationError("scenario evidence is not from the qualification-matrix lane")
    return {
        "schema": SCHEMA,
        "version": version,
        "development": {
            "commit": development,
            "tree": _object(repo, development, "tree"),
            "projections": _projection_hashes(repo, development),
        },
        "public_snapshot": {
            "commit": snapshot,
            "tree": _object(repo, snapshot, "tree"),
            "projections": _projection_hashes(repo, snapshot),
        },
        "verifier_revision": verifier,
        "lanes": normalized_lanes,
        "platform_checks": normalized_platform_checks,
        "scenarios": normalized_scenarios,
    }


def _validate_candidate(root: Path, candidate: Mapping[str, object]) -> dict[str, object]:
    if set(candidate) != _CANDIDATE_KEYS or candidate.get("schema") != SCHEMA:
        if "required_scenarios" in candidate:
            raise QualificationError("scenario ratchet is owned by the trusted verifier")
        raise QualificationError("candidate schema is not canonical v2")
    version = candidate.get("version")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise QualificationError("candidate version is invalid")
    development = candidate.get("development")
    public = candidate.get("public_snapshot")
    if not isinstance(development, Mapping) or not isinstance(public, Mapping):
        raise QualificationError("candidate object bindings are malformed")
    dev_commit = development.get("commit")
    public_commit = public.get("commit")
    if not isinstance(dev_commit, str) or not isinstance(public_commit, str):
        raise QualificationError("candidate commits are missing")
    lanes = candidate.get("lanes")
    platform_checks = candidate.get("platform_checks")
    scenarios = candidate.get("scenarios")
    verifier = candidate.get("verifier_revision")
    if not isinstance(verifier, str):
        raise QualificationError("candidate verifier revision is missing")
    expected = build_candidate(
        root,
        version=version,
        development_ref=dev_commit,
        public_snapshot_ref=public_commit,
        verifier_ref=verifier,
        lane_results=lanes if isinstance(lanes, Mapping) else {},
        platform_checks=platform_checks if isinstance(platform_checks, Mapping) else {},
        scenario_results=scenarios if isinstance(scenarios, Mapping) else {},
    )
    if not secrets.compare_digest(canonical_bytes(expected), canonical_bytes(dict(candidate))):
        raise QualificationError("candidate bindings do not match independently recomputed objects")
    return expected


def _instant(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise QualificationError("timestamp must be canonical UTC") from exc


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def decode_ed25519_key(value: str, *, label: str) -> bytes:
    """Decode one canonical 32-byte Ed25519 seed/public key."""

    if not _SHA256.fullmatch(value):
        raise QualificationError(f"{label} must be 64 lowercase hexadecimal characters")
    return bytes.fromhex(value)


def _seed(value: bytes) -> bytes:
    if len(value) != 32:
        raise QualificationError("release qualification signing seed must be 32 bytes")
    return value


def _pinned_public_key() -> bytes:
    try:
        return decode_ed25519_key(PINNED_PUBLIC_KEY_HEX, label="pinned qualification public key")
    except QualificationError as exc:
        raise QualificationError("release qualification public key is not provisioned") from exc


def issue_attestation(
    root: str | Path,
    candidate: Mapping[str, object],
    *,
    signing_seed: bytes,
    now: str | datetime | None = None,
    nonce: str | None = None,
) -> dict[str, object]:
    """Recompute the untrusted claim and sign it at the protected boundary."""

    trusted = _validate_candidate(Path(root).resolve(), candidate)
    if not secrets.compare_digest(
        ed25519.public_from_seed(_seed(signing_seed)), _pinned_public_key()
    ):
        raise QualificationError("signing seed does not match the pinned qualification public key")
    issued = _instant(now)
    nonce_value = nonce or secrets.token_hex(32)
    if not _SHA256.fullmatch(nonce_value):
        raise QualificationError("attestation nonce is invalid")
    payload: dict[str, object] = {
        "schema": ATTESTATION_SCHEMA,
        "candidate_sha256": hashlib.sha256(canonical_bytes(trusted)).hexdigest(),
        "version": trusted["version"],
        "development_commit": trusted["development"]["commit"],  # type: ignore[index]
        "public_snapshot_commit": trusted["public_snapshot"]["commit"],  # type: ignore[index]
        "verifier_revision": trusted["verifier_revision"],
        "issued_at": _iso(issued),
        "expires_at": _iso(issued + ATTESTATION_TTL),
        "nonce": nonce_value,
    }
    payload["signature"] = ed25519.sign(_seed(signing_seed), canonical_bytes(payload)).hex()
    return payload


def consume_attestation(
    root: str | Path,
    candidate: Mapping[str, object],
    attestation: Mapping[str, object],
    *,
    version: str,
    development_ref: str,
    public_snapshot_ref: str,
    ledger_path: str | Path,
    now: str | datetime | None = None,
) -> None:
    """Verify exact bindings and atomically consume the one-time nonce."""

    repo = Path(root).resolve()
    trusted = _validate_candidate(repo, candidate)
    required = {
        "schema",
        "candidate_sha256",
        "version",
        "development_commit",
        "public_snapshot_commit",
        "verifier_revision",
        "issued_at",
        "expires_at",
        "nonce",
        "signature",
    }
    if set(attestation) != required or attestation.get("schema") != ATTESTATION_SCHEMA:
        raise QualificationError("attestation schema is not canonical v2")
    signature = attestation.get("signature")
    unsigned = {key: attestation[key] for key in attestation if key != "signature"}
    try:
        signature_bytes = bytes.fromhex(signature) if isinstance(signature, str) else b""
    except ValueError:
        signature_bytes = b""
    if not ed25519.verify(_pinned_public_key(), canonical_bytes(unsigned), signature_bytes):
        raise QualificationError("attestation signature is invalid")
    digest = hashlib.sha256(canonical_bytes(trusted)).hexdigest()
    if attestation.get("candidate_sha256") != digest:
        raise QualificationError("attestation does not bind this candidate")
    development = _object(repo, development_ref, "commit")
    snapshot = _object(repo, public_snapshot_ref, "commit")
    if (
        trusted["version"] != version
        or attestation.get("version") != version
        or attestation.get("development_commit") != development
        or attestation.get("public_snapshot_commit") != snapshot
        or attestation.get("verifier_revision") != trusted["verifier_revision"]
        or trusted["development"]["commit"] != development  # type: ignore[index]
        or trusted["public_snapshot"]["commit"] != snapshot  # type: ignore[index]
    ):
        raise QualificationError("attestation object or version binding is mismatched")
    instant = _instant(now)
    if instant < _instant(str(attestation["issued_at"])):
        raise QualificationError("attestation is not yet valid")
    if instant >= _instant(str(attestation["expires_at"])):
        raise QualificationError("attestation is stale")
    nonce = attestation.get("nonce")
    if not isinstance(nonce, str) or not _SHA256.fullmatch(nonce):
        raise QualificationError("attestation nonce is invalid")
    try:
        ledger.consume(ledger_path, nonce)
    except ledger.LedgerError as exc:
        raise QualificationError(str(exc)) from exc


def load_document(path: str | Path) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise QualificationError(f"qualification JSON has duplicate key: {key}")
            result[key] = value
        return result

    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw, object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"cannot read qualification JSON: {path}") from exc
    if not isinstance(value, dict):
        raise QualificationError("qualification JSON must be an object")
    if raw != canonical_bytes(value) + b"\n":
        raise QualificationError("qualification JSON is not canonical")
    return value


def main(argv: list[str] | None = None) -> int:
    import sys

    import release_qualification_cli

    return release_qualification_cli.main(argv, qualification=sys.modules[__name__])


if __name__ == "__main__":
    raise SystemExit(main())
