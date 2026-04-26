"""TAUSIK gate runner -- execute quality gates for a given trigger.

Usage: python gate_runner.py <trigger> [--files file1 file2 ...]
Triggers: task-done, commit, review

Exit codes:
  0 -- all gates passed (or only warnings)
  1 -- at least one blocking gate failed
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from project_config import get_gates_for_trigger, load_config  # noqa: E402


def count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


_FILESIZE_EXEMPT_DIRS = (
    "tests/",
    "agents/claude/mcp/",
    "agents/cursor/mcp/",
    "agents/qwen/mcp/",
    ".claude/mcp/",
)


from gate_stack_dispatch import (  # noqa: E402,F401
    gate_applies_to,
    infer_stacks_from_files,
    skipped_result,
)


def _normalize_path(p: str) -> str:
    """Canonicalize path for matching: forward slashes, strip leading './'."""
    n = os.path.normpath(p).replace("\\", "/")
    if n.startswith("./"):
        n = n[2:]
    return n


def run_filesize_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Check file sizes against max_lines threshold.

    Exempt: tests, MCP handlers (dispatchers, not creative logic).
    Per-file exempts via gate.exempt_files: entries with '/' match by exact
    path, bare names match by basename (covers a file anywhere in tree).
    """
    max_lines = gate.get("max_lines", 400)
    exempt_paths: set[str] = set()
    exempt_basenames: set[str] = set()
    for entry in gate.get("exempt_files") or []:
        norm = entry.replace("\\", "/")
        if "/" in norm:
            exempt_paths.add(_normalize_path(norm))
        else:
            exempt_basenames.add(norm)

    violations = []
    for f in files:
        if not os.path.isfile(f):
            continue
        normalized = f.replace("\\", "/")
        if any(d in normalized for d in _FILESIZE_EXEMPT_DIRS):
            continue
        canon = _normalize_path(f)
        if canon in exempt_paths or os.path.basename(canon) in exempt_basenames:
            continue
        lines = count_lines(f)
        if lines > max_lines:
            violations.append(f"  {f}: {lines} lines (max {max_lines})")
    if violations:
        return False, "Files exceeding line limit:\n" + "\n".join(violations)
    return True, "All files within line limit."


def run_tdd_order_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Check that test files are present among changed files.

    TDD enforcement: if source files were changed, test files should also be changed.
    Skips if only non-code files were modified.
    """
    code_exts = {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".php",
    }
    test_patterns = (
        "test_",
        "_test.",
        ".test.",
        ".spec.",
        "Test.",  # Java/Kotlin: FooTest.java, FooTest.kt
        "Tests.",  # Java/Kotlin: FooTests.java
        "tests/",
        "test/",
        "__tests__/",
    )

    code_files = []
    test_files = []
    for f in files:
        normalized = f.replace("\\", "/")
        _, ext = os.path.splitext(f)
        if ext.lower() not in code_exts:
            continue
        if any(p in normalized for p in test_patterns):
            test_files.append(f)
        else:
            code_files.append(f)

    if not code_files:
        return True, "No source code files changed — TDD check skipped."
    if test_files:
        return (
            True,
            f"TDD OK: {len(test_files)} test file(s) modified alongside {len(code_files)} source file(s).",
        )
    return False, (
        f"{len(code_files)} source file(s) changed but no test files modified. "
        "TDD requires tests to be written/updated alongside code changes."
    )


from gate_test_resolver import resolve_test_files_for_relevant  # noqa: F401, E402


# Sentinel returned by run_command_gate when a scoped relevant_files set
# yields no matching test files. run_gates converts it into skipped_result.
_SCOPED_SKIP_SENTINEL = "__TAUSIK_SCOPED_SKIP__"


def run_command_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Run a command-based gate. Substitutes {files} / {test_files_for_files}.

    Special return: (True, _SCOPED_SKIP_SENTINEL) when {test_files_for_files}
    is in cmd and no test files map from a non-empty relevant_files. The
    caller (run_gates) translates this into a skipped_result entry so the
    UI shows SKIP, not PASS, and we don't run an irrelevant full suite.
    """
    import shlex

    cmd = gate.get("command", "")
    if not cmd:
        return True, "No command configured."

    file_exts_raw = gate.get("file_extensions") or []
    if file_exts_raw and "{files}" in cmd:
        allowed = {(e if e.startswith(".") else "." + e).lower() for e in file_exts_raw}
        files = [f for f in files if os.path.splitext(f)[1].lower() in allowed]
        if not files:
            return True, (
                "No files matching " + ", ".join(sorted(allowed)) + " — gate skipped."
            )

    if "{test_files_for_files}" in cmd:
        test_files = resolve_test_files_for_relevant(files)
        # Scoped-only semantics:
        #   - relevant_files non-empty + no test mapping → SKIP (scoped run for
        #     a module without test_<basename>.py — running the full suite for
        #     an unrelated module defeats the scoping promise).
        #   - relevant_files empty → SKIP (was: fall back to full suite).
        #     MCP task_done has a 10s budget; the suite always exceeds it and
        #     burns budget for zero verification value. Forces callers to pass
        #     relevant_files to opt in to actual verification.
        if not test_files:
            return True, _SCOPED_SKIP_SENTINEL
        test_files_str = " ".join(shlex.quote(t) for t in test_files)
        cmd = cmd.replace("{test_files_for_files}", test_files_str)

    files_str = " ".join(shlex.quote(f) for f in files) if files else "."
    cmd = cmd.replace("{files}", files_str)
    # Detect shell operators -- need shell=True for pipes and redirects
    needs_shell = any(op in cmd for op in ("|", "&&", ">>", "2>&1"))
    timeout = gate.get("timeout", 120)
    try:
        if needs_shell:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        else:
            result = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            return True, output or "Passed."
        return False, output or f"Failed with exit code {result.returncode}."
    except subprocess.TimeoutExpired:
        return False, f"Gate timed out ({timeout}s)."
    except Exception as e:
        return False, f"Gate error: {e}"


