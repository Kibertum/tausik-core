#!/usr/bin/env python3
"""
Auto-generate missing stack/role reference templates.

When a detected stack has no reference file for a phase (init/plan/review),
generates a minimal template in the project's .claude/references/ directory.

No external dependencies — Python 3.11+ stdlib only.
"""

import os


# ---------------------------------------------------------------------------
# Stack reference templates
# ---------------------------------------------------------------------------

def generate_stack_plan(stack_name: str) -> str:
    """Generate a minimal plan-phase stack reference."""
    return f"""# {stack_name} — Plan Reference

<!-- auto-generated: edit with project-specific patterns -->

## Principles
- Follow {stack_name} conventions and best practices
- Prefer official documentation patterns
- Keep dependencies minimal
- Write tests alongside implementation

## Code Patterns
- Follow existing project patterns (check codebase first)
- Use consistent naming conventions
- Handle errors explicitly

## Conventions
- Match the project's existing code style
- Follow the project's import ordering
- Use project-standard directory structure
"""


def generate_stack_review(stack_name: str) -> str:
    """Generate a minimal review-phase stack reference."""
    return f"""# {stack_name} — Review Checklist

<!-- auto-generated: edit with project-specific checks -->

## {stack_name}-Specific Checks
- [ ] Follows {stack_name} best practices
- [ ] No deprecated APIs or patterns
- [ ] Error handling is consistent
- [ ] Dependencies are justified and minimal

## General Checks
- [ ] No hardcoded secrets or credentials
- [ ] Input validation at system boundaries
- [ ] Resource cleanup (connections, handles)
- [ ] Tests cover new/changed behavior
"""


def generate_stack_init(stack_name: str) -> str:
    """Generate a minimal init-phase stack reference (YAML format)."""
    return f"""# {stack_name} Stack Reference
# auto-generated: edit with project-specific paths

name: {stack_name}
detect:
  files: []
  patterns: ["{stack_name.lower()}"]

scan_paths:
  src:
    paths: ["src/"]
    patterns: ["*.*"]

test_command: "echo 'configure test command for {stack_name}'"
"""


def generate_role(role_name: str) -> str:
    """Generate a minimal role reference."""
    return f"""# {role_name} Role

<!-- auto-generated: edit with project-specific criteria -->

## Focus
- Apply {role_name} mindset to every task
- Follow project conventions

## Acceptance Criteria
- Work meets the task goal
- No regressions introduced
- Code follows project patterns
"""


# ---------------------------------------------------------------------------
# Validation and generation
# ---------------------------------------------------------------------------

def validate_stack_references(lib_dir: str, detected_stacks: list[str]) -> dict[str, list[str]]:
    """Check which stacks are missing reference files.

    Returns: {stack: [missing_phases]}
    """
    refs_dir = os.path.join(lib_dir, "references", "stacks")
    missing = {}

    for stack in detected_stacks:
        gaps = []
        for phase in ("init", "plan", "review"):
            phase_dir = os.path.join(refs_dir, phase)
            # Check both .md and .yaml
            has_md = os.path.isfile(os.path.join(phase_dir, f"{stack}.md"))
            has_yaml = os.path.isfile(os.path.join(phase_dir, f"{stack}.yaml"))
            if not has_md and not has_yaml:
                gaps.append(phase)
        if gaps:
            missing[stack] = gaps

    return missing


def validate_role_references(lib_dir: str, roles: list[str]) -> list[str]:
    """Check which roles are missing reference files."""
    roles_dir = os.path.join(lib_dir, "references", "roles")
    missing = []
    for role in roles:
        if not os.path.isfile(os.path.join(roles_dir, f"{role}.md")):
            missing.append(role)
    return missing


def ensure_references(lib_dir: str, target_dir: str,
                      detected_stacks: list[str],
                      roles: list[str] | None = None) -> list[str]:
    """Check for missing references and generate templates in target_dir.

    Generates into .claude/references/ (project-specific, NOT into .claude-lib/).
    Returns list of generated file descriptions.
    """
    generated = []

    # --- Stack references ---
    missing_stacks = validate_stack_references(lib_dir, detected_stacks)

    generators = {
        "init": generate_stack_init,
        "plan": generate_stack_plan,
        "review": generate_stack_review,
    }
    extensions = {
        "init": ".yaml",
        "plan": ".md",
        "review": ".md",
    }

    for stack, phases in missing_stacks.items():
        for phase in phases:
            gen_fn = generators[phase]
            ext = extensions[phase]
            out_dir = os.path.join(target_dir, "references", "stacks", phase)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{stack}{ext}")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(gen_fn(stack))
            generated.append(f"{stack} ({phase})")

    # --- Role references ---
    if roles:
        missing_roles = validate_role_references(lib_dir, roles)
        for role in missing_roles:
            out_dir = os.path.join(target_dir, "references", "roles")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{role}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(generate_role(role))
            generated.append(f"role:{role}")

    return generated


def print_validation_warnings(lib_dir: str, detected_stacks: list[str]):
    """Print warnings about missing stack references."""
    missing = validate_stack_references(lib_dir, detected_stacks)
    for stack, phases in missing.items():
        print(f"  WARNING: Stack '{stack}' missing references: {', '.join(phases)}")
