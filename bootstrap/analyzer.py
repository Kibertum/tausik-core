#!/usr/bin/env python3
"""
Smart project analyzer for bootstrap.

Scans project structure and recommends extension skills, stacks, and roles.
No external dependencies — Python 3.11+ stdlib only.
"""

import os


# ---------------------------------------------------------------------------
# Source file counting (skip vendor/generated dirs)
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    ".claude",
    ".claude-lib",
    ".claude-project",
    "__pycache__",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "vendor",
    ".rag",
    "coverage",
    ".tox",
    ".mypy_cache",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".cs",
    ".java",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".dart",
    ".lua",
    ".ex",
    ".exs",
    ".vue",
    ".svelte",
}


def count_source_files(project_dir: str) -> int:
    """Count source files, skipping vendor directories."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if os.path.splitext(f)[1].lower() in SOURCE_EXTENSIONS:
                count += 1
                if count > 200:  # early exit — we know it's large
                    return count
    return count


# ---------------------------------------------------------------------------
# File content search helpers
# ---------------------------------------------------------------------------


def _file_contains(filepath: str, keywords: list[str]) -> bool:
    """Check if file contains any of the keywords (case-insensitive)."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read(64_000).lower()  # read first 64KB
        return any(kw.lower() in content for kw in keywords)
    except OSError:
        return False


def _any_file_exists(project_dir: str, patterns: list[str]) -> bool:
    """Check if any file matching pattern exists in project root."""
    for p in patterns:
        if "*" in p:
            # Simple glob for root-level files
            for f in os.listdir(project_dir):
                if f.endswith(p.replace("*", "")):
                    return True
        else:
            if os.path.exists(os.path.join(project_dir, p)):
                return True
    return False


def _has_dir(project_dir: str, dirname: str) -> bool:
    """Check if directory exists."""
    return os.path.isdir(os.path.join(project_dir, dirname))


def _find_files(project_dir: str, extensions: list[str], limit: int = 5) -> list[str]:
    """Find files with given extensions, return up to limit paths."""
    found = []
    for dirpath, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if any(f.endswith(ext) for ext in extensions):
                found.append(os.path.join(dirpath, f))
                if len(found) >= limit:
                    return found
    return found


# ---------------------------------------------------------------------------
# Extension skill detection rules
# ---------------------------------------------------------------------------


def detect_extension_skills(project_dir: str) -> dict[str, str]:
    """Detect which extension skills the project needs.

    Returns dict: skill_name -> reason
    """
    skills = {}
    src_count = count_source_files(project_dir)

    # --- test ---
    test_signals = [
        "pytest.ini",
        "pyproject.toml",
        "jest.config.js",
        "jest.config.ts",
        "vitest.config.ts",
        "vitest.config.js",
        "karma.conf.js",
        "playwright.config.ts",
        "cypress.config.js",
        "cypress.config.ts",
    ]
    has_test_config = _any_file_exists(project_dir, test_signals)
    has_test_dir = (
        _has_dir(project_dir, "tests")
        or _has_dir(project_dir, "__tests__")
        or _has_dir(project_dir, "test")
        or _has_dir(project_dir, "spec")
    )
    # Also check pyproject.toml for [tool.pytest]
    pyproject = os.path.join(project_dir, "pyproject.toml")
    if not has_test_config and os.path.isfile(pyproject):
        has_test_config = _file_contains(pyproject, ["[tool.pytest", "[tool.coverage"])

    if has_test_config or has_test_dir:
        skills["test"] = "test infrastructure detected"

    # --- review ---
    if src_count >= 5:
        skills["review"] = f"{src_count}+ source files"

    # --- security ---
    security_keywords = [
        "jwt",
        "oauth",
        "auth",
        "bcrypt",
        "password",
        "token",
        "stripe",
        "payment",
        "credit_card",
        "api_key",
        "secret_key",
    ]
    env_file = os.path.join(project_dir, ".env")
    env_example = os.path.join(project_dir, ".env.example")
    has_env = os.path.isfile(env_file) or os.path.isfile(env_example)
    has_security_code = False
    # Check a few key files for security keywords
    for ext in [".py", ".js", ".ts", ".go", ".rs", ".php"]:
        for fpath in _find_files(project_dir, [ext], limit=10):
            if _file_contains(fpath, security_keywords):
                has_security_code = True
                break
        if has_security_code:
            break

    if has_env and has_security_code:
        skills["security"] = "auth/security patterns + .env detected"
    elif has_security_code:
        skills["security"] = "auth/security patterns in code"

    # --- pdf ---
    pdf_files = _find_files(project_dir, [".pdf"], limit=1)
    if pdf_files:
        skills["pdf"] = "PDF files in project"
    else:
        # Check deps for pdf libraries
        for dep_file in ["requirements.txt", "pyproject.toml", "package.json"]:
            fp = os.path.join(project_dir, dep_file)
            if os.path.isfile(fp) and _file_contains(
                fp, ["pdfkit", "pypdf", "pdf-parse", "pdfmake", "reportlab"]
            ):
                skills["pdf"] = "PDF library in dependencies"
                break

    # --- excel ---
    xlsx_files = _find_files(project_dir, [".xlsx", ".xls"], limit=1)
    if xlsx_files:
        skills["excel"] = "Excel files in project"
    else:
        for dep_file in ["requirements.txt", "pyproject.toml", "package.json"]:
            fp = os.path.join(project_dir, dep_file)
            if os.path.isfile(fp) and _file_contains(
                fp, ["openpyxl", "xlsxwriter", "pandas", "exceljs", "xlsx"]
            ):
                skills["excel"] = "Excel library in dependencies"
                break

    # --- docs ---
    has_docs_dir = _has_dir(project_dir, "docs") or _has_dir(
        project_dir, "documentation"
    )
    readme = os.path.join(project_dir, "README.md")
    big_readme = False
    if os.path.isfile(readme):
        try:
            with open(readme, encoding="utf-8", errors="ignore") as f:
                big_readme = len(f.readlines()) > 100
        except OSError:
            pass
    if has_docs_dir or big_readme:
        skills["docs"] = "docs directory or large README"

    # --- sentry (via .mcp.json) ---
    mcp_json = os.path.join(project_dir, ".mcp.json")
    if os.path.isfile(mcp_json):
        if _file_contains(mcp_json, ["sentry"]):
            skills["sentry"] = "Sentry MCP configured"

    # --- optimize ---
    if src_count >= 50:
        skills["optimize"] = f"{src_count}+ source files (large project)"

    return skills


