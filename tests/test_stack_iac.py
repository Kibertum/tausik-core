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
    @pytest.mark.parametrize(
        "gate_name,files,expected",
        [
            pytest.param("pytest", ["Dockerfile"], False, id="pytest_skipped_on_dockerfile"),
            pytest.param("pytest", ["main.tf"], False, id="pytest_skipped_on_terraform"),
            pytest.param(
                "ansible-lint", ["scripts/main.py"], False, id="ansible_lint_skipped_on_python"
            ),
            pytest.param("hadolint", ["Dockerfile"], True, id="hadolint_runs_for_dockerfile"),
            pytest.param(
                "terraform-validate",
                ["modules/vpc/main.tf"],
                True,
                id="terraform_validate_runs_for_tf",
            ),
            pytest.param(
                "kubeval", ["k8s/deployment.yaml"], True, id="kubeval_runs_for_k8s_manifest"
            ),
        ],
    )
    def test_cross_stack_applicability(self, gate_name, files, expected):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES[gate_name], "name": gate_name}
        assert gate_applies_to(gate, files) is expected
