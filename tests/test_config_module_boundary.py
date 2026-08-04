"""project-config-god-module-split: the config loader must no longer drag the DB
layer at import time, and the moved constants/helpers must remain reachable through
project_config for back-compat.

The import-time edge project_config -> project_backend/project_service was the
blocker for a standalone config loader (v2-engine-standalone-package): reading
.tausik/config.json must not require the database code. These tests pin the split.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

_SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"


class TestConfigDbEdgeBroken:
    def test_source_has_no_db_layer_import(self):
        # AST guard: project_config must not import project_backend / project_service
        # at any level (the reverse map of the edge we just cut).
        tree = ast.parse((_SCRIPTS / "project_config.py").read_text(encoding="utf-8"))
        banned = {"project_backend", "project_service"}
        offenders: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders += [n.name for n in node.names if n.name.split(".")[0] in banned]
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in banned:
                    offenders.append(node.module)
        assert not offenders, f"project_config still imports the DB layer: {offenders}"

    def test_project_config_imports_without_db_layer(self):
        # Functional proof: with the DB modules made unimportable, importing
        # project_config still succeeds — the loader stands alone.
        code = (
            "import sys\n"
            "sys.modules['project_backend'] = None\n"
            "sys.modules['project_service'] = None\n"
            "import project_config\n"
            "assert callable(project_config.load_config)\n"
            "assert callable(project_config.get_config_path)\n"
            "print('ok')\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(_SCRIPTS),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert r.returncode == 0, r.stderr
        assert "ok" in r.stdout

    def test_service_factory_still_requires_db_layer(self):
        # NEGATIVE/boundary: the factory legitimately needs the DB layer, so in the
        # same DB-blocked environment importing service_factory must FAIL — proving
        # the dependency moved rather than vanished.
        code = "import sys\nsys.modules['project_backend'] = None\nimport service_factory\n"
        r = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(_SCRIPTS),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert r.returncode != 0


class TestReExportsUnchanged:
    def test_constants_and_helpers_reexported_identically(self):
        import project_config
        import tausik_constants

        # Same objects — so `from project_config import X` and the new home agree.
        assert project_config.resolve_context_tier is tausik_constants.resolve_context_tier
        assert (
            project_config.normalize_llm_pricing_config
            is tausik_constants.normalize_llm_pricing_config
        )
        assert (
            project_config.lookup_llm_usd_per_million_tokens
            is tausik_constants.lookup_llm_usd_per_million_tokens
        )
        assert project_config.CONTEXT_TIER_VALUES is tausik_constants.CONTEXT_TIER_VALUES
        assert project_config.DEFAULT_CONTEXT_TIER == "standard"
        assert project_config.DEFAULT_SESSION_MAX_MINUTES == 180
        assert project_config.DEFAULT_SESSION_WARN_THRESHOLD_MINUTES == 150
        assert project_config.DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES == 10
        assert project_config.DEFAULT_SESSION_CAPACITY_CALLS == 200

    def test_get_service_moved_to_service_factory(self):
        import service_factory

        assert callable(service_factory.get_service)
        # And it is gone from project_config (moved, not duplicated).
        import project_config

        assert not hasattr(project_config, "get_service")
