"""Guard tests locking the single-source-of-truth for the bootstrap IDE list (v156 P4).

The P0 reconciliation folded three divergent lists into bootstrap_config; the
four-ide-registries-collapse finished the job — bootstrap_config no longer even
holds its own copy:

  * IDE_REGISTRY   (ide_utils)   — the one registry of per-host facts
  * IDE_DIRS       (bootstrap_config) — DERIVED config_dir column of the registry
  * SCAFFOLD_IDES  (bootstrap_config) — hosts with a real generate_* branch
  * VALID_IDES     (skill_profile_detect) — DERIVED: exactly SCAFFOLD_IDES

These tests fail the moment someone reintroduces a hardcoded IDE list or breaks
the IDE_DIRS ⊇ SCAFFOLD_IDES invariant.

Run: pytest tests/test_ide_single_source.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BOOTSTRAP = os.path.join(_ROOT, "bootstrap")
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

from bootstrap_config import IDE_DIRS, SCAFFOLD_IDES  # noqa: E402
from pathlib import Path  # noqa: E402


def test_scaffold_ides_subset_of_ide_dirs():
    """Every scaffold-capable IDE must have a discoverable config dir."""
    assert set(SCAFFOLD_IDES) <= set(IDE_DIRS), (
        f"SCAFFOLD_IDES has entries missing from IDE_DIRS: {set(SCAFFOLD_IDES) - set(IDE_DIRS)}"
    )


def test_ide_dirs_is_derived_from_the_registry():
    """four-ide-registries-collapse: IDE_DIRS is not a second copy — it is the
    registry's config_dir column. A new host registered in IDE_REGISTRY is
    therefore discoverable by the wrapper with no further edit."""
    from ide_utils import IDE_REGISTRY

    assert IDE_DIRS == {ide: entry["config_dir"] for ide, entry in IDE_REGISTRY.items()}


def test_ide_profile_alphabet_is_exactly_the_scaffold_list():
    """`config set ide_profile <slug>` must accept every host bootstrap can
    scaffold and nothing else — opencode was refused as unknown while fully
    scaffolded, which is what four-ide-registries-collapse fixed."""
    from skill_profile_detect import VALID_IDES

    assert VALID_IDES == frozenset(SCAFFOLD_IDES)


def test_unknown_ide_is_unknown_on_every_surface():
    """NEGATIVE: a name no registry knows is rejected by every surface — no
    surface carries its own broader alphabet that would accept it."""
    import ide_utils
    import providers

    unknown = "not-an-ide"
    assert unknown not in IDE_DIRS
    assert unknown not in SCAFFOLD_IDES
    assert unknown not in ide_utils.IDE_REGISTRY
    from skill_profile_detect import VALID_IDES

    assert unknown not in VALID_IDES
    with pytest.raises(KeyError):
        providers.get(unknown)


def test_windsurf_discoverable_but_not_scaffolded():
    """windsurf is wrapper-discoverable (IDE_DIRS) but has no generator, so it is
    intentionally absent from SCAFFOLD_IDES. Documents the split.

    `codex` sat here too until session #241, when it got `bootstrap_codex` and
    moved to the scaffold-capable test below. The split itself is the point and
    survives: membership in SCAFFOLD_IDES is a promise, and it is kept backed by
    a generator rather than by intent.
    """
    assert "windsurf" in IDE_DIRS
    assert "windsurf" not in SCAFFOLD_IDES


@pytest.mark.parametrize(
    ("ide", "why"),
    [
        pytest.param("kilo", "v156: the P0 fix — discoverable AND scaffold-capable", id="kilo"),
        pytest.param(
            "codex",
            "session #241: Codex has a hook API (measured on codex.exe), so it is a "
            "first-class target rather than a wrapper-discoverable directory",
            id="codex",
        ),
    ],
)
def test_is_scaffold_capable(ide, why):
    """Both halves matter: discoverable by the wrapper AND backed by a generator.

    One test over both, because the assertion is one — a per-IDE copy says
    nothing the parameter does not, and the next host would add a third.
    """
    assert ide in IDE_DIRS, why
    assert ide in SCAFFOLD_IDES, why


def test_argparse_ide_choices_derive_from_scaffold_ides():
    """The --ide choices must be exactly SCAFFOLD_IDES + 'all' — no hand-maintained list."""
    from bootstrap_modes import build_parser

    parser = build_parser()
    action = next(a for a in parser._actions if "--ide" in getattr(a, "option_strings", []))
    assert list(action.choices) == [*SCAFFOLD_IDES, "all"]


def test_ide_all_expands_to_scaffold_ides():
    """`--ide all` must expand to exactly SCAFFOLD_IDES (verified via the source expression)."""
    import inspect

    import bootstrap

    src = inspect.getsource(
        bootstrap.run_bootstrap if hasattr(bootstrap, "run_bootstrap") else bootstrap.main
    )
    # The reduction line: ides = list(SCAFFOLD_IDES) if args.ide == "all" else [args.ide]
    assert "list(SCAFFOLD_IDES)" in src, "--ide all no longer derives from SCAFFOLD_IDES"


def test_no_hardcoded_ide_list_literal_in_bootstrap():
    """No source file under bootstrap/ should hardcode the IDE list as a literal
    sequence (it must reference IDE_DIRS / SCAFFOLD_IDES instead)."""
    import glob
    import re

    # A literal listing 3+ known IDEs in sequence — the anti-pattern P0 removed.
    pattern = re.compile(
        r'["\']claude["\'].{0,40}["\']cursor["\'].{0,40}["\'](?:qwen|kilo|windsurf)["\']'
    )
    offenders = []
    for path in glob.glob(os.path.join(_BOOTSTRAP, "*.py")):
        if os.path.basename(path) == "bootstrap_config.py":
            continue  # the canonical definitions live here
        text = Path(path).read_text(encoding="utf-8")
        for m in pattern.finditer(text):
            offenders.append(f"{os.path.basename(path)}: {m.group(0)}")
    assert not offenders, "hardcoded IDE list reintroduced: " + "; ".join(offenders)
