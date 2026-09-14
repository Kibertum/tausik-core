"""Every generator that writes a rules file must warn when the mode cannot apply.

MEASURED FIRST, AND THE MEASUREMENT REFUTED THE PREMISE IT WAS GATHERED UNDER.
The task behind this file said the output-economy directive "reaches the agent
ONCE at bootstrap, not every turn". Answered by running things, session #230:

  * The SessionStart hook injects 7,263 bytes (~1,815 tokens) of context and does
    NOT carry the directive — the marker "Output economy" is absent from it.
  * The directive lives in the RULES FILE, and the harness supplies the rules
    file as project instructions in EVERY request. That is observable directly:
    CLAUDE.md's content sits in this session's own system prompt hours in. So
    delivery is per-turn; what happens once is the WRITE.
  * It survives compaction by construction, because rules are in the request
    PREFIX and compaction shortens the conversation history.
  * Cost: the directive is capped at 888 characters (~222 tokens; 700 before
    the 1.9 response contract) against a median per-call context of 276,702 —
    0.08%, against a measured ceiling of about 2% saved. It repays roughly
    twenty-five times over.

WHAT THE MEASUREMENT DID FIND is what this file guards. All five generators that
write a rules file — claude, agents, cursorrules, qwen, opencode — call
`warn_output_mode_not_applied` today. Nothing stops a sixth from forgetting, and
a host whose generator stays silent leaves the user believing compression is on
while nothing was written: the silent no-op the framework refuses to ship, and
precisely the "guarantees are not Claude-only" promise.

The check reads the AST rather than a list of function names, because a list
would grow separately from the code it describes — which is how the divergence
this release keeps finding gets in.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_BOOTSTRAP = _REPO / "bootstrap"

CROSSCUTTING_SCOPE = ["bootstrap/"]

#: A function BUILDS a rules body when it calls one of these. Recognising the
#: builder rather than the file name is what keeps a differently-named host's
#: generator inside the check.
_BODY_BUILDERS = ("build_full_body", "build_rules_body")
_WARNING = "warn_output_mode_not_applied"


def _called_names(node: ast.AST) -> set[str]:
    """Names actually CALLED inside a function, by AST rather than by substring.

    The first version of this check matched the builder's name anywhere in the
    source, so `build_full_body` matched ITSELF — the builder was reported as a
    generator that forgot to warn. Checking the name instead of the call is the
    defect this suite keeps finding elsewhere; it does not get a pass here.
    """
    names: set[str] = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def rules_generators(root: Path) -> dict[str, bool]:
    """{function: calls the warning} for every function that WRITES a rules file.

    A generator both calls a body builder and writes the result. Requiring the
    write excludes the builder itself and any helper that merely composes text.
    """
    writes = {"write", "write_text", "open"}
    found: dict[str, bool] = {}
    for path in sorted(root.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in _BODY_BUILDERS:
                continue
            called = _called_names(node)
            if not (called & set(_BODY_BUILDERS)) or not (called & writes):
                continue
            found[f"{path.name}::{node.name}"] = _WARNING in called
    return found


class TestEveryRulesGeneratorWarns:
    def test_the_check_has_a_subject(self):
        """A detector that finds nothing proves nothing."""
        generators = rules_generators(_BOOTSTRAP)
        assert len(generators) >= 5, (
            f"expected at least the five known rules generators, found {sorted(generators)}"
        )

    def test_none_of_them_is_silent(self):
        silent = sorted(name for name, warns in rules_generators(_BOOTSTRAP).items() if not warns)
        assert not silent, (
            f"these generators write a rules file without calling {_WARNING}: {silent}. "
            "On that host `output_mode: caveman` would be accepted, written nowhere, and "
            "reported as done — the user believes compression is on while the rules file "
            "was preserved untouched."
        )


class TestTheCheckWouldNoticeASilentGenerator:
    """Made to fail, on a planted module, so the guard is evidence not decoration."""

    def _plant(self, tmp_path: Path, body: str) -> Path:
        (tmp_path / "bootstrap_planted.py").write_text(body, encoding="utf-8")
        return tmp_path

    def test_a_generator_without_the_warning_is_caught(self, tmp_path):
        root = self._plant(
            tmp_path,
            "def generate_planted_md(p, mode):\n"
            "    text = build_full_body(p, mode)\n"
            "    open(p, 'w').write(text)\n",
        )
        found = rules_generators(root)
        assert found == {"bootstrap_planted.py::generate_planted_md": False}

    def test_a_generator_with_the_warning_passes(self, tmp_path):
        root = self._plant(
            tmp_path,
            "def generate_planted_md(p, mode):\n"
            "    text = build_full_body(p, mode)\n"
            "    warn_output_mode_not_applied(p, mode)\n"
            "    open(p, 'w').write(text)\n",
        )
        assert rules_generators(root) == {"bootstrap_planted.py::generate_planted_md": True}

    def test_a_function_that_builds_nothing_is_not_a_generator(self, tmp_path):
        """The check keys on building the rules body, not on being called
        `generate_*` — a name-based rule would miss a differently-named host and
        flag helpers that write no rules at all."""
        root = self._plant(tmp_path, "def generate_something_else(p):\n    return 1\n")
        assert rules_generators(root) == {}


class TestTheDirectiveStaysTheOnlyLeverAndStaysSmall:
    def test_the_cap_is_pinned(self):
        """The measuring task did not add a lever or resize it (700). The 1.9
        response contract moved the cap to its measured 888 — by measurement,
        not by rounding up; `tests/test_response_contract_shape.py` pins the
        no-headroom half of that."""
        import sys

        sys.path.insert(0, str(_BOOTSTRAP))
        from bootstrap_templates import CAVEMAN_DIRECTIVE, CAVEMAN_DIRECTIVE_MAX_CHARS

        assert CAVEMAN_DIRECTIVE_MAX_CHARS == 888
        assert len(CAVEMAN_DIRECTIVE) <= CAVEMAN_DIRECTIVE_MAX_CHARS

    def test_the_session_start_hook_does_not_carry_a_second_copy(self):
        """Two deliveries of one rule is the duplication the border forbids."""
        source = (_REPO / "scripts" / "hooks" / "session_start.py").read_text(
            encoding="utf-8", errors="replace"
        )
        assert "Output economy" not in source
        assert "CAVEMAN" not in source
