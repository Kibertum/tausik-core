"""Integration guard: `output_mode` at the config ROOT must actually reach the rules.

This file exists because the unit tests could not see the bug they were meant to prevent.
`tests/test_caveman_output_mode.py` calls `build_full_body(output_mode="caveman")` and the
generators directly — passing the value in by hand. That proves the generators render the
directive; it proves nothing about whether a user's config ever *delivers* that value.

It did not. `bootstrap_ide` received `config` = `full_cfg["bootstrap"]` (the nested section)
and resolved `output_mode` from it, while the docs (and the resolver's own docstring) put the
key at the ROOT, next to `context_tier`. A user set the documented key, bootstrap printed
"Done!", exited 0 — and no compression was applied, with no warning. A silent no-op: the exact
failure class this release was written to abolish.

So these tests drive the REAL path: write an actual `.tausik/config.json`, run the actual
`bootstrap_ide`, and read the file a user would read.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (os.path.join(_ROOT, "bootstrap"), os.path.join(_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bootstrap as bootstrap_mod  # noqa: E402
from bootstrap_modes import load_bootstrap_config  # noqa: E402

pytestmark = pytest.mark.slow  # spawns real bootstrap work (file copies)


def _make_project(tmp_path, root_config: dict):
    """A project whose .tausik/config.json carries `root_config` at the ROOT."""
    project = tmp_path / "proj"
    (project / ".tausik").mkdir(parents=True)
    cfg = {"bootstrap": {"project": "demo", "core_skills": []}, **root_config}
    (project / ".tausik" / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return project


def _run_bootstrap_ide(project, ide="claude"):
    """Drive the real dispatcher exactly the way main() does."""
    config, full_cfg = load_bootstrap_config(str(project), bootstrap_mod.get_ide_target)
    bootstrap_mod.bootstrap_ide(
        _ROOT,
        str(project),
        ide,
        config,
        ["python"],
        vendor_skills=None,
        venv_python=None,
        context_tier="standard",
        full_cfg=full_cfg,
        brain_enabled=False,
    )


# Where each scaffolded IDE's rules file lands, relative to the project root.
# `kilo` is deliberately absent and asserted so below: it has NO rules generator (it reads
# AGENTS.md, which bootstrap_ide writes separately) — recorded here so its absence reads as a
# decision rather than an oversight.
_RULES_FILE = {
    "claude": "CLAUDE.md",
    "cursor": ".cursorrules",
    "qwen": "QWEN.md",
    "opencode": os.path.join(".opencode", "tausik-rules.md"),
}


class TestEveryScaffoldIdeGetsTheMode:
    """Parametrized over SCAFFOLD_IDES itself, not a list I typed.

    The first version of this file only drove `claude`. That is exactly why it missed the
    dispatcher dropping `output_mode` on the way to `scaffold_opencode` — OpenCode was the one
    IDE of five that silently got "off", and no test looked. Deriving the parameters from the
    code's own list means the next IDE is covered the day it is added, without anyone
    remembering to extend this file.
    """

    def test_rules_file_map_covers_every_scaffold_ide(self):
        """Guard the guard: if a new IDE lands, this fails until its rules file is declared —
        rather than the suite quietly testing four IDEs out of six."""
        from bootstrap_config import SCAFFOLD_IDES

        undeclared = [i for i in SCAFFOLD_IDES if i not in _RULES_FILE and i != "kilo"]
        assert not undeclared, (
            f"scaffolded IDEs with no rules file declared here: {undeclared}. Add them to "
            "_RULES_FILE so the output_mode wiring is actually verified for them."
        )

    @pytest.mark.parametrize("ide", sorted(_RULES_FILE))
    def test_root_caveman_reaches_this_ide(self, tmp_path, ide):
        project = _make_project(tmp_path, {"output_mode": "caveman"})
        _run_bootstrap_ide(project, ide=ide)
        rules = project / _RULES_FILE[ide]
        assert rules.is_file(), f"{ide}: no rules file generated at {rules}"
        assert "caveman mode" in rules.read_text(encoding="utf-8"), (
            f"{ide}: the documented ROOT output_mode=caveman never reached its rules file — "
            "the dispatcher is dropping the value on the way to this IDE's generator"
        )

    @pytest.mark.parametrize("ide", sorted(_RULES_FILE))
    def test_off_by_default_for_this_ide(self, tmp_path, ide):
        project = _make_project(tmp_path, {})
        _run_bootstrap_ide(project, ide=ide)
        assert "caveman mode" not in (project / _RULES_FILE[ide]).read_text(encoding="utf-8")

    def test_kilo_has_no_rules_generator_by_design(self):
        """Kilo reads AGENTS.md (written by bootstrap_ide for every non-opencode host), so it has
        no rules file of its own. Pinned so a future reader does not 'fix' its absence."""
        from bootstrap_config import SCAFFOLD_IDES

        assert "kilo" in SCAFFOLD_IDES
        assert "kilo" not in _RULES_FILE


class TestRootOutputModeReachesTheRules:
    """THE regression test. It fails on the pre-fix tree."""

    def test_root_caveman_lands_in_claude_md(self, tmp_path):
        project = _make_project(tmp_path, {"output_mode": "caveman"})
        _run_bootstrap_ide(project)
        body = (project / "CLAUDE.md").read_text(encoding="utf-8")
        assert "caveman mode" in body, (
            "the documented ROOT `output_mode: caveman` did not reach CLAUDE.md — the knob is "
            "a silent no-op (this is the bug this file exists for)"
        )

    def test_root_caveman_lands_in_agents_md(self, tmp_path):
        project = _make_project(tmp_path, {"output_mode": "caveman"})
        _run_bootstrap_ide(project)
        assert "caveman mode" in (project / "AGENTS.md").read_text(encoding="utf-8")

    def test_off_by_default_produces_no_directive(self, tmp_path):
        """The converse: no key → no directive. Guards against always-on."""
        project = _make_project(tmp_path, {})
        _run_bootstrap_ide(project)
        assert "caveman mode" not in (project / "CLAUDE.md").read_text(encoding="utf-8")

    def test_bootstrap_section_key_is_not_the_documented_location(self, tmp_path):
        """`output_mode` nested under `bootstrap` is NOT the documented spot; it must not
        silently work there either, or we would have two contradictory truths."""
        project = tmp_path / "p2"
        (project / ".tausik").mkdir(parents=True)
        (project / ".tausik" / "config.json").write_text(
            json.dumps(
                {"bootstrap": {"project": "demo", "core_skills": [], "output_mode": "caveman"}}
            ),
            encoding="utf-8",
        )
        _run_bootstrap_ide(project)
        assert "caveman mode" not in (project / "CLAUDE.md").read_text(encoding="utf-8")


class TestExistingFilesAreNotSilentlySkipped:
    """Generators are preserve-if-exists. Flipping the knob on an already-bootstrapped
    project therefore changes nothing on disk — which must be SAID, not swallowed."""

    def test_warns_when_existing_file_lacks_the_requested_directive(self, tmp_path, capsys):
        project = _make_project(tmp_path, {"output_mode": "caveman"})
        (project / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\nhand-written, no directive\n", encoding="utf-8"
        )
        _run_bootstrap_ide(project)
        out = capsys.readouterr().out
        assert "output_mode" in out and "caveman" in out, (
            "bootstrap applied nothing and said nothing — the user believes compression is on"
        )
        # The user's file is theirs: we warn, we do not rewrite it.
        assert "hand-written" in (project / "CLAUDE.md").read_text(encoding="utf-8")

    def test_no_warning_when_existing_file_already_has_the_directive(self, tmp_path, capsys):
        project = _make_project(tmp_path, {"output_mode": "caveman"})
        (project / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n## Output economy (caveman mode)\n", encoding="utf-8"
        )
        _run_bootstrap_ide(project)
        out = capsys.readouterr().out
        assert "already exists" not in out.lower() or "caveman mode" not in out.lower()

    def test_no_warning_when_mode_is_off(self, tmp_path, capsys):
        """No crying wolf on the default path."""
        project = _make_project(tmp_path, {})
        (project / "CLAUDE.md").write_text("# CLAUDE.md\n\nexisting\n", encoding="utf-8")
        _run_bootstrap_ide(project)
        assert "output_mode" not in capsys.readouterr().out
