"""TAUSIK gate runner -- execute quality gates for a given trigger.

Usage: python gate_runner.py <trigger> [--files file1 file2 ...]
Triggers: task-done, commit, review

Exit codes:
  0 -- all gates passed (or only warnings)
  1 -- at least one blocking gate failed
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess  # noqa: F401 — re-exported attr for backwards-compat monkeypatching (`gate_runner.subprocess.run`); the module is `subprocess` itself, so patching it here patches it globally for gate_command_runner too.
import sys
import time
from typing import Any, Callable

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from project_config import get_gates_for_trigger, load_config  # noqa: E402


# Filesize gate moved to gate_filesize.py (gate_runner sat exactly at the 400
# cap). Re-exported so tests and the run_gates dispatch import them unchanged.
from gate_filesize import count_lines, run_filesize_gate  # noqa: E402,F401

from gate_stack_dispatch import (  # noqa: E402,F401
    gate_applies_to,
    infer_stacks_from_files,
    skipped_result,
)


from gate_tdd_order import run_tdd_order_gate  # noqa: F401, E402
from gate_renar_drift import run_renar_drift_gate  # noqa: F401, E402
from gate_bootstrap_drift import run_bootstrap_drift_gate  # noqa: F401, E402
from gate_test_resolver import resolve_test_files_for_relevant  # noqa: F401, E402
from gate_registry import impl_for  # noqa: E402
from tausik_utils import cli_invocation  # noqa: E402

# How to spell the CLI in a remediation the reader's shell will accept.
_CLI = cli_invocation()

# A gate with neither an implementation nor a command. Routed through the same
# skip path as _SCOPED_SKIP_SENTINEL so it reads as SKIP everywhere, including
# the persisted `gate_runs` row.
_NO_IMPL_SENTINEL = "__TAUSIK_GATE_NO_IMPL__"

# v14b-filesize-debt-paydown: run_command_gate + _SCOPED_SKIP_SENTINEL extracted
# to gate_command_runner.py; re-exported so tests/test_gates.py import path holds.
from gate_command_runner import (  # noqa: F401, E402
    _SCOPED_SKIP_SENTINEL,
    SCOPE_PREFIX,
    run_command_gate,
    split_scope,
)


def run_gates(
    trigger: str,
    files: list[str] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[bool, list[dict]]:
    """Run all enabled gates for a trigger.

    Returns (all_passed, results) where all_passed means no blocking gate failed.
    Each result: {name, severity, passed, output}.
    """
    cfg = load_config()
    gates = get_gates_for_trigger(trigger, cfg)
    if not gates:
        return True, []

    results = []
    has_block_failure = False

    total = len(gates)
    # v1.4 r14-mcp-streaming-progress: emit a "run_start" event with the
    # max budget sum so MCP hosts (VS Code Claude Extension etc.) can show
    # an ETA before pytest blocks the channel for tens of seconds.
    if progress_callback:
        try:
            timeout_sum = 0
            for g in gates:
                t = g.get("timeout_seconds") or g.get("timeout") or 0
                try:
                    timeout_sum += int(t)
                except (TypeError, ValueError):
                    continue
            progress_callback(
                {
                    "event": "run_start",
                    "trigger": trigger,
                    "total": total,
                    "max_seconds": timeout_sum,
                    "gates": [g.get("name") for g in gates],
                }
            )
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            pass
    for idx, gate in enumerate(gates, start=1):
        name = gate["name"]
        severity = gate.get("severity", "warn")
        start_ms = time.monotonic()
        if progress_callback:
            progress_callback(
                {
                    "event": "gate_start",
                    "index": idx,
                    "total": total,
                    "name": name,
                    "severity": severity,
                }
            )

        if not gate_applies_to(gate, files or []):
            skipped = skipped_result(gate, files or [])
            # Third result-shaping branch: it needs duration_ms too, or a
            # stack-mismatch skip persists as NULL while every other outcome
            # carries a real value.
            skipped["duration_ms"] = int((time.monotonic() - start_ms) * 1000)
            results.append(skipped)
            if progress_callback:
                progress_callback(
                    {
                        "event": "gate_done",
                        "index": idx,
                        "total": total,
                        "name": name,
                        "severity": severity,
                        "passed": True,
                        "skipped": True,
                        "duration_ms": int((time.monotonic() - start_ms) * 1000),
                        "output": skipped.get("output", ""),
                    }
                )
            continue

        # gate-registry-single-source: the chain of `if name == ...` that used
        # to stand here was the second of four places a gate had to be declared,
        # and the only one a reader of `default_gates` had no reason to visit.
        # Dispatch is now a registry lookup; a gate the registry does not know
        # (stack-declared, user-defined) is a command gate by construction.
        impl = impl_for(name)
        if impl is not None:
            passed, output = impl(gate, files or [])
        elif gate.get("command"):
            passed, output = run_command_gate(gate, files or [])
        else:
            # No implementation and no command: this gate cannot run. It used to
            # reach `run_command_gate`, which answered "No command configured."
            # as a PASS — a gate that never executes reporting success, the
            # exact reading `gate_verdict` exists to forbid. Say SKIP, loudly.
            passed, output = True, _NO_IMPL_SENTINEL

        # Scoped-skip sentinel from run_command_gate: either relevant_files
        # were provided but no test files mapped, OR no relevant_files at
        # all (full-suite fallback removed in v1.3 — burns MCP 10s budget).
        if output in (_SCOPED_SKIP_SENTINEL, _NO_IMPL_SENTINEL):
            if output == _NO_IMPL_SENTINEL:
                skip_reason = (
                    f"Gate '{name}' declares no command and the framework ships no "
                    f"implementation for it — nothing to run, so it is SKIPPED, not "
                    f"passed. Give it a `command`, or remove it from `gates` in "
                    f".tausik/config.json."
                )
                logging.getLogger("tausik.gates").warning(skip_reason)
            else:
                skip_reason = (
                    "No test file maps to relevant_files via "
                    "tests/test_<basename>.py heuristic; gate skipped (scoped run)."
                    if files
                    # verify-warn-names-a-flag-verify-does-not-have: this
                    # used to name a bare `--relevant-files` with no command
                    # attached, and the command a reader would try it on
                    # (`verify`) did not have the flag. Name the whole line.
                    else (
                        "No relevant_files passed; gate skipped. Declare the "
                        f"scope: `{_CLI} verify --task <slug> --relevant-files "
                        "<paths...>`."
                    )
                )
            results.append(
                {
                    "name": name,
                    "severity": severity,
                    "passed": True,
                    "skipped": True,
                    "output": skip_reason,
                    "duration_ms": int((time.monotonic() - start_ms) * 1000),
                }
            )
            if progress_callback:
                progress_callback(
                    {
                        "event": "gate_done",
                        "index": idx,
                        "total": total,
                        "name": name,
                        "severity": severity,
                        "passed": True,
                        "skipped": True,
                        "duration_ms": int((time.monotonic() - start_ms) * 1000),
                        "output": skip_reason,
                    }
                )
            continue

        # Lift the genuine scope label off the output ONCE, here, at the single
        # boundary where gate output becomes a result dict. Only a run_command_gate
        # scoped run carries the private sentinel; everything else (filesize, a
        # spoofed "SCOPE:" line in tool stdout) yields an empty scope and untouched
        # body. `output` from here on is the sentinel-free body that gets stored.
        scope, output = split_scope(output)

        # duration_ms and skipped used to reach the progress callback only, so
        # any caller that did not pass one lost them — including the code that
        # now persists gate outcomes (l26-gate-results-persist).
        result = {
            "name": name,
            "severity": severity,
            "passed": passed,
            "output": output,
            "scope": scope,
            "skipped": False,
            "duration_ms": int((time.monotonic() - start_ms) * 1000),
        }
        results.append(result)
        if progress_callback:
            progress_callback(
                {
                    "event": "gate_done",
                    "index": idx,
                    "total": total,
                    "name": name,
                    "severity": severity,
                    "passed": passed,
                    "skipped": False,
                    "duration_ms": int((time.monotonic() - start_ms) * 1000),
                    "output": output,
                    "scope": scope,
                }
            )

        if not passed and severity == "block":
            has_block_failure = True

    return not has_block_failure, results


def gate_verdict(result: dict) -> str:
    """Name one gate's outcome: ``PASS`` / ``FAIL`` / ``SKIP``.

    verify-summary-reports-skipped-as-pass. This lived in five places, and
    they had already drifted in both directions: three spelled it
    ``"PASS" if r["passed"] else "FAIL"`` — which reports a *skipped* gate as
    a success, because `run_gates` marks a skipped gate ``passed=True`` — and
    two got it right. The lying version reached the `summary` column of
    `verification_runs`, so a run whose `gate_runs` rows honestly recorded
    ``skipped=1`` was described, on the same row, as "hadolint=PASS,
    pytest=PASS". The machine guards were never fooled; the human reading the
    line was, and that is what kept an open hole alive for an extra session.

    ``skipped`` is checked first and wins even against ``passed=False``. That
    combination is not produced by `run_gates` at any of its three skip sites,
    but the reading must still be unambiguous: a gate that did not execute
    cannot have failed, so calling it FAIL would be inventing a result.
    """
    if result.get("skipped"):
        return "SKIP"
    return "PASS" if result.get("passed") else "FAIL"


def summarize_results(results: list[dict]) -> str:
    """One-line ``name=VERDICT`` summary — the `verification_runs.summary` text.

    Order follows the input rather than sorting: the sequence gates ran in is
    itself information, and reordering it would make two runs of the same set
    look different for no reason.
    """
    return ", ".join(f"{r['name']}={gate_verdict(r)}" for r in results) or "ok"


def format_results(results: list[dict]) -> str:
    """Format gate results for display.

    A passing gate prints its verdict and nothing else — except the scope line,
    if it has one. That exception is the whole point: `[PASS] pytest` over two
    of 318 test files is the reading that costs (session #134 closed on one
    while the full suite was red), and a pass is exactly where the output used
    to be dropped.

    The scope line is read from the trusted ``scope`` field (lifted off a private
    sentinel by `run_gates`), never grepped out of the gate's stdout — a "SCOPE:"
    line a subprocess printed is just body text, not the framework's disclosure.
    """
    if not results:
        return "No gates configured for this trigger."
    lines = []
    for r in results:
        icon = gate_verdict(r)
        sev = f" ({r['severity']})" if not r["passed"] else ""
        lines.append(f"  [{icon}] {r['name']}{sev}")
        scope = r.get("scope") or ""
        if scope:
            lines.append(f"         {scope}")
        output = r.get("output") or ""
        if not r["passed"] and output:
            # `output` is already the sentinel-free body — the scope line lives in
            # the trusted field above and is never duplicated here.
            for line in output.split("\n")[:5]:
                lines.append(f"         {line}")
    return "\n".join(lines)


def check_file_conflicts(tasks: list[dict]) -> list[tuple[str, str, list[str]]]:
    """Check if tasks have overlapping relevant_files.

    Args:
        tasks: list of dicts with 'slug' and 'relevant_files' (comma-separated string or None)

    Returns:
        List of (slug1, slug2, shared_files) tuples for conflicts.
    """
    file_map: dict[str, list[str]] = {}
    for task in tasks:
        slug = task.get("slug", "")
        files_str = task.get("relevant_files") or ""
        if not files_str:
            continue
        files = [f.strip() for f in files_str.split(",") if f.strip()]
        for f in files:
            file_map.setdefault(f, []).append(slug)

    conflicts = []
    seen = set()
    for _f, slugs in file_map.items():
        if len(slugs) > 1:
            for i, s1 in enumerate(slugs):
                for s2 in slugs[i + 1 :]:
                    pair = (min(s1, s2), max(s1, s2))
                    if pair not in seen:
                        seen.add(pair)
                        shared = [ff for ff, ss in file_map.items() if s1 in ss and s2 in ss]
                        conflicts.append((pair[0], pair[1], shared))
    return conflicts


def main() -> None:
    for stream in (sys.stdout, sys.stderr):  # Win console cp1252 → utf-8
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run TAUSIK quality gates")
    parser.add_argument("trigger", choices=["task-done", "commit", "review"])
    parser.add_argument("--files", nargs="*", default=[])
    args = parser.parse_args()

    all_passed, results = run_gates(args.trigger, args.files)
    print(f"Gates for '{args.trigger}':")
    print(format_results(results))

    if not all_passed:
        print("\nBLOCKED: Fix blocking gate failures before proceeding.")
        sys.exit(1)
    elif any(not r["passed"] and not r.get("skipped") for r in results):
        print("\nWARNINGS: Non-blocking issues found. Consider fixing.")
    else:
        # "All gates passed." after a `[SKIP]` is the same lie `gate_verdict`
        # was extracted to end (verify-summary-reports-skipped-as-pass): a
        # skipped gate is marked passed=True, so the naive else read it as a
        # clean pass. Name the skips instead — an all-skipped run verified
        # nothing, and a partly-skipped one verified less than it looks.
        skipped = [r for r in results if r.get("skipped")]
        if skipped and len(skipped) == len(results):
            names = ", ".join(r["name"] for r in skipped)
            print(
                f"\nNOTE: no gate actually executed — every gate SKIPPED ({names}). "
                "A skip is not a verification."
            )
        elif skipped:
            names = ", ".join(r["name"] for r in skipped)
            print(f"\nGates passed, but these did NOT execute (SKIP, not verified): {names}.")
        else:
            print("\nAll gates passed.")


if __name__ == "__main__":
    main()
