"""Unit tests for scripts/stack_registry.py — layered loader + deep-merge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Match the pattern used elsewhere in the suite: prepend scripts/ to sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from stack_registry import StackRegistry  # noqa: E402


def _write(stack_dir: Path, decl: dict) -> None:
    stack_dir.mkdir(parents=True, exist_ok=True)
    (stack_dir / "stack.json").write_text(json.dumps(decl), encoding="utf-8")


# --- Loading -----------------------------------------------------------------


class TestLoadBuiltin:
    def test_missing_dir_records_error(self, tmp_path):
        reg = StackRegistry()
        reg.load_builtin(tmp_path / "does-not-exist")
        assert reg.all_stacks() == frozenset()
        assert any("not found" in e for e in reg.errors)

    def test_empty_dir_no_errors(self, tmp_path):
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.all_stacks() == frozenset()
        assert reg.errors == []

    def test_loads_valid_stack(self, tmp_path):
        _write(
            tmp_path / "python",
            {
                "name": "python",
                "extensions": [".py"],
                "detect": [{"file": "pyproject.toml", "type": "exact"}],
            },
        )
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.all_stacks() == {"python"}
        assert reg.extensions_for("python") == {".py"}
        sigs = reg.signatures_for("python")
        assert sigs == [{"file": "pyproject.toml", "type": "exact"}]
        assert reg.errors == []

    def test_malformed_json_skipped_with_error(self, tmp_path):
        sd = tmp_path / "broken"
        sd.mkdir()
        (sd / "stack.json").write_text("{ not json", encoding="utf-8")
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.all_stacks() == frozenset()
        assert len(reg.errors) == 1
        assert "broken" in reg.errors[0]

    def test_schema_invalid_skipped_with_error(self, tmp_path):
        # Missing required `name`.
        _write(tmp_path / "bad", {"extensions": [".x"]})
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.all_stacks() == frozenset()
        assert any("'name' is required" in e for e in reg.errors)

    def test_hidden_and_underscore_dirs_ignored(self, tmp_path):
        _write(tmp_path / "_internal", {"name": "skip-me"})
        _write(tmp_path / ".hidden", {"name": "skip-me-too"})
        _write(tmp_path / "ok", {"name": "ok"})
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.all_stacks() == {"ok"}

    def test_loose_files_in_root_ignored(self, tmp_path):
        # _schema.json sits at stacks/ root and must NOT trip the loader.
        (tmp_path / "_schema.json").write_text("{}", encoding="utf-8")
        _write(tmp_path / "go", {"name": "go", "extensions": [".go"]})
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.all_stacks() == {"go"}

    def test_duplicate_name_recorded(self, tmp_path):
        _write(tmp_path / "py1", {"name": "python"})
        _write(tmp_path / "py2", {"name": "python"})
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        # First wins (alphabetical); second logs.
        assert reg.all_stacks() == {"python"}
        assert any("duplicate stack name" in e for e in reg.errors)


# --- User overrides + deep-merge --------------------------------------------


class TestUserOverrides:
    def _setup_python_builtin(self, builtin_dir: Path) -> None:
        _write(
            builtin_dir / "python",
            {
                "name": "python",
                "extensions": [".py"],
                "detect": [{"file": "pyproject.toml", "type": "exact"}],
                "gates": {
                    "pytest": {"enabled": True, "severity": "block"},
                    "ruff": {"enabled": True, "severity": "block"},
                },
            },
        )

    def test_extends_inherits_base_fields(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._setup_python_builtin(builtin)
        _write(
            user / "python",
            {"name": "python", "extends": "builtin:python"},
        )
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        # Inherited fields preserved.
        assert reg.extensions_for("python") == {".py"}
        assert reg.signatures_for("python") == [
            {"file": "pyproject.toml", "type": "exact"}
        ]
        # Inherited gates kept (no override).
        gates = reg.gates_for("python")
        assert "pytest" in gates and "ruff" in gates

    def test_extensions_extra_is_additive(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._setup_python_builtin(builtin)
        _write(
            user / "python",
            {
                "name": "python",
                "extends": "builtin:python",
                "extensions_extra": [".pyi"],
            },
        )
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        # Both base and added — extensions_extra is additive, not replace.
        assert reg.extensions_for("python") == {".py", ".pyi"}

    def test_null_gate_disables_inherited(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._setup_python_builtin(builtin)
        _write(
            user / "python",
            {
                "name": "python",
                "extends": "builtin:python",
                "gates": {"pytest": None},
            },
        )
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        gates = reg.gates_for("python")
        assert "pytest" not in gates  # null disables inherited
        assert "ruff" in gates  # untouched gate still inherited

    def test_gate_per_key_override(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._setup_python_builtin(builtin)
        _write(
            user / "python",
            {
                "name": "python",
                "extends": "builtin:python",
                "gates": {"pytest": {"enabled": False, "severity": "warn"}},
            },
        )
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        gates = reg.gates_for("python")
        assert gates["pytest"]["enabled"] is False
        assert gates["pytest"]["severity"] == "warn"
        # Other inherited gate untouched.
        assert gates["ruff"]["enabled"] is True

    def test_unknown_extends_target_recorded_and_skipped(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._setup_python_builtin(builtin)
        _write(
            user / "ghost",
            {"name": "ghost", "extends": "builtin:does-not-exist"},
        )
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        assert "ghost" not in reg.all_stacks()
        assert any("does-not-exist" in e for e in reg.errors)

    def test_user_decl_without_extends_is_standalone(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        builtin.mkdir()  # empty
        _write(user / "ruby", {"name": "ruby", "extensions": [".rb"]})
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        assert reg.all_stacks() == {"ruby"}
        assert reg.extensions_for("ruby") == {".rb"}

    def test_load_user_missing_dir_is_silent(self, tmp_path):
        builtin = tmp_path / "builtin"
        self._setup_python_builtin(builtin)
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(tmp_path / "no-such-user-dir")
        # Built-ins still present, no errors added.
        assert "python" in reg.all_stacks()
        assert all("user" not in e.lower() for e in reg.errors)


# --- Reload + cache ----------------------------------------------------------


class TestReload:
    def test_reload_resets_layers(self, tmp_path):
        d1 = tmp_path / "set1"
        d2 = tmp_path / "set2"
        _write(d1 / "python", {"name": "python"})
        _write(d2 / "go", {"name": "go"})
        reg = StackRegistry()
        reg.load_builtin(d1)
        assert reg.all_stacks() == {"python"}
        reg.reload(d2)
        assert reg.all_stacks() == {"go"}
        # Errors list is reset on reload.
        assert reg.errors == []

    def test_resolve_cache_invalidated_on_load(self, tmp_path):
        d = tmp_path / "stacks"
        _write(d / "python", {"name": "python", "extensions": [".py"]})
        reg = StackRegistry()
        reg.load_builtin(d)
        assert ".py" in reg.extensions_for("python")
        # Mutate underlying file and reload — cache must reflect new state.
        _write(d / "python", {"name": "python", "extensions": [".py", ".pyi"]})
        reg.load_builtin(d)
        assert reg.extensions_for("python") == {".py", ".pyi"}


# --- Public accessors --------------------------------------------------------


class TestAccessors:
    def test_unknown_stack_returns_empty(self, tmp_path):
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.signatures_for("ghost") == []
        assert reg.extensions_for("ghost") == frozenset()
        assert reg.filenames_for("ghost") == frozenset()
        assert reg.path_hints_for("ghost") == frozenset()
        assert reg.gates_for("ghost") == {}
        assert reg.guide_path_for("ghost") is None

    def test_filenames_and_path_hints_returned(self, tmp_path):
        _write(
            tmp_path / "ansible",
            {
                "name": "ansible",
                "filenames": ["ansible.cfg"],
                "path_hints": ["/playbooks/", "/roles/"],
            },
        )
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.filenames_for("ansible") == {"ansible.cfg"}
        assert reg.path_hints_for("ansible") == {"/playbooks/", "/roles/"}

    def test_gates_for_filters_null_disabled(self, tmp_path):
        # Direct decl with a null gate (no extends) — null still filtered out.
        _write(
            tmp_path / "x",
            {
                "name": "x",
                "gates": {
                    "pytest": {"enabled": True, "severity": "block"},
                    "ruff": None,
                },
            },
        )
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        gates = reg.gates_for("x")
        assert "pytest" in gates
        assert "ruff" not in gates

    def test_gates_for_returns_fresh_dict(self, tmp_path):
        _write(
            tmp_path / "x",
            {
                "name": "x",
                "gates": {"pytest": {"enabled": True, "severity": "block"}},
            },
        )
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        a = reg.gates_for("x")
        a["pytest"]["enabled"] = False  # mutate caller's copy
        b = reg.gates_for("x")
        assert b["pytest"]["enabled"] is True  # registry unaffected

    def test_guide_path_default(self, tmp_path):
        sd = tmp_path / "go"
        _write(sd, {"name": "go"})
        (sd / "guide.md").write_text("# Go guide", encoding="utf-8")
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        gp = reg.guide_path_for("go")
        assert gp is not None
        assert gp.endswith("guide.md")

    def test_guide_path_custom(self, tmp_path):
        sd = tmp_path / "rs"
        _write(sd, {"name": "rs", "guide_path": "RUST.md"})
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        gp = reg.guide_path_for("rs")
        assert gp is not None
        assert gp.endswith("RUST.md")


class TestSourceTracking:
    def test_builtin_only_source(self, tmp_path):
        builtin = tmp_path / "builtin"
        _write(builtin / "py", {"name": "py"})
        reg = StackRegistry()
        reg.load_builtin(builtin)
        assert reg.source_for("py") == "builtin"
        assert reg.is_user_overridden("py") is False

    def test_user_only_source(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        builtin.mkdir()  # empty
        _write(user / "ruby", {"name": "ruby"})
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        assert reg.source_for("ruby") == "user"
        assert reg.is_user_overridden("ruby") is False

    def test_overridden_source(self, tmp_path):
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        _write(builtin / "py", {"name": "py", "extensions": [".py"]})
        _write(
            user / "py",
            {"name": "py", "extends": "builtin:py", "extensions_extra": [".pyi"]},
        )
        reg = StackRegistry()
        reg.load_builtin(builtin)
        reg.load_user(user)
        assert reg.source_for("py") == "overridden"
        assert reg.is_user_overridden("py") is True

    def test_unknown_stack_source_none(self, tmp_path):
        reg = StackRegistry()
        reg.load_builtin(tmp_path)
        assert reg.source_for("ghost") is None
        assert reg.is_user_overridden("ghost") is False
