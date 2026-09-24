"""The directories the framework WRITES — one source for everyone who asks.

complexity-proxy-counts-state-projection (1.10, github#76). Three registries
each listed derived trees by hand and each leaked on the next tree: the
complexity detector knew `docs/_generated/` and not the `tausik/` projection,
so a task that journaled diligently looked more and more understated (9 of 10,
then 23 of 26 declared files were projection files).

The exporters read their layout FROM here (`state_triggers._tree_root`,
`gen_doc_constants.output_json_path`), and every consumer asking "did the
framework write this?" reads `relative_dirs()` — so a new tree is declared once.
`tausik/gates.json` and `tausik/policy.json` are NOT derived: they are
hand-written configuration and stay behaviour-bearing.
"""

from __future__ import annotations

#: The state projection root, beside `.tausik/` (state_triggers._tree_root).
PROJECTION_ROOT = "tausik"
#: Where gen_doc_constants writes its output.
DOC_CONSTANTS_DIR = ("docs", "_generated")


def relative_dirs() -> tuple[str, ...]:
    """Project-relative directories (trailing '/') whose files are generated."""
    from state_serialize import ENTITY_DIRS

    return ("/".join(DOC_CONSTANTS_DIR) + "/",) + tuple(
        f"{PROJECTION_ROOT}/{name}/" for name in ENTITY_DIRS
    )
