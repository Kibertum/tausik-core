"""A hook that imports a sibling must be importable as `hooks.<name>`.

Hooks live in `scripts/hooks/` and import each other by BARE NAME
(`from token_rows import ...`). That resolves only when `scripts/hooks` is on
`sys.path`, which happens automatically when a hook is RUN as a script — its own
directory becomes `sys.path[0]`. It does NOT happen when a hook is IMPORTED as
`hooks.<name>`, which is what `model_routing` and `validate_prompt_caching` do.

Measured in session #228: five modules failed that import — `_common`,
`bash_cmd_scan`, `bash_firewall`, `pwsh_cmd_norm` and `session_metrics`. The
last one is the one that was actually reached: `model_routing` caught the
ImportError and returned None, so EVERY `task start` printed
"active: unknown (no transcript readable)" while the transcript sat on disk and
named `claude-opus-5`. The framework that promises quality on any model could
not tell which model was running, and said so in a way that read like a missing
file rather than a broken import.

WHY EACH IMPORT RUNS IN ITS OWN INTERPRETER: importing them in one process is
worthless as evidence. The first module that inserts `scripts/hooks` onto
`sys.path` silently repairs every module imported after it, so the failures you
observe depend on alphabetical order. That is exactly how this stayed hidden.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

#: This suite walks every file in scripts/hooks/, so a change ANYWHERE under
#: that directory can make it red — the scoped-pytest gate must run it whenever
#: a hook is touched, not only when this file is edited.
CROSSCUTTING_SCOPE = ["scripts/hooks/"]

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
_HOOKS = _SCRIPTS / "hooks"


def _hook_module_names() -> set[str]:
    return {p.stem for p in _HOOKS.glob("*.py") if p.stem != "__init__"}


def _imports_a_sibling(path: Path, siblings: set[str]) -> bool:
    """True when the module imports another hooks module by bare name."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and node.module.split(".")[0] in siblings:
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in siblings:
                    return True
    return False


def _sibling_importers() -> list[str]:
    siblings = _hook_module_names()
    return sorted(
        name for name in siblings if _imports_a_sibling(_HOOKS / f"{name}.py", siblings - {name})
    )


