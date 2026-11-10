"""Content-addressed release gate for the TAUSIK 1.11.8 adherence contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping, Sequence, cast

from adherence_contract import artifact_hash, build_evidence
from can_stop import run_native_stop_probe

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "dist" / "adherence-1.11.8.json"

PROJECTION_ROOTS = (".codex", ".cursor")
PROJECTION_EXCLUDED_PARTS = {"__pycache__", ".mypy_cache", ".pytest_cache"}

NATIVE_LANES = {
    "contract": ("tests/test_adherence_contract.py", "tests/test_adherence_release.py"),
    "codex_cursor": (
        "tests/test_bootstrap_codex.py",
        "tests/test_bootstrap_codex_mcp.py",
        "tests/test_codex_support_matrix.py",
        "tests/test_codex_write_gate.py",
        "tests/test_cursor_governance.py",
        "tests/test_doctor_codex_transport.py",
        "tests/test_doctor_cursor_mcp_surface.py",
        "tests/test_session_start_hook.py",
        "tests/test_subagent_reviewer.py",
    ),
    "governance_restart": (
        "tests/test_execution_lease.py",
        "tests/test_work_continuity.py",
        "tests/test_memory_preflight.py",
        "tests/test_can_stop.py",
    ),
    "migration": (
        "tests/test_migrations.py",
        "tests/test_schema_upgrade_parity.py",
        "tests/test_init_schema_upgrade_order.py",
    ),
}

_SUMMARY = re.compile(r"(?P<count>\d+) (?P<kind>passed|failed|skipped|deselected)")


class ReleaseGateError(RuntimeError):
    """A release precondition or acceptance check failed."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_text_sha256(path: Path) -> str:
    """Hash repository text independently of checkout newline policy."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _projection_rows(root: Path) -> list[dict[str, str]]:
    rows = []
    for projection_root in PROJECTION_ROOTS:
        base = root / projection_root
        if not base.is_dir():
            raise ReleaseGateError(f"installed projection is missing: {projection_root}")
        for path in sorted(base.rglob("*")):
            if (
                path.is_file()
                and not PROJECTION_EXCLUDED_PARTS.intersection(path.parts)
                and path.suffix != ".pyc"
            ):
                rows.append({"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)})
    if not rows:
        raise ReleaseGateError("installed projection trees contain no files")
    return rows


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode:
        raise ReleaseGateError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_identity(root: Path, paths: Sequence[str] | None = None) -> dict[str, str]:
    """Return the immutable target identity after refusing any repository dirt."""
    args = ["status", "--porcelain=v1", "--untracked-files=all"]
    if paths is not None:
        args.extend(("--", *paths))
    dirty = _git(root, *args)
    if dirty:
        names = [line[3:] for line in dirty.splitlines()]
        raise ReleaseGateError("relevant tree is dirty: " + ", ".join(names))
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    if not re.fullmatch(r"[0-9a-f]{40}", commit + tree[:0]) or not re.fullmatch(
        r"[0-9a-f]{40}", tree
    ):
        raise ReleaseGateError("target commit or tree hash is not canonical")
    return {"commit_sha": commit, "tree_sha": tree}


@contextmanager
def immutable_worktree(root: Path, commit_sha: str):
    """Materialize and remove a detached snapshot of the reviewed commit."""
    with tempfile.TemporaryDirectory(prefix="tausik-release-") as temporary:
        snapshot = Path(temporary).resolve() / "snapshot"
        _git(
            root,
            "-c",
            "core.autocrlf=false",
            "worktree",
            "add",
            "--detach",
            str(snapshot),
            commit_sha,
        )
        try:
            observed = _git(snapshot, "rev-parse", "HEAD")
            if observed != commit_sha:
                raise ReleaseGateError("detached worktree does not match the target commit")
            yield snapshot
        finally:
            _git(root, "worktree", "remove", "--force", str(snapshot))


def _load(root: Path, name: str) -> object:
    path = root / "tests" / "fixtures" / "adherence" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _matching_census(events: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    actions: OrderedDict[str, list[Mapping[str, object]]] = OrderedDict()
    for event in events:
        actions.setdefault(str(event["action_id"]), []).append(event)
    return [
        {
            "action_id": action_id,
            "event_count": len(rows),
            "event_sha256": artifact_hash(rows),
            "route": rows[0]["route"],
            "status": "executed",
        }
        for action_id, rows in actions.items()
    ]


def evaluator_self_test(root: Path, commit_sha: str) -> dict[str, object]:
    """Prove evaluator arithmetic; native acceptance is a separate phase."""
    events = _load(root, "valid-events-v1.json")
    assert isinstance(events, list)
    census = _matching_census(events)
    negative = build_evidence(events, "negative-control", commit_sha, census)
    acceptance = build_evidence(events, "acceptance", commit_sha, census)
    negative_counts = cast(Mapping[str, object], negative["counts"])
    acceptance_counts = cast(Mapping[str, object], acceptance["counts"])
    if not negative["accepted"] or negative_counts["failed"] != 0:
        raise ReleaseGateError("negative-control sentinels were accepted")
    if not acceptance["accepted"] or acceptance_counts["collected"] == 0:
        raise ReleaseGateError("acceptance cohort missed a frozen threshold")
    return {"negative_control": negative, "acceptance": acceptance}


def verify_frozen_artifacts(root: Path) -> dict[str, object]:
    """Refuse edits to closed migrations and the reviewed contract bundle."""
    manifest = _load(root, "release-manifest-v1.json")
    assert isinstance(manifest, dict)
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ReleaseGateError("release manifest has no frozen files")
    observed = {name: _canonical_text_sha256(root / name) for name in sorted(files)}
    if observed != files:
        changed = [name for name in observed if observed[name] != files.get(name)]
        raise ReleaseGateError("frozen release artifacts changed: " + ", ".join(changed))
    return {"manifest_sha256": artifact_hash(manifest), "files": observed}


def _collect_nodes(root: Path, files: Sequence[str]) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-m",
        "slow or not slow",
        *files,
    ]
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    nodes = sorted(
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if "::" in line and line.lstrip().startswith("tests/")
    )
    if result.returncode or not nodes:
        raise ReleaseGateError("native lane collection failed or returned zero node IDs")
    return nodes


def _pytest_lane(
    root: Path, name: str, expected: Mapping[str, object], files: Sequence[str]
) -> dict[str, object]:
    nodes = _collect_nodes(root, files)
    nodes_sha256 = artifact_hash(nodes)
    expected_count = expected.get("count")
    expected_sha256 = expected.get("nodes_sha256")
    if len(nodes) != expected_count or nodes_sha256 != expected_sha256:
        raise ReleaseGateError(
            f"native lane {name} collection changed: {len(nodes)} tests, {nodes_sha256}"
        )
    command = [sys.executable, "-m", "pytest", "-q", "-m", "slow or not slow", *files]
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    combined = "\n".join((result.stdout, result.stderr))
    counts = {kind: 0 for kind in ("passed", "failed", "skipped", "deselected")}
    for match in _SUMMARY.finditer(combined):
        counts[match.group("kind")] = int(match.group("count"))
    collected = counts["passed"] + counts["failed"] + counts["skipped"]
    if (
        result.returncode
        or counts["passed"] != len(nodes)
        or counts["skipped"]
        or counts["deselected"]
        or not collected
    ):
        stdout_tail = "\n".join(result.stdout.splitlines()[-40:])
        stderr_tail = "\n".join(result.stderr.splitlines()[-8:])
        raise ReleaseGateError(
            f"native lane {name} failed or collected zero tests (exit={result.returncode}):"
            f"\nstdout:\n{stdout_tail}\nstderr:\n{stderr_tail}"
        )
    return {
        "command": command[1:],
        "counts": {**counts, "collected": collected},
        "nodes_sha256": nodes_sha256,
        "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "passed": True,
    }


def native_lanes(root: Path) -> dict[str, object]:
    """Execute real Windows child processes for the supported host paths."""
    if os.name != "nt":
        raise ReleaseGateError("native 1.11.8 acceptance requires Windows")
    manifest = _load(root, "release-manifest-v1.json")
    assert isinstance(manifest, dict)
    expected_lanes = manifest.get("native_lanes")
    if not isinstance(expected_lanes, dict):
        raise ReleaseGateError("release manifest has no exact native lane identities")
    lanes = {
        name: _pytest_lane(
            root, name, cast(Mapping[str, object], expected_lanes.get(name, {})), files
        )
        for name, files in NATIVE_LANES.items()
    }
    failures = {
        "process_crash": ("raise SystemExit(7)", 2.0),
        "host_timeout": ("import time; time.sleep(2)", 0.05),
        "malformed_stdout": ("print('not-json')", 2.0),
        "no_stdout": ("", 2.0),
    }
    verdicts = {}
    for name, (program, timeout) in failures.items():
        verdict = run_native_stop_probe(
            [sys.executable, "-c", program], payload={}, timeout=timeout
        )
        verdicts[name] = {"hard_enforced": verdict.enforced, "reason": verdict.reason}
    if any(row["hard_enforced"] for row in verdicts.values()):
        raise ReleaseGateError("a fail-open Stop state was reported as hard enforcement")
    return {"platform": sys.platform, "lanes": lanes, "stop_fail_open": verdicts}


def projection_evidence(root: Path) -> dict[str, object]:
    """Generate, check and hash the complete Codex and Cursor projection trees."""
    generate = subprocess.run(
        [sys.executable, "bootstrap/bootstrap.py", "--project-dir", str(root), "--ide", "all"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if generate.returncode:
        raise ReleaseGateError("Codex/Cursor bootstrap generation failed")
    result = subprocess.run(
        [
            sys.executable,
            "bootstrap/bootstrap.py",
            "--project-dir",
            str(root),
            "--ide",
            "all",
            "--check",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode:
        raise ReleaseGateError("installed host projections drift from bootstrap source")
    rows = _projection_rows(root)
    return {
        "sha256": artifact_hash(rows),
        "file_count": len(rows),
        "files": rows,
        "bootstrap_check": True,
    }


def build_report(
    root: Path = ROOT,
    *,
    run_native: bool = True,
    target: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Build the final report; any missing release property raises."""
    identity = dict(target or git_identity(root))
    evaluator = evaluator_self_test(root, identity["commit_sha"])
    report: dict[str, object] = {
        "release": "1.11.8",
        "publication": {
            "channel": "GitHub Release asset",
            "asset": "adherence-1.11.8.json",
        },
        "target": identity,
        "frozen": verify_frozen_artifacts(root),
        "projections": projection_evidence(root),
        "phases": {
            "evaluator_self_test": evaluator,
            "native_acceptance": native_lanes(root) if run_native else {"status": "not-run"},
        },
    }
    if not run_native:
        raise ReleaseGateError("advisory-only evidence cannot release 1.11.8")
    report["content_sha256"] = artifact_hash(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        identity = git_identity(ROOT)
        with immutable_worktree(ROOT, identity["commit_sha"]) as snapshot:
            report = build_report(snapshot, target=identity)
    except ReleaseGateError as exc:
        print(f"RELEASE BLOCKED: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RELEASE ACCEPTED: {report['content_sha256']} ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
