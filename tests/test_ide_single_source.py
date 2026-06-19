"""Guard tests locking the single-source-of-truth for the bootstrap IDE list (v156 P4).

Three previously-divergent lists (_IDE_DIRS, `--ide all`, the wrapper loop) were
reconciled in P0 into two canonical constants in bootstrap_config:

  * IDE_DIRS      — every .{ide}/ dir the CLI wrapper may discover (6)
  * SCAFFOLD_IDES — IDEs with a real generate_*_config branch; the only
                    individually-selectable `--ide` targets and what `--ide all`
                    expands to (4)

These tests fail the moment someone reintroduces a hardcoded IDE list or breaks
the IDE_DIRS ⊇ SCAFFOLD_IDES invariant.

Run: pytest tests/test_ide_single_source.py -v
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BOOTSTRAP = os.path.join(_ROOT, "bootstrap")
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

from bootstrap_config import IDE_DIRS, SCAFFOLD_IDES  # noqa: E402


def test_scaffold_ides_subset_of_ide_dirs():
    """Every scaffold-capable IDE must have a discoverable config dir."""
    assert set(SCAFFOLD_IDES) <= set(IDE_DIRS), (
        f"SCAFFOLD_IDES has entries missing from IDE_DIRS: {set(SCAFFOLD_IDES) - set(IDE_DIRS)}"
    )


def test_windsurf_codex_discoverable_but_not_scaffolded():
    """windsurf/codex are wrapper-discoverable (IDE_DIRS) but have no generator,
    so they are intentionally absent from SCAFFOLD_IDES. Documents the split."""
    for ide in ("windsurf", "codex"):
        assert ide in IDE_DIRS
        assert ide not in SCAFFOLD_IDES


def test_kilo_is_scaffold_capable():
    """v156: Kilo must be both discoverable and scaffold-capable (the P0 fix)."""
    assert "kilo" in IDE_DIRS
    assert "kilo" in SCAFFOLD_IDES


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
        text = open(path, encoding="utf-8").read()
        for m in pattern.finditer(text):
            offenders.append(f"{os.path.basename(path)}: {m.group(0)}")
    assert not offenders, "hardcoded IDE list reintroduced: " + "; ".join(offenders)
