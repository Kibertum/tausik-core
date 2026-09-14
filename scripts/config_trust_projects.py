"""Per-project overlays inside a trusted configuration tier.

The user (``~/.tausik/config.json``) and managed tiers are per-machine. Gotcha
#690 measured what that costs: a workaround an operator wrote for ONE consumer
project sat at the top level of the user tier and silently governed every
project on the box, and ``doctor`` on a fresh project had to notice a foreign
``auto_verify`` and tighten it back. This module is the scoped alternative —
a ``projects`` object whose keys are absolute project directories and whose
values are overlays that apply only to that directory. Identity is decided by
``realpath`` plus ``normcase``, never by a name the repository could choose.

Stdlib-only and import-light like ``config_trust``, which composes these
helpers into its layers; hooks read both as a fresh subprocess.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("config_trust")

#: Per-project overlays inside a trusted tier.
PROJECTS_KEY = "projects"


def project_key(project_dir: str) -> str:
    """The spelling under which a ``projects`` entry matches a project directory.

    Identity, not form: the operator may write forward or back slashes and any
    case, and Windows hands out 8.3 short names for ``TMP`` — ``realpath`` plus
    ``normcase`` settles all of those the way ``find_tausik_dir`` settles the
    home tier (memory: compare directories by realpath, not by spelling).
    """
    return os.path.normcase(os.path.realpath(os.path.expanduser(project_dir)))


def scoped_entry(layer: dict, tier: str, project_dir: str | None) -> dict:
    """The ``projects`` overlay of *layer* that names *project_dir*, else ``{}``.

    A malformed section or entry is ignored with a warning — never a crash and
    never applied to every project by accident. ``None`` for *project_dir*
    (a caller that cannot say which project it speaks for) matches nothing.
    """
    section = layer.get(PROJECTS_KEY)
    if section is None:
        return {}
    if not isinstance(section, dict):
        logger.warning("%s config: %r must be an object — section ignored", tier, PROJECTS_KEY)
        return {}
    if project_dir is None:
        return {}
    wanted = project_key(project_dir)
    for spelled, entry in section.items():
        if not isinstance(spelled, str) or project_key(spelled) != wanted:
            continue
        if not isinstance(entry, dict):
            logger.warning(
                "%s config: %s[%r] must be an object — entry ignored", tier, PROJECTS_KEY, spelled
            )
            return {}
        return entry
    return {}


def machine_wide(layer: dict) -> dict:
    """*layer* without its ``projects`` section — the part that governs every project."""
    return {k: v for k, v in layer.items() if k != PROJECTS_KEY}
