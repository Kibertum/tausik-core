"""Agent friction against the framework becomes a FILED defect draft, not a swallowed log line.

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

PRECISION IS THE CONTRACT (AC-6, convention #351): a detector that fires on
normal work — a red verify, a fail-then-green retry loop, a dead end about the
agent's OWN code — is worse than none, because it teaches the reader to skip
the drafts. The negative lanes pin each boundary: fail-then-green is NOT
signal C, a task-code dead end is NOT signal E, and the live-tree test fails
the suite beyond five findings on this very repository.

NETWORK (AC-4, memory #352): this module contains NO network code and no
config flag can add any. Sending a draft anywhere is a human act on a specific
issue; a test guards the import surface so the guarantee is mechanical.

Verdict is WARN-grade everywhere: drafts land in `.tausik/friction/*.md`,
redacted (AC-3) by reusing brain_scrubbing's detectors — the matched spans are
replaced, no second pattern set is written.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

_INVOCATIONS_FILE = "cli_invocations.jsonl"
_DRAFTS_DIR = "friction"
_TAIL_ROWS = 500
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
            "schema_version": 1,
            "ts": datetime.now(timezone.utc).isoformat(),
            "argv": list(sys_argv(argv)),
            "exit": int(exit_code),
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


def _read_invocations(tausik_dir: str) -> list[dict]:
    path = os.path.join(tausik_dir, _INVOCATIONS_FILE)
    rows: list[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    except (OSError, ValueError):
        return []
    return rows[-_TAIL_ROWS:]


def _cmd(row: dict) -> str:
    argv = row.get("argv") or []
    return str(argv[0]) if argv else ""


def _ts(row: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(row.get("ts")))
    except ValueError:
        return None


def _minutes_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 60.0


def _signal_a(rows: list[dict]) -> list[FrictionSignal]:
    """Non-zero exits, collapsed per command — AC-5: count, not copies.

    Fires only at >=2 failures of the SAME command in the window: a single
    red exit is the framework teaching (a gate refusal carries its own
    remediation), and the live corpus proved one-shot reds are the ordinary
    rhythm — this session's own task-done refusal lit the detector up.
    """
    by_cmd: dict[str, FrictionSignal] = {}
    for row in rows:
        if int(row.get("exit") or 0) == 0:
            continue
        cmd = _cmd(row) or "?"
        if cmd in by_cmd:
            by_cmd[cmd].count += 1
        else:
            by_cmd[cmd] = FrictionSignal(
                kind="nonzero-exit",
                signature=f"nonzero-exit:{cmd}",
                sample=" ".join(str(a) for a in (row.get("argv") or []))[:200],
                remedy_hint=f"`tausik {cmd} --help` documents the real signature; a refusal names the missing piece",
            )
    return [s for s in by_cmd.values() if s.count >= 2]


def _signal_b(rows: list[dict]) -> list[FrictionSignal]:
    """>--help of the same command right after its failure — the agent guessed."""
    out: list[FrictionSignal] = []
    for prev, cur in zip(rows, rows[1:]):
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
        out.append(
            FrictionSignal(
                kind="help-after-failure",
                signature=f"help-after-failure:{_cmd(prev)}",
                sample=" ".join(str(a) for a in argv)[:200],
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
            if len(fails) >= 2 and len(argvs) > 1:
                cmd = _cmd(run[0])
                out.append(
                    FrictionSignal(
                        kind="arg-guessing",
                        signature=f"arg-guessing:{cmd}",
                        count=len(run),
                        sample=" ; ".join(
                            " ".join(str(a) for a in (r.get("argv") or []))[:80] for r in run[:3]
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
    return (now - dt).days <= _DEAD_END_WINDOW_DAYS


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
                    signature=f"framework-dead-end:{(row.get('title') or '')[:60]}",
                    sample=blob[:300],
                    remedy_hint="an agent documented the FRAMEWORK failing — a defect candidate, not agent error",
                )
            )
    return out


# --- Drafts (AC-2/AC-3/AC-5) ---------------------------------------------------


def redact(text: str, cfg: dict | None = None) -> str:
    """Replace what brain_scrubbing flags: paths, emails, URLs, blocklist names.

    Reuses the DETECTOR (its pattern set is the single source); the only new
    code here is the replacement itself — detecting twice with two pattern
    lists is the defect this task exists to prevent.
    """
    from brain_scrubbing import scrub

    issues = scrub(text).get("issues", [])
    for issue in issues:
        match = issue.get("match") or ""
        if match:
            text = text.replace(match, "[redacted]")
    return text


def write_drafts(
    tausik_dir: str, signals: list[FrictionSignal], cfg: dict | None = None
) -> list[str]:
    """One file per signature — identical signals collapse to a counter (AC-5)."""
    out_dir = os.path.join(tausik_dir, _DRAFTS_DIR)
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for sig in signals:
        slug = re.sub(r"[^a-z0-9]+", "-", sig.signature.lower()).strip("-")[:80]
        path = os.path.join(out_dir, f"{slug}.md")
        body = (
            f"# Friction draft: {sig.kind}\n\n"
            f"- signature: `{sig.signature}`\n"
            f"- collapsed occurrences: {sig.count}\n"
            f"- remedy hint: {sig.remedy_hint}\n"
            f"- sample (redacted):\n\n```\n{redact(sig.sample)}\n```\n\n"
            "Draft, not an issue: review, then either file it with the owner's word\n"
            "or delete this file. Nothing is sent anywhere by this tool.\n"
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        written.append(path)
    return written


# --- The audit entry -----------------------------------------------------------


def detect_friction(tausik_dir: str, svc=None) -> list[FrictionSignal]:
    signals: list[FrictionSignal] = []
    rows = _read_invocations(tausik_dir)
    signals += _signal_a(rows)
    signals += _signal_b(rows)
    signals += _signal_c(rows)
    if svc is not None:
        with contextlib.suppress(Exception):
            events = svc.events_list(entity_type="supervision", n=200)
            signals += _signal_d(events)
        with contextlib.suppress(Exception):
            memories = svc.memory_list(mem_type="dead_end", n=500, include_archived=True)
            signals += _signal_e(memories)
    return signals


def run_friction_cmd(svc) -> None:  # ProjectService arrives from the CLI dispatcher
    """`tausik doctor --friction`: detect, file redacted drafts, print. Exit 0."""
    from project_config import find_tausik_dir

    tdir = find_tausik_dir() or os.path.join(os.getcwd(), ".tausik")
    print("TAUSIK doctor — agent friction (filed drafts, WARN verdict)")
    print("=" * 56)
    signals = detect_friction(tdir, svc)
    if not signals:
        print("  no friction signals — invocations, bypasses and dead ends re-read clean")
    else:
        written = write_drafts(tdir, signals)
        for sig in signals:
            print(f"  ! [{sig.kind}] x{sig.count} — {sig.signature}")
            print(f"      {sig.remedy_hint}")
        print(
            f"\n  {len(written)} redacted draft(s) in .tausik/{_DRAFTS_DIR}/ — review, then file or delete."
        )
    print("=" * 56)
    print("Nothing is sent anywhere: no network code exists in this module (AC-4).")


def drafts_count(tausik_dir: str) -> int:
    """How many filed drafts await a human — doctor prints this on every run."""
    try:
        return len(
            [f for f in os.listdir(os.path.join(tausik_dir, _DRAFTS_DIR)) if f.endswith(".md")]
        )
    except OSError:
        return 0


def assert_no_network_surface(module_path: str | None = None) -> bool:
    """Mechanical AC-4 guard: the module source contains no network imports."""
    path = module_path or os.path.abspath(__file__)
    with open(path, encoding="utf-8") as fh:
        return not _NETWORK_IMPORT_RE.search(fh.read())


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