def _imports_a_sibling_at_module_level(path: Path, siblings: set[str]) -> bool:
    """Sibling imported at TOP LEVEL, i.e. needed the moment the module loads."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and node.module.split(".")[0] in siblings:
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in siblings:
                    return True
    return False


def _eager_sibling_importers() -> list[str]:
    """Modules that need scripts/hooks on sys.path AT IMPORT TIME.

    A module whose sibling import sits inside a function (`check_docs`,
    `task_cost_budget_check` import `_common` that way) loads fine without the
    path; it would only fail when that function runs. Demanding an own-directory
    insert from those would be a rule about style, not about a failure — and a
    check that fires where nothing breaks teaches people to ignore it.
    """
    siblings = _hook_module_names()
    return sorted(
        name
        for name in siblings
        if _imports_a_sibling_at_module_level(_HOOKS / f"{name}.py", siblings - {name})
    )


_PROBE = "import sys, importlib\nsys.path.insert(0, sys.argv[1])\nimportlib.import_module('hooks.' + sys.argv[2])\n"


def _import_in_clean_interpreter(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _PROBE, str(_SCRIPTS), name],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO),
        timeout=60,
    )


class TestSiblingImportersAreImportableAsAPackage:
    def test_there_are_sibling_importers_to_check(self):
        """A detector that finds nothing proves nothing — pin that it looks."""
        assert _sibling_importers(), "no hook imports a sibling — the check has no subject"
        assert _eager_sibling_importers(), "no hook imports a sibling at module level"

    @pytest.mark.parametrize("name", _sibling_importers())
    def test_module_imports_as_hooks_dot_name(self, name):
        proc = _import_in_clean_interpreter(name)
        assert proc.returncode == 0, (
            f"hooks.{name} does not import with only scripts/ on sys.path:\n"
            f"{proc.stderr.strip()[-400:]}\n"
            "Add `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` "
            "so the module's own directory is reachable when it is imported "
            "rather than run."
        )


class TestTheConsumerThatWasBroken:
    def test_auto_find_transcript_returns_this_projects_transcript(self):
        """`model_routing` swallows the ImportError, so the symptom was silence."""
        sys.path.insert(0, str(_SCRIPTS))
        import model_routing

        found = model_routing._auto_find_transcript()
        if found is None:
            pytest.skip("no transcript for this project on this machine")
        assert os.path.isfile(found)
        assert found.endswith(".jsonl")

    def test_the_banner_names_a_model_instead_of_unknown(self):
        sys.path.insert(0, str(_SCRIPTS))
        import model_routing

        if model_routing._auto_find_transcript() is None:
            pytest.skip("no transcript for this project on this machine")
        text = model_routing.format_task_start_banner(complexity="medium")
        assert "no transcript readable" not in text
        assert "active:" in text

    def test_absent_transcript_still_reports_unknown_rather_than_a_guess(self):
        """The cure must not become a muffler: no transcript still means unknown.

        A recommendation confident about a model nobody observed is the failure
        this project keeps finding elsewhere (decision #334).
        """
        sys.path.insert(0, str(_SCRIPTS))
        import model_routing

        text = model_routing.format_task_start_banner(
            complexity="medium", transcript_path="/no/such/transcript.jsonl"
        )
        assert "unknown" in text
        assert "no transcript readable" in text


class TestRunningAsAScriptStillWorks:
    """Two live paths, not one: the SessionEnd hook invokes the FILE."""

    def test_session_metrics_runs_as_a_script(self):
        proc = subprocess.run(
            [sys.executable, str(_HOOKS / "session_metrics.py"), "--auto"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(_REPO),
            timeout=180,
        )
        # 0 with metrics, or 0 with "No transcript found" on a machine without
        # one. What must not happen is an ImportError traceback.
        assert "ModuleNotFoundError" not in (proc.stderr or "")
        assert "Traceback" not in (proc.stderr or "")


def _assignments_in(scope: ast.AST) -> dict[str, ast.expr]:
    """Names assigned DIRECTLY in this scope, without descending into nested defs."""
    found: dict[str, ast.expr] = {}
    body = getattr(scope, "body", [])
    for node in body:
        for stmt in ast.walk(node) if not isinstance(node, _SCOPES) else ():
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        found[target.id] = stmt.value
    return found


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _referenced_sources(expr: ast.expr, constants: dict[str, ast.expr]) -> list[str]:
    """The expression's own text plus that of every name it reaches.

    Resolved through the AST rather than by substituting strings, and bounded by
    a seen-set so a self-referential name cannot spin. This exists because most
    hooks insert a NAMED value (`_HOOKS_DIR`, or `os.path.dirname(_HOOK_DIR)`
    two levels down), so judging the insert line's literal text reports a hole
    where there is none — checking the name instead of the fact, the very defect
    this suite keeps finding elsewhere.
    """
    sources: list[str] = []
    pending: list[ast.expr] = [expr]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        text = ast.unparse(node)
        if text in seen:
            continue
        seen.add(text)
        sources.append(text)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in constants:
                pending.append(constants[sub.id])
    return sources


def _is_path_insert(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "insert"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "path"
        and len(node.args) >= 2
    )


def _path_insert_sources(path: Path) -> list[list[str]]:
    """For each `sys.path.insert`, the texts its value is built from.

    Scope-aware on purpose. An earlier version pooled every assignment in the
    file, so function locals named `path`, `proj` and `tausik_dir` were
    substituted into unrelated expressions and produced nonsense like
    `os.(os.(os....(__file__)))`. A name means what it means where it is used.
    """
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    module_names = _assignments_in(tree)
    found: list[list[str]] = []

    def collect(scope: ast.AST, visible: dict[str, ast.expr]) -> None:
        for node in ast.walk(scope):
            if _is_path_insert(node):
                found.append(_referenced_sources(node.args[1], visible))

    scopes: list[tuple[ast.AST, dict[str, ast.expr]]] = []
    for node in ast.walk(tree):
        if isinstance(node, _SCOPES):
            scopes.append((node, {**module_names, **_assignments_in(node)}))

    inner_inserts = {id(n) for scope, _ in scopes for n in ast.walk(scope) if _is_path_insert(n)}
    for node in ast.walk(tree):
        if _is_path_insert(node) and id(node) not in inner_inserts:
            found.append(_referenced_sources(node.args[1], module_names))
    for scope, visible in scopes:
        for node in scope.body:
            for sub in ast.walk(node):
                if _is_path_insert(sub):
                    found.append(_referenced_sources(sub.args[1], visible))
    return found


class TestNoSysPathEntryComesFromAmbientInput:
    """CWD, the environment and argv must never decide what a hook imports.

    NOT "every entry must be `__file__`": some hooks deliberately add the
    DEPLOYED profile's scripts directory, computed from an explicit project
    root. That is a designed mechanism, not a hole, and a check that forbade it
    would be wrong rather than strict. What must never happen is a path taken
    from ambient input, where a neighbouring file can shadow a hook module.
    """

    @pytest.mark.parametrize("name", _sibling_importers())
    def test_no_entry_is_derived_from_cwd_env_or_argv(self, name):
        for sources in _path_insert_sources(_HOOKS / f"{name}.py"):
            joined = " | ".join(sources)
            for forbidden in ("getcwd", "environ", "argv"):
                assert forbidden not in joined, (
                    f"{name}: a sys.path entry reads {forbidden} — {joined!r}"
                )

    @pytest.mark.parametrize("name", _eager_sibling_importers())
    def test_the_own_directory_entry_is_derived_from_dunder_file(self, name):
        """The insert that makes `hooks.<name>` importable, and where it comes from."""
        all_sources = " | ".join(
            " | ".join(sources) for sources in _path_insert_sources(_HOOKS / f"{name}.py")
        )
        assert "__file__" in all_sources, (
            f"{name} imports a sibling but no sys.path entry derives from __file__, "
            "so the module is importable only when RUN, not when imported."
        )

    def test_the_check_would_notice_a_cwd_derived_path(self, tmp_path):
        """A guard nobody has seen fail is not evidence (SENAR): make it fail.

        Two levels of indirection, exactly like the real
        `os.path.dirname(_HOOK_DIR)`: the check must see through the name, not
        stop at it.
        """
        planted = tmp_path / "planted.py"
        planted.write_text(
            "import os, sys\n_D = os.getcwd()\nsys.path.insert(0, os.path.dirname(_D))\n",
            encoding="utf-8",
        )
        found = _path_insert_sources(planted)
        assert found, "the collector found no sys.path.insert at all"
        joined = " | ".join(found[0])
        assert "getcwd" in joined
        assert "__file__" not in joined

    def test_a_local_name_is_resolved_inside_its_own_function(self, tmp_path):
        """Scope, not a global name pool: locals were what produced garbage."""
        planted = tmp_path / "scoped.py"
        planted.write_text(
            "import os, sys\n"
            "def go():\n"
            "    d = os.environ['X']\n"
            "    sys.path.insert(0, d)\n",
            encoding="utf-8",
        )
        joined = " | ".join(_path_insert_sources(planted)[0])
        assert "environ" in joined

    def test_a_file_derived_path_behind_two_names_is_accepted(self, tmp_path):
        """The other direction: no false alarm on the idiom the hooks use."""
        planted = tmp_path / "ok.py"
        planted.write_text(
            "import os, sys\n"
            "_HOOK_DIR = os.path.dirname(os.path.abspath(__file__))\n"
            "sys.path.insert(1, os.path.dirname(_HOOK_DIR))\n",
            encoding="utf-8",
        )
        joined = " | ".join(_path_insert_sources(planted)[0])
        assert "__file__" in joined
        assert "getcwd" not in joined
