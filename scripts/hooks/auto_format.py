#!/usr/bin/env python3
"""PostToolUse hook: auto-format edited files by detected stack.

Runs after Write/Edit. Determines formatter from file extension.
Also logs the changed file to the active TAUSIK task.
Exit codes: 0 = success, 1 = warning (non-blocking).
"""

import json
import os
import subprocess
import sys

# Extension → formatter command
FORMATTERS = {
    ".py": ["ruff", "format", "--quiet"],
    ".ts": ["npx", "prettier", "--write"],
    ".tsx": ["npx", "prettier", "--write"],
    ".js": ["npx", "prettier", "--write"],
    ".jsx": ["npx", "prettier", "--write"],
    ".json": ["npx", "prettier", "--write"],
    ".css": ["npx", "prettier", "--write"],
    ".scss": ["npx", "prettier", "--write"],
    ".html": ["npx", "prettier", "--write"],
    ".go": ["gofmt", "-w"],
    ".rs": ["rustfmt"],
}


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or not os.path.isfile(file_path):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Auto-format by extension
    _, ext = os.path.splitext(file_path)
    formatter = FORMATTERS.get(ext.lower())
    if formatter:
        try:
            subprocess.run(
                formatter + [file_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=project_dir,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Formatter not installed — graceful degradation
            pass

    # Log to active task
    tausik_cmd = os.path.join(project_dir, ".tausik", "tausik")
    if os.path.exists(tausik_cmd):
        try:
            # Get active task
            result = subprocess.run(
                [tausik_cmd, "task", "list", "--status", "active"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=project_dir,
            )
            lines = [
                line
                for line in result.stdout.strip().splitlines()
                if line.strip()
                and not line.startswith("slug")
                and not line.startswith("---")
            ]
            if lines:
                slug = lines[0].split()[0]
                rel_path = os.path.relpath(file_path, project_dir).replace("\\", "/")
                subprocess.run(
                    [tausik_cmd, "task", "log", slug, f"Modified: {rel_path}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=project_dir,
                )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
