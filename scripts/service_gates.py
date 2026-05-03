"""TAUSIK GatesMixin — QG-0/QG-2 verification logic for task lifecycle."""

from __future__ import annotations

import json

import re
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

# v1.3.4 (med-batch-2-qg #1): negative-scenario detection lives in its own
# module for filesize compliance. Re-exported so existing imports of
# `service_gates.has_negative_scenario` and `service_gates.NEGATIVE_SCENARIO_KEYWORDS`
# keep working.
from gate_negative_scenario import (  # noqa: F401, E402
    NEGATIVE_SCENARIO_KEYWORDS,
    has_negative_scenario,
)


SECURITY_KEYWORDS = (
    "auth",
    "login",
    "password",
    "token",
    "jwt",
    "session",
    "oauth",
    "payment",
    "billing",
    "charge",
    "stripe",
    "pii",
    "personal data",
    "encrypt",
    "decrypt",
    "secret",
    "credential",
    "api key",
    "авториз",
    "пароль",
    "токен",
    "оплат",
    "платёж",
    "персональн",
)

SECURITY_AC_KEYWORDS = (
    "security",
    "безопасн",
    "xss",
    "injection",
    "csrf",
    "sanitiz",
    "escap",
    "encrypt",
    "hash",
    "salt",
    "rate limit",
    "brute",
    "privilege",
    "escalat",
)


# qg0_dimensions_score lives in gate_qg0_score.py for filesize-gate compliance;
# re-export keeps `from service_gates import qg0_dimensions_score` working.
from gate_qg0_score import qg0_dimensions_score  # noqa: F401, E402


