"""Bootstrap must never touch .tausik/stacks/ — user customizations are sacred.

The contract: a user can drop overrides into .tausik/stacks/<name>/stack.json
and trust that `python bootstrap/bootstrap.py` will not mutate, delete, or
overwrite them. Built-in stacks live in <repo>/stacks/ and are subject to
upgrade; user overrides in .tausik/stacks/ are not.

These tests poke the public copy_stacks helper and the high-level bootstrap
entrypoint to assert that property holds for every code path.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

# Add bootstrap/ + scripts/ to sys.path so test imports work without bootstrap.
_REPO = Path(__file__).resolve().parents[1]
for sub in ("bootstrap", "scripts"):
    p = str(_REPO / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from bootstrap_stacks import copy_stacks  # noqa: E402


def _make_user_override(user_stacks_dir: Path, name: str, decl: dict) -> Path:
    """Drop a fake user override at .tausik/stacks/<name>/stack.json."""
    sd = user_stacks_dir / name
    sd.mkdir(parents=True, exist_ok=True)
    decl_path = sd / "stack.json"
    decl_path.write_text(json.dumps(decl), encoding="utf-8")
    return decl_path


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestCopyStacksLeavesUserDirAlone:
    def test_user_override_file_untouched_after_copy_stacks(self, tmp_path):
        """copy_stacks writes to <target>/stacks, never to .tausik/stacks/."""
        # Stand up a minimal lib + target.
        lib = tmp_path / "lib"
        target = tmp_path / "target"
        (lib / "stacks" / "python").mkdir(parents=True)
        (lib / "stacks" / "python" / "stack.json").write_text(
            json.dumps({"name": "python"}), encoding="utf-8"
        )
        (target).mkdir()

        # User has their own override under <project>/.tausik/stacks/.
        user_stacks = tmp_path / "user_project" / ".tausik" / "stacks"
        decl_path = _make_user_override(
            user_stacks,
            "ruby",
            {"name": "ruby", "extensions": [".rb"]},
        )
        before = _read(decl_path)

        # Run copy_stacks for the lib → target path. Must not touch the
        # unrelated .tausik/stacks dir even though it lives nearby on disk.
        copy_stacks(str(lib), str(target), "claude", ["python"])

        assert decl_path.exists(), "user override file was deleted"
        assert _read(decl_path) == before, "user override file was modified"

    def test_user_override_for_same_stack_name_untouched(self, tmp_path):
        """Even if user overrides a built-in name (e.g. python), .tausik/stacks/ wins."""
        lib = tmp_path / "lib"
        target = tmp_path / "target"
        (lib / "stacks" / "python").mkdir(parents=True)
        (lib / "stacks" / "python" / "stack.json").write_text(
            json.dumps({"name": "python", "extensions": [".py"]}),
            encoding="utf-8",
        )
        (target).mkdir()

        user_stacks = tmp_path / "user_project" / ".tausik" / "stacks"
        custom = _make_user_override(
            user_stacks,
            "python",
            {
                "name": "python",
                "extends": "builtin:python",
                "extensions_extra": [".pyi", ".pyx"],
            },
        )
        before = _read(custom)

        copy_stacks(str(lib), str(target), "claude", ["python"])

        assert custom.exists(), "user override of built-in name was deleted"
        assert _read(custom) == before, "user override of built-in was modified"
        # Built-in copy went to target/stacks/python, not into .tausik/stacks/.
        assert (target / "stacks" / "python" / "stack.json").is_file()


class TestCopyStacksRespectsTargetIsolation:
    def test_target_is_never_user_stacks_dir(self, tmp_path):
        """copy_stacks's target_dir is the bootstrap output (.claude/), not .tausik/.

        Defensive check: even if a caller mistakenly passed `.tausik` as
        target_dir, the function still writes only into <target>/stacks/<name>,
        and the test asserts the call signature can't accidentally clobber
        a sibling .tausik/stacks/ tree.
        """
        lib = tmp_path / "lib"
        (lib / "stacks" / "go").mkdir(parents=True)
        (lib / "stacks" / "go" / "stack.json").write_text(
            json.dumps({"name": "go"}), encoding="utf-8"
        )

        # Pretend the caller passed `.tausik/` as target. copy_stacks will
        # write into .tausik/stacks/go — that's the caller's mistake, but
        # our job is to guarantee bootstrap.py never makes that call. The
        # real bootstrap.py uses .claude/, not .tausik/. We assert that
        # invariant by inspecting the entrypoint code rather than running
        # bootstrap end-to-end.
        bootstrap_py = _REPO / "bootstrap" / "bootstrap.py"
        text = bootstrap_py.read_text(encoding="utf-8")
        # Must call copy_stacks with `target_dir`, not with the user dir.
        assert "copy_stacks(lib_dir, target_dir, ide, stacks)" in text, (
            "bootstrap.py must call copy_stacks with target_dir; "
            "regression risk: passing .tausik as target would clobber overrides"
        )

    def test_no_file_path_in_copy_stacks_resolves_under_user_dir(self, tmp_path):
        """Hard sanity check on the contract: when running with target_dir != .tausik,
        no file path produced by copy_stacks contains '.tausik'.
        """
        lib = tmp_path / "lib"
        target = tmp_path / "claude_target"
        (lib / "stacks" / "rust").mkdir(parents=True)
        (lib / "stacks" / "rust" / "stack.json").write_text(
            json.dumps({"name": "rust"}), encoding="utf-8"
        )
        target.mkdir()

        copy_stacks(str(lib), str(target), "claude", ["rust"])

        # Walk what was created and assert nothing landed in .tausik.
        for root, _dirs, files in os.walk(target):
            assert ".tausik" not in root, f"copy_stacks wrote into .tausik: {root}"
            for f in files:
                full = os.path.join(root, f)
                assert ".tausik" not in full, full


class TestCopyStacksIdempotent:
    def test_two_runs_dont_corrupt_user_dir(self, tmp_path):
        """Running bootstrap twice in a row preserves user overrides intact."""
        lib = tmp_path / "lib"
        target = tmp_path / "target"
        (lib / "stacks" / "python").mkdir(parents=True)
        (lib / "stacks" / "python" / "stack.json").write_text(
            json.dumps({"name": "python"}), encoding="utf-8"
        )
        target.mkdir()

        user_stacks = tmp_path / "user_project" / ".tausik" / "stacks"
        decl_path = _make_user_override(
            user_stacks,
            "elixir",
            {"name": "elixir", "extensions": [".ex"]},
        )
        before = _read(decl_path)

        copy_stacks(str(lib), str(target), "claude", ["python"])
        # Wipe target to simulate a clean bootstrap and run again.
        shutil.rmtree(target)
        target.mkdir()
        copy_stacks(str(lib), str(target), "claude", ["python"])

        assert _read(decl_path) == before
