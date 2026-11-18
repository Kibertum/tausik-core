"""Ensure a consumer `.gitignore` keeps generated TAUSIK trees out of git.

Bootstrap used to leave gitignore hygiene to the quickstart echo of `.tausik/`.
Agents then followed the outdated "track the profile folder" sentence and
force-added `.cursor/` / `.claude/` on every upgrade. This helper appends the
missing lines so a fresh or re-bootstrapped project refuses those paths by
default — including `.tausik-lib/` on consumers (export-only, #1057/#444).
The commit gate `harness_projection` still blocks a force-add.
"""

from __future__ import annotations

from pathlib import Path

_MARKER = "# TAUSIK — generated / runtime (do not commit)"


def _required_lines(project_dir: str) -> list[str]:
    try:
        from ide_utils import all_profile_dirs

        profiles = sorted(all_profile_dirs())
    except Exception:  # noqa: BLE001 — bootstrap must not depend on import order
        profiles = [".claude", ".cursor", ".codex", ".qwen", ".kilo", ".opencode", ".windsurf"]
    extra = [
        ".agents/",
        ".kilocode/",
        ".claude-project/",
        "opencode.json",
        ".mcp.json",
        ".cursorrules",
    ]
    # Framework trees belong in `.tausik-lib`, not the consumer index. Never
    # append them to the framework repository itself (it owns bootstrap/ and
    # harness/ as source). Consumer marker: `.tausik-lib` present.
    # Export-only contract (#1057 / #444): ignore the lib checkout itself on
    # day-0 so agents cannot stage the vendor tree before the first git add.
    lib = Path(project_dir) / ".tausik-lib"
    if lib.exists() or lib.is_symlink():
        # hooks ship via bootstrap into the (gitignored) IDE profile; staging
        # scripts/hooks/ beside .tausik-lib is the recurring framework dump.
        extra.extend([".tausik-lib/", "bootstrap/", "harness/", "scripts/hooks/"])
    lines = [".tausik/"]
    lines.extend(f"{p}/" if not p.endswith("/") else p for p in profiles)
    lines.extend(extra)
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def ensure_tausik_gitignore(project_dir: str) -> list[str]:
    """Append missing TAUSIK ignore rules. Returns the lines that were added."""
    path = Path(project_dir) / ".gitignore"
    existing = ""
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
    present = {
        ln.strip() for ln in existing.splitlines() if ln.strip() and not ln.strip().startswith("#")
    }
    missing = [ln for ln in _required_lines(project_dir) if ln not in present]
    if not missing:
        return []
    block = ["", _MARKER, *missing, ""]
    prefix = "" if (not existing or existing.endswith("\n")) else "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(prefix + "\n".join(block))
    return missing
