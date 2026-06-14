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
        from project_config import load_config, resolve_context_tier  # noqa: PLC0415

        cfg = load_config() or {}
        project_name = cfg.get("project_name") or os.path.basename(project_dir)
        stacks = cfg.get("stacks") or []
        tier = resolve_context_tier(cfg)
        expected = build_full_body(
            project_name,
            stacks,
            "an AI agent (Claude Code)",
            ".claude",
            ide="claude",
            context_tier=tier,
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


def check_scripts_drift(project_dir: str) -> int | None:
    """Compare deployed .claude/scripts/ against scripts/ source dir.

    Counts missing-in-dst as drift; binary compare with line-ending
    normalisation (CRLF→LF) so cross-platform deploys don't false-positive.
    """
    src = os.path.join(project_dir, "scripts")
    dst = os.path.join(project_dir, ".claude", "scripts")
    if not os.path.isdir(src) or not os.path.isdir(dst):
        return None
    differ = 0
    for name in os.listdir(src):
        if not name.endswith(".py"):
            continue
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if not os.path.isfile(d):
            differ += 1
            continue
        try:
            with open(s, "rb") as f1, open(d, "rb") as f2:
                if f1.read().replace(b"\r\n", b"\n") != f2.read().replace(b"\r\n", b"\n"):
                    differ += 1
        except OSError:
            pass
    return differ
