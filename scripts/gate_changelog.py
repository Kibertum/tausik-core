"""Continuous-CHANGELOG gate (QG-2) — changelog-continuous-gate.

Decision #161 / convention #275: every 1.8 task updates CHANGELOG.md and its
mirror CHANGELOG.ru.md at close. That discipline lived only as a line in each
task's acceptance_criteria — reviewable, but not mechanical. This gate makes it
mechanically un-skippable: at `task done`, git must show uncommitted changes in
EACH configured changelog file, or the close is blocked (fail-closed, by the
whole-tree-proof pattern of Decision #157 — a claim git cannot back never
closes a task).

MECHANISM GENERIC, POLICY CONFIGURED. TAUSIK is a framework other projects
bootstrap; hardcoding "both a Russian and English changelog must change" would
permanently block any project that keeps no changelog, or one language only.
So the requirement is read from config:

    config.task_done.changelog_gate = {
        "enabled": true,                              # default: false (opt-in)
        "files": ["CHANGELOG.md", "CHANGELOG.ru.md"]  # all must have a diff
    }

Disabled by default — a fresh project is not forced into a discipline it never
adopted. TAUSIK's own `.tausik/config.json` turns it on with both files.

Honest exceptions (docs, cleanup, measurement — a task that legitimately
changes no behaviour) close with `task done --no-changelog`, which logs an
explicit supervision-bypass event (no silent skip — l26-bypass-telemetry).
Fileless tasks (`--no-file-changes`) never reach this gate: `_run_quality_gates_report`
returns before it for that path, and a task that touched no files could carry
no changelog diff anyway.
"""

from __future__ import annotations

import os
from typing import Any

from gate_block import _block
from tausik_utils import cli_invocation

# Spelled for the reader's shell, resolved once per process: `.tausik/tausik`
# is not runnable in cmd.exe (which needs a backslash) and the backslash form
# is not runnable in Git Bash — a remediation line the reader cannot paste is
# not remediation. See tausik_utils.cli_invocation for the measured table.
_CLI = cli_invocation()

# Default changelog files when the gate is enabled without an explicit list.
# Mirrors TAUSIK's own bilingual convention so an enable-only config is useful
# out of the box; a project overrides `files` for a different layout.
_DEFAULT_CHANGELOG_FILES = ["CHANGELOG.md", "CHANGELOG.ru.md"]


def _read_changelog_gate_config(
    tausik_dir: str | None = None,
) -> tuple[bool, list[str], str | None]:
    """Return (enabled, files, config_error) for config.task_done.changelog_gate.

    `tausik_dir` selects WHOSE config is read. A gate holding a project handle
    must not resolve policy from the ambient cwd (memory #265, defect
    `mcp-config-read-paths`): an MCP server launched elsewhere would otherwise
    judge this project by another project's config.

    Three outcomes, deliberately distinct:

    * NOT CONFIGURED — no `changelog_gate` block, or the config layer has no
      `task_done` at all. The gate is opt-in; a project that never adopted it
      is not nagged. → (False, [], None)
    * CONFIGURED AND VALID → (enabled, files, None). `enabled` is type-checked,
      not truthy-coerced: a hand-edited JSON string `"false"` must not read as
      True (`bool("false")` is True), which would turn the gate ON against the
      author's intent and block every future `task done`.
    * CONFIGURED AND MALFORMED — the block exists but its shape is wrong (not
      an object, `enabled` not a boolean, `files` present but not a list of
      strings), or the config could not be loaded at all. This is the case the
      first cut got wrong: it fell open, justified by a `tausik doctor` check
      that does not exist, so a typo like `{"enable": true}` silently and
      permanently disabled a policy the project believes is enforced. A stated
      intent that cannot be read is UNKNOWN, not "off" → the error is returned
      and the caller fails closed (Decision #157).
    """
    try:
        from project_config import load_config

        td = load_config(tausik_dir).get("task_done", {})
    except Exception as e:  # noqa: BLE001 — unreadable config is unknown policy, not absent policy
        return (False, [], f"config could not be loaded ({type(e).__name__}: {e})")
    if td is None or (isinstance(td, dict) and "changelog_gate" not in td):
        return (False, [], None)  # never adopted — silence is correct
    if not isinstance(td, dict):
        return (False, [], "`task_done` is not an object")
    raw = td["changelog_gate"]
    if not isinstance(raw, dict):
        return (
            False,
            [],
            f"`task_done.changelog_gate` must be an object, got {type(raw).__name__}",
        )
    if "enabled" in raw and not isinstance(raw["enabled"], bool):
        return (
            False,
            [],
            f"`task_done.changelog_gate.enabled` must be true or false, got "
            f"{type(raw['enabled']).__name__} ({raw['enabled']!r})",
        )
    enabled = raw.get("enabled") is True
    files = list(_DEFAULT_CHANGELOG_FILES)
    if "files" in raw:
        files_raw = raw["files"]
        # A bare string here is the easy authoring slip. Substituting TAUSIK's
        # own bilingual default would upgrade a single-language project into
        # requiring a CHANGELOG.ru.md it will never write — a permanent block
        # from a typo. Say so instead.
        if not isinstance(files_raw, list) or not all(
            isinstance(f, str) and f.strip() for f in files_raw
        ):
            return (
                False,
                [],
                "`task_done.changelog_gate.files` must be a list of non-empty "
                f"file paths, got {type(files_raw).__name__} ({files_raw!r})",
            )
        if files_raw:
            files = [f.strip() for f in files_raw]
    return (enabled, files, None)