class GatesMixin:
    """QG-0 and QG-2 verification methods for task lifecycle."""

    be: SQLiteBackend

    def run_verify_for_task(
        self,
        task_slug: str | None,
        relevant_files: list[str] | None = None,
        scope: str = "standard",
        trigger: str = "verify",
    ) -> dict[str, Any]:
        """Public Verify-First entry point — wraps run_gates_with_cache.

        v1.4: replaces the prior MCP `_handle_verify` direct access to
        `svc.be._conn`, keeping CLI/MCP layered through the service. Returns
        a structured dict so MCP can format consistently.

        Behavior:
          - With `task_slug`: scoped verify against the task's relevant_files
            (if not passed explicitly) and recorded in `verification_runs`.
          - Without `task_slug`: full-suite, file-scope empty, no DB write.
            Mirrors `tausik verify` CLI without --task.
          - `trigger` defaults to "verify" so this is the canonical entrypoint
            for the Verify-First Contract; pass "task-done" to dry-run the
            cheap-gate pipeline.
        """
        from service_verification import run_gates_with_cache

        files: list[str] = list(relevant_files or [])
        task_created_at: str | None = None
        if task_slug:
            task = self.be.task_get(task_slug)
            if task is None:
                raise ServiceError(f"Task '{task_slug}' not found")
            if not files:
                raw = task.get("relevant_files") or "[]"
                try:
                    import json as _json

                    files = _json.loads(raw) if raw else []
                except (TypeError, ValueError):
                    files = []
            task_created_at = task.get("created_at")
        passed, results, status = run_gates_with_cache(
            self.be._conn,
            task_slug or "",
            files or None,
            scope=scope,
            append_notes_fn=(self.be.task_append_notes if task_slug else None),
            task_created_at=task_created_at,
            trigger=trigger,
        )
        return {
            "passed": passed,
            "status": status,
            "scope": scope,
            "trigger": trigger,
            "task_slug": task_slug,
            "results": results,
        }

    def _check_qg0_start(self, slug: str, task: dict[str, Any]) -> list[str]:
        """QG-0 Context Gate: validate goal, AC, scope, negative scenarios, security.

        Returns list of warning strings (empty if no warnings).
        Raises ServiceError for hard-gate failures.
        """
        warnings: list[str] = []
        missing = []
        if not task.get("goal") or not task["goal"].strip():
            missing.append("goal")
        if not task.get("acceptance_criteria") or not task["acceptance_criteria"].strip():
            missing.append("acceptance_criteria")
        if missing:
            raise ServiceError(
                f"QG-0 Context Gate: '{slug}' cannot start — missing {', '.join(missing)}. "
                f"Fix: .tausik/tausik task update {slug} --goal '...' --acceptance-criteria '...'"
            )
        # QG-0: warn if scope not defined (SENAR Core Rule 2)
        if not task.get("scope") or not task["scope"].strip():
            warnings.append(
                f"WARNING: Task '{slug}' has no scope defined. "
                f"SENAR recommends defining what to change and what NOT to touch."
            )
        # QG-0: scope_exclude warning for medium/complex tasks (SENAR Core Rule 2)
        complexity = task.get("complexity") or "medium"
        if complexity in ("medium", "complex"):
            if not task.get("scope_exclude") or not task["scope_exclude"].strip():
                warnings.append(
                    f"WARNING: Task '{slug}' ({complexity}) has no scope_exclude. "
                    f"SENAR recommends defining what NOT to touch for medium/complex tasks."
                )
        # QG-0: negative scenario required in AC (SENAR Core Start Gate #3).
        # v1.3.4 (med-batch-2-qg #1): use boundary-aware detection instead of
        # substring match. "Works without errors" no longer satisfies the gate.
        ac_text = task.get("acceptance_criteria") or ""
        if ac_text and not has_negative_scenario(ac_text):
            raise ServiceError(
                f"QG-0 Start Gate: '{slug}' AC has no negative scenario. "
                f"SENAR requires at least one error/boundary case in acceptance criteria. "
                f"Fix: add a criterion like 'Returns 400 on invalid input' or 'Ошибка при пустом поле'."
            )
        # SENAR Rule 9.2: session duration — block task_start after limit
        try:
            session_warning = self.session_check_duration()  # type: ignore[attr-defined]
            if session_warning:
                raise ServiceError(
                    f"QG-0 Start Gate: {session_warning} "
                    f"Use '/end' to finish session, or 'session extend' to continue."
                )
        except (AttributeError, Exception) as e:
            if isinstance(e, ServiceError):
                raise
            pass  # GatesMixin used outside ProjectService — skip
        # SENAR Rule 9.5: audit overdue warning at task start
        try:
            audit_warning = self.audit_check()  # type: ignore[attr-defined]
            if audit_warning:
                warnings.append(f"AUDIT: {audit_warning}")
        except (AttributeError, Exception):
            pass
        # QG-0: security surface warning (SENAR Core Start Gate #5).
        # ac_text is now case-preserving for has_negative_scenario (which
        # is itself case-insensitive); lowercase here for the SECURITY_AC
        # substring check which expects already-lowered keywords.
        ac_lower = ac_text.lower()
        title_and_goal = f"{task.get('title', '')} {task.get('goal', '')}".lower()
        if any(kw in title_and_goal for kw in SECURITY_KEYWORDS):
            if not any(kw in ac_lower for kw in SECURITY_AC_KEYWORDS):
                warnings.append(
                    f"WARNING: Task '{slug}' appears security-relevant but AC has no security criteria. "
                    f"SENAR recommends identifying threat surface and adding security AC."
                )
        # QG-0: 9-dimension intent completeness (prompt-master pattern)
        dims = qg0_dimensions_score(task)
        filled = sum(1 for v in dims.values() if v)
        if filled < 5:
            missing_dims = [k for k, v in dims.items() if not v]
            warnings.append(
                f"CONTEXT: Task '{slug}' has only {filled}/9 intent dimensions defined. "
                f"Consider adding: {', '.join(missing_dims)}. "
                f"(prompt-master: thin context = drift risk)"
            )
        return warnings

    def _verify_ac(self, slug: str, task: dict[str, Any], ac_verified: bool) -> list[str]:
        """QG-2: Verify acceptance criteria evidence exists (per-criterion).

        Returns list of warning strings (empty if no warnings).
        Raises ServiceError for hard-gate failures.
        """
        if not task.get("acceptance_criteria"):
            return []
        if not ac_verified:
            raise ServiceError(
                f"QG-2: '{slug}' cannot complete — acceptance criteria not verified. "
                f"Verify each criterion, then: .tausik/tausik task done {slug} --ac-verified"
            )
        notes = task.get("notes") or ""
        ac_text = task["acceptance_criteria"].strip()
        # Parse numbered AC: lines starting with "1.", "2.", etc.
        ac_items = re.findall(r"^\s*\d+[\.\)]\s*(.+)", ac_text, re.MULTILINE)
        if not ac_items:
            # Fallback: split by newlines
            ac_items = [ln.strip() for ln in ac_text.splitlines() if ln.strip()]
        if not ac_items:
            return []
        # Check that evidence acknowledges verification. Accept any of:
        #  - literal "ac verified" / "verified ac" phrase
        #  - any line with checkmark (✓✔✅) — implies per-item evidence
        #  - "verified" keyword (broader, catches "verified all AC" etc)
        notes_l = notes.lower()
        has_marker = (
            "ac verified" in notes_l
            or "verified ac" in notes_l
            or "verified" in notes_l
            or any(c in notes for c in "✓✔✅")
        )
        if not has_marker:
            raise ServiceError(
                f"QG-2: '{slug}' has {len(ac_items)} acceptance criteria but no verification "
                f"evidence in task notes. Log verification: "
                f'.tausik/tausik task log {slug} "AC verified: 1. ✓ 2. ✓ ..."'
            )
        # Per-criterion check: warn if not all numbered criteria have evidence
        warnings: list[str] = []
        ac_verified_lines = re.findall(r"\d+[\.\)].*(?:[\u2713\u2714\u2705]|\[v\])", notes)
        if len(ac_verified_lines) < len(ac_items):
            warnings.append(
                f"WARNING: {len(ac_items)} AC criteria, but only {len(ac_verified_lines)} "
                f"have explicit evidence markers (✓). Consider verifying each criterion."
            )
        return warnings

    def _verify_plan_complete(self, slug: str, task: dict[str, Any]) -> None:
        """Check all plan steps are done."""
        if not task.get("plan"):
            return
        try:
            steps = json.loads(task["plan"])
            total = len(steps)
            done_count = sum(1 for s in steps if s.get("done"))
            if done_count < total:
                raise ServiceError(
                    f"Plan incomplete ({done_count}/{total} steps). "
                    f"Complete remaining steps with: .tausik/tausik task step {slug} N"
                )
        except (json.JSONDecodeError, TypeError) as e:
            raise ServiceError(f"Corrupted plan data for task '{slug}': {e}")

    def _determine_checklist_tier(
        self,
        task: dict[str, Any],
        relevant_files: list[str] | None = None,
    ) -> str:
        """Auto-detect verification checklist tier based on task risk.

        Tiers: lightweight (4 items), standard (10), high (18), critical (28).

        v1.3.4 (med-batch-2-qg #2): also consult `is_security_sensitive`
        on `relevant_files` — a "fix typo" task (title=trivial) that touches
        scripts/auth.py is security-sensitive in practice. Without this
        check, such a task picked tier='lightweight' (4 items) even though
        the file change ought to demand critical-tier review.
        """
        from service_verification import is_security_sensitive

        complexity = task.get("complexity") or "medium"
        title_goal = f"{task.get('title', '')} {task.get('goal', '')}".lower()
        # Security keywords in title/goal -> high tier
        is_security_title = any(kw in title_goal for kw in SECURITY_KEYWORDS)
        # Security-sensitive files (auth/payment/hooks/...) -> critical tier
        is_security_files = is_security_sensitive(relevant_files or [])

        if is_security_files:
            return "critical"
        if complexity == "simple" and not is_security_title:
            return "lightweight"
        if is_security_title:
            return "high"
        if complexity == "complex":
            return "critical"
        return "standard"

    def _check_verification_checklist(self, slug: str, task: dict[str, Any]) -> str:
        """SENAR Core Rule 5: Verification checklist (28 items, 4 tiers).

        Returns warning string (empty if OK). Advisory — not a hard gate.
        Tier auto-detected from complexity + security keywords.

        v1.4 (r14-senar-checklist-deeper): the v1.3 implementation counted
        keyword hits in `notes` ("scope", "phantom", "secret"…). That made
        QG-2 trivial to fool ("scope clean, no secrets" produced 2 hits)
        and gave nothing for AC traceability. We now run a structured AC
        evidence parser (`service_ac_evidence`) on top of the keyword
        check and surface the gaps:
          - per-AC coverage (which AC have explicit evidence)
          - test-ref coverage (which AC cite tests/test_*.py::test_*)
          - negative-scenario evidence presence
        """
        from service_ac_evidence import build_report

        notes_text = task.get("notes") or ""
        notes_lower = notes_text.lower()
        try:
            rf_raw = task.get("relevant_files") or "[]"
            rf = json.loads(rf_raw) if isinstance(rf_raw, str) else (rf_raw or [])
        except (TypeError, ValueError, json.JSONDecodeError):
            rf = []
        tier = self._determine_checklist_tier(task, relevant_files=rf)
        lightweight_kw = ["scope", "phantom", "test tamper", "secret", "hardcoded secret"]
        standard_kw = lightweight_kw + [
            "delet",
            "test quality",
            "input valid",
            "deprecat",
            "cross-file",
            "code quality",
        ]
        high_kw = standard_kw + [
            "null guard",
            "empty config",
            "header trust",
            "idor",
            "return true",
            "auth coverage",
            "deserializ",
            "ssrf",
        ]
        critical_kw = high_kw + [
            "dependency version",
            "magic number",
            "over-engineer",
            "duplicat",
            "edge case",
            "naming",
            "commit scope",
            "string format",
            "unreachable",
            "swallow",
        ]
        tier_kw = {
            "lightweight": lightweight_kw,
            "standard": standard_kw,
            "high": high_kw,
            "critical": critical_kw,
        }
        tier_count = {"lightweight": 4, "standard": 10, "high": 18, "critical": 28}
        checks = tier_kw.get(tier, standard_kw)
        kw_hits = sum(1 for kw in checks if kw in notes_lower)

        warnings: list[str] = []
        if kw_hits == 0:
            warnings.append(
                f"NOTE: Verification checklist ({tier}, {tier_count[tier]} items) — "
                "no checklist items found in notes. Run /review before closing."
            )

        ac_text = task.get("acceptance_criteria") or ""
        if ac_text.strip():
            report = build_report(ac_text, notes_text)
            if report.total_ac:
                if report.covered < report.total_ac:
                    gap_str = ", ".join(str(i) for i in report.gaps())
                    warnings.append(
                        f"NOTE: AC evidence parser found {report.covered}/"
                        f"{report.total_ac} criteria with explicit evidence "
                        f"(gaps: AC {gap_str}). Add 'AC-N: ✓ tested via tests/...' "
                        "lines via `task log`."
                    )
                if tier in ("high", "critical") and report.covered_with_tests == 0:
                    warnings.append(
                        f"NOTE: tier={tier} requires test-ref evidence (e.g. "
                        "'tests/test_foo.py::test_bar') — none found in notes."
                    )
                if tier in ("high", "critical") and not report.has_negative_evidence:
                    warnings.append(
                        "NOTE: high/critical task should exercise the AC's "
                        "negative scenario — no `Negative:` evidence found in notes."
                    )

        return "\n".join(warnings)

    @staticmethod
    def _extract_files_from_gate_output(output: str) -> list[str]:
        files = re.findall(r"^\s+([^\s:]+):\s+\d+\s+lines", output or "", re.MULTILINE)
        return files

    def _run_quality_gates_report(
        self,
        slug: str,
        relevant_files: list[str] | None,
        progress_fn: Any | None = None,
        trigger: str = "task-done",
    ) -> dict[str, Any]:
        """Return detailed gate report for MCP/agent-friendly handling.

        Verify-First Contract (v1.4): when called with trigger="task-done"
        (the default — i.e. via the `task_done` flow), this method ALSO
        checks whether a fresh `tausik verify` green exists for this task
        and refuses to close the task if not. The check is opt-out via
        `config.task_done.auto_verify=true` for the legacy "run heavy gates
        inline" behavior — useful in CI where one long step is fine but
        interactive MCP hosts (VS Code Claude Extension) hang.

        When called with trigger="verify" (i.e. via `tausik verify --task`),
        this method runs the verify-trigger gates and records the result in
        `verification_runs`. No "fresh verify run" check — that would be
        circular.
        """
        report: dict[str, Any] = {
            "passed": True,
            "results": [],
            "cache_status": None,
            "blocking_failures": [],
            "scope": None,
        }
        try:
            from service_verification import (
                is_security_sensitive,
                run_gates_with_cache,
            )
        except ImportError:
            import logging

            logging.getLogger("tausik.gates").warning("service_verification not available")
            return report

        task = self.be.task_get(slug) or {}
        scope = self._determine_checklist_tier(task, relevant_files=relevant_files)
        if is_security_sensitive(relevant_files or []):
            scope = "critical"
        report["scope"] = scope

        passed, results, status = run_gates_with_cache(
            self.be._conn,
            slug,
            relevant_files,
            scope=scope,
            append_notes_fn=self.be.task_append_notes,
            task_created_at=task.get("created_at"),
            progress_fn=progress_fn,
            trigger=trigger,
        )
        report["passed"] = passed
        report["results"] = results
        report["cache_status"] = status

        if not passed:
            failed = [r for r in results if not r.get("passed") and r.get("severity") == "block"]
            report["blocking_failures"] = [
                {
                    "gate": r.get("name"),
                    "files": self._extract_files_from_gate_output(r.get("output", "")),
                    "output": r.get("output", ""),
                    "remediation": (
                        "Fix gate issues and rerun task_done. For filesize: "
                        "split oversized modules or configure "
                        "gates.filesize.exempt_files in .tausik/config.json."
                    ),
                }
                for r in failed
            ]
            return report

        # Verify-First Contract enforcement: only on the task-done path,
        # only when there ARE verify-trigger gates configured (otherwise no
        # heavy verification was ever expected — small projects are fine),
        # and only when auto_verify is NOT explicitly opted-in.
        if trigger == "task-done":
            self._enforce_verify_first(report, slug, relevant_files)
        return report

    def _enforce_verify_first(
        self,
        report: dict[str, Any],
        slug: str,
        relevant_files: list[str] | None,
    ) -> None:
        """Add a synthetic blocking_failure if no fresh `tausik verify` run
        exists for this task and the project has verify-trigger gates.

        Three opt-out paths:
          - config.task_done.auto_verify = true  →  legacy inline behavior;
            in that case we run the verify-trigger gates inline right here.
          - No verify-trigger gates configured (small projects, no pytest
            etc.) →  nothing to wait on, skip enforcement.
          - Security-sensitive files →  cache always refused, but we still
            require an explicit verify run; the agent must call `tausik
            verify` immediately before `task done` to avoid stale greens.
        """
        from service_verification import (
            DEFAULT_CACHE_TTL_S,
            has_fresh_verify_run,
            run_gates_with_cache,
        )

        try:
            from project_config import get_gates_for_trigger, load_config

            cfg = load_config()
            verify_gates = get_gates_for_trigger("verify", cfg)
        except Exception:
            verify_gates = []
            cfg = {}
        if not verify_gates:
            return  # no heavy gates configured, nothing to enforce

        td_cfg = cfg.get("task_done", {}) if isinstance(cfg, dict) else {}
        auto_verify = bool(td_cfg.get("auto_verify", False))
        ttl = int(
            cfg.get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
            if isinstance(cfg, dict)
            else DEFAULT_CACHE_TTL_S
        )

        fresh, hit = has_fresh_verify_run(self.be._conn, slug, relevant_files, max_age_s=ttl)
        if fresh and hit is not None:
            self.be.task_append_notes(
                slug,
                f"Verify-First: cache hit (verify run #{hit['id']} at {hit['ran_at']})",
            )
            return

        if auto_verify:
            # Legacy CI-style behavior: run the verify trigger inline.
            self.be.task_append_notes(
                slug,
                "Verify-First: auto_verify=true — running verify gates inline "
                "(legacy behavior; task_done will block until they finish).",
            )
            try:
                passed, results, _status = run_gates_with_cache(
                    self.be._conn,
                    slug,
                    relevant_files,
                    scope=report.get("scope") or "standard",
                    append_notes_fn=self.be.task_append_notes,
                    trigger="verify",
                )
            except Exception as e:
                report["passed"] = False
                report["blocking_failures"].append(
                    {
                        "gate": "verify-first",
                        "files": [],
                        "output": f"auto_verify run crashed: {e}",
                        "remediation": (
                            "Fix the failing verify gate or set "
                            "config.task_done.auto_verify=false and run "
                            "`tausik verify` manually."
                        ),
                    }
                )
                return
            if not passed:
                report["passed"] = False
                blocking = [
                    r for r in results if not r.get("passed") and r.get("severity") == "block"
                ]
                report["blocking_failures"].extend(
                    {
                        "gate": r.get("name"),
                        "files": self._extract_files_from_gate_output(r.get("output", "")),
                        "output": r.get("output", ""),
                        "remediation": (
                            "Fix gate issues and rerun task_done. "
                            "(auto_verify=true caused inline run.)"
                        ),
                    }
                    for r in blocking
                )
            return

        # Default v1.4 behavior: refuse to close.
        gate_names = ", ".join(g.get("name", "?") for g in verify_gates)
        report["passed"] = False
        report["blocking_failures"].append(
            {
                "gate": "verify-first",
                "files": list(relevant_files or []),
                "output": (
                    f"QG-2: no fresh `tausik verify` run for this task "
                    f"(verify gates configured: {gate_names}). "
                    f"Run `tausik verify --task {slug}` first — it caches; "
                    f"then `task done` closes in milliseconds. To opt out "
                    f"set config.task_done.auto_verify=true (legacy)."
                ),
                "remediation": (
                    f".tausik/tausik verify --task {slug}  &&  "
                    f".tausik/tausik task done {slug} --ac-verified"
                ),
            }
        )

    def _run_quality_gates(
        self, slug: str, relevant_files: list[str] | None, progress_fn: Any | None = None
    ) -> None:
        """QG-2 Implementation Gate: scoped gates with verify cache.

        Delegates to `service_verification.run_gates_with_cache` — see that
        module for cache rules (10 min TTL, files_hash invalidation,
        security-sensitive bypass). The scope passed in (and recorded with
        the verify run) is derived from the task's complexity tier per
        SENAR Rule 5: simple→lightweight, medium→standard, complex→high.
        Security-sensitive `relevant_files` (per `is_security_sensitive`)
        promote to `critical`.
        """
        gate_report = self._run_quality_gates_report(slug, relevant_files, progress_fn=progress_fn)
        if not gate_report["passed"]:
            failures = gate_report.get("blocking_failures", [])
            details = "; ".join(
                f"{f.get('gate')}: {(f.get('output') or '')[:140]}" for f in failures
            )
            raise ServiceError(
                f"QG-2 Implementation Gate: blocking gates failed for '{slug}'. "
                f"Fix issues first: {details}"
            )
