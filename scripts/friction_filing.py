"""Idempotent, fail-closed filing of detected friction into local TAUSIK tasks."""

from __future__ import annotations

import hashlib
import os
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from friction_detect import FrictionSignal


class FilingRefused(RuntimeError):
    """A signal could not be made safe enough to persist."""


def _publication_config(tausik_dir: str) -> dict:
    from project_config import load_config

    section = dict(load_config(tausik_dir).get("publication") or {})
    names = list(section.get("project_names") or [])
    project_name = os.path.basename(os.path.dirname(os.path.abspath(tausik_dir)))
    if project_name:
        names.append(project_name)
    section["project_names"] = names
    return section


def redact_or_refuse(text: str, cfg: dict) -> str:
    """Redact every shared-scrubber match and refuse an incomplete scrub."""
    from brain_scrubbing import scrub_with_config
    from secret_patterns import redact_secret_literals, secret_literal_names

    try:
        result = scrub_with_config(str(text), cfg)
        redacted = str(text)
        for issue in result.get("issues", []):
            match = issue.get("match")
            if not isinstance(match, str) or not match:
                raise FilingRefused("scrubber returned an issue without a replaceable match")
            redacted = redacted.replace(match, "[redacted]")
        redacted, _secret_kinds = redact_secret_literals(redacted)
        if not scrub_with_config(redacted, cfg).get("ok"):
            raise FilingRefused("scrubbed value still contains blocked material")
        if secret_literal_names(redacted):
            raise FilingRefused("scrubbed value still contains a credential pattern")
        return redacted
    except FilingRefused:
        raise
    except Exception as exc:
        raise FilingRefused(f"scrubber failed: {type(exc).__name__}") from exc


def _safe_kind(kind: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", kind.lower()).strip("-")[:32] or "unknown"


def _fields(signal: FrictionSignal, cfg: dict) -> dict[str, str | int]:
    full = {
        "kind": redact_or_refuse(signal.kind, cfg),
        "identity": redact_or_refuse(signal.signature, cfg),
        "sample": redact_or_refuse(signal.sample, cfg),
        "hint": redact_or_refuse(signal.remedy_hint, cfg),
    }
    key = f"{full['kind']}\0{full['identity']}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    kind = _safe_kind(full["kind"])
    # Truncation is a presentation concern and happens only after the complete
    # raw value has passed redaction and the redacted correlation key is bound.
    values = {name: value[:500] for name, value in full.items()}
    return {
        **values,
        "slug": f"friction-{kind}-{digest}",
        "title": f"Investigate {kind} framework friction [{digest}]",
        "goal": (
            f"Remove recurring {values['kind']} friction for redacted source "
            f"{values['identity']} without weakening an intentional refusal."
        ),
        "acceptance": (
            "1. Reproduce the parser-recognized friction path from redacted evidence. "
            "2. Fix the framework cause and prove the same path succeeds or gives actionable help. "
            "3. Error case: normal fail-to-green work remains below the filing threshold."
        ),
        "evidence": (
            f"Friction evidence: kind={values['kind']}; source={values['identity']}; "
            f"collapsed_count={int(signal.count)}; sample={values['sample']}; "
            f"remedy_hint={values['hint']}"
        ),
    }


def file_signal(svc: Any, signal: FrictionSignal, tausik_dir: str) -> tuple[str, str]:
    """Create or update one planning task; never change a started/claimed task."""
    fields = _fields(signal, _publication_config(tausik_dir))
    slug = str(fields["slug"])
    with svc.be.transaction():
        current = svc.be.task_get(slug)
        if current is not None:
            if (
                current.get("status") != "planning"
                or current.get("started_at")
                or current.get("claimed_by")
            ):
                return slug, "unchanged"
            evidence = str(fields["evidence"])
            if any(log.get("message") == evidence for log in svc.task_logs(slug)):
                return slug, "unchanged"
            svc.task_log(slug, evidence, phase="planning")
            return slug, "updated"

        svc.task_add(
            None,
            slug,
            str(fields["title"]),
            complexity="medium",
            goal=str(fields["goal"]),
            role="developer",
        )
        svc.task_update(
            slug,
            acceptance_criteria=str(fields["acceptance"]),
            scope="Local framework friction identified by redacted telemetry.",
            scope_exclude="No network, remote issue, push, publication, claim or task start.",
            rollback_plan="Delete the unstarted planning task if the signal is disproved.",
        )
        svc.task_log(slug, str(fields["evidence"]), phase="planning")
    return slug, "created"


def file_signals(svc: Any, signals: list[FrictionSignal], tausik_dir: str) -> list[str]:
    """File every safe signal, reporting refusals without hiding other signals."""
    lines: list[str] = []
    for signal in signals:
        try:
            slug, action = file_signal(svc, signal, tausik_dir)
            lines.append(f"{action}: {slug} (x{signal.count})")
        except FilingRefused as exc:
            lines.append(f"REFUSED {signal.kind}: {exc}")
        except Exception as exc:  # noqa: BLE001 — one DB failure must not hide other signals
            lines.append(f"REFUSED {signal.kind}: filing failed ({type(exc).__name__})")
    return lines


def pending_friction_count(svc: Any) -> int:
    """Read-only count used by ordinary doctor."""
    return sum(
        1
        for task in svc.task_list(status="planning,active,blocked,review", include_archived=True)
        if re.fullmatch(r"friction-[a-z0-9-]+-[0-9a-f]{16}", str(task.get("slug") or ""))
        and str(task.get("title") or "").startswith("Investigate ")
    )