def enforce_changelog(
    svc: Any,
    report: dict[str, Any],
    slug: str,
    *,
    no_changelog: bool = False,
) -> None:
    """Block the close unless git shows a diff in every configured changelog
    file. No-op when the gate is disabled in config.

    `no_changelog` is the honest-exception escape: it skips the git check and
    records a countable supervision-bypass event with the reason, so the skip
    is never silent.
    """
    from project_root import root_from_service

    root = root_from_service(svc)
    tausik_dir_arg = None if root is None else os.path.join(root, ".tausik")
    enabled, files, config_error = _read_changelog_gate_config(tausik_dir_arg)
    if config_error:
        # The block exists but cannot be read. "Unknown policy" is not "no
        # policy": a project that wrote this block believes the discipline is
        # enforced, and a typo must not silently retire it.
        _block(
            report,
            "changelog",
            f"QG-2 continuous-changelog: task '{slug}' — the changelog-gate policy "
            f"in .tausik/config.json is unreadable: {config_error}. A policy that "
            f"cannot be read is unknown, not off — fail-closed (Decision #157). "
            f"Fix the `task_done.changelog_gate` block, or remove it entirely to "
            f"opt out of the gate.",
            'Repair `.tausik/config.json` → `"task_done": {"changelog_gate": '
            '{"enabled": true, "files": ["CHANGELOG.md"]}}` (or delete the block to opt out)',
        )
        return
    if not enabled:
        return  # opt-in policy, not configured for this project

    if no_changelog:
        # Explicit exception (docs / cleanup / measurement). Never silent:
        # leave a countable trace, symmetric to auto_verify's bypass event.
        # Best-effort — a telemetry write failure must not crash task_done.
        try:
            svc.be.event_add(
                "supervision",
                slug,
                "bypass_changelog_gate",
                "--no-changelog — task declares no changelog entry warranted "
                "(docs/cleanup/measurement); continuous-changelog gate skipped",
            )
        except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
            pass
        try:
            svc.be.task_append_notes(
                slug,
                "Changelog gate: skipped via --no-changelog (no behaviour "
                "change; exception logged).",
            )
        except Exception:  # noqa: BLE001 — best-effort note, never blocks
            pass
        return

    from verify_git_diff import _normalize_repo_path, files_with_substantive_additions

    if root is None:
        # Fail-closed, same reason as _enforce_no_file_changes: with no project
        # directory to scope git to, a cwd fallback would inspect whatever repo
        # the process stands in (mcp-config-read-paths, in a gate).
        _block(
            report,
            "changelog",
            f"QG-2 continuous-changelog: task '{slug}' — this service exposes no "
            f"project directory to scope the git check to. Cannot prove a "
            f"changelog entry exists — fail-closed.",
            f"{_CLI} task done {slug} --ac-verified --no-changelog  "
            f"(only if no changelog entry is warranted)",
        )
        return

    # CONTENT, not byte-dirtiness. `uncommitted_changes` would accept a file
    # made dirty by a single appended blank line — compliance theatre that
    # satisfies the gate and records "verified" while convention #275 (a real
    # entry, every task) goes unmet. The proof required is an added line with
    # characters on it.
    # Commits made DURING the task count too. The `/ship` skill commits at step
    # 7 and closes at step 8, so demanding an uncommitted diff would block the
    # framework's own canonical close path and leave `--no-changelog` as the
    # only way through — a rule whose sole passable route is its bypass trains
    # the bypass. Falls back to uncommitted-only when the task carries no
    # timestamp (stricter, never looser).
    since = None
    try:
        task = svc.be.task_get(slug) or {}
        since = task.get("started_at") or task.get("created_at")
    except Exception:  # noqa: BLE001 — no timestamp just narrows the window
        since = None
    substantive = files_with_substantive_additions(files, root=root, since=since)
    remediation = (
        f"Add an [Unreleased] entry to {' AND '.join(files)}, then re-run "
        f"`{_CLI} task done {slug} --ac-verified`. If this task warrants "
        f"no changelog entry (docs/cleanup/measurement), close with "
        f"`--no-changelog` instead."
    )
    if substantive is None:
        _block(
            report,
            "changelog",
            f"QG-2 continuous-changelog: task '{slug}' — git could not verify "
            f"changelog changes (not a repo, git missing, or the call failed). "
            f"An unprovable changelog state is 'unknown', not 'verified present' "
            f"— fail-closed. Fix git, or use --no-changelog if no entry is due.",
            remediation,
        )
        return

    written = {_normalize_repo_path(p) for p in substantive}
    missing = [f for f in files if _normalize_repo_path(f) not in written]
    if missing:
        _block(
            report,
            "changelog",
            f"QG-2 continuous-changelog: task '{slug}' closes without a changelog "
            f"entry in: {', '.join(missing)} (convention #275 — every task updates "
            f"{' + '.join(files)}). A whitespace-only edit does not count: the file "
            f"must gain a line with text on it. Add the entry, or close with "
            f"--no-changelog if this task warrants none (docs/cleanup/measurement).",
            remediation,
        )
        return
    # Every required file gained real text — the discipline holds.
    try:
        svc.be.task_append_notes(
            slug,
            f"Changelog gate: verified — git shows added changelog text in {', '.join(files)}.",
        )
    except Exception:  # noqa: BLE001 — best-effort note, never blocks
        pass
