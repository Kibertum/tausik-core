"""TAUSIK doctor drift checks — extracted from project_cli_doctor.py.

Holds the heavy CLAUDE.md / scripts/ drift comparators (and the
trimmed-baseline detector) so project_cli_doctor stays under the
400-line filesize gate. Pure re-org — no semantic changes.
"""

from __future__ import annotations

import os
import sys

_TRIMMED_BASELINE_MAX_BYTES = 6144  # v1.4-polish trim target was 4KB; allow headroom


def is_trimmed_baseline(text: str, size_bytes: int) -> bool:
    """True when CLAUDE.md is the v1.4-polish trimmed baseline.

    The trim (T2.2 / commit 43c56cb) cut detail to a `## Reference` section
    pointing to docs/{ru,en}/agent-contract.md. Honour that as a canonical
    user-accepted state instead of warning every doctor run. Two cheap
    signals together: file <6KB AND `## Reference` body links to
    agent-contract.md. Both required to avoid mis-classifying a
    larger/different customisation.
    """
    if size_bytes > _TRIMMED_BASELINE_MAX_BYTES:
        return False
    import re as _re

    m = _re.search(
        r"^## Reference\s*\n(.+?)(?=^## |\Z)",
        text,
        flags=_re.IGNORECASE | _re.MULTILINE | _re.DOTALL,
    )
    if not m:
        return False
    body = m.group(1)
    return bool(_re.search(r"docs/(?:ru|en)/agent-contract\.md", body))


def _resolve_output_mode_for_drift(cfg: dict) -> str:
    """output_mode from the config root, or "off". Never raises — drift is best-effort."""
    try:
        from bootstrap_config import resolve_output_mode  # noqa: PLC0415

        # str(): resolve_output_mode is imported across a sys.path boundary mypy can't
        # follow, so it infers Any; the function's own contract is str.
        return str(resolve_output_mode(cfg))
    except Exception:  # noqa: BLE001 — best-effort: bootstrap/ may not be importable here
        raw = cfg.get("output_mode", "off") if isinstance(cfg, dict) else "off"
        mode = raw.strip().lower() if isinstance(raw, str) else "off"
        return mode if mode in ("off", "caveman") else "off"


def check_claudemd_drift(project_dir: str) -> int | None:
    """Compare static CLAUDE.md sections against bootstrap_templates output.

    Returns the number of sections that differ, 0 when current is the
    v1.4-polish trimmed baseline, or None when comparison is impossible
    (file missing, template import failed). DYNAMIC + user-customised
    tail sections are skipped.
    """
    md_path = os.path.join(project_dir, "CLAUDE.md")
    if not os.path.isfile(md_path):
        return None
    try:
        size_bytes = os.path.getsize(md_path)
    except OSError:
        size_bytes = -1
    try:
        with open(md_path, encoding="utf-8") as f:
            current = f.read()
    except OSError:
        return None
    if is_trimmed_baseline(current, size_bytes if size_bytes >= 0 else len(current.encode())):
        return 0
    try:
        sys.path.insert(0, os.path.join(project_dir, ".tausik-lib", "bootstrap"))
        sys.path.insert(0, os.path.join(project_dir, "bootstrap"))
        import importlib  # noqa: PLC0415

        try:
            bt = importlib.import_module("bootstrap_templates")
            build_full_body = bt.build_full_body
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            return None
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        return None
    try:
        from project_config import load_project_config, resolve_context_tier  # noqa: PLC0415

        # l26-config-not-repo-state-audit: read the RAW project tier, not the
        # merged load_config(). This check's subject is "does the tracked
        # CLAUDE.md match the config it was generated from" — and the generator
        # (bootstrap load_bootstrap_config) reads the raw .tausik/config.json,
        # never the user/managed tiers. Judging with the merged config made an
        # org-wide managed key (e.g. output_mode) silently change "expected", so
        # the same commit drifted on one machine and not another. Mirror the
        # producer (oracle rule): same raw file, scoped to THIS project's dir
        # rather than the ambient cwd.
        cfg = load_project_config(os.path.join(project_dir, ".tausik")) or {}
        project_name = cfg.get("project_name") or os.path.basename(project_dir)
        stacks = cfg.get("stacks") or []
        tier = resolve_context_tier(cfg)
        # output_mode must be rendered into `expected` too, or this check is blind to the
        # whole feature: with it hardcoded off, a CLAUDE.md that is MISSING the directive
        # the config asked for looks perfectly correct to the only automated check we have.
        mode = _resolve_output_mode_for_drift(cfg)
        expected = build_full_body(
            project_name,
            stacks,
            "an AI agent (Claude Code)",
            ".claude",
            ide="claude",
            context_tier=tier,
            output_mode=mode,
        )
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        return None

    import re as _re

    def _split(text: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        parts = _re.split(r"^(## [^\n]+)$", text, flags=_re.MULTILINE)
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            lower_h = heading.lower()
            if lower_h.startswith("## project:"):
                continue
            if "DYNAMIC:START" in body or lower_h.startswith("## current state"):
                continue
            sections[heading] = body.strip()
        return sections

    expected_sections = _split(expected)
    current_sections = _split(current)
    differ = 0
    for heading, body in expected_sections.items():
        if current_sections.get(heading, "").strip() != body.strip():
            differ += 1
    return differ


# IDE profiles bootstrap deploys `scripts/` into (one dot-dir each: .claude,
# .cursor, …). Imported from the bootstrapper so this does not become a second,
# silently-diverging copy of the list (convention #249). The literal fallback is
# a defensive last resort for when bootstrap/ is not importable across the
# sys.path boundary — it is annotated so a future editor keeps the two aligned.
def _scaffold_ides() -> list[str]:
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), "bootstrap"))
        from bootstrap_config import SCAFFOLD_IDES  # noqa: PLC0415

        return list(SCAFFOLD_IDES)
    except Exception:  # noqa: BLE001 — bootstrap/ may be absent; fall back, do not crash the check
        # MIRROR of bootstrap_config.SCAFFOLD_IDES — keep in step with it.
        return ["claude", "cursor", "qwen", "kilo", "opencode"]


