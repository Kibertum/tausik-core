"""`tausik aidd autogen` — draft vision.md seeded from repo signals.

Gathers machine-extractable facts about the current repo (package
name/description, README title/intro, top-level source dirs, detected
languages, test framework) and injects them as an auto-detected facts
block into the AIDD vision.md template. Stdlib-only, no LLM call. A
missing signal degrades to a placeholder; the command never crashes.
"""

from __future__ import annotations

import json
import os
import sys

from project_cli_aidd import _read, find_templates_dir, write_file_with_conflict

try:  # tomllib is stdlib on Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - project pins 3.11+
    tomllib = None  # type: ignore[assignment]

_PLACEHOLDER = "_(not detected — fill in manually)_"

# Directories never treated as project source dirs / never walked for languages.
_DENY_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".tausik",
        ".claude",
        ".idea",
        ".vscode",
        "site-packages",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "target",
        "coverage",
        "htmlcov",
        ".tox",
        ".eggs",
        "vendor",
    }
)

# Code file extension → language label. Non-code extensions are ignored.
_EXT_LANG: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".sh": "Shell",
    ".sql": "SQL",
    ".scala": "Scala",
}

_JS_TEST_FRAMEWORKS: tuple[str, ...] = ("jest", "vitest", "mocha", "ava", "jasmine")


