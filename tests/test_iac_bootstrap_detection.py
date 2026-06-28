"""IaC stack detection in bootstrap (closes v1.5 HIGH DRIFT)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from bootstrap_config import STACK_SIGNATURES, _signature_match, detect_stacks


_IAC = ("terraform", "ansible", "helm", "kubernetes", "docker")


# === STACK_SIGNATURES has IaC entries ===


class TestIacSignatures:
    @pytest.mark.parametrize("stack", _IAC)
    def test_iac_stack_in_signatures(self, stack):
        assert stack in STACK_SIGNATURES
        assert STACK_SIGNATURES[stack], f"empty signature list for {stack}"


# === _signature_match supports three forms ===


class TestSignatureMatch:
    def test_exact_filename_match(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM scratch\n")
        result = _signature_match(str(tmp_path), "Dockerfile")
        assert result is not None
        assert result.endswith("Dockerfile")

    def test_exact_filename_miss(self, tmp_path):
        assert _signature_match(str(tmp_path), "Dockerfile") is None

    def test_directory_marker_match(self, tmp_path):
        os.makedirs(tmp_path / "playbooks")
        result = _signature_match(str(tmp_path), "playbooks/")
        assert result is not None

    def test_directory_marker_miss(self, tmp_path):
        # File with same name shouldn't match a directory marker
        (tmp_path / "playbooks").write_text("not-a-dir")
        assert _signature_match(str(tmp_path), "playbooks/") is None

    def test_glob_at_root(self, tmp_path):
        (tmp_path / "main.tf").write_text("# tf\n")
        assert _signature_match(str(tmp_path), "*.tf") is not None

    def test_glob_one_level_deep(self, tmp_path):
        os.makedirs(tmp_path / "modules" / "vpc")
        (tmp_path / "modules" / "vpc" / "main.tf").write_text("# tf\n")
        # Walks up to 3 levels — modules/vpc/main.tf is 2 levels deep
        assert _signature_match(str(tmp_path), "*.tf") is not None

    def test_glob_no_match(self, tmp_path):
        assert _signature_match(str(tmp_path), "*.tf") is None


# === detect_stacks honours IaC patterns ===


class TestDetectStacks:
    def test_terraform_only(self, tmp_path):
        (tmp_path / "main.tf").write_text('resource "null_resource" "x" {}')
        stacks = detect_stacks(str(tmp_path))
        assert "terraform" in stacks
        # No Python signals → python should NOT appear
        assert "python" not in stacks

    def test_docker_only(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM alpine:3.19\n")
        stacks = detect_stacks(str(tmp_path))
        assert "docker" in stacks

    def test_ansible_via_directory(self, tmp_path):
        os.makedirs(tmp_path / "roles" / "web" / "tasks")
        (tmp_path / "roles" / "web" / "tasks" / "main.yml").write_text(
            "- name: x\n  debug: msg=hi\n"
        )
        stacks = detect_stacks(str(tmp_path))
        assert "ansible" in stacks

    def test_helm_via_chart_yaml(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text(
            "apiVersion: v2\nname: my-app\nversion: 0.1.0\n"
        )
        stacks = detect_stacks(str(tmp_path))
        assert "helm" in stacks

    def test_kubernetes_via_manifests_dir(self, tmp_path):
        os.makedirs(tmp_path / "k8s")
        (tmp_path / "k8s" / "deployment.yaml").write_text("kind: Deployment\n")
        stacks = detect_stacks(str(tmp_path))
        assert "kubernetes" in stacks

    def test_mixed_python_terraform(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        (tmp_path / "main.tf").write_text("# tf\n")
        stacks = detect_stacks(str(tmp_path))
        assert "python" in stacks
        assert "terraform" in stacks

    def test_bare_config_yaml_no_false_iac_trigger(self, tmp_path):
        # The user's nightmare — a yaml with no IaC structure should not
        # trigger ansible/helm/k8s false positives.
        (tmp_path / "config.yaml").write_text("foo: bar\n")
        stacks = detect_stacks(str(tmp_path))
        for s in _IAC:
            assert s not in stacks, f"false-positive: {s} on bare config.yaml"

    def test_empty_repo_no_iac(self, tmp_path):
        stacks = detect_stacks(str(tmp_path))
        for s in _IAC:
            assert s not in stacks


# === auto-enable for IaC stacks via STACK_GATE_MAP ===


class TestAutoEnable:
    def test_terraform_auto_enables_terraform_validate(self, tmp_path):
        (tmp_path / "main.tf").write_text("# tf\n")
        from bootstrap_config import detect_stacks
        from project_config import auto_enable_gates_for_stacks

        stacks = detect_stacks(str(tmp_path))
        cfg: dict = {}
        newly = auto_enable_gates_for_stacks(cfg, stacks)
        assert "terraform-validate" in newly

    def test_docker_auto_enables_hadolint(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM scratch\n")
        from bootstrap_config import detect_stacks
        from project_config import auto_enable_gates_for_stacks

        stacks = detect_stacks(str(tmp_path))
        cfg: dict = {}
        newly = auto_enable_gates_for_stacks(cfg, stacks)
        assert "hadolint" in newly

    def test_ansible_auto_enables_ansible_lint(self, tmp_path):
        os.makedirs(tmp_path / "roles" / "web" / "tasks")
        (tmp_path / "roles" / "web" / "tasks" / "main.yml").write_text(
            "- debug: msg=hi\n"
        )
        from bootstrap_config import detect_stacks
        from project_config import auto_enable_gates_for_stacks

        stacks = detect_stacks(str(tmp_path))
        cfg: dict = {}
        newly = auto_enable_gates_for_stacks(cfg, stacks)
        assert "ansible-lint" in newly


# === stack guide files exist ===


class TestStackGuides:
    @pytest.mark.parametrize("stack", _IAC)
    def test_iac_stack_guide_exists(self, stack):
        # v1.6: stack guides moved to <repo>/stacks/<name>/guide.md.
        path = os.path.join(
            os.path.dirname(__file__), "..", "stacks", stack, "guide.md"
        )
        assert os.path.isfile(path), f"missing stacks/{stack}/guide.md"
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Testing" in content or "Validation" in content
        assert "Pitfalls" in content or "Checklist" in content
