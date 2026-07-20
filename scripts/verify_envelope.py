"""Wall-clock bound around the whole gate cycle (v14-verify-pipeline-envelope-timeout).

Extracted from `verify_cached_run.py` when that file crossed the 400-line
filesize gate. The cut follows a responsibility boundary rather than
convenience: everything here answers "run this with a time limit and fail
legibly if it overruns", and none of it knows anything about the verify cache,
declared scope or `verification_runs`. `verify_cached_run` re-exports the
public names, so `service_verification` and existing tests keep importing them
unchanged.

The bound covers the ENTIRE `run_gates` cycle, not each gate. Its purpose is
not to make gates fast — it is to keep a misconfigured or hanging gate from
making `task done` look like the agent froze, which on an interactive MCP host
is indistinguishable from a crash and provokes exactly the wrong recovery.
"""

from __future__ import annotations

from typing import Any, Callable

# Default 60s suits interactive MCP hosts; CI can disable the envelope entirely
# with `verify_pipeline_timeout_seconds=0`, where one long step is fine.
DEFAULT_PIPELINE_TIMEOUT_S = 60


class GateEnvelopeTimeoutError(RuntimeError):
    """Raised when `run_gates` exceeds the verify pipeline envelope timeout.

    Surfaces a remediation hint (raise the limit, opt into auto_verify, or
    narrow `relevant_files`) so an interactive agent can recover deliberately
    instead of guessing whether the host hung.
    """


def resolve_pipeline_timeout_s(cfg: dict | None) -> int:
    """Resolve `verify_pipeline_timeout_seconds` from config.

    Returns the configured value when ≥0; `DEFAULT_PIPELINE_TIMEOUT_S` when
    missing or invalid; `0` is a valid disable-sentinel and is preserved.
    """
    if not isinstance(cfg, dict):
        return DEFAULT_PIPELINE_TIMEOUT_S
    raw = cfg.get("verify_pipeline_timeout_seconds", DEFAULT_PIPELINE_TIMEOUT_S)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PIPELINE_TIMEOUT_S
    return max(0, v)


def resolve_envelope_from_config() -> int:
    """The configured envelope, falling back to the default if config is unreadable."""
    try:
        from project_config import load_config

        return resolve_pipeline_timeout_s(load_config())
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return DEFAULT_PIPELINE_TIMEOUT_S


def run_within_envelope(
    run_gates: Callable[..., tuple[bool, list[dict[str, Any]]]],
    trigger: str,
    relevant_files: list[str] | None,
    *,
    progress_fn: Callable[[dict[str, Any]], None] | None = None,
    envelope_s: int | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Call `run_gates` under a wall-clock bound. Returns its (passed, results).

    `run_gates` is passed IN rather than imported here, so the caller keeps
    control of when that import happens: the suite patches it — sometimes by
    swapping the whole `gate_runner` module — and importing it in this module
    would bind the name at a different moment and quietly miss the patch
    (memory #243).

    An `envelope_s` of 0 or less disables the bound and calls straight through.
    Any exception raised inside the gate cycle propagates unchanged; only an
    actual overrun becomes `GateEnvelopeTimeoutError`.
    """
    if envelope_s is None:
        envelope_s = resolve_envelope_from_config()
    if envelope_s <= 0:
        return run_gates(trigger, relevant_files, progress_callback=progress_fn)

    # daemon thread + join(timeout): ThreadPoolExecutor.__exit__ waits for
    # in-flight workers, which would block the abort path. A daemon thread
    # leaves the lingering subprocess unwound at interpreter exit instead.
    import threading

    result: dict[str, Any] = {}
    exc: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["v"] = run_gates(trigger, relevant_files, progress_callback=progress_fn)
        except BaseException as e:  # noqa: BLE001 — re-raised on the calling thread below
            exc["e"] = e

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(envelope_s)
    if t.is_alive():
        raise GateEnvelopeTimeoutError(
            f"verify pipeline exceeded {envelope_s}s envelope timeout. "
            "Options: raise `verify_pipeline_timeout_seconds` in "
            ".tausik/config.json, set `task_done.auto_verify=true` "
            "to run gates inline (legacy), or narrow `relevant_files` "
            "to reduce gate fan-out."
        )
    if "e" in exc:
        raise exc["e"]
    return result["v"]
