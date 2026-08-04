"""Bootstrap drift check — does the deployed profile still match source?

bootstrap-drift-harness-tree-ungated. The scripts/ tree is laid out one-to-one
(`scripts/foo.py` → `.{ide}/scripts/foo.py`), so a name-based comparator suffices
for it (service_doctor_drift.scripts_drift_names). The harness/ tree is NOT: bootstrap
fans `harness/{ide}/mcp/*` into `.{ide}/mcp/`, `harness/claude/subagents/*` into
`.{ide}/agents/`, and so on. Reproducing that fan-out as a second comparator is
exactly the silently-diverging copy convention #249 warns against.

So this module makes bootstrap's OWN copy functions the oracle for the harness
fan-out: it scaffolds those copy-only trees into a throwaway temp directory with
the same `copy_*` calls `bootstrap_ide` uses, then byte-compares that temp against
the installed profile. One formula, and it can never disagree with the real layout
because it IS the real layout run into a different destination.

Scoped to the harness fan-out trees, which are plain copies and config-
independent: mcp, roles, subagents, aidd-templates. Excluded, and why:
  * scripts/ is laid out one-to-one, so the fast name-based
    service_doctor_drift.scripts_drift_names already covers it — re-scaffolding
    238 files per profile here just to re-derive the same answer made the check
    take seconds. The gate runs BOTH comparators.
  * GENERATED files (settings.json, CLAUDE.md, .mcp.json, .cursorrules, …) are
    not copies of source at all — comparing them to source is meaningless, and
    they are never scaffolded here, so they raise no false positive.
  * skills/ runs stub generation + orphan rmtree keyed on config; stacks/ and
    references/ are config- or size-heavy. Their drift is real but out of this
    task's scope; the gate message names the boundary rather than hiding it.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from bootstrap_config import IDE_DIRS, SCAFFOLD_IDES
from bootstrap_copy import (
    copy_aidd_templates,
    copy_mcp,
    copy_roles,
    copy_subagents,
)

_IGNORED_PARTS = {"__pycache__", ".git"}


def _files_equal(a: str, b: str) -> bool:
    """Byte compare with CRLF→LF normalisation (a cross-platform checkout must
    not false-positive), mirroring service_doctor_drift.scripts_drift_names."""
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read().replace(b"\r\n", b"\n") == fb.read().replace(b"\r\n", b"\n")
    except OSError:
        return False


def _scaffold_copy_trees(lib_dir: str, tmp_target: str, ide: str) -> None:
    """Run bootstrap's harness copy-layout into a throwaway target. Same calls as
    bootstrap_ide, minus every generator, minus scripts/ (covered fast elsewhere)
    and minus the config-dependent trees (skills/stacks/references)."""
    copy_mcp(lib_dir, tmp_target, ide)
    copy_roles(lib_dir, tmp_target, ide)
    copy_subagents(lib_dir, tmp_target, ide)
    copy_aidd_templates(lib_dir, tmp_target)


def _drift_for_ide(lib_dir: str, project_dir: str, ide: str) -> list[str]:
    """Deployed files of ONE installed profile that differ from a fresh scaffold.

    Returns `.{ide}/{rel}` for every scaffolded file missing-in-profile or
    differing by content. An absent profile yields `[]` (nothing deployed to
    fall behind — a fresh clone / CI has profiles gitignored, and demanding one
    is the first gate an operator disables). Orphans (files in the profile but
    not the scaffold) are deliberately NOT flagged: they are stale extras such
    as compiled `.pyc`, not a source edit that failed to land.
    """
    installed = os.path.join(project_dir, IDE_DIRS[ide])
    if not os.path.isdir(installed):
        return []
    tmp_target = tempfile.mkdtemp(prefix=f"tausik-drift-{ide}-")
    drift: list[str] = []
    try:
        _scaffold_copy_trees(lib_dir, tmp_target, ide)
        for root, dirs, files in os.walk(tmp_target):
            dirs[:] = [d for d in dirs if d not in _IGNORED_PARTS]
            for fname in files:
                if fname.endswith(".pyc"):
                    continue
                src = os.path.join(root, fname)
                rel = os.path.relpath(src, tmp_target)
                if any(part in _IGNORED_PARTS for part in rel.split(os.sep)):
                    continue
                deployed = os.path.join(installed, rel)
                if not os.path.isfile(deployed) or not _files_equal(src, deployed):
                    drift.append(f"{IDE_DIRS[ide]}/{rel.replace(os.sep, '/')}")
    finally:
        # Guaranteed cleanup even if a copy_* raised — a check must not leave
        # temp trees behind on every task-done.
        shutil.rmtree(tmp_target, ignore_errors=True)
    return sorted(drift)


def check_deployed_trees(
    lib_dir: str, project_dir: str, ides: list[str] | None = None
) -> list[str]:
    """Scaffold the copy-only trees and report every deployed file that drifts.

    Reuses bootstrap's real `copy_*` functions as the layout oracle (one
    formula). Only profiles present on disk are checked; absent ones are skipped
    (inert on a fresh clone / CI). Returns a sorted, de-duplicated list of
    `.{ide}/{rel}` drift paths across all checked profiles — empty when clean.
    """
    if not os.path.isdir(os.path.join(lib_dir, "harness")):
        # No harness source tree to scaffold from — nothing to compare. Callers
        # read [] as "clean" (matching scripts_drift_names' skip-when-absent).
        return []
    targets = ides if ides is not None else list(SCAFFOLD_IDES)
    seen: set[str] = set()
    out: list[str] = []
    for ide in targets:
        if ide not in IDE_DIRS:
            continue
        for path in _drift_for_ide(lib_dir, project_dir, ide):
            if path not in seen:
                seen.add(path)
                out.append(path)
    return sorted(out)
