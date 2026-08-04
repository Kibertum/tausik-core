"""Draft + risk assessment for shared-brain artifact publish.

Uses `brain_classifier.classify` — project-specific markers imply **high** risk
(local-only), requiring `confirm_high_risk` on the real Notion write.

WHICH CATEGORIES THE GATE COVERS is decided by `_CLASSIFIER_CATEGORY` and by
nothing else: a category in that mapping is gated, a category outside it is
waved through. As of decision #205 that is **patterns, gotchas and decisions**.

The enumeration is repeated here for a reader rather than left implicit, and it
is pinned to the registry by a test — because the previous version of this line
said "patterns/gotchas", stayed unchanged when decisions were added, and was
then CITED as evidence that decisions were exempt. A sentence that once served
as proof of behaviour keeps being read as proof after it stops being true.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Mapping

from brain_classifier import classify

_CLASSIFIER_CATEGORY = {"patterns": "pattern", "gotchas": "gotcha", "decisions": "decision"}

_TEXT_KEYS_PATTERNS = (
    "name",
    "description",
    "when_to_use",
    "example",
    "scope",
    "artifact_taxonomy_kind",
)
_TEXT_KEYS_GOTCHAS = (
    "name",
    "description",
    "wrong_way",
    "right_way",
    "scope",
    "artifact_taxonomy_kind",
)

_TEXT_KEYS_DECISIONS = ("name", "decision", "rationale")

# Keyed, not branched. This used to be `PATTERNS if category == "patterns" else
# GOTCHAS`, which silently read any third category with gotcha keys — a blob of
# empty strings, classified as "empty content" → local → high risk → every
# publish blocked. A lookup makes an unregistered category say so instead of
# guessing, which is what let `decisions` be added at all.
_TEXT_KEYS_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "patterns": _TEXT_KEYS_PATTERNS,
    "gotchas": _TEXT_KEYS_GOTCHAS,
    "decisions": _TEXT_KEYS_DECISIONS,
}

_TAGS_STACK = ("tags", "stack")


def _stringify(v: Any) -> str:
    if isinstance(v, (list, tuple)):
        return " ".join(str(x) for x in v)
    return str(v) if v is not None else ""


def artifact_blob_for_classifier(category: str, fields: Mapping[str, Any]) -> str:
    """Concatenate classify-relevant text like scrub_inputs does for markers.

    Every key a category publishes must be listed for it: the blob is what the
    risk assessment sees, and a field left out of it is a field that cannot
    influence the verdict — the same shape of gap that let `decide` judge a
    decision by its headline while shipping its rationale.
    """
    keys = _TEXT_KEYS_BY_CATEGORY.get(category)
    if keys is None:
        raise KeyError(
            f"no classifier text keys registered for category {category!r}; "
            f"add them to _TEXT_KEYS_BY_CATEGORY rather than letting the blob "
            f"fall back to another category's fields"
        )
    lines = [_stringify(fields.get(k)) for k in keys]
    lines.extend(_stringify(fields.get(k)) for k in _TAGS_STACK)
    return "\n".join(lines)


def assess_publish_risk(
    category: str,
    fields: Mapping[str, Any],
    cfg: Mapping[str, Any] | None,
) -> tuple[Literal["low", "high"], str]:
    """Return (level, reason) for one candidate publish.

    Covers the categories in `_CLASSIFIER_CATEGORY` — patterns, gotchas and
    decisions since #205. Anything outside it is reported "low" with a reason
    that says WHY it is low: no classifier exists for that category, which is
    not the same claim as "this content was examined and looks safe".
    """
    if category not in _CLASSIFIER_CATEGORY:
        return "low", "category has no artifact classifier"
    blob = artifact_blob_for_classifier(category, fields)
    cat = _CLASSIFIER_CATEGORY[category]
    d = classify(blob, cat, cfg=dict(cfg or {}))
    if d.target == "local":
        return "high", d.reason
    return "low", d.reason


def maybe_block_high_risk_publish(
    category: str,
    fields: Mapping[str, Any],
    cfg: Mapping[str, Any] | None,
    *,
    confirm_high_risk: bool,
) -> tuple[bool, str | None]:
    """Return (blocked, message).

    Applies to the categories in `_CLASSIFIER_CATEGORY` — patterns, gotchas and
    decisions since #205 — and to nothing else: an unregistered category returns
    "not blocked" here without consulting the classifier at all.
    """
    if category not in _CLASSIFIER_CATEGORY:
        return False, None
    level, reason = assess_publish_risk(category, fields, cfg)
    if level == "high" and not confirm_high_risk:
        return True, (
            "high-risk publish: content looks project-specific "
            f"({reason}). Set confirm_high_risk=true after human review, "
            "or use brain_draft_artifact to inspect."
        )
    return False, None


def draft_artifact_publish(
    category: str,
    fields: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Dry-run: taxonomy + card + scrub + risk. Does not write to Notion."""
    import brain_artifact_card
    import brain_artifact_taxonomy
    import brain_mcp_write
    import brain_snippet_detect

    out: dict[str, Any] = {"category": category}
    # Mirror store_record: auto-fill the inferred kind FIRST (on a copy — a
    # dry-run never mutates the caller's fields), then validate the enriched
    # copy so taxonomy_ok matches the real write outcome under strict mode.
    work = dict(fields)
    inferred = brain_snippet_detect.maybe_autofill_snippet_kind(category, work, cfg)
    out["taxonomy_inferred"] = inferred

    ok_tax, tax_err = brain_artifact_taxonomy.validate_artifact_taxonomy_for_store(
        category, work, cfg
    )
    out["taxonomy_ok"] = ok_tax
    out["taxonomy_error"] = tax_err

    ok_card, card_err = brain_artifact_card.validate_artifact_card_for_store(category, work, cfg)
    out["card_ok"] = ok_card
    out["card_error"] = card_err

    ok_ext, ext_err = brain_artifact_card.validate_external_repo_url_for_store(category, work, cfg)
    out["external_repo_ok"] = ok_ext
    out["external_repo_error"] = ext_err

    scrub = brain_mcp_write.scrub_inputs(category, fields, cfg)
    out["scrub_ok"] = scrub["ok"]
    out["scrub_issues"] = scrub.get("issues") or []

    level, reason = assess_publish_risk(category, fields, cfg)
    out["risk_level"] = level
    out["risk_reason"] = reason

    gate_ok = ok_tax and ok_card and ok_ext and scrub["ok"]
    out["would_publish_ok"] = gate_ok and level != "high"
    out["would_need_confirm"] = gate_ok and level == "high"
    return out


