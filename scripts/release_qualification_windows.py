"""Trusted outer controller for the native Windows qualification lane."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import release_qualification_junit as junit
import release_qualification_v2 as qualification
from release_qualification_evidence import MAX_EVIDENCE_BYTES, read_bounded_file


class WindowsQualificationError(RuntimeError):
    """The native lane could not produce trusted evidence."""


def _hash(path: Path) -> str:
    # Windows checkouts may materialize CRLF; pins are LF object bytes.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _validate_ratchet(candidate: Path, trusted: Path) -> Path:
    candidate_harness = candidate / qualification.SCENARIO_HARNESS_PATH
    trusted_harness = trusted / qualification.SCENARIO_HARNESS_PATH
    candidate_manifest = candidate / qualification.SCENARIO_MANIFEST_PATH
    expected = {
        candidate_harness: qualification.PINNED_SCENARIO_HARNESS_SHA256,
        trusted_harness: qualification.PINNED_SCENARIO_HARNESS_SHA256,
        candidate_manifest: qualification.PINNED_SCENARIO_MANIFEST_SHA256,
    }
    try:
        observed = {path: _hash(path) for path in expected}
    except OSError as exc:
        raise WindowsQualificationError("qualification ratchet file is unreadable") from exc
    mismatches = [
        f"{path.as_posix()}: got {observed[path][:12]} want {digest[:12]}"
        for path, digest in expected.items()
        if observed[path] != digest
    ]
    if mismatches:
        raise WindowsQualificationError(
            "qualification ratchet hash mismatch: " + "; ".join(mismatches)
        )
    return trusted_harness


def _pytest_command(harness: Path, report: Path) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-m",
        "pytest",
        "-c",
        os.devnull,
        "--noconftest",
        "--override-ini",
        "addopts=",
        "--override-ini",
        "faulthandler_timeout=300",
        "--override-ini",
        "faulthandler_exit_on_timeout=true",
        "-p",
        "xdist.plugin",
        "-n",
        "auto",
        "-m",
        "slow",
        str(harness),
        "--tb=short",
        f"--junitxml={report}",
    ]


def _read_report(path: Path) -> bytes:
    try:
        return read_bounded_file(path, max_bytes=MAX_EVIDENCE_BYTES)
    except ValueError as exc:
        raise WindowsQualificationError("Windows evidence exceeds the byte limit") from exc
    except OSError as exc:
        raise WindowsQualificationError("Windows evidence is unreadable") from exc


def _publish(output: Path, payload: bytes) -> None:
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise WindowsQualificationError("Windows evidence target must be a fresh file") from exc


def run(candidate: Path, trusted: Path, output: Path) -> None:
    candidate = candidate.resolve()
    trusted = trusted.resolve()
    harness = _validate_ratchet(candidate, trusted)
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        environment.pop(name, None)
    environment.update(
        {
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "TAUSIK_QUALIFICATION_ROOT": str(candidate),
            "TAUSIK_QUALIFICATION_MANIFEST": str(candidate / qualification.SCENARIO_MANIFEST_PATH),
        }
    )
    with tempfile.TemporaryDirectory(prefix="tausik-windows-qualification-") as temporary:
        report = Path(temporary) / "qualification-windows.xml"
        result = subprocess.run(
            _pytest_command(harness, report),
            cwd=trusted,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="backslashreplace",
            timeout=5400,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            diagnostic = (result.stderr or result.stdout)[-2000:]
            raise WindowsQualificationError(
                f"native Windows qualification failed ({result.returncode}): {diagnostic}"
            )
        payload = _read_report(report)
        try:
            junit.validate_windows_report(payload)
        except junit.JunitEvidenceError as exc:
            raise WindowsQualificationError(str(exc)) from exc
        _publish(output.resolve(), payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--trusted", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        run(Path(args.candidate), Path(args.trusted), Path(args.output))
    except WindowsQualificationError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
