"""Command-line adapter for the release qualification verifier."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from types import ModuleType

from release_qualification_evidence import MAX_EVIDENCE_BYTES, read_bounded_file


def _read_bounded(path: str, *, qualification: ModuleType) -> bytes:
    """Read one untrusted CI artifact without allowing verifier memory exhaustion."""
    try:
        return read_bounded_file(path, max_bytes=MAX_EVIDENCE_BYTES)
    except ValueError as exc:
        raise qualification.QualificationError(
            "qualification evidence exceeds the byte limit"
        ) from exc


def main(argv: list[str] | None = None, *, qualification: ModuleType | None = None) -> int:
    if qualification is None:
        import release_qualification_v2 as qualification
    assert qualification is not None

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    commands = parser.add_subparsers(dest="command", required=True)
    candidate = commands.add_parser("candidate")
    candidate.add_argument("--version", required=True)
    candidate.add_argument("--development-ref", required=True)
    candidate.add_argument("--public-snapshot-ref", required=True)
    candidate.add_argument("--verifier-ref", required=True)
    candidate.add_argument("--lane-results", required=True)
    candidate.add_argument("--platform-checks", required=True)
    candidate.add_argument("--scenario-results", required=True)
    candidate.add_argument("--output", required=True)
    scenarios = commands.add_parser("scenarios-from-junit")
    scenarios.add_argument("--public-snapshot-ref", required=True)
    scenarios.add_argument("--junit", required=True)
    scenarios.add_argument("--output", required=True)
    lanes = commands.add_parser("lanes-from-junit")
    lanes.add_argument("--public-snapshot-ref", required=True)
    lanes.add_argument("--run-id", required=True, type=int)
    lanes.add_argument("--lint-report", required=True)
    lanes.add_argument("--matrix-junit", required=True)
    lanes.add_argument("--full-junit", required=True)
    lanes.add_argument("--output", required=True)
    platforms = commands.add_parser("platform-checks")
    platforms.add_argument("--public-snapshot-ref", required=True)
    platforms.add_argument("--conclusion", required=True)
    platforms.add_argument("--run-id", required=True, type=int)
    platforms.add_argument("--run-attempt", required=True, type=int)
    platforms.add_argument("--workflow-sha", required=True)
    platforms.add_argument("--output", required=True)
    attest = commands.add_parser("attest")
    attest.add_argument("--candidate", required=True)
    attest.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "candidate":
            value = qualification.build_candidate(
                args.root,
                version=args.version,
                development_ref=args.development_ref,
                public_snapshot_ref=args.public_snapshot_ref,
                verifier_ref=args.verifier_ref,
                lane_results=qualification.load_document(args.lane_results),
                platform_checks=qualification.load_document(args.platform_checks),
                scenario_results=qualification.load_document(args.scenario_results),
            )
        elif args.command == "scenarios-from-junit":
            value = qualification.scenario_results_from_junit(
                args.root,
                args.public_snapshot_ref,
                _read_bounded(args.junit, qualification=qualification),
            )
        elif args.command == "lanes-from-junit":
            value = qualification.lane_results_from_junit(
                args.public_snapshot_ref,
                args.run_id,
                lint_report=_read_bounded(args.lint_report, qualification=qualification),
                matrix_report=_read_bounded(args.matrix_junit, qualification=qualification),
                full_report=_read_bounded(args.full_junit, qualification=qualification),
            )
        elif args.command == "platform-checks":
            value = qualification.native_windows_platform_checks(
                args.public_snapshot_ref,
                conclusion=args.conclusion,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                workflow_sha=args.workflow_sha,
            )
        else:
            secret = os.environ.get(qualification.SIGNING_SEED_ENV)
            if secret is None:
                raise qualification.QualificationError(
                    f"protected signing environment lacks {qualification.SIGNING_SEED_ENV}"
                )
            value = qualification.issue_attestation(
                args.root,
                qualification.load_document(args.candidate),
                signing_seed=qualification.decode_ed25519_key(secret, label="signing seed"),
            )
        Path(args.output).write_bytes(qualification.canonical_bytes(dict(value)) + b"\n")
    except qualification.QualificationError as exc:
        print(f"REFUSED: {exc}")
        return 1
    except OSError as exc:
        target = exc.filename or "qualification artifact"
        print(f"REFUSED: qualification file operation failed: {target}")
        return 1
    return 0
