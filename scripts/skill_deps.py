"""Skill dependency installation — resolving .tausik/venv and driving pip.

Split out of ``skill_manager`` at the 400-line filesize cap. Kept together
because the pip hardening comment, the index constant and the argv it builds
only make sense next to each other.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any

# Passed explicitly to pip so a pip.conf we do not own cannot repoint the index.
# A command-line argument overrides the defaults pip loads from config files.
DEFAULT_PIP_INDEX_URL = "https://pypi.org/simple"

_SAFE_PKG = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9._,-]+\])?(?:[<>=!~]=?[\w.+*-]+)?$"
)


def _resolve_venv_python(tausik_dir: str) -> str | None:
    """Path to .tausik/venv python, whatever the surrounding layout is.

    `bootstrap_venv` sits next to the core checkout, but a bootstrapped project
    receives only `scripts/`: importing it from a sibling `bootstrap/` finds
    nothing there. That ImportError used to be swallowed, so pip dependencies
    declared by a skill were never installed and nothing said why.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.abspath(tausik_dir))
    for cand in (
        os.path.join(here, "..", "bootstrap"),
        os.path.join(here, "..", "..", "bootstrap"),
        os.path.join(project_dir, ".tausik-lib", "bootstrap"),
    ):
        if not os.path.isdir(cand):
            continue
        if cand not in sys.path:
            sys.path.insert(0, cand)
        try:
            from bootstrap_venv import get_venv_python  # type: ignore[import-not-found]
        except ImportError:
            continue
        return get_venv_python(tausik_dir)

    # Core is out of reach; the venv layout is fixed, so derive it directly.
    if sys.platform == "win32":
        candidates = [os.path.join(tausik_dir, "venv", "Scripts", "python.exe")]
    else:
        candidates = [
            os.path.join(tausik_dir, "venv", "bin", "python3"),
            os.path.join(tausik_dir, "venv", "bin", "python"),
        ]
    return next((p for p in candidates if os.path.isfile(p)), None)


def install_skill_deps(repo_dir: str, skill_info: dict[str, Any], tausik_dir: str) -> bool:
    """Install skill pip dependencies into .tausik/venv/.

    Dependencies come from skill_info["requires"] list.
    """
    requires = skill_info.get("requires", [])
    if not requires:
        return True

    bad = [r for r in requires if not isinstance(r, str) or not _SAFE_PKG.match(r)]
    if bad:
        print(f"  REFUSED: unsafe package specs in 'requires': {bad}")
        return False

    print(f"  Installing dependencies: {', '.join(requires)}")
    print(
        "  WARNING: packages come from an external skill manifest. Review before use in production."
    )

    venv_python = _resolve_venv_python(tausik_dir)
    if not venv_python:
        print(
            f"  Warning: venv python not found under {tausik_dir}, cannot install deps: {requires}"
        )
        return False

    # Harden the subprocess so pip cannot be redirected to a hostile index by a
    # PIP_* variable in the parent environment or by a pip.conf we do not own.
    #
    # v1.3.4 (med-batch-1-hooks #2) tried to do this with `--no-config`. That
    # flag does not exist in ANY pip — 22.3.1 (what `ensurepip` ships with
    # Python 3.11) and 26.0.1 both answer `no such option: --no-config` with
    # rc=2. The "hardening" therefore broke every `requires` install instead of
    # protecting it, and the unit test that asserted the flag was mocking
    # subprocess, so it never asked a real pip. See ``TestPipFlagsAreRealFlags``.
    #
    # What actually holds, read out of pip/_internal/configuration.py rather
    # than assumed:
    #   * `iter_config_files` yields GLOBAL and SITE unconditionally, so no flag
    #     and no env var suppresses /etc/pip.conf or <venv>/pip.conf.
    #   * `--isolated` skips USER config and every PIP_* env var. It is real and
    #     present in both pip versions above.
    #   * Config values become optparse *defaults* (cli/parser.py
    #     `_update_defaults`), and an explicit command-line argument overrides a
    #     default. So passing `--index-url` is what genuinely pins the index.
    #
    # Residual, accepted: an `extra-index-url` in a GLOBAL/SITE pip.conf still
    # adds a second index. Nothing short of `--no-index` suppresses that, and
    # that would forbid installing anything at all.
    safe_env = os.environ.copy()
    for var in (
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_TRUSTED_HOST",
        "PIP_INDEX",
        "PIP_FIND_LINKS",
    ):
        safe_env.pop(var, None)

    cmd = [
        venv_python,
        "-m",
        "pip",
        "install",
        "--isolated",
        "--index-url",
        DEFAULT_PIP_INDEX_URL,
        "--quiet",
        "--",
    ] + requires

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=safe_env,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            print(f"  pip install failed: {result.stderr}")
            return False
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"  pip install error: {e}")
        return False
