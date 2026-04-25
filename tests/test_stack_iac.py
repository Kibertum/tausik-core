"""IaC vertical — Ansible/Terraform/Helm/K8s/Docker lint-only gates."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "iac.db")))
    yield s
    s.be.close()


_IAC_STACKS = ("ansible", "terraform", "helm", "kubernetes", "docker")


# === VALID_STACKS extension ===


class TestValidStacks:
    @pytest.mark.parametrize("stack", _IAC_STACKS)
    def test_iac_stack_in_valid(self, stack):
        from project_types import VALID_STACKS

        assert stack in VALID_STACKS


# === Default gate registration ===


class TestRegistration:
    @pytest.mark.parametrize(
        "gate_name,stack",
        [
            ("ansible-lint", "ansible"),
            ("terraform-validate", "terraform"),
            ("helm-lint", "helm"),
            ("kubeval", "kubernetes"),
            ("hadolint", "docker"),
        ],
    )
    def test_gate_registered(self, gate_name, stack):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES[gate_name]
        assert stack in gate["stacks"]
        assert gate["enabled"] is False  # auto-enable via bootstrap

    def test_in_stack_gate_map(self):
        from project_config import STACK_GATE_MAP

        assert "ansible-lint" in STACK_GATE_MAP.get("ansible", [])
        assert "terraform-validate" in STACK_GATE_MAP.get("terraform", [])
        assert "helm-lint" in STACK_GATE_MAP.get("helm", [])
        assert "kubeval" in STACK_GATE_MAP.get("kubernetes", [])
        assert "hadolint" in STACK_GATE_MAP.get("docker", [])

    def test_descriptions_state_lint_only(self):
        """Honest scope: each IaC gate must call out 'NOT policy-as-code'."""
        from project_config import DEFAULT_GATES

        for name in ("ansible-lint", "terraform-validate", "helm-lint", "kubeval"):
            desc = DEFAULT_GATES[name]["description"].lower()
            assert "not policy-as-code" in desc or "not vulnerability" in desc
        # hadolint is best-practice/lint, not policy — explicitly disclaims vuln scans
        assert "not vulnerability" in DEFAULT_GATES["hadolint"]["description"].lower()


# === Filename + extension detection ===


class TestStackInference:
    @pytest.mark.parametrize(
        "path,expected_stack",
        [
            ("Dockerfile", "docker"),
            ("Dockerfile.prod", "docker"),
            ("Containerfile", "docker"),
            ("infra/main.tf", "terraform"),
            ("variables.tfvars", "terraform"),
            ("charts/myapp/Chart.yaml", "helm"),
            ("charts/myapp/values.yml", "helm"),
            ("ansible.cfg", "ansible"),
        ],
    )
    def test_filename_extension_detection(self, path, expected_stack):
        from gate_stack_dispatch import infer_stacks_from_files

        out = infer_stacks_from_files([path])
        assert expected_stack in out

    @pytest.mark.parametrize(
        "path,expected_stack",
        [
            ("playbooks/site.yml", "ansible"),
            ("roles/web/tasks/main.yaml", "ansible"),
            ("k8s/deployment.yaml", "kubernetes"),
            ("manifests/svc.yml", "kubernetes"),
            (".kube/config.yaml", "kubernetes"),
        ],
    )
    def test_path_hint_detection(self, path, expected_stack):
        from gate_stack_dispatch import infer_stacks_from_files

        out = infer_stacks_from_files([path])
        assert expected_stack in out

    def test_unrelated_yaml_not_tagged(self):
        """A bare config.yaml in repo root must NOT auto-tag any IaC stack."""
        from gate_stack_dispatch import infer_stacks_from_files

        out = infer_stacks_from_files(["config.yaml", "data.yml"])
        # No fragment/filename match — IaC stacks should not appear.
        for s in _IAC_STACKS:
            assert s not in out


# === Stack info exposure ===


class TestStackInfo:
    @pytest.mark.parametrize(
        "stack,gate_name",
        [
            ("ansible", "ansible-lint"),
            ("terraform", "terraform-validate"),
            ("helm", "helm-lint"),
            ("kubernetes", "kubeval"),
            ("docker", "hadolint"),
        ],
    )
    def test_stack_info_lists_lint_gate(self, svc, stack, gate_name):
        info = svc.stack_info(stack)
        names = [g["name"] for g in info["gates"]]
        assert gate_name in names
        # Universal filesize gate must also be present
        assert "filesize" in names


# === Cross-stack filtering (regression / negative) ===


class TestCrossStackFiltering:
    def test_pytest_skipped_on_dockerfile(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["pytest"], "name": "pytest"}
        assert gate_applies_to(gate, ["Dockerfile"]) is False

    def test_pytest_skipped_on_terraform(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["pytest"], "name": "pytest"}
        assert gate_applies_to(gate, ["main.tf"]) is False

    def test_ansible_lint_skipped_on_python(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["ansible-lint"], "name": "ansible-lint"}
        assert gate_applies_to(gate, ["scripts/main.py"]) is False

    def test_hadolint_runs_for_dockerfile(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["hadolint"], "name": "hadolint"}
        assert gate_applies_to(gate, ["Dockerfile"]) is True

    def test_terraform_validate_runs_for_tf(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["terraform-validate"], "name": "terraform-validate"}
        assert gate_applies_to(gate, ["modules/vpc/main.tf"]) is True

    def test_kubeval_runs_for_k8s_manifest(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["kubeval"], "name": "kubeval"}
        assert gate_applies_to(gate, ["k8s/deployment.yaml"]) is True
