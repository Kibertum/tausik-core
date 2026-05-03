"""TAUSIK RAG — project structure detection, .gitignore, file filtering."""

from __future__ import annotations

import fnmatch
import os
from pathlib import PurePosixPath

# Always ignored directories (never indexed)
ALWAYS_IGNORE_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".tausik", ".claude", ".cursor",
    "venv", ".venv", "env", ".env", "dist", "build", ".next", ".nuxt",
    ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage",
    ".tox", "target", "vendor", "bower_components", ".gradle", ".idea",
    ".vscode", ".DS_Store", "egg-info", ".eggs",
})

# Indexable file extensions -> language name
EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".ex": "elixir", ".exs": "elixir",
    ".lua": "lua",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".sql": "sql",
    ".r": "r", ".R": "r",
    ".dart": "dart",
    ".vue": "vue", ".svelte": "svelte",
    ".md": "markdown", ".mdx": "markdown",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".tf": "terraform", ".hcl": "terraform",
    ".dockerfile": "docker",
}

# Special filenames (no extension) -> language
SPECIAL_FILES: dict[str, str] = {
    "Dockerfile": "docker", "Makefile": "make", "Jenkinsfile": "groovy",
    "Vagrantfile": "ruby", "Rakefile": "ruby", "Gemfile": "ruby",
    ".gitignore": "gitignore", ".dockerignore": "gitignore",
    "CMakeLists.txt": "cmake",
}

# Max file size to index (1 MB)
MAX_FILE_SIZE = 1_048_576
# Max files to index per project
MAX_FILES = 5000


def parse_gitignore(project_dir: str) -> list[str]:
    """Read .gitignore and return list of glob patterns."""
    patterns: list[str] = []
    gitignore = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(gitignore):
        return patterns
    try:
        with open(gitignore, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Normalize: remove trailing slash (we match both files and dirs)
                patterns.append(line.rstrip("/"))
    except OSError:
        pass
    return patterns


def _matches_ignore(rel_path: str, patterns: list[str]) -> bool:
    """Check if relative path matches any gitignore pattern."""
    # Normalize to posix
    posix = PurePosixPath(rel_path).as_posix()
    name = os.path.basename(rel_path)
    for pat in patterns:
        # Pattern with slash — match against full path
        if "/" in pat:
            if fnmatch.fnmatch(posix, pat) or fnmatch.fnmatch(posix, pat + "/*"):
                return True
        else:
            # Pattern without slash — match against each path component
            if fnmatch.fnmatch(name, pat):
                return True
            # Also check directory components
            for part in PurePosixPath(posix).parts:
                if fnmatch.fnmatch(part, pat):
                    return True
    return False


def detect_language(file_path: str) -> str | None:
    """Detect language from file extension or name."""
    basename = os.path.basename(file_path)
    if basename in SPECIAL_FILES:
        return SPECIAL_FILES[basename]
    _, ext = os.path.splitext(basename)
    return EXT_TO_LANG.get(ext.lower())


def get_file_list(project_dir: str) -> list[dict[str, str]]:
    """Return indexable files: [{path, rel_path, language}].

    Respects .gitignore, skips binaries, caps at MAX_FILES.
    """
    patterns = parse_gitignore(project_dir)
    files: list[dict[str, str]] = []

    for root, dirs, filenames in os.walk(project_dir):
        # Prune ignored directories
        dirs[:] = [
            d for d in dirs
            if d not in ALWAYS_IGNORE_DIRS
            and not d.startswith(".")
            or d in (".github",)  # allow .github
        ]
        # Also prune dirs matching gitignore
        rel_root = os.path.relpath(root, project_dir).replace("\\", "/")
        if rel_root != ".":
            dirs[:] = [
                d for d in dirs
                if not _matches_ignore(f"{rel_root}/{d}", patterns)
            ]

        for fname in filenames:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, project_dir).replace("\\", "/")

            # Skip gitignored
            if _matches_ignore(rel_path, patterns):
                continue

            # Detect language
            lang = detect_language(fname)
            if not lang:
                continue

            # Skip large files
            try:
                if os.path.getsize(full_path) > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            files.append({
                "path": full_path,
                "rel_path": rel_path,
                "language": lang,
            })

            if len(files) >= MAX_FILES:
                return files

    return files


def detect_project_languages(project_dir: str) -> dict[str, int]:
    """Count files per language in the project."""
    files = get_file_list(project_dir)
    counts: dict[str, int] = {}
    for f in files:
        lang = f["language"]
        counts[lang] = counts.get(lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
