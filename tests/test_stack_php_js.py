"""PHP + JS/TS verticals — test runner gates."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "php-js.db")))
    yield s
    s.be.close()


class TestRegistration:
    def test_phpunit_registered(self):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES["phpunit"]
        assert "php" in gate["stacks"]
        assert "laravel" in gate["stacks"]
        # v1.4 Verify-First Contract: heavy gates moved to verify trigger
        assert "verify" in gate["trigger"]
        assert gate["severity"] == "block"

    def test_js_test_registered(self):
        from project_config import DEFAULT_GATES

        gate = DEFAULT_GATES["js-test"]
        for s in ("javascript", "typescript", "react", "next", "vue", "nuxt", "svelte"):
            assert s in gate["stacks"]
        assert "npm test" in gate["command"]

    def test_in_stack_gate_map(self):
        from project_config import STACK_GATE_MAP

        assert "phpunit" in STACK_GATE_MAP.get("php", [])
        assert "phpunit" in STACK_GATE_MAP.get("laravel", [])
        for s in ("typescript", "javascript", "react", "next"):
            assert "js-test" in STACK_GATE_MAP.get(s, [])

    def test_descriptions_mention_override(self):
        from project_config import DEFAULT_GATES

        assert "Override" in DEFAULT_GATES["phpunit"]["description"]
        assert "Override" in DEFAULT_GATES["js-test"]["description"]


class TestStackInfo:
    def test_php_info(self, svc):
        info = svc.stack_info("php")
        names = [g["name"] for g in info["gates"]]
        assert "phpunit" in names
        assert "phpstan" in names

    def test_typescript_info(self, svc):
        info = svc.stack_info("typescript")
        names = [g["name"] for g in info["gates"]]
        assert "js-test" in names
        assert "tsc" in names
        assert "eslint" in names


class TestStackFiltering:
    @pytest.mark.parametrize(
        "gate,files,expected",
        [
            pytest.param("phpunit", ["main.py"], False, id="phpunit_skipped_for_python"),
            pytest.param("phpunit", ["src/User.php"], True, id="phpunit_runs_for_php"),
            pytest.param("js-test", ["main.go"], False, id="js_test_skipped_for_go"),
            pytest.param("js-test", ["app.tsx"], True, id="js_test_runs_for_tsx"),
        ],
    )
    def test_gate_applicability(self, gate, files, expected):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        assert gate_applies_to(DEFAULT_GATES[gate], files) is expected
