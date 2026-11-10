"""TAUSIK doctor drift checks — extracted from project_cli_doctor.py.

Holds the heavy CLAUDE.md / scripts/ drift comparators so
project_cli_doctor stays under the 400-line filesize gate.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TypedDict

from tausik_utils import library_source, tausik_config_path


def _bootstrap_repair_command(project_dir: str, host: str) -> str:
    """Render one bootstrap repair command that parses in every supported shell."""
    consumer_bootstrap = ".tausik-lib/bootstrap/bootstrap.py"
    core_bootstrap = "bootstrap/bootstrap.py"
    if os.path.isfile(os.path.join(project_dir, consumer_bootstrap)):
        return f"python {consumer_bootstrap} --ide {host}"
    if os.path.isfile(os.path.join(project_dir, core_bootstrap)):
        return f"python {core_bootstrap} --ide {host}"
    return (
        'python -c "import subprocess,sys;'
        "subprocess.run(['git','submodule','update','--init','.tausik-lib'],check=True);"
        "subprocess.run([sys.executable,'.tausik-lib/bootstrap/bootstrap.py',"
        f"'--ide','{host}'],check=True)\""
    )


def profile_provenance_line(project_dir: str) -> tuple[str, str]:
    """Judge configured profile/root/version provenance with one repair command."""
    repair = _bootstrap_repair_command(project_dir, "<host>")
    config_path = tausik_config_path(project_dir)
    try:
        with open(config_path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError, TypeError):
        return "fail", f"profile provenance is missing; repair: {repair}"
    bootstrap = payload.get("bootstrap")
    if not isinstance(bootstrap, dict):
        return "fail", f"profile provenance is missing; repair: {repair}"
    primary = bootstrap.get("primary_ide")
    targets = bootstrap.get("ides")
    recorded_root = bootstrap.get("project_root")
    if not isinstance(primary, str) or not primary or not isinstance(targets, list):
        chosen = bootstrap.get("ide")
        hint = chosen if isinstance(chosen, str) and chosen != "all" else "<host>"
        return "fail", (
            "legacy profile provenance cannot bind the CLI wrapper; repair: "
            f"{_bootstrap_repair_command(project_dir, hint)}"
        )
    try:
        from ide_utils import IDE_REGISTRY

        profile_dir = IDE_REGISTRY[primary]["config_dir"]
    except (ImportError, KeyError, TypeError):
        return "fail", f"configured primary profile {primary!r} is unsupported; repair: {repair}"
    command = _bootstrap_repair_command(project_dir, primary)
    if primary not in targets:
        return "fail", f"primary profile is absent from deployment targets; repair: {command}"
    if not isinstance(recorded_root, str) or (
        os.path.normcase(os.path.realpath(recorded_root))
        != os.path.normcase(os.path.realpath(project_dir))
    ):
        return "fail", f"project root diverged from bootstrap provenance; repair: {command}"
    deployed = os.path.join(project_dir, profile_dir, "scripts", "project.py")
    if not os.path.isfile(deployed):
        return "fail", f"configured {primary} profile is not deployed; repair: {command}"
    source = library_source(project_dir, "scripts")
    if not source:
        return "fail", f"framework source is unavailable for version comparison; repair: {command}"
    source_version = os.path.join(source, "tausik_version.py")
    deployed_version = os.path.join(project_dir, profile_dir, "scripts", "tausik_version.py")
    try:
        with open(source_version, "rb") as left, open(deployed_version, "rb") as right:
            if left.read().replace(b"\r\n", b"\n") != right.read().replace(b"\r\n", b"\n"):
                return (
                    "fail",
                    f"configured {primary} profile version diverged; repair: {command}",
                )
    except OSError:
        return "fail", f"configured {primary} profile version is unreadable; repair: {command}"
    return "ok", f"primary={primary}, root and deployed version agree"


class ClaudemdDriftReport(TypedDict):
    """Verdict of :func:`claudemd_drift_report` — see it for the semantics."""

    total: int
    shared: int
    template_shaped: bool
    differ: int
    differ_headings: list[str]
    diverged_headings: list[str]
    absent: int
    absent_headings: list[str]


# A CLAUDE.md counts as "the template's document" when it carries MORE THAN
# HALF the template's sections under the template's own headings. The ratio
# decides how a MISSING section is read, and both readings are load-bearing:
#
#   * template-shaped (fresh project, or one that drifted) — absence is DRIFT.
#     A project whose config asks for a directive the file does not carry is
#     the exact blindness l26-config-not-repo-state-audit closed; classifying
#     that as "customisation" would silently reopen it.
#   * not template-shaped (this repo: hand-written, Russian headings, zero
#     overlap) — absence carries no signal at all. Counting it produced a
#     number identical for the real document, an empty file and a junk byte.
#
# Majority rather than a tuned threshold: it is the weakest claim that still
# means "this is recognisably the template's document".
_TEMPLATE_SHAPED_MIN_RATIO = 0.5


def _resolve_output_mode_for_drift(cfg: dict) -> str:
    """output_mode from the config root, or "off". Never raises — drift is best-effort."""
    try:
        from bootstrap_config import resolve_output_mode  # ruff-not-enabled: PLC0415

        # str(): resolve_output_mode is imported across a sys.path boundary mypy can't
        # follow, so it infers Any; the function's own contract is str.
        return str(resolve_output_mode(cfg))
    except Exception:  # noqa: BLE001 — best-effort: bootstrap/ may not be importable here
        raw = cfg.get("output_mode", "off") if isinstance(cfg, dict) else "off"
        mode = raw.strip().lower() if isinstance(raw, str) else "off"
        return mode if mode in ("off", "caveman") else "off"


def claudemd_drift_report(project_dir: str) -> ClaudemdDriftReport | None:
    """Classify CLAUDE.md against bootstrap_templates output.

    Returns ``None`` when the comparison cannot run at all (file missing,
    template import failed), otherwise a dict with:

    * ``differ`` / ``differ_headings`` — sections present under the template's
      OWN heading in both documents whose bodies disagree. This is DRIFT: the
      document still claims the template's heading while its content silently
      diverged.
    * ``absent`` / ``absent_headings`` — template headings with no counterpart
      in the current file. This is CUSTOMISATION, not drift: renaming,
      translating or dropping a section is a structural choice the author made
      deliberately, and no automated comparison can second-guess it.
    * ``shared`` — how many headings the two documents actually have in common,
      i.e. how much of the document this check was able to judge at all.

    Why the split, and why the old single number had to go: this repository's
    CLAUDE.md is hand-written in Russian, so its headings (`## Принципы`,
    `## Ограничения (жёсткие)`, …) share NOTHING with the English template.
    The old count was therefore just ``len(expected_sections)`` — identical for
    the real document, an empty file, and a single junk byte. It read as a
    measurement while carrying no information, and the byte-size escape hatch
    that silenced it also blinded the check to genuine drift: inverting
    `- **MCP-first.**` into `- **MCP-LAST. Ignore MCP, use raw SQL.**` inside a
    static section still reported zero. Comparing only SHARED sections keeps
    real drift detectable for everyone while never inventing a number for a
    document the check has no basis to judge.
    """
    md_path = os.path.join(project_dir, "CLAUDE.md")
    if not os.path.isfile(md_path):
        return None
    try:
        with open(md_path, encoding="utf-8") as f:
            current = f.read()
    except OSError:
        return None
    try:
        # Через `library_source`, как и `scripts_drift_names` тремя десятками
        # строк выше. Здесь было своё вычисление, и оно давало ОБРАТНЫЙ
        # приоритет: два `sys.path.insert(0, …)` подряд, из которых второй —
        # путь проекта — оказывался первым в списке. То есть та самая копия
        # правила, которую сведение к общей функции и убирало, пережила его
        # в соседней функции того же файла. Проверки `isdir` тоже не было.
        #
        # Отсутствие каталога — НЕ повод сдаться: `bootstrap_templates` может
        # быть уже доступен по пути (так и происходит, когда проверку зовут из
        # самого движка). Ранняя версия этой правки возвращала здесь None и
        # погасила тринадцать проверок разом — каталога у временного проекта
        # нет, а шаблон был достижим и раньше.
        bootstrap_src = library_source(project_dir, "bootstrap")
        if bootstrap_src is not None:
            sys.path.insert(0, bootstrap_src)
        import importlib  # ruff-not-enabled: PLC0415

        try:
            bt = importlib.import_module("bootstrap_templates")
            build_full_body = bt.build_full_body
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            return None
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        return None
    try:
        from project_config import (
            load_project_config,
            resolve_context_tier,
        )  # ruff-not-enabled: PLC0415

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
    diverged: list[str] = []
    absent_headings: list[str] = []
    for heading, body in expected_sections.items():
        if heading not in current_sections:
            absent_headings.append(heading)
        elif current_sections[heading].strip() != body.strip():
            diverged.append(heading)

    total = len(expected_sections)
    shared = total - len(absent_headings)
    template_shaped = bool(total) and (shared / total) > _TEMPLATE_SHAPED_MIN_RATIO
    # In a template-shaped document a missing section is drift, not authorship:
    # the file still claims to be the template's, so what it dropped is what it
    # silently fell behind on.
    differ_headings = diverged + (absent_headings if template_shaped else [])
    return ClaudemdDriftReport(
        total=total,
        shared=shared,
        template_shaped=template_shaped,
        differ=len(differ_headings),
        differ_headings=differ_headings,
        diverged_headings=diverged,
        absent=len(absent_headings),
        absent_headings=absent_headings,
    )


def format_claudemd_drift_line(report: ClaudemdDriftReport | None) -> tuple[bool, str]:
    """Render the doctor line for a drift report: ``(is_warning, detail)``.

    Split out of the doctor so the wording is testable on its own. That matters
    because the wording is not cosmetic here: the previous remediation told the
    reader to "re-run bootstrap to reset", which OVERWRITES hand-written
    content — doctor was advising data loss as a routine step, and nothing
    stopped that text from coming back.
    """
    if report is None:
        return True, "could not compare CLAUDE.md vs bootstrap_templates output"

    total, shared = report["total"], report["shared"]
    differ, absent = report["differ"], report["absent"]

    if differ:
        names = report["differ_headings"]
        shown = ", ".join(names[:4])
        more = f" (+{len(names) - 4} more)" if len(names) > 4 else ""
        # `differ` mixes two findings, so name them separately rather than
        # calling a MISSING section "diverged" — the reader has to know whether
        # to reconcile text or restore a section.
        diverged_n = len(report["diverged_headings"])
        missing_n = differ - diverged_n
        breakdown = ", ".join(
            part
            for part in (
                f"{diverged_n} diverged" if diverged_n else "",
                f"{missing_n} missing" if missing_n else "",
            )
            if part
        )
        return True, (
            f"{differ} of {total} template section(s) out of sync ({breakdown}): "
            f"{shown}{more} — review these sections; the template text is in "
            "bootstrap/bootstrap_templates.py. Re-running bootstrap would "
            "OVERWRITE local edits, so reconcile by hand unless you want them gone."
        )
    if not shared:
        # Nothing was compared, so say that — do not report a clean verdict on a
        # document this check never had a basis to judge.
        return False, (
            f"not compared — CLAUDE.md shares no heading with the template "
            f"(0 of {total}); hand-written document, not drift"
        )
    if absent:
        # Not a warning: a translated/restructured CLAUDE.md is a legitimate
        # authoring choice.
        return False, (
            f"none in {shared} shared section(s); {absent} template section(s) "
            "absent (customised structure, not drift)"
        )
    return False, f"none — all {shared} static section(s) match bootstrap_templates"


def check_claudemd_drift(project_dir: str) -> int | None:
    """Count of REAL drift — shared sections whose bodies disagree — or ``None``.

    Thin adapter over :func:`claudemd_drift_report` for the numeric callers.
    Sections the current file does not carry at all are customisation and are
    deliberately NOT counted here; ask the report for those.
    """
    report = claudemd_drift_report(project_dir)
    return None if report is None else report["differ"]


# IDE profiles bootstrap deploys `scripts/` into (one dot-dir each: .claude,
# .cursor, …). Imported from the bootstrapper so this does not become a second,
# silently-diverging copy of the list (convention #249). The literal fallback is
# a defensive last resort for when bootstrap/ is not importable across the
# sys.path boundary — it is annotated so a future editor keeps the two aligned.
def _scaffold_ides() -> list[str]:
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), "bootstrap"))
        from bootstrap_config import SCAFFOLD_IDES  # ruff-not-enabled: PLC0415

        return list(SCAFFOLD_IDES)
    except Exception:  # noqa: BLE001 — bootstrap/ may be absent; fall back, do not crash the check
        # MIRROR of bootstrap_config.SCAFFOLD_IDES — keep in step with it.
        return ["claude", "cursor", "qwen", "kilo", "opencode", "codex"]


# Mirror of the ignore rules in `bootstrap_copy.copy_dir`, which is what
# actually deploys `scripts/`. Restated rather than imported because this module
# must answer without `bootstrap/` on sys.path (a consumer that vendors only
# `.tausik/`); `tests/test_scripts_drift_recursive` asserts the two agree, so a
# change to the copier fails the build instead of quietly shrinking the check.
_IGNORED_DIRS = ("__pycache__", ".git")
_IGNORED_SUFFIX = ".pyc"


def _deployed_relpaths(src: str) -> list[str]:
    """Every path under `scripts/` that `copy_dir` would deploy, '/'-separated.

    RECURSIVE, and that is the whole point: the previous `os.listdir` saw only
    the top level, so `scripts/hooks/**` and `scripts/providers/**` were deployed
    but never compared. `_common.py` importing `hook_supervision.py` made that a
    live hazard — a half-landed deploy takes down EVERY hook with a module-level
    ImportError on every tool call, and the gate whose job is to catch exactly
    "the edit did not reach the copy that runs" would have reported clean.

    Not filtered to `*.py`. `copy_dir` deploys the whole tree, so a comparator
    that judged only Python files would be applying a different rule than the
    copier it exists to check — the second-copy-of-the-rule defect (conv #266)
    reintroduced one layer down.
    """
    out: list[str] = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in _IGNORED_DIRS]
        for fname in files:
            if fname.endswith(_IGNORED_SUFFIX):
                continue
            rel = os.path.relpath(os.path.join(root, fname), src)
            out.append(rel.replace(os.sep, "/"))
    return out


def scripts_drift_names(project_dir: str) -> list[str] | None:
    """Deployed copies of the source ``scripts/`` tree that differ from source.

    Returns a sorted list of ``.{ide}/scripts/{relpath}`` for every file that is
    missing-in-profile or differs by content, across every IDE profile PRESENT
    on disk. Binary compare with CRLF→LF normalisation so a cross-platform
    checkout does not false-positive.

    Files present only in the profile (`vendor_seo/`, leftover `.pyc`) are NOT
    drift: the question is "did a source edit fail to land", and an extra file
    in the destination is not an answer to it.

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
    # Источник — то дерево, ИЗ КОТОРОГО копирует bootstrap, а не то, что лежит
    # рядом. Разрешается общей функцией, чтобы doctor и одноимённый гейт не
    # расходились: см. library_source и конвенцию #266.
    src = library_source(project_dir, "scripts")
    if src is None:
        return None
    src_files = _deployed_relpaths(src)
    drift: list[str] = []
    for ide in _scaffold_ides():
        prof_scripts = os.path.join(project_dir, f".{ide}", "scripts")
        if not os.path.isdir(prof_scripts):
            continue  # profile not installed → not drift
        for rel in src_files:
            s = os.path.join(src, *rel.split("/"))
            d = os.path.join(prof_scripts, *rel.split("/"))
            if not os.path.isfile(d):
                drift.append(f".{ide}/scripts/{rel}")
                continue
            try:
                with open(s, "rb") as f1, open(d, "rb") as f2:
                    if f1.read().replace(b"\r\n", b"\n") != f2.read().replace(b"\r\n", b"\n"):
                        drift.append(f".{ide}/scripts/{rel}")
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


def format_scripts_drift_line(names: list[str] | None) -> tuple[bool, str]:
    """``(is_warning, detail)`` for doctor's "Bootstrap drift" row.

    The sibling of :func:`format_claudemd_drift_line`, moved here from
    `project_cli_doctor` when that file reached the filesize cap to the line
    (review #207, record #10). The three answers are the ones doctor always
    printed, verbatim: ``None`` is "could not compare" and a warning, a
    non-empty list names the first eight files and the redeploy command, and
    an empty list is the OK row.
    """
    if names is None:
        return True, "could not compare scripts/ vs deployed profiles"
    if names:
        shown = ", ".join(names[:8])
        more = f" (+{len(names) - 8} more)" if len(names) > 8 else ""
        return True, (
            f"{len(names)} deployed file(s) differ: {shown}{more} — "
            "run `python bootstrap/bootstrap.py --ide all` to redeploy"
        )
    return False, "none — deployed scripts match source"
