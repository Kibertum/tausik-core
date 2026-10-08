"""`tausik doctor --harness-audit` — a deterministic scan of the INSTALLED state.

Task nothing-scans-the-installed-harness-state. The asymmetry this closes, named
out loud (AC-3): signatures and the install-guard protect the INCOMING tree — a
skill is scanned before it lands, a repo is signed before it is trusted — but
AFTER installation nothing re-reads what is actually on disk. An injection does
not need to survive the gate; it needs to reach the installed state by any other
route (an editor, a sync tool, a hand copy), and until now that state was never
looked at again.

The scan is read-only, deterministic, offline: no LLM, no network, no writes.
It reuses the detectors that already exist (AC-2) — a second pattern set is how
the first one silently diverges:

  * invisible Unicode  — ``skill_content_scan.scan_skill_tree`` (the install
    guard's own detector, pointed at the deployed profile trees instead of an
    incoming skill tree);
  * secrets           — ``hooks/secret_scan._PATTERNS``, imported from the hook
    that already enforces Rule 10.12 on writes;
  * hook drift        — ``service_doctor_drift.scripts_drift_names`` plus the
    harness-tree comparator the bootstrap-drift gate uses;
  * memory directives — the one genuinely NEW check (AC-4): memory rows are
    UNREVIEWED context a future agent ingests verbatim, so imperative
    constructs addressed to that agent are named, not assumed benign.

VERDICT IS WARN, NEVER BLOCK (AC-5): legitimate memory records carry legitimate
imperatives (conventions ARE imperatives — that is their job), so false
positives are inevitable and a gate that halted work on its own memory would be
switched off wholesale. The imperative list is therefore deliberately NARROW:
deception-shaped directives (hide from the owner, ignore previous instructions,
act without the owner knowing), not ordinary "always log your steps".

Precision is a requirement, not a hope (AC-7): the live-tree test in
tests/test_harness_audit.py fails the suite if a clean project collects more
than five findings — the threshold the task set for keeping the check at all.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from dataclasses import dataclass

from skill_content_scan import scan_invisible_unicode
from tausik_utils import library_source


@dataclass(frozen=True)
class AuditFinding:
    """One WARN-level observation about the installed harness state."""

    area: str  # installed-unicode | installed-secrets | hook-drift | memory
    target: str  # file path or memory id, never empty
    detail: str  # what was found, named so a human can act


# --- Secrets: the hook's own pattern list, imported, not restated (AC-2) ------

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] | None = None


def _secret_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """``hooks/secret_scan._PATTERNS``, loaded from the hook file itself.

    Importlib-by-path because ``scripts/hooks/`` is not a package; the hook's
    own module header puts its directory on ``sys.path`` for its siblings, so
    loading it has no further requirements. A load failure returns an empty
    list — an audit that crashed on a missing detector would be a bigger
    outage than the finding it missed, and the empty list is reported in the
    section header, not passed off as "clean".
    """
    global _SECRET_PATTERNS
    if _SECRET_PATTERNS is not None:
        return _SECRET_PATTERNS
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks", "secret_scan.py")
    try:
        spec = importlib.util.spec_from_file_location("tausik_secret_scan_for_audit", path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SECRET_PATTERNS = list(mod._PATTERNS)  # private on purpose: the point IS reuse
    except Exception:  # noqa: BLE001 — report the gap, never crash the audit
        _SECRET_PATTERNS = []
    return _SECRET_PATTERNS


def scan_text_secrets(text: str) -> list[str]:
    """Detector names that fire on *text* (the matched literal stays out of the
    report — a secret scan that prints the secret is its own incident)."""
    return [name for name, pat in _secret_patterns() if pat.search(text)]


# --- Memory directives: the one new detector (AC-4) ---------------------------
#
# Deception-shaped imperatives only. A convention that says "всегда логируй"
# / "always cite the test" is memory doing its job; a directive that the agent
# conceal, override or bypass the owner is context no one reviewed instructing
# the next reader to defect. RU and EN, lowercase compare.
_DIRECTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore-previous",
        re.compile(r"ignore\s+(?:all\s+)?previous|disregard\s+(?:all\s+)?previous"),
    ),
    (
        "conceal-from-owner",
        re.compile(
            r"do\s*n[o']t\s+tell|не\s+сообщай|не\s+говори\s+(?:владельцу|пользователю)|скрой\s+от"
        ),
    ),
    (
        "act-without-owner-knowing",
        re.compile(
            r"without\s+(?:the\s+)?(?:user|owner|human)\s+knowing|without\s+telling|без\s+ведома|втайне\s+от"
        ),
    ),
    ("covert-action", re.compile(r"secretly|тайно|exfiltrate|exfil\b")),
)


def imperative_directives(text: str) -> list[str]:
    """Labels of deception-shaped imperatives in *text*; empty means none."""
    lowered = text.lower()
    return [label for label, pat in _DIRECTIVE_PATTERNS if pat.search(lowered)]


# --- The audit ----------------------------------------------------------------


# Directories inside a deployed profile that are NOT the installed harness:
# `node_modules` is third-party runtime bulk, `worktrees` holds Agent Manager
# checkouts (whole separate projects with their own audit), `__pycache__` and
# `.git` are machinery. Measured on the live tree: without these exclusions the
# first run collected 9 of 10 findings from `.kilo/node_modules` and
# `.kilo/worktrees` — third-party and sibling-project noise, not installed state.
_EXCLUDED_DIRS = frozenset({"node_modules", "worktrees", "__pycache__", ".git"})


def _iter_prose_files(root: str):
    """Agent-readable files under *root*, one walk for both detectors.

    Reuses the install-guard's suffix list (``skill_content_scan``) so "what
    counts as prose" has one definition; adds the state-specific directory
    exclusions above, which the incoming-tree scan never needed.
    """
    from skill_content_scan import _SCANNED_SUFFIXES  # same rule, one source

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        for name in files:
            if name.lower().endswith(_SCANNED_SUFFIXES):
                yield os.path.join(dirpath, name)


def _scan_profile(root: str) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    """``(unicode_hits, secret_hits)`` — ``{relpath: findings}`` for each detector."""
    unicode_hits: dict[str, list[dict]] = {}
    secret_hits: dict[str, list[str]] = {}
    for path in _iter_prose_files(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        rel = os.path.relpath(path, root).replace("\\", "/")
        inv = scan_invisible_unicode(text)
        if inv:
            unicode_hits[rel] = inv
        sec = scan_text_secrets(text)
        if sec:
            secret_hits[rel] = sec
    return unicode_hits, secret_hits


def _drift_findings(project_dir: str) -> tuple[list[AuditFinding], str]:
    """Deployed-vs-source drift, reusing the comparators doctor and the gate use."""
    from service_doctor_drift import scripts_drift_names

    scripts = scripts_drift_names(project_dir)
    if scripts is None and library_source(project_dir, "scripts") is None:
        return [], "no scripts/ source — hook drift not compared"
    names = sorted(set(scripts or []))
    harness: list[str] = []
    try:
        from gate_bootstrap_drift import _harness_drift_names  # reuse, not a second formula

        harness = list(_harness_drift_names(project_dir))
    except Exception:  # noqa: BLE001 — bootstrap/ may be absent in a consumer
        harness = []
    names = sorted(set(names + harness))
    if not names:
        return [], ""
    shown = ", ".join(names[:8])
    more = f" (+{len(names) - 8} more)" if len(names) > 8 else ""
    return (
        [
            AuditFinding(
                area="hook-drift",
                target=names[0],
                detail=(
                    f"{len(names)} deployed file(s) differ from source ({shown}{more}) — "
                    "an edit reached the profile by a route other than bootstrap. "
                    "Review, then `python bootstrap/bootstrap.py --ide all` to redeploy."
                ),
            )
        ],
        "",
    )


def _memory_findings(svc) -> list[AuditFinding]:
    """Memory rows carrying directives addressed to a future agent (AC-4).

    Memory is UNREVIEWED context: nothing between ``memory add`` and the next
    agent's context window reads these words. This scan is the only reader, so
    it reports rather than convicts — WARN findings, never a block.
    """
    findings: list[AuditFinding] = []
    try:
        rows = svc.memory_list(n=1_000_000, include_archived=True)
    except Exception:  # noqa: BLE001 — a closed DB is a doctor-level fact, not a crash here
        return findings
    for row in rows:
        blob = " ".join(str(row.get(k) or "") for k in ("title", "content"))
        directives = imperative_directives(blob)
        invisible = scan_invisible_unicode(blob)
        if directives or invisible:
            kinds = directives + [f"hidden:{f['codepoint']}" for f in invisible[:3]]
            findings.append(
                AuditFinding(
                    area="memory",
                    target=f"memory #{row.get('id')} «{str(row.get('title'))[:60]}»",
                    detail=(
                        "unreviewed context carrying agent-directed construct(s): "
                        + ", ".join(kinds)
                        + " — memory is ingested verbatim by the next agent; "
                        "verify this row was written by YOUR side"
                    ),
                )
            )
    return findings


def audit_installed_harness(project_dir: str, svc=None) -> list[AuditFinding]:
    """Scan the installed state. Read-only; every finding is WARN-grade."""
    from ide_utils import all_profile_dirs

    findings: list[AuditFinding] = []

    profiles = [
        d for d in sorted(all_profile_dirs()) if os.path.isdir(os.path.join(project_dir, d))
    ]
    for prof in profiles:
        root = os.path.join(project_dir, prof)
        flagged, secret_hits = _scan_profile(root)
        for rel, hits in sorted(flagged.items()):
            kinds = ", ".join(sorted({f["kind"] for f in hits}))
            findings.append(
                AuditFinding(
                    area="installed-unicode",
                    target=f"{prof}/{rel}",
                    detail=f"{len(hits)} hidden-instruction char(s) [{kinds}] in INSTALLED "
                    "state — nothing guards this tree after install",
                )
            )
        for rel, detectors in sorted(secret_hits.items()):
            findings.append(
                AuditFinding(
                    area="installed-secrets",
                    target=f"{prof}/{rel}",
                    detail="secret-pattern hit(s): "
                    + ", ".join(detectors)
                    + " (matched literal not printed)",
                )
            )

    root_mcp = os.path.join(project_dir, ".mcp.json")
    if os.path.isfile(root_mcp):
        try:
            with open(root_mcp, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        detectors = scan_text_secrets(text)
        invisible = scan_invisible_unicode(text)
        if detectors or invisible:
            findings.append(
                AuditFinding(
                    area="installed-secrets" if detectors else "installed-unicode",
                    target=".mcp.json",
                    detail="; ".join(
                        [f"secret-pattern: {', '.join(detectors)}" if detectors else ""]
                        + ([f"{len(invisible)} hidden char(s)"] if invisible else [])
                    ).strip("; "),
                )
            )

    drift_findings, _note = _drift_findings(project_dir)
    findings.extend(drift_findings)

    if svc is not None:
        findings.extend(_memory_findings(svc))

    return findings


def run_harness_audit_cmd(svc) -> None:  # ProjectService arrives from the CLI dispatcher
    """Print the audit. WARN verdict by construction (AC-5): never exits non-zero."""
    project_dir = os.getcwd()
    print("TAUSIK doctor — harness audit (INSTALLED state)")
    print("=" * 52)
    print(
        "Asymmetry this scan closes: signatures and the install-guard check the\n"
        "INCOMING tree; after install, nothing re-reads what is on disk — and an\n"
        "injection only needs to reach the installed state. All findings are WARN."
    )
    findings = audit_installed_harness(project_dir, svc)
    if not findings:
        print("  no findings — installed profiles, MCP configs and memory re-read clean")
    by_area: dict[str, list[AuditFinding]] = {}
    for f in findings:
        by_area.setdefault(f.area, []).append(f)
    for area in sorted(by_area):
        print(f"\n  [{area}] {len(by_area[area])} finding(s)")
        for f in by_area[area]:
            print(f"    ! {f.target}")
            print(f"      {f.detail}")
    print("=" * 52)
    print(f"WARN verdict: {len(findings)} finding(s); audit never blocks (AC-5).")


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
    sys.exit(0)
