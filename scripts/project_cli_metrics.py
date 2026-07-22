"""TAUSIK CLI helpers — metrics subcommand dispatch.

Extracted from project_cli_ops.py to keep it under the 400-line filesize
gate (filesize-debt-paydown follow-up). Pure re-org — no semantic changes.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService


def render_extended_metrics(m: dict[str, Any]) -> None:
    """Print the per-tier, calibration-drift and defect-escape tail of the metrics
    summary. Extracted from project_cli_ops._print_metrics so that file stays under
    the 400-line filesize gate when l26-defect-escape-rate added the escape section.
    Output is byte-identical to the inline version it replaced."""
    per_tier = m.get("per_tier") or {}
    if per_tier:
        print("\n--- Per-tier (agent-native units) ---")
        order = ["trivial", "light", "moderate", "substantial", "deep", "unset"]
        for tier in order:
            d = per_tier.get(tier)
            if not d:
                continue
            ab = d["avg_budget"] if d["avg_budget"] is not None else "-"
            aa = d["avg_actual"] if d["avg_actual"] is not None else "-"
            print(
                f"  {tier:>11}: count={d['count']:<4} budget={ab:<6} "
                f"actual={aa:<6} fpsr={d['fpsr_pct']}%"
            )
    drift = m.get("calibration_drift")
    if drift:
        print(
            f"\nCalibration drift: {drift['label']} "
            f"(avg actual/budget = {drift['avg_ratio']}, n={drift['samples']})"
        )
    # l26-defect-escape-rate: the outcome metric. DER is the crude aggregate; this
    # shows whether verification and risk_score actually track escapes.
    esc = m.get("defect_escape")
    if esc:
        ov = esc["overall"]
        print("\n--- Defect Escape (l26) ---")
        print(f"Escape rate:   {ov['rate_pct']}% ({ov['escaped']}/{ov['done']} done escaped)")
        bv = esc.get("by_verification", {})
        for label in ("verified", "unverified"):
            d = bv.get(label)
            if d and d["done"]:
                print(f"  {label:<11}: {d['rate_pct']}% ({d['escaped']}/{d['done']})")
        bt = esc.get("risk_backtest", {})
        if bt.get("escaped_avg_risk") is not None or bt.get("clean_avg_risk") is not None:
            ea = bt["escaped_avg_risk"] if bt["escaped_avg_risk"] is not None else "-"
            ca = bt["clean_avg_risk"] if bt["clean_avg_risk"] is not None else "-"
            print(
                f"  risk backtest: escaped avg={ea} (n={bt['escaped_n']}) "
                f"vs clean avg={ca} (n={bt['clean_n']})"
            )
    # l26-bypass-telemetry: how many times supervision was switched off. Only
    # rendered when non-zero — a clean run stays quiet, but a bypass can no
    # longer hide as silence (the whole point: the count is falsifiable).
    byp = m.get("supervision_bypasses") or {}
    if byp.get("total"):
        print("\n--- Supervision bypasses (l26) ---")
        print(f"Total: {byp['total']}")
        for action, cnt in byp.get("by_action", {}).items():
            print(f"  {action:<26}: {cnt}")
    # l26-complexity-self-declared: detections are supervision that WORKED —
    # rendered under their OWN heading so they are never misread as bypasses.
    det = m.get("supervision_detections") or {}
    if det.get("total"):
        print("\n--- Supervision detections (l26) ---")
        print(f"Total: {det['total']}")
        for action, cnt in det.get("by_action", {}).items():
            print(f"  {action:<26}: {cnt}")
    # hook-fail-open-db-error-telemetry: silent fail-open degradations — a guard
    # that let an edit through because it could not read the DB. Its OWN heading
    # so it is never misread as a bypass (nobody switched it off) or a detection
    # (nothing was caught). Rendered only when non-zero.
    deg = m.get("supervision_degradations") or {}
    if deg.get("total"):
        print("\n--- Supervision degradations / fail-open (l26) ---")
        print(f"Total: {deg['total']}")
        for action, cnt in deg.get("by_action", {}).items():
            print(f"  {action:<26}: {cnt}")


def dispatch_metrics_subcmd(svc: ProjectService, args: Any) -> bool:
    """Handle `metrics <sub>`: record-session, log-usage, cost, tokens.

    Returns True if a subcommand was dispatched (caller should return),
    False if the request is for the default `metrics` summary view.
    """
    sub = getattr(args, "metrics_cmd", None)
    if sub == "record-session":
        kw = dict(
            tokens_input=args.tokens_input,
            tokens_output=args.tokens_output,
            tokens_total=args.tokens_total,
            cost_usd=args.cost_usd,
            tool_calls=getattr(args, "tool_calls", 0),
            model=getattr(args, "model", ""),
            session_id=getattr(args, "session_id", None),
        )
        print(svc.metrics_record_session(**kw))
        return True
    if sub == "log-usage":
        kw = dict(
            tokens_input=args.tokens_input,
            tokens_output=args.tokens_output,
            tokens_total=args.tokens_total,
            cost_usd=args.cost_usd,
            tool_calls=getattr(args, "tool_calls", 0),
            model=getattr(args, "model", ""),
            task_slug=getattr(args, "task_slug", None),
            session_id=getattr(args, "session_id", None),
        )
        print(svc.metrics_log_usage_event(**kw))
        return True
    if sub == "cost" or getattr(args, "cost", False):
        from project_cli_ops import _print_usage_cost_rollup

        _print_usage_cost_rollup(svc, getattr(args, "since", None), getattr(args, "until", None))
        return True
    if sub == "tokens":
        from service_token_metrics import print_cli

        print_cli(int(getattr(args, "last", 10) or 10), bool(getattr(args, "as_json", False)))
        return True
    return False


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
