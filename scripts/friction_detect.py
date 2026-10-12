"""Agent friction against the framework becomes a local planning task.

Task agent-friction-becomes-a-filed-defect-not-a-swallowed-one. The asymmetry:
every refusal the framework hands an agent — a non-zero CLI exit, a rejected
argument, a gate block, a stale MCP server — currently dies in the session log,
which nobody re-reads. The next agent repeats the same fight; the owner never
hears the framework misbehaved. Friction is telemetry with no reader.

THE SIGNALS (AC-1) — the FORM, each measurable on existing or hereby-recorded
telemetry, never on prose judgment:

  A. non-zero CLI exit            — `.tausik/cli_invocations.jsonl` (recorded
                                     below; the CLI is the only place that
                                     knows its own exit code);
  B. `--help` right after a failed
     call of the same command      — same file, consecutive rows (the agent
                                     guessed arguments and asked the parser);
  C. same command retried with
     different arguments, mostly
     failing                       — same file, consecutive runs (argument
                                     guessing without the help escape);
  D. supervision DEGRADED — the
     guard itself could not run     — `events` rows `entity_type='supervision'`,
                                     `action LIKE 'fail_open_%'` (l26-bypass-
                                     telemetry). Deliberately NOT `bypass_%`:
                                     a TAUSIK_SKIP_HOOKS skip is the agent's
                                     own audited choice (metrics count it),
                                     not the framework failing the agent; the
                                     live corpus proved it — 22 bypass entities
                                     of accumulated history, none actionable.
  E. dead end recorded ABOUT THE
     FRAMEWORK itself              — memory rows `type='dead_end'` whose text
     names a framework surface failing (MCP empty params, drift, stale server).

PRECISION IS THE CONTRACT (AC-6, convention on live-data accuracy): a detector
that fires on
normal work — a red verify, a fail-then-green retry loop, a dead end about the
agent's OWN code — is worse than none, because it teaches the reader to skip
the findings. The negative lanes pin each boundary: fail-then-green is NOT
signal C, a task-code dead end is NOT signal E, and the live-tree test fails
the suite beyond five findings on this very repository.

NETWORK (AC-4, the owner's per-issue-only rule): this module contains NO network code and no
config flag can add any. Sending anything elsewhere is a separate human act;
a test guards the import surface so the guarantee is mechanical.

Verdict is WARN-grade everywhere. Explicit `doctor --friction` files one
redacted, QG-0-ready local planning task per correlation key; ordinary doctor
only reports those tasks and remains read-only.
"""

from __future__ import annotations

import functools
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

_INVOCATIONS_FILE = "cli_invocations.jsonl"
_HELP_WINDOW_MIN = 10

_NETWORK_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(urllib|http\.client|requests|socket|ftplib|smtplib|xmlrpc)",
    re.MULTILINE,
)


@dataclass
class FrictionSignal:
    """One collapsed friction signal: kind, dedup key, count, human sample."""

    kind: str  # nonzero-exit | help-after-failure | arg-guessing | gate-bypass | framework-dead-end
    signature: str
    count: int = 1
    sample: str = ""
    remedy_hint: str = ""


# --- Recorder (signal A/B/C source) -------------------------------------------