# ---------------------------------------------------------------------------
# Enhanced stack detection
# ---------------------------------------------------------------------------

EXTRA_STACK_SIGNATURES = {
    "nestjs": [("package.json", '"@nestjs/core"')],
    "express": [("package.json", '"express"')],
    "elixir": [("mix.exs", None)],
    "phoenix": [("mix.exs", "phoenix")],
    "python": [("pyproject.toml", None), ("requirements.txt", None)],
    "php": [("composer.json", None)],
    "pyqt": [
        ("requirements.txt", "pyqt"),
        ("requirements.txt", "pyside"),
        ("pyproject.toml", "pyqt"),
        ("pyproject.toml", "pyside"),
    ],
    "lua-wow": [],  # detected via .toc files below
}


def detect_stacks_enhanced(project_dir: str) -> list[str]:
    """Enhanced stack detection including monorepo and extra stacks."""
    # Import the base detection from bootstrap
    from bootstrap_config import detect_stacks, STACK_SIGNATURES

    found = detect_stacks(project_dir)

    # Extra stacks not in base STACK_SIGNATURES
    for stack, signatures in EXTRA_STACK_SIGNATURES.items():
        if stack in found or stack in STACK_SIGNATURES:
            continue
        for filename, keyword in signatures:
            filepath = os.path.join(project_dir, filename)
            if os.path.isfile(filepath):
                if keyword is None:
                    found.append(stack)
                    break
                try:
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        if keyword in f.read().lower():
                            found.append(stack)
                            break
                except OSError:
                    pass

    # Lua WoW: detect .toc files
    if "lua-wow" not in found:
        toc_files = _find_files(project_dir, [".toc"], limit=1)
        if toc_files:
            found.append("lua-wow")

    # Monorepo detection
    monorepo_signals = ["pnpm-workspace.yaml", "nx.json", "lerna.json", "turbo.json"]
    if _any_file_exists(project_dir, monorepo_signals):
        # Scan inner packages for additional stacks
        for pkg_dir in ["packages", "apps"]:
            pkg_root = os.path.join(project_dir, pkg_dir)
            if os.path.isdir(pkg_root):
                for entry in os.listdir(pkg_root):
                    inner = os.path.join(pkg_root, entry)
                    if os.path.isdir(inner):
                        inner_stacks = detect_stacks(inner)
                        for s in inner_stacks:
                            if s not in found:
                                found.append(s)

    return found


# ---------------------------------------------------------------------------
# Main analysis entry point
# ---------------------------------------------------------------------------


def analyze_project(project_dir: str, lib_dir: str | None = None) -> dict:
    """Analyze project and return recommendations.

    Returns:
        {
            "extension_skills": {"skill": "reason", ...},
            "detected_stacks": ["stack1", "stack2"],
            "source_files": int,
        }
    """
    project_dir = os.path.abspath(project_dir)

    # Detect extension skills
    ext_skills = detect_extension_skills(project_dir)

    # Detect stacks (enhanced if bootstrap module available, otherwise basic)
    try:
        stacks = detect_stacks_enhanced(project_dir)
    except ImportError:
        # Fallback: basic detection without importing bootstrap
        stacks = _basic_detect_stacks(project_dir)

    src_count = count_source_files(project_dir)

    return {
        "extension_skills": ext_skills,
        "detected_stacks": stacks,
        "source_files": src_count,
    }


def _basic_detect_stacks(project_dir: str) -> list[str]:
    """Minimal stack detection."""
    from bootstrap_config import detect_stacks

    return detect_stacks(project_dir)


def print_analysis(analysis: dict):
    """Print analysis results to stdout."""
    print("\n  Smart analysis:")
    print(f"    Source files: {analysis['source_files']}")

    if analysis["detected_stacks"]:
        print(f"    Stacks: {', '.join(analysis['detected_stacks'])}")
    else:
        print("    Stacks: none detected")

    if analysis["extension_skills"]:
        print("    Recommended extension skills:")
        for skill, reason in sorted(analysis["extension_skills"].items()):
            print(f"      + {skill} ({reason})")
    else:
        print("    Extension skills: none recommended")
