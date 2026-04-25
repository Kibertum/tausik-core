"""Tests for skills maturity: roles, stacks, bootstrap, workflow, stack validation."""

import os
import sys

import pytest

# Add scripts to path
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "agents")
BOOTSTRAP_DIR = os.path.join(os.path.dirname(__file__), "..", "bootstrap")
SKILLS_OFFICIAL_DIR = os.path.join(os.path.dirname(__file__), "..", "skills-official")

# Built-in skills (always in core)
BUILTIN_SKILLS = [
    "start",
    "end",
    "task",
    "plan",
    "checkpoint",
    "commit",
    "explore",
    "review",
    "test",
    "ship",
    "debug",
]

# Official skills (may be in skills-official/ or separate repo)
has_official = os.path.isdir(SKILLS_OFFICIAL_DIR)


def _skill_path(skill: str) -> str | None:
    """Resolve skill path: built-in → official."""
    p = os.path.join(AGENTS_DIR, "skills", skill, "SKILL.md")
    if os.path.isfile(p):
        return p
    p = os.path.join(SKILLS_OFFICIAL_DIR, skill, "SKILL.md")
    if os.path.isfile(p):
        return p
    return None


# === Role Profiles ===


class TestRoleProfiles:
    ROLES = ["developer", "architect", "qa", "tech-writer", "ui-ux"]
    REQUIRED_SECTIONS = ["Core Priorities", "Skill Modifiers", "Anti-patterns"]
    REQUIRED_SKILL_SECTIONS = ["/review", "/plan", "/task", "/test", "/commit"]

    def test_all_role_files_exist(self):
        for role in self.ROLES:
            path = os.path.join(AGENTS_DIR, "roles", f"{role}.md")
            assert os.path.isfile(path), f"Missing role file: {path}"

    @pytest.mark.parametrize("role", ROLES)
    def test_role_has_required_sections(self, role):
        path = os.path.join(AGENTS_DIR, "roles", f"{role}.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for section in self.REQUIRED_SECTIONS:
            assert section in content, f"Role '{role}' missing section: {section}"

    @pytest.mark.parametrize("role", ROLES)
    def test_role_has_skill_modifiers(self, role):
        path = os.path.join(AGENTS_DIR, "roles", f"{role}.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for skill in self.REQUIRED_SKILL_SECTIONS:
            assert skill in content, (
                f"Role '{role}' missing modifier for skill: {skill}"
            )


# === Stack Guides ===


class TestStackGuides:
    STACKS = ["python", "react", "typescript", "go", "vue"]
    REQUIRED_SECTIONS = [
        "Testing",
        "Review Checklist",
        "Conventions",
        "Common Pitfalls",
    ]

    def test_all_stack_files_exist(self):
        # v1.6: stacks live in <repo>/stacks/<name>/guide.md (plugin layout).
        repo_root = os.path.dirname(AGENTS_DIR)
        for stack in self.STACKS:
            path = os.path.join(repo_root, "stacks", stack, "guide.md")
            assert os.path.isfile(path), f"Missing stack file: {path}"

    @pytest.mark.parametrize("stack", STACKS)
    def test_stack_has_required_sections(self, stack):
        repo_root = os.path.dirname(AGENTS_DIR)
        path = os.path.join(repo_root, "stacks", stack, "guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for section in self.REQUIRED_SECTIONS:
            assert section in content, f"Stack '{stack}' missing section: {section}"


# === Built-in Skills ===


class TestBuiltinSkills:
    @pytest.mark.parametrize("skill", BUILTIN_SKILLS)
    def test_builtin_skill_exists(self, skill):
        path = os.path.join(AGENTS_DIR, "skills", skill, "SKILL.md")
        assert os.path.isfile(path), f"Missing built-in skill: {skill}"

    @pytest.mark.parametrize("skill", BUILTIN_SKILLS)
    def test_builtin_skill_has_frontmatter(self, skill):
        path = os.path.join(AGENTS_DIR, "skills", skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---"), (
            f"Built-in skill '{skill}' missing frontmatter"
        )
        assert "context:" in content, f"Built-in skill '{skill}' missing context field"
        assert "effort:" in content, f"Built-in skill '{skill}' missing effort field"

    @pytest.mark.parametrize("skill", ["task", "commit", "plan"])
    def test_key_builtin_skills_suggest_next(self, skill):
        path = os.path.join(AGENTS_DIR, "skills", skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Suggest next" in content or "/" in content, (
            f"Built-in skill '{skill}' missing workflow hints"
        )


# === Official Skills (skipped if skills-official/ not present) ===


@pytest.mark.skipif(not has_official, reason="skills-official/ not available")
class TestOfficialSkills:
    OFFICIAL_SKILLS = [
        "audit",
        "bitrix24",
        "confluence",
        "daily",
        "diff",
        "dispatch",
        "docs",
        "excel",
        "go",
        "init",
        "jira",
        "loop-task",
        "next",
        "onboard",
        "optimize",
        "pdf",
        "presale",
        "retro",
        "run",
        "security",
        "sentry",
        "ultra",
    ]

    @pytest.mark.parametrize("skill", OFFICIAL_SKILLS)
    def test_official_skill_exists(self, skill):
        path = os.path.join(SKILLS_OFFICIAL_DIR, skill, "SKILL.md")
        assert os.path.isfile(path), f"Missing official skill: {skill}"

    @pytest.mark.parametrize("skill", OFFICIAL_SKILLS)
    def test_official_skill_has_frontmatter(self, skill):
        path = os.path.join(SKILLS_OFFICIAL_DIR, skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---"), (
            f"Official skill '{skill}' missing frontmatter"
        )
        assert "context:" in content, f"Official skill '{skill}' missing context field"
        assert "effort:" in content, f"Official skill '{skill}' missing effort field"

    @pytest.mark.parametrize("skill", OFFICIAL_SKILLS)
    def test_official_skill_has_algorithm(self, skill):
        path = os.path.join(SKILLS_OFFICIAL_DIR, skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "## Algorithm" in content or "### 1." in content, (
            f"Official skill '{skill}' missing algorithm structure"
        )

    @pytest.mark.parametrize("skill", OFFICIAL_SKILLS)
    def test_official_skill_has_workflow_hints(self, skill):
        """Official skills should reference other skills for workflow continuity."""
        path = os.path.join(SKILLS_OFFICIAL_DIR, skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        import re

        has_hint = (
            "Suggest next" in content
            or "suggest next" in content
            or bool(re.search(r"/\w+", content))  # references like /review, /task
        )
        assert has_hint, f"Official skill '{skill}' missing workflow hints"

    @pytest.mark.parametrize("skill", OFFICIAL_SKILLS)
    def test_official_skill_responds_in_user_language(self, skill):
        path = os.path.join(SKILLS_OFFICIAL_DIR, skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "user's language" in content.lower(), (
            f"Official skill '{skill}' missing user language instruction"
        )

    def test_registry_json_exists(self):
        path = os.path.join(SKILLS_OFFICIAL_DIR, "registry.json")
        assert os.path.isfile(path), "Missing registry.json in skills-official/"

    def test_registry_json_covers_all_skills(self):
        import json

        path = os.path.join(SKILLS_OFFICIAL_DIR, "registry.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        skills = data.get("skills", {})
        for skill in self.OFFICIAL_SKILLS:
            assert skill in skills, f"registry.json missing skill: {skill}"


# === Workflow Hints (cross-cutting, uses resolver) ===


class TestWorkflowHints:
    SKILLS_WITH_HINTS = [
        ("task", ["ship"]),
        ("commit", ["task", "end"]),
        ("plan", ["task"]),
        ("ship", ["task", "end"]),
        ("debug", ["ship"]),
    ]

    @pytest.mark.parametrize("skill,expected_hints", SKILLS_WITH_HINTS)
    def test_builtin_skill_suggests_next(self, skill, expected_hints):
        """Built-in skills should suggest next skills."""
        path = os.path.join(AGENTS_DIR, "skills", skill, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        found_any = any(f"/{hint}" in content for hint in expected_hints)
        assert found_any, f"Skill '{skill}' doesn't suggest any of {expected_hints}"


# === Stack Validation ===


class TestStackValidation:
    def _make_svc(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        db_path = str(tmp_path / "test.db")
        be = SQLiteBackend(db_path)
        svc = ProjectService(be)
        svc.epic_add("e1", "Epic")
        svc.story_add("e1", "s1", "Story")
        return svc, be

    def test_valid_stack_accepted(self, tmp_path):
        svc, be = self._make_svc(tmp_path)
        result = svc.task_add("s1", "t1", "Task", stack="python", role="developer")
        assert "created" in result
        be.close()

    def test_invalid_stack_rejected(self, tmp_path):
        from tausik_utils import ServiceError

        svc, be = self._make_svc(tmp_path)
        with pytest.raises(ServiceError, match="Invalid stack"):
            svc.task_add("s1", "t1", "Task", stack="cobol", role="developer")
        be.close()

    def test_none_stack_accepted(self, tmp_path):
        svc, be = self._make_svc(tmp_path)
        result = svc.task_add("s1", "t1", "Task", role="developer")
        assert "created" in result
        be.close()

    def test_stack_filter_in_task_list(self, tmp_path):
        svc, be = self._make_svc(tmp_path)
        svc.task_add("s1", "t1", "Python task", stack="python", role="developer")
        svc.task_add("s1", "t2", "React task", stack="react", role="developer")
        svc.task_add("s1", "t3", "No stack task", role="developer")
        python_tasks = svc.task_list(stack="python")
        assert len(python_tasks) == 1
        assert python_tasks[0]["slug"] == "t1"
        all_tasks = svc.task_list()
        assert len(all_tasks) == 3
        be.close()

    def test_stack_validation_on_update(self, tmp_path):
        from tausik_utils import ServiceError

        svc, be = self._make_svc(tmp_path)
        svc.task_add("s1", "t1", "Task", stack="python", role="developer")
        svc.task_update("t1", stack="react")
        task = svc.task_show("t1")
        assert task["stack"] == "react"
        with pytest.raises(ServiceError, match="Invalid stack"):
            svc.task_update("t1", stack="cobol")
        be.close()


# === Bootstrap Integration ===


class TestBootstrapRolesStacks:
    def test_copy_roles_function_exists(self):
        sys.path.insert(0, BOOTSTRAP_DIR)
        from bootstrap_copy import copy_roles

        assert callable(copy_roles)

    def test_copy_stacks_function_exists(self):
        sys.path.insert(0, BOOTSTRAP_DIR)
        from bootstrap_copy import copy_stacks

        assert callable(copy_stacks)

    def test_copy_stacks_filters_by_detected(self, tmp_path):
        sys.path.insert(0, BOOTSTRAP_DIR)
        from bootstrap_copy import copy_stacks

        lib_dir = os.path.join(os.path.dirname(__file__), "..")
        target = str(tmp_path / "target")
        os.makedirs(target)
        n = copy_stacks(lib_dir, target, "claude", ["python", "react"])
        assert n >= 2
        stacks_dir = os.path.join(target, "stacks")
        # v1.6: each stack lives in stacks/<name>/{stack.json, guide.md}.
        assert os.path.isfile(os.path.join(stacks_dir, "python", "stack.json"))
        assert os.path.isfile(os.path.join(stacks_dir, "python", "guide.md"))
        assert os.path.isfile(os.path.join(stacks_dir, "react", "stack.json"))
        # Non-detected stacks must not be copied.
        assert not os.path.isdir(os.path.join(stacks_dir, "go"))
        assert not os.path.isdir(os.path.join(stacks_dir, "vue"))

    def test_copy_stacks_all_when_none_detected(self, tmp_path):
        sys.path.insert(0, BOOTSTRAP_DIR)
        from bootstrap_copy import copy_stacks

        lib_dir = os.path.join(os.path.dirname(__file__), "..")
        target = str(tmp_path / "target")
        os.makedirs(target)
        n = copy_stacks(lib_dir, target, "claude", [])
        assert n >= 5

    def test_copy_roles_copies_all(self, tmp_path):
        sys.path.insert(0, BOOTSTRAP_DIR)
        from bootstrap_copy import copy_roles

        lib_dir = os.path.join(os.path.dirname(__file__), "..")
        target = str(tmp_path / "target")
        os.makedirs(target)
        n = copy_roles(lib_dir, target, "claude")
        assert n == 5
        roles_dir = os.path.join(target, "roles")
        for role in ["developer", "architect", "qa", "tech-writer", "ui-ux"]:
            assert os.path.isfile(os.path.join(roles_dir, f"{role}.md"))


# === VALID_STACKS constant ===


class TestValidStacks:
    def test_valid_stacks_exists(self):
        from project_types import VALID_STACKS

        assert isinstance(VALID_STACKS, frozenset)
        assert len(VALID_STACKS) >= 15

    def test_valid_stacks_contains_major_stacks(self):
        from project_types import VALID_STACKS

        for stack in ["python", "react", "typescript", "go", "vue", "rust", "java"]:
            assert stack in VALID_STACKS, f"Missing major stack: {stack}"

    def test_all_stack_guides_have_valid_stack(self):
        from project_types import VALID_STACKS

        stacks_dir = os.path.join(AGENTS_DIR, "stacks")
        for fname in os.listdir(stacks_dir):
            if fname.endswith(".md"):
                stack_name = fname.replace(".md", "")
                assert stack_name in VALID_STACKS, (
                    f"Stack guide '{fname}' not in VALID_STACKS"
                )