def _detect_package_meta(root: str) -> tuple[str | None, str | None]:
    """Return (name, description) from pyproject.toml or package.json."""
    name: str | None = None
    description: str | None = None
    pyproject = os.path.join(root, "pyproject.toml")
    if tomllib is not None and os.path.isfile(pyproject):
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            proj = data.get("project", {}) or {}
            name = proj.get("name") or name
            description = proj.get("description") or description
        except (OSError, tomllib.TOMLDecodeError, AttributeError):
            pass
    if name and description:
        return name, description
    pkg = os.path.join(root, "package.json")
    if os.path.isfile(pkg):
        try:
            with open(pkg, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                name = name or data.get("name")
                description = description or data.get("description")
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    return name, description


def _parse_readme(text: str) -> tuple[str | None, str | None]:
    """Extract first heading title and first prose paragraph from README text."""
    title: str | None = None
    para: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if title is None:
            if line.startswith("#"):
                title = line.lstrip("#").strip() or None
            continue
        if not line:
            if para:
                break
            continue
        if line.startswith(("#", "![", ">", "|", "---", "===", "<")):
            if para:
                break
            continue
        para.append(line)
    return title, (" ".join(para).strip() or None)


def _detect_readme(root: str) -> tuple[str | None, str | None]:
    """Return (title, first_paragraph) from a README file, else (None, None)."""
    for cand in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        path = os.path.join(root, cand)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    return _parse_readme(f.read())
            except OSError:
                return None, None
    return None, None


def _detect_top_dirs(root: str) -> list[str]:
    """Top-level directories that look like source dirs (deny-list filtered)."""
    try:
        entries = os.listdir(root)
    except OSError:
        return []
    dirs = [
        name
        for name in entries
        if not name.startswith(".")
        and name not in _DENY_DIRS
        and os.path.isdir(os.path.join(root, name))
    ]
    return sorted(dirs)


def _detect_languages(root: str, max_files: int = 4000) -> list[str]:
    """Languages present, ordered by file count (bounded walk)."""
    counts: dict[str, int] = {}
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in _DENY_DIRS]
        for fn in filenames:
            lang = _EXT_LANG.get(os.path.splitext(fn)[1].lower())
            if not lang:
                continue  # non-code files don't consume the budget (review fix)
            seen += 1
            if seen > max_files:
                break
            counts[lang] = counts.get(lang, 0) + 1
        if seen > max_files:
            break
    return [lang for lang, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def _pyproject_has_pytest(data: dict) -> bool:
    """True if pyproject declares pytest as a tool or a dependency.

    Precise navigation avoids false matches on a project/description merely
    containing the substring 'pytest'.
    """
    if "pytest" in (data.get("tool") or {}):
        return True
    project = data.get("project") or {}
    deps = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        deps.extend(group or [])
    return any(str(d).lower().startswith("pytest") for d in deps)


def _detect_test_framework(root: str) -> str | None:
    """Best-effort test framework detection; None when undetermined."""
    pyproject = os.path.join(root, "pyproject.toml")
    if tomllib is not None and os.path.isfile(pyproject):
        try:
            with open(pyproject, "rb") as fb:
                data = tomllib.load(fb)
            if _pyproject_has_pytest(data):
                return "pytest"
        except (OSError, tomllib.TOMLDecodeError, TypeError):
            pass
    for req in ("requirements.txt", "requirements-dev.txt", "setup.cfg", "tox.ini"):
        path = os.path.join(root, req)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as ft:
                    if "pytest" in ft.read().lower():
                        return "pytest"
            except OSError:
                pass
    pkg = os.path.join(root, "package.json")
    if os.path.isfile(pkg):
        try:
            with open(pkg, "r", encoding="utf-8") as fj:
                data = json.load(fj)
            deps = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
            for fw in _JS_TEST_FRAMEWORKS:
                if fw in deps:
                    return fw
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    tests_dir = os.path.join(root, "tests")
    if os.path.isdir(tests_dir):
        try:
            if any(f.startswith("test_") and f.endswith(".py") for f in os.listdir(tests_dir)):
                return "pytest"
        except OSError:
            pass
    return None


def gather_signals(root: str) -> dict:
    """Collect all repo signals into a dict. Never raises on a missing source."""
    name, description = _detect_package_meta(root)
    readme_title, readme_para = _detect_readme(root)
    return {
        "name": name or readme_title,
        "description": description or readme_para,
        "top_dirs": _detect_top_dirs(root),
        "languages": _detect_languages(root),
        "test_framework": _detect_test_framework(root),
    }


def _sanitize(text: str) -> str:
    """Flatten newlines/CR so a repo signal can't inject Markdown structure
    (headings, list items) into the generated vision.md (v15p review)."""
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def _fmt(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(_sanitize(v) for v in value) if value else _PLACEHOLDER
    if value is None or value == "":
        return _PLACEHOLDER
    return _sanitize(str(value))


def _render_facts_block(signals: dict) -> str:
    return "\n".join(
        [
            "## Project facts (auto-detected)",
            "",
            "> Generated by `tausik aidd autogen` from repo signals — review and edit.",
            "",
            f"- **Name:** {_fmt(signals.get('name'))}",
            f"- **Description:** {_fmt(signals.get('description'))}",
            f"- **Top-level source dirs:** {_fmt(signals.get('top_dirs'))}",
            f"- **Languages:** {_fmt(signals.get('languages'))}",
            f"- **Test framework:** {_fmt(signals.get('test_framework'))}",
        ]
    )


def render_vision(template_text: str, signals: dict) -> str:
    """Inject the auto-detected facts block before the first ## section."""
    facts = _render_facts_block(signals)
    idx = template_text.find("\n## ")
    if idx == -1:
        return template_text.rstrip("\n") + "\n\n" + facts + "\n"
    head = template_text[:idx].rstrip("\n")
    rest = template_text[idx + 1 :]  # keep the "## ..." heading
    return head + "\n\n" + facts + "\n\n" + rest


def cmd_aidd_autogen(
    *,
    write: bool = False,
    force: bool = False,
    root: str | None = None,
    prompt=None,
    log=None,
) -> int:
    """CLI entry for `tausik aidd autogen`. Returns a POSIX exit code."""
    out_log = log or (lambda msg: print(msg))
    root = root or os.getcwd()
    src_dir = find_templates_dir()
    if src_dir is None:
        print("Error: AIDD templates not found in harness/aidd-templates", file=sys.stderr)
        return 1
    try:
        template_text = _read(os.path.join(src_dir, "vision.md"))
    except OSError as e:
        print(f"Error: cannot read vision.md template: {e}", file=sys.stderr)
        return 1
    content = render_vision(template_text, gather_signals(root))
    if not write:
        print(content)
        return 0
    write_file_with_conflict(
        os.path.join(root, "vision.md"),
        content,
        force=force,
        prompt=prompt,
        log=out_log,
    )
    return 0
