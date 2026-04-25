"""Default quality gate configurations (extracted from project_config.py).

Each entry is keyed by gate name and supports: enabled, severity, trigger,
command, description, file_extensions, stacks, timeout, max_lines.
"""

from __future__ import annotations

DEFAULT_GATES: dict[str, dict] = {
    "pytest": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done", "review"],
        # SENAR Rule 5: scoped to relevant_files via {test_files_for_files}
        # substitution. Falls back to full `tests/` when no test files map
        # from relevant_files (regression-safe).
        "command": "pytest -x -q {test_files_for_files}",
        "description": "Run pytest scoped to task's relevant_files",
        "timeout": 180,
        # Stack-aware dispatch: only run on Python projects. Without this
        # filter the gate would silently fall back to running an empty
        # `tests/` directory on non-Python projects (false-pass).
        "stacks": ["python", "fastapi", "django", "flask"],
    },
    "ruff": {
        "enabled": True,
        "severity": "block",
        "trigger": ["commit"],
        "command": "ruff check {files}",
        "description": "Lint with ruff before commit",
        "file_extensions": [".py"],
    },
    "mypy": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "mypy {files}",
        "description": "Type-check with mypy before commit",
        "file_extensions": [".py"],
    },
    "filesize": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": None,
        "description": "Warn if files exceed max_lines threshold",
        "max_lines": 400,
    },
    "bandit": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["review"],
        "command": "bandit -r {files} -q",
        "description": "Security scan with bandit",
    },
    # TypeScript / JavaScript gates
    "tsc": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "npx tsc --noEmit 2>&1 | head -20",
        "description": "TypeScript type-check",
        "stacks": ["typescript", "react", "next", "vue", "nuxt", "svelte"],
    },
    "eslint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "npx eslint {files} --max-warnings 0 2>&1 | head -20",
        "description": "ESLint check",
        "stacks": [
            "typescript",
            "javascript",
            "react",
            "next",
            "vue",
            "nuxt",
            "svelte",
        ],
    },
    # Go gates
    "go-vet": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "go vet ./... 2>&1 | head -20",
        "description": "Go vet static analysis",
        "stacks": ["go"],
    },
    "golangci-lint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "golangci-lint run {files} 2>&1 | head -20",
        "description": "Go linter suite",
        "stacks": ["go"],
    },
    "go-test": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done"],
        "command": "go test ./... 2>&1 | tail -30",
        "description": "Run Go tests for the module",
        "stacks": ["go"],
        "timeout": 180,
    },
    # Rust gates
    "cargo-check": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "cargo check 2>&1 | head -20",
        "description": "Rust compilation check",
        "stacks": ["rust"],
    },
    "clippy": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "cargo clippy — -D warnings 2>&1 | head -20",
        "description": "Rust linter",
        "stacks": ["rust"],
    },
    "cargo-test": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done"],
        "command": "cargo test --quiet 2>&1 | tail -30",
        "description": "Run Rust tests for the crate",
        "stacks": ["rust"],
        "timeout": 240,
    },
    # PHP gates
    "phpstan": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "vendor/bin/phpstan analyse {files} --no-progress 2>&1 | head -20",
        "description": "PHP static analysis",
        "stacks": ["php", "laravel"],
    },
    "phpcs": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "vendor/bin/phpcs {files} 2>&1 | head -20",
        "description": "PHP code style check",
        "stacks": ["php", "laravel"],
    },
    "phpunit": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done"],
        "command": "vendor/bin/phpunit 2>&1 | tail -30",
        "description": "PHPUnit/Pest. Override via config gates.phpunit.command for composer/pest.",
        "stacks": ["php", "laravel"],
        "timeout": 240,
    },
    "js-test": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done"],
        "command": "npm test --silent 2>&1 | tail -30",
        "description": "JS/TS tests (jest/vitest). Override gates.js-test.command for yarn/bun/pnpm.",
        "stacks": [
            "javascript",
            "typescript",
            "react",
            "next",
            "vue",
            "nuxt",
            "svelte",
        ],
        "timeout": 240,
    },
    # Java / Kotlin gates
    "javac": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done"],
        "command": "mvn compile -q 2>&1 | head -20",
        "description": "Java compilation check",
        "stacks": ["java"],
    },
    "ktlint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "ktlint {files} 2>&1 | head -20",
        "description": "Kotlin code style check",
        "stacks": ["kotlin"],
    },
    # TDD enforcement gate
    "tdd_order": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done"],
        "command": None,
        "description": "Verify test files were modified (TDD enforcement)",
    },
    # --- Infrastructure-as-Code: lint/syntax only, NOT policy-as-code ---
    # OPA/Sentinel/Checkov/tfsec/Trivy are NOT included — add them as custom
    # gates via .tausik/config.json under "gates" if your team needs them.
    "ansible-lint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done", "commit"],
        "command": "ansible-lint {files} 2>&1 | head -30",
        "description": "Ansible playbook linter — lint/syntax only, NOT policy-as-code (OPA/Sentinel/Checkov NOT included).",
        "stacks": ["ansible"],
        "timeout": 120,
    },
    "terraform-validate": {
        "enabled": False,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": "terraform fmt -check && terraform validate 2>&1 | head -30",
        "description": "Terraform fmt+validate — syntax only, NOT policy-as-code (Checkov/tfsec/Sentinel NOT included).",
        "stacks": ["terraform"],
        "timeout": 120,
    },
    "helm-lint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done", "commit"],
        "command": "helm lint . 2>&1 | head -30",
        "description": "Helm chart linter — lint/syntax only, NOT policy-as-code.",
        "stacks": ["helm"],
        "timeout": 60,
    },
    "kubeval": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done", "commit"],
        "command": "kubeval {files} 2>&1 | head -30",
        "description": "K8s manifest schema validation — schema only, NOT policy-as-code (kube-score/OPA Gatekeeper NOT included).",
        "stacks": ["kubernetes"],
        "timeout": 60,
    },
    "hadolint": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done", "commit"],
        "command": "hadolint {files} 2>&1 | head -30",
        "description": "Dockerfile linter — lint/best-practice only, NOT vulnerability scanning (Trivy/Grype NOT included).",
        "stacks": ["docker"],
        "timeout": 60,
    },
}
