"""Guard: the MCP server's `sys.path` insert must resolve in every DEPLOYED profile.

`harness/claude/mcp/project/tools_spec.py` puts `../../scripts` on `sys.path`
at import time and then imports `service_specs` from it. Two levels up is the
arithmetic of the DEPLOYED layout -- `.claude/mcp/project/` -> `.claude/scripts`
-- and that is the only layout in which the module runs as a server.

NOTHING ASSERTED THAT UNTIL NOW. A bootstrap change that moved `scripts/` one
level in a profile would break the server's import at startup, and no test in
the tree would have noticed: inserting a path that does not exist raises
nothing, so the failure surfaces later as an ImportError whose cause is already
out of view.

MEASURED, and the measurement is why this file exists instead of a "fail
loudly" patch inside `tools_spec`: six copies of the module exist -- five
deployed profiles where the directory IS there, and the source tree where it is
NOT, because the repository keeps `scripts/` at its root rather than under
`harness/claude/`. Making the insert loud would break the source tree, where
the absence is legitimate and the importers (this suite's conftest) put
`scripts/` on the path themselves. So the invariant is stated where it is true.

Profiles are found by WALKING, never by a typed list -- and the walk must
descend into dot-directories, which `glob` does not. That is not a stylistic
note: measuring this with `glob("**/tools_spec.py")` finds ONE copy instead of
six and reports the path as broken everywhere.

THE CHECK TAKES A ROOT so it can be pointed at a SYNTHETIC tree. A guard that
only ever runs over a healthy real tree is green whether or not it works, and
breaking the real one to prove otherwise would mean writing outside this task's
declared scope. Both broken shapes are therefore built in a tmp dir and fed to
the same function the real assertions use.
"""

from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Walked, not enumerated: a sixth profile added by bootstrap is guarded on
# arrival. `scripts/` is the directory the insert must reach; `service_specs`
# is the module the import actually needs, so both are checked -- a directory
# that exists but is empty would satisfy the first and still fail the server.
CROSSCUTTING_SCOPE = ["harness/", "bootstrap/"]

_MODULE = "tools_spec.py"
_NEEDED = "service_specs.py"
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".tausik"}


def deployed_copies(root: str) -> list[str]:
    """Directories holding a DEPLOYED `tools_spec.py` (the source tree excluded).

    The source copy is excluded deliberately, not overlooked: `harness/claude/`
    has no `scripts/` sibling and never will, because the repository keeps its
    scripts at the root. Including it would turn this guard into an assertion
    that the repository is laid out like a deployed profile, which it is not.
    """
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        if _MODULE not in filenames:
            continue
        rel = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel.startswith("harness/"):
            continue
        found.append(dirpath)
    return sorted(found)


def unresolved_profiles(root: str) -> list[str]:
    """Deployed profiles whose `../../scripts` would not serve the import."""
    broken: list[str] = []
    for project_dir in deployed_copies(root):
        scripts = os.path.normpath(os.path.join(project_dir, "..", "..", "scripts"))
        profile = os.path.relpath(project_dir, root).replace("\\", "/")
        shown = os.path.relpath(scripts, root).replace("\\", "/")
        if not os.path.isdir(scripts):
            broken.append(f"{profile}: {shown} is not a directory")
        elif not os.path.isfile(os.path.join(scripts, _NEEDED)):
            broken.append(f"{profile}: {shown} has no {_NEEDED}")
    return broken


def _make_profile(base: str, name: str, *, scripts: bool = True, module: bool = True) -> None:
    project = os.path.join(base, name, "mcp", "project")
    os.makedirs(project, exist_ok=True)
    open(os.path.join(project, _MODULE), "w").close()
    if scripts:
        sdir = os.path.join(base, name, "scripts")
        os.makedirs(sdir, exist_ok=True)
        if module:
            open(os.path.join(sdir, _NEEDED), "w").close()


# --- the check itself, on synthetic trees that CAN fail ---------------------


def test_a_synthetic_profile_laid_out_correctly_is_accepted(tmp_path):
    """The neighbouring bucket: a check that flags everything proves nothing."""
    _make_profile(str(tmp_path), ".claude")
    assert deployed_copies(str(tmp_path))
    assert unresolved_profiles(str(tmp_path)) == []


def test_a_profile_with_no_scripts_dir_is_reported(tmp_path):
    _make_profile(str(tmp_path), ".claude", scripts=False)
    found = unresolved_profiles(str(tmp_path))
    assert len(found) == 1
    assert "is not a directory" in found[0]


def test_a_scripts_dir_without_the_needed_module_is_reported(tmp_path):
    """A directory that exists but is empty satisfies `isdir` and fails the
    server — the shape a check written on `isdir` alone would let through."""
    _make_profile(str(tmp_path), ".claude", module=False)
    found = unresolved_profiles(str(tmp_path))
    assert len(found) == 1
    assert _NEEDED in found[0]


def test_the_walk_descends_into_dot_directories(tmp_path):
    """Pins the trap that broke the first measurement of this very defect.

    Every profile lives in a directory starting with `.`, and `glob` skips
    those by default: measuring with `glob("**/tools_spec.py")` found one copy
    instead of six and made a healthy layout look broken everywhere.
    """
    _make_profile(str(tmp_path), ".hidden-profile")
    assert deployed_copies(str(tmp_path)), "the walk skipped a dot-directory"


# --- the invariant over the real tree ---------------------------------------


def test_the_walk_finds_deployed_profiles_at_all():
    """Without this the assertion below is green on an empty list."""
    assert deployed_copies(_ROOT), (
        "no deployed MCP profile found — either bootstrap has not run, or the "
        "walk stopped descending into dot-directories and this guard is checking "
        "nothing"
    )


def test_every_deployed_profile_resolves_the_scripts_dir():
    broken = unresolved_profiles(_ROOT)
    assert not broken, (
        "the MCP server's `sys.path` insert (`../../scripts`) does not resolve in "
        "these deployed profiles — the server would fail to import service_specs "
        "at startup:\n  " + "\n  ".join(broken)
    )


def test_the_resolved_scripts_dir_belongs_to_the_profile_itself():
    """Two levels must reach the PROFILE's own scripts, not the repository's.

    This assertion started life as "the neighbouring level counts do not
    resolve", and measuring it proved that false: three levels up from a
    deployed `mcp/project/` lands on the REPOSITORY root, whose `scripts/` also
    contains `service_specs.py`. Both counts resolve, so resolvability cannot
    tell the right one from the wrong one.

    Whose scripts it is can. A profile that reached the repository's scripts
    would work in this checkout and fail wherever the profile is installed
    without the source tree beside it — a failure that would appear only on a
    user's machine. Sessions #209 and #210 both miscounted these levels; this
    is what makes the count evidence instead of coincidence.
    """
    for project_dir in deployed_copies(_ROOT):
        scripts = os.path.normpath(os.path.join(project_dir, "..", "..", "scripts"))
        profile_root = os.path.normpath(os.path.join(project_dir, "..", ".."))
        profile = os.path.relpath(profile_root, _ROOT).replace("\\", "/")
        assert os.path.dirname(scripts) == profile_root, (
            f"{profile}: the insert resolves outside the profile, to "
            f"{os.path.relpath(scripts, _ROOT)}"
        )
        assert profile_root != _ROOT, (
            f"{profile}: a deployed profile must not resolve to the repository "
            f"root — it would depend on the source tree being installed with it"
        )