def run_gates(trigger: str, files: list[str] | None = None) -> tuple[bool, list[dict]]:
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

    for gate in gates:
        name = gate["name"]
        severity = gate.get("severity", "warn")

        if not gate_applies_to(gate, files or []):
            results.append(skipped_result(gate, files or []))
            continue

        if name == "filesize":
            passed, output = run_filesize_gate(gate, files or [])
        elif name == "tdd_order":
            passed, output = run_tdd_order_gate(gate, files or [])
        else:
            passed, output = run_command_gate(gate, files or [])

        # Scoped-skip sentinel from run_command_gate: either relevant_files
        # were provided but no test files mapped, OR no relevant_files at
        # all (full-suite fallback removed in v1.3 — burns MCP 10s budget).
        if output == _SCOPED_SKIP_SENTINEL:
            skip_reason = (
                "No test file maps to relevant_files via "
                "tests/test_<basename>.py heuristic; gate skipped (scoped run)."
                if files
                else (
                    "No relevant_files passed; gate skipped. Pass relevant_files "
                    "for actual verification (e.g. --relevant-files src/foo.py)."
                )
            )
            results.append(
                {
                    "name": name,
                    "severity": severity,
                    "passed": True,
                    "skipped": True,
                    "output": skip_reason,
                }
            )
            continue

        results.append(
            {
                "name": name,
                "severity": severity,
                "passed": passed,
                "output": output,
            }
        )

        if not passed and severity == "block":
            has_block_failure = True

    return not has_block_failure, results


def format_results(results: list[dict]) -> str:
    """Format gate results for display."""
    if not results:
        return "No gates configured for this trigger."
    lines = []
    for r in results:
        if r.get("skipped"):
            icon = "SKIP"
        elif r["passed"]:
            icon = "PASS"
        else:
            icon = "FAIL"
        sev = f" ({r['severity']})" if not r["passed"] else ""
        lines.append(f"  [{icon}] {r['name']}{sev}")
        if not r["passed"] and r["output"]:
            for line in r["output"].split("\n")[:5]:
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
    for f, slugs in file_map.items():
        if len(slugs) > 1:
            for i, s1 in enumerate(slugs):
                for s2 in slugs[i + 1 :]:
                    pair = (min(s1, s2), max(s1, s2))
                    if pair not in seen:
                        seen.add(pair)
                        shared = [
                            ff for ff, ss in file_map.items() if s1 in ss and s2 in ss
                        ]
                        conflicts.append((pair[0], pair[1], shared))
    return conflicts


def main() -> None:
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
    elif any(not r["passed"] for r in results):
        print("\nWARNINGS: Non-blocking issues found. Consider fixing.")
    else:
        print("\nAll gates passed.")


if __name__ == "__main__":
    main()