def record_invocation_exit(exit_code: int, argv: list[str] | None = None) -> bool:
    """Append one CLI invocation row. Best-effort: never raises, never slows.

    Records successes too — signals B and C are SEQUENCES, and a sequence needs
    its green members to tell a retry-loop (normal) from guessing (friction).
    """
    try:
        from project_config import find_tausik_dir

        tdir = find_tausik_dir()
        if not tdir:
            return False
        row = {
            "schema_version": 2,
            "ts": datetime.now(timezone.utc).isoformat(),
            "argv": list(sys_argv(argv)),
            "exit": int(exit_code),
            "origin": "pytest" if os.environ.get("PYTEST_CURRENT_TEST") else "cli",
        }
        with open(os.path.join(tdir, _INVOCATIONS_FILE), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return True
    except Exception:  # noqa: BLE001 — telemetry must never break the CLI it measures
        return False


def sys_argv(argv: list[str] | None = None) -> list[str]:
    if argv is not None:
        return argv
    import sys

    return list(sys.argv[1:])


def _read_invocations(tausik_dir: str) -> tuple[list[dict], int, int, int, int]:
    path = os.path.join(tausik_dir, _INVOCATIONS_FILE)
    try:
        with open(path, encoding="utf-8") as fh:
            raw = [line for line in fh if line.strip()]
    except OSError:
        return [], 0, 0, 0, 0
    from telemetry_retention import POLICIES

    keep = next(p.keep_lines for p in POLICIES if p.name == _INVOCATIONS_FILE)
    assert keep is not None
    omitted = max(0, len(raw) - keep)
    rows: list[dict] = []
    malformed = legacy = test_generated = 0
    for line in raw[-keep:]:
        try:
            row = json.loads(line)
        except (TypeError, ValueError):
            malformed += 1
            continue
        if not isinstance(row, dict):
            malformed += 1
            continue
        if row.get("schema_version") != 2:
            legacy += 1
            continue
        argv = row.get("argv")
        if (
            not isinstance(argv, list)
            or not all(isinstance(part, str) for part in argv)
            or not isinstance(row.get("exit"), int)
            or isinstance(row.get("exit"), bool)
            or not isinstance(row.get("ts"), str)
            or _ts(row) is None
            or row.get("origin") not in ("cli", "pytest")
        ):
            malformed += 1
            continue
        if row["origin"] == "pytest":
            test_generated += 1
            continue
        rows.append(row)
    return rows, omitted, malformed, legacy, test_generated


def command_path(argv: list[str]) -> str:
    """Return the parser-recognized command path, stopping before arguments."""
    choices = _command_tree()
    path: list[str] = []
    for token in argv:
        child = choices.get(str(token))
        if child is not None:
            path.append(str(token))
            choices = child
            continue
        if str(token).startswith("-"):
            continue
        break
    return " ".join(path)


@functools.lru_cache(maxsize=1)
def _command_tree() -> dict[str, Any]:
    import argparse

    from project_parser import build_parser

    def children(parser) -> dict[str, Any]:
        action = next(
            (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None
        )
        if action is None:
            return {}
        return {name: children(child) for name, child in action.choices.items()}

    return children(build_parser())


def _cmd(row: dict) -> str:
    argv = row.get("argv") or []
    return command_path([str(part) for part in argv])


def _ts(row: dict) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(row.get("ts")))
    except ValueError:
        return None
    if parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _minutes_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 60.0


def _signal_a(rows: list[dict]) -> list[FrictionSignal]:
    """Non-zero exits, collapsed per command — AC-5: count, not copies.

    Fires only at >=2 failures of the SAME command in the window: a single
    red exit is the framework teaching (a gate refusal carries its own
    remediation), and the live corpus proved one-shot reds are the ordinary
    rhythm — this session's own task-done refusal lit the detector up.
    """
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        cmd = _cmd(row) or "?"
        grouped.setdefault(cmd, []).append(row)
    out: list[FrictionSignal] = []
    for cmd, attempts in grouped.items():
        failures = [row for row in attempts if int(row.get("exit") or 0) != 0]
        if len(failures) < 2 or int(attempts[-1].get("exit") or 0) == 0:
            continue
        out.append(
            FrictionSignal(
                kind="nonzero-exit",
                signature=f"nonzero-exit:{cmd}",
                count=len(failures),
                sample=" ".join(str(a) for a in (failures[-1].get("argv") or [])),
                remedy_hint=f"`tausik {cmd} --help` documents the real signature; a refusal names the missing piece",
            )
        )
    return out


def _signal_b(rows: list[dict]) -> list[FrictionSignal]:
    """>--help of the same command right after its failure — the agent guessed."""
    out: list[FrictionSignal] = []
    for index, (prev, cur) in enumerate(zip(rows, rows[1:])):
        if int(prev.get("exit") or 0) == 0:
            continue
        argv = cur.get("argv") or []
        if "--help" not in argv and "-h" not in argv:
            continue
        if _cmd(cur) != _cmd(prev):
            continue
        t1, t2 = _ts(prev), _ts(cur)
        if t1 and t2 and _minutes_between(t1, t2) > _HELP_WINDOW_MIN:
            continue
        recovered = False
        for later in rows[index + 2 :]:
            later_argv = later.get("argv") or []
            if _cmd(later) != _cmd(prev) or "--help" in later_argv or "-h" in later_argv:
                continue
            later_ts = _ts(later)
            if t1 and later_ts and _minutes_between(t1, later_ts) > _HELP_WINDOW_MIN:
                break
            if int(later.get("exit") or 0) == 0:
                recovered = True
                break
        if recovered:
            continue
        out.append(
            FrictionSignal(
                kind="help-after-failure",
                signature=f"help-after-failure:{_cmd(prev)}",
                sample=" ".join(str(a) for a in argv),
                remedy_hint="the agent did not know the arguments — the command's discoverability failed",
            )
        )
    return out


def _signal_c(rows: list[dict]) -> list[FrictionSignal]:
    """>=3 consecutive same-command attempts, >=2 failing, differing argv.

    A fail-then-GREEN retry loop is the normal edit-fix-rerun rhythm and is
    deliberately NOT here (AC-6): the sequence must stay mostly failing.
    """
    out: list[FrictionSignal] = []
    run: list[dict] = []
    for row in rows + [{"argv": None, "exit": 0}]:  # sentinel flushes the last run
        if _cmd(row) and (not run or _cmd(run[0]) == _cmd(row)):
            run.append(row)
            continue
        if len(run) >= 3:
            fails = [r for r in run if int(r.get("exit") or 0) != 0]
            argvs = {json.dumps(r.get("argv") or [], sort_keys=True) for r in run}
            recovered = int(run[-1].get("exit") or 0) == 0
            if len(fails) >= 2 and len(argvs) > 1 and not recovered:
                cmd = _cmd(run[0])
                out.append(
                    FrictionSignal(
                        kind="arg-guessing",
                        signature=f"arg-guessing:{cmd}",
                        count=len(run),
                        sample=" ; ".join(
                            " ".join(str(a) for a in (r.get("argv") or [])) for r in run
                        ),
                        remedy_hint="the agent retried one command with different arguments — the signature it needed was not discoverable",
                    )
                )
        run = [row] if _cmd(row) else []
    return out


def _signal_d(events: list[dict]) -> list[FrictionSignal]:
    """Supervision DEGRADATIONS — a guard that could not do its job.

    Only `fail_open_*`: the framework failing the agent. A `bypass_*` row is a
    deliberate skip the agent chose and metrics already audit — counting it
    here would drown the drafts in the agent's own history (measured: 22
    entities in the live corpus at first run).
    """
    by_entity: dict[str, FrictionSignal] = {}
    for ev in events:
        action = str(ev.get("action") or "")
        if not action.startswith("fail_open_"):
            continue
        entity = str(ev.get("entity_id") or "?")
        sig = by_entity.setdefault(
            entity,
            FrictionSignal(
                kind="supervision-degraded",
                signature=f"supervision-degraded:{entity}",
                sample=action,
                remedy_hint="a supervision guard could not run (fail-open) — the framework failed the agent, not vice versa",
            ),
        )
        sig.count += 1
    for sig in by_entity.values():
        sig.count -= 1
    return list(by_entity.values())


# Signal E: a dead end that names a FRAMEWORK surface failing. Precision-first
# twice over: "mcp/tausik" plus a failure word, AND a 7-day window — the live
# corpus holds six genuine-looking MCP dead ends from the v14b era, every one
# already processed by the task that recorded it. A draft is for friction
# AWAITING a human; history is not awaiting anyone.
_FRAMEWORK_DEAD_END_RE = re.compile(r"mcp|таусик|tausik", re.IGNORECASE)
_DEAD_END_FAILURE_RE = re.compile(
    r"пуст|empty|drift|stale|refus|отказ|не принимает|не отдаёт", re.IGNORECASE
)
_DEAD_END_WINDOW_DAYS = 7


def _recent_iso(dt: datetime | None) -> bool:
    if dt is None:
        return False  # an undatable row is not a fresh signal — precision first
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = now - dt
    return timedelta(0) <= age <= timedelta(days=_DEAD_END_WINDOW_DAYS)


def _signal_e(memories: list[dict]) -> list[FrictionSignal]:
    out = []
    for row in memories:
        if str(row.get("type") or row.get("mem_type") or "") != "dead_end":
            continue
        try:
            created = datetime.fromisoformat(str(row.get("created_at") or ""))
        except ValueError:
            created = None
        if not _recent_iso(created):
            continue
        blob = f"{row.get('title') or ''}\n{row.get('content') or ''}"
        if _FRAMEWORK_DEAD_END_RE.search(blob) and _DEAD_END_FAILURE_RE.search(blob):
            out.append(
                FrictionSignal(
                    kind="framework-dead-end",
                    signature=f"framework-dead-end:{row.get('title') or ''}",
                    sample=blob,
                    remedy_hint="an agent documented the FRAMEWORK failing — a defect candidate, not agent error",
                )
            )
    return out


def _collapse(signals: list[FrictionSignal]) -> list[FrictionSignal]:
    """One signal per correlation key, with all observed occurrences counted."""
    unique: dict[tuple[str, str], FrictionSignal] = {}
    for signal in signals:
        key = (signal.kind, signal.signature)
        current = unique.get(key)
        if current is None:
            unique[key] = signal
            continue
        current.count += signal.count
        current.sample = signal.sample
        current.remedy_hint = signal.remedy_hint
    return list(unique.values())


# --- The audit entry -----------------------------------------------------------


def detect_friction(
    tausik_dir: str, svc=None, *, notices: list[str] | None = None
) -> list[FrictionSignal]:
    signals: list[FrictionSignal] = []
    rows, omitted, malformed, legacy, test_generated = _read_invocations(tausik_dir)
    if omitted and notices is not None:
        notices.append(
            f"invocation analysis used the declared retained tail; {omitted} older row(s) "
            "were outside the window"
        )
    if legacy and notices is not None:
        notices.append(f"ignored {legacy} legacy invocation row(s) without trusted origin")
    if test_generated and notices is not None:
        notices.append(f"excluded {test_generated} pytest-generated invocation row(s)")
    if malformed:
        if notices is not None:
            notices.append(
                f"REFUSED CLI filing: {malformed} malformed invocation row(s) make the "
                "retained corpus incomplete"
            )
    else:
        signals += _signal_a(rows)
        signals += _signal_b(rows)
        signals += _signal_c(rows)
    if svc is not None:
        try:
            events = svc.events_list(entity_type="supervision", n=200)
            signals += _signal_d(events)
        except Exception as exc:  # noqa: BLE001 - every source stays independent
            if notices is not None:
                notices.append(
                    f"REFUSED supervision filing: event source failed ({type(exc).__name__})"
                )
        try:
            memories = svc.memory_list(mem_type="dead_end", n=500, include_archived=True)
            signals += _signal_e(memories)
        except Exception as exc:  # noqa: BLE001 - every source stays independent
            if notices is not None:
                notices.append(
                    f"REFUSED dead-end filing: memory source failed ({type(exc).__name__})"
                )
    return _collapse(signals)


def run_friction_cmd(svc) -> None:  # ProjectService arrives from the CLI dispatcher
    """`tausik doctor --friction`: detect and file local planning tasks. Exit 0."""
    from friction_filing import file_signals
    from project_config import find_tausik_dir

    tdir = find_tausik_dir() or os.path.join(os.getcwd(), ".tausik")
    print("TAUSIK doctor — agent friction (local planning tasks, WARN verdict)")
    print("=" * 56)
    notices: list[str] = []
    signals = detect_friction(tdir, svc, notices=notices)
    if not signals:
        if notices:
            print("  no actionable signal in the supported rows; corpus notices follow")
        else:
            print("  no friction signals — invocations, bypasses and dead ends re-read clean")
    else:
        for line in file_signals(svc, signals, tdir):
            print(f"  {line}")
    for notice in notices:
        print(f"  NOTE: {notice}")
    print("=" * 56)
    print("Nothing is sent anywhere: no network code exists in this module (AC-4).")


def assert_no_network_surface(module_path: str | None = None) -> bool:
    """Mechanical AC-4 guard: the module source contains no network imports."""
    path = module_path or os.path.abspath(__file__)
    with open(path, encoding="utf-8") as fh:
        return not _NETWORK_IMPORT_RE.search(fh.read())


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
