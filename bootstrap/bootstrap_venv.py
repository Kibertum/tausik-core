"""TAUSIK bootstrap — venv creation and dependency installation.

Ensures .tausik/venv/ exists with Python >= 3.11 and requirements installed.
Cross-platform: Windows (python / py -3) and Unix (python3 / python).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv

# Minimum Python version for TAUSIK
MIN_PYTHON = (3, 11)
MIN_PYTHON_STR = ".".join(str(v) for v in MIN_PYTHON)

DOWNLOAD_URL = "https://www.python.org/downloads/"
DOWNLOAD_MSG = f"""
  Python >= {MIN_PYTHON_STR} is required but was not found.

  Please install it:
    Windows:  https://www.python.org/downloads/
              or: winget install Python.Python.3.13
    macOS:    brew install python@3.13
    Ubuntu:   sudo apt install python3.13
    Fedora:   sudo dnf install python3.13

  After installing, re-run bootstrap.
"""


def _check_version(python: str) -> tuple[int, ...] | None:
    """Return Python version tuple or None if unusable."""
    try:
        result = subprocess.run(
            [
                python,
                "-c",
                "import sys; print(sys.version_info.major, sys.version_info.minor)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        parts = result.stdout.strip().split()
        if len(parts) != 2:
            return None
        return (int(parts[0]), int(parts[1]))
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError):
        return None


def find_python() -> str | None:
    """Find the best Python interpreter >= MIN_PYTHON.

    Search order:
      1. sys.executable (the Python running bootstrap)
      2. Unix: python3, python  |  Windows: python, py -3
      3. None if nothing found

    Returns absolute path to python or None.
    """
    candidates: list[str] = []

    # The Python running bootstrap is the first candidate
    candidates.append(sys.executable)

    if sys.platform == "win32":
        # Windows: python is usually the right one (python3 is MS Store alias)
        candidates.extend(["python", "py"])
    else:
        # Unix: python3 first, then python
        candidates.extend(["python3", "python"])

    best_path: str | None = None
    best_version: tuple[int, ...] | None = None

    for candidate in candidates:
        ver = _check_version(candidate)
        if ver is None:
            continue
        if ver < MIN_PYTHON:
            continue

        # Resolve to absolute path
        if os.path.isabs(candidate):
            resolved = candidate
        else:
            resolved = shutil.which(candidate)
            if not resolved:
                continue

            # For 'py' launcher on Windows, get the actual python it delegates to
            if os.path.basename(resolved).startswith("py"):
                actual = _resolve_py_launcher(candidate)
                if actual:
                    resolved = actual

        # Pick highest version
        if best_version is None or ver > best_version:
            best_path = resolved
            best_version = ver

    return best_path


def _resolve_py_launcher(py_cmd: str) -> str | None:
    """Resolve Windows 'py' launcher to actual python path."""
    try:
        result = subprocess.run(
            [py_cmd, "-3", "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.isfile(path):
                return path
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_venv_python(tausik_dir: str) -> str | None:
    """Return path to venv python if it exists."""
    if sys.platform == "win32":
        p = os.path.join(tausik_dir, "venv", "Scripts", "python.exe")
    else:
        p = os.path.join(tausik_dir, "venv", "bin", "python3")
        if not os.path.isfile(p):
            p = os.path.join(tausik_dir, "venv", "bin", "python")
    return p if os.path.isfile(p) else None


def ensure_venv(tausik_dir: str) -> str:
    """Create .tausik/venv/ if it doesn't exist. Returns venv python path.

    Raises SystemExit if no suitable Python found.
    """
    venv_dir = os.path.join(tausik_dir, "venv")

    # Check if venv already exists and is valid
    existing = get_venv_python(tausik_dir)
    if existing:
        ver = _check_version(existing)
        if ver and ver >= MIN_PYTHON:
            return existing
        # Version too old — recreate
        print(
            f"  Venv Python is {'.'.join(str(v) for v in ver) if ver else 'broken'}, "
            f"need >= {MIN_PYTHON_STR}. Recreating..."
        )
        shutil.rmtree(venv_dir, ignore_errors=True)

    # Find system Python
    python = find_python()
    if not python:
        print(DOWNLOAD_MSG)
        sys.exit(1)

    ver = _check_version(python)
    ver_str = ".".join(str(v) for v in ver) if ver else "?"
    print(f"  Creating venv with Python {ver_str} ({python})")

    # Create venv with pip
    venv.create(venv_dir, with_pip=True, clear=True)

    result = get_venv_python(tausik_dir)
    if not result:
        print(f"  Error: venv created but python not found in {venv_dir}")
        sys.exit(1)

    return result


def install_requirements(tausik_dir: str, lib_dir: str) -> bool:
    """Install requirements.txt into .tausik/venv/.

    Collects requirements from:
      1. lib_dir/requirements.txt (core)
      2. Future: vendor requirements

    Returns True if installation succeeded.
    """
    venv_python = get_venv_python(tausik_dir)
    if not venv_python:
        print("  Error: venv not found. Run ensure_venv() first.")
        return False

    req_file = os.path.join(lib_dir, "requirements.txt")
    if not os.path.isfile(req_file):
        print("  No requirements.txt found, skipping dependency install.")
        return True

    print("  Installing dependencies from requirements.txt...")
    try:
        result = subprocess.run(
            [venv_python, "-m", "pip", "install", "-r", req_file, "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  pip install failed:\n{result.stderr}")
            return False
        print("  Dependencies installed successfully.")
        return True
    except subprocess.TimeoutExpired:
        print("  pip install timed out (120s). Check your network connection.")
        return False
    except (FileNotFoundError, OSError) as e:
        print(f"  pip install error: {e}")
        return False


def install_cli_wrapper(bootstrap_dir: str, tausik_dir: str) -> None:
    """Copy tausik CLI wrapper scripts (bash + cmd) into .tausik/ and make them executable."""
    import shutil
    import stat

    for wrapper in ("tausik_wrapper.sh", "tausik_wrapper.cmd"):
        src = os.path.join(bootstrap_dir, wrapper)
        if not os.path.exists(src):
            continue
        ext = os.path.splitext(wrapper)[1]
        dst = os.path.join(tausik_dir, f"tausik{ext}" if ext == ".cmd" else "tausik")
        shutil.copy2(src, dst)
        if ext != ".cmd":
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC)