def format_draft_report(payload: dict[str, Any]) -> str:
    """Markdown summary for MCP / CLI."""
    lines = [
        "## Artifact draft (no Notion write)",
        "",
        f"- **category**: `{payload.get('category')}`",
        f"- **risk_level**: **{payload.get('risk_level')}** — {payload.get('risk_reason', '')}",
        f"- **taxonomy_ok**: {payload.get('taxonomy_ok')}",
        f"- **card_ok**: {payload.get('card_ok')}",
        f"- **external_repo_ok**: {payload.get('external_repo_ok')}",
        f"- **scrub_ok**: {payload.get('scrub_ok')}",
    ]
    if payload.get("taxonomy_inferred"):
        lines.append(
            f"- **taxonomy_inferred**: `{payload['taxonomy_inferred']}` "
            "(auto-classified; caller omitted artifact_taxonomy_kind)"
        )
    if payload.get("taxonomy_error"):
        lines.append(f"- **taxonomy_error**: {payload['taxonomy_error']}")
    if payload.get("card_error"):
        lines.append(f"- **card_error**: {payload['card_error']}")
    if payload.get("external_repo_error"):
        lines.append(f"- **external_repo_error**: {payload['external_repo_error']}")
    issues = payload.get("scrub_issues") or []
    if issues:
        lines.append("- **scrub issues**:")
        for i in issues:
            lines.append(f"  - {i}")
    lines.append("")
    lines.append(
        f"- **would_publish_ok** (low risk, gates pass): {payload.get('would_publish_ok')}"
    )
    lines.append(
        f"- **would_need_confirm** (high risk, gates pass): {payload.get('would_need_confirm')}"
    )
    return "\n".join(lines)


def load_payload_from_cli(args: Any) -> dict[str, Any]:
    """Parse --json or --file into a dict."""
    import os

    raw = getattr(args, "json_payload", None)
    path = getattr(args, "json_file", None)
    if path:
        p = os.path.expanduser(path)
        with open(p, encoding="utf-8") as f:
            raw = f.read()
    if not raw or not str(raw).strip():
        raise ValueError("Provide --json or --file with a JSON object")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def category_from_kind(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k == "pattern":
        return "patterns"
    if k == "gotcha":
        return "gotchas"
    raise ValueError("kind must be 'pattern' or 'gotcha'")


def log_artifact_publish_audit(category: str, fields: Mapping[str, Any]) -> None:
    """Best-effort `brain_events` row (project DB) for publish telemetry."""
    if category not in ("patterns", "gotchas"):
        return
    try:
        from brain_metrics_log import log_brain_event

        name = str(fields.get("name") or "")[:120]
        log_brain_event(
            "write",
            query=f"artifact_publish:{category}:{name}",
            result_count=1,
        )
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        pass