def scripts_drift_names(project_dir: str) -> list[str] | None:
    """Names of source ``scripts/*.py`` that differ from their DEPLOYED copies.

    Returns a sorted list of ``.{ide}/scripts/{name}`` for every file that is
    missing-in-profile or differs by content, across every IDE profile PRESENT
    on disk. Binary compare with CRLF→LF normalisation so a cross-platform
    checkout does not false-positive.

    Two distinct empties, because callers act on them differently:
      * ``None`` — the source ``scripts/`` dir is missing, so nothing can be
        compared (a broken checkout, not a clean one).
      * ``[]`` — comparison ran and found no drift. This INCLUDES the case where
        no profile is present at all: a fresh clone or CI has the profiles
        gitignored, and "no deployed copy to fall behind" is clean, not drift.
        A gate MUST pass here — demanding a profile that need not exist is the
        first gate an operator disables.

    Why all present profiles and not just ``.claude``: the defect is "a source
    edit did not reach the copy that actually runs", and any installed IDE
    profile is such a copy. An absent profile is skipped; a present one is
    mandatory.
    """
    src = os.path.join(project_dir, "scripts")
    if not os.path.isdir(src):
        return None
    src_files = [n for n in os.listdir(src) if n.endswith(".py")]
    drift: list[str] = []
    for ide in _scaffold_ides():
        prof_scripts = os.path.join(project_dir, f".{ide}", "scripts")
        if not os.path.isdir(prof_scripts):
            continue  # profile not installed → not drift
        for name in src_files:
            s = os.path.join(src, name)
            d = os.path.join(prof_scripts, name)
            if not os.path.isfile(d):
                drift.append(f".{ide}/scripts/{name}")
                continue
            try:
                with open(s, "rb") as f1, open(d, "rb") as f2:
                    if f1.read().replace(b"\r\n", b"\n") != f2.read().replace(b"\r\n", b"\n"):
                        drift.append(f".{ide}/scripts/{name}")
            except OSError:
                pass
    return sorted(drift)


def check_scripts_drift(project_dir: str) -> int | None:
    """Count of deployed ``scripts/`` files that drift from source, or ``None``.

    Thin adapter over :func:`scripts_drift_names` — kept so the numeric-count
    callers (doctor's summary line) do not need surgery. ``None`` propagates the
    "cannot compare" signal; an empty drift list is ``0``.
    """
    names = scripts_drift_names(project_dir)
    return None if names is None else len(names)
