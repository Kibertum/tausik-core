"""Regression tests for Windows/Unicode stdio (v156 P1).

The boot bug: on a Windows host whose locale stdout encoding is cp1251/cp1252,
any TAUSIK process that prints Unicode (Cyrillic, ✓, →) crashes with
UnicodeEncodeError. The fix is layered:

  * CLI wrapper exports PYTHONUTF8=1               → tests below (env path)
  * hooks run via `python -X utf8 <hook>`          → tests below (flag path)
  * standalone entry points call fix_stdio_encoding() (bootstrap, MCP servers)
    which reconfigures stdout/stderr at runtime    → tests below (runtime path)

Empirically (Russian-locale Windows): PYTHONUTF8 / -X utf8 fix the *locale
default* but do NOT override an explicit PYTHONIOENCODING (higher precedence);
only the runtime reconfigure does. The tests encode exactly that.

Run: pytest tests/test_unicode_stdio.py -v
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")

# Characters that cp1251 AND cp1252 both fail to encode.
_UNICODE = "✓ привет"  # "✓ привет"


def _clean_env(**overrides):
    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)
    env.update(overrides)
    return env


def _run(args, code, env):
    # errors="replace": these tests deliberately make the CHILD emit mis-encoded
    # (cp1251) bytes. The PARENT decodes captured output with the locale codec, and on
    # a UTF-8 locale (Linux CI) + Python 3.13 a strict decode of those bytes raises
    # UnicodeDecodeError OUT of subprocess.run — the harness crashes instead of the
    # assertion running. Replacing undecodable bytes keeps the harness alive; the
    # ASCII phrase "UnicodeEncodeError" we assert on survives intact.
    return subprocess.run(
        [sys.executable, *args, "-c", code],
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
    )


# --- The bug reproduces (cross-platform via forced cp1251) -------------------


def test_cp1251_stdout_crashes_without_fix():
    """Forcing cp1251 stdout + Unicode print reproduces the UnicodeEncodeError."""
    r = _run([], f"print({_UNICODE!r})", _clean_env(PYTHONIOENCODING="cp1251"))
    assert r.returncode != 0
    assert "UnicodeEncodeError" in r.stderr


# --- Runtime fix: fix_stdio_encoding() (bootstrap + MCP servers) -------------


@pytest.mark.skipif(sys.platform != "win32", reason="fix_stdio_encoding reconfigures only on win32")
def test_fix_stdio_encoding_overrides_locale():
    """fix_stdio_encoding() reconfigures stdout to UTF-8 even over cp1251."""
    code = (
        f"import sys; sys.path.insert(0, {_SCRIPTS!r}); "
        "from tausik_utils import fix_stdio_encoding; fix_stdio_encoding(); "
        f"print({_UNICODE!r})"
    )
    r = _run([], code, _clean_env(PYTHONIOENCODING="cp1251"))
    assert r.returncode == 0, r.stderr


def test_fix_stdio_encoding_is_safe_to_call():
    """AC#5 negative: calling fix_stdio_encoding() never raises, even when the
    stream has no reconfigure attribute (non-Windows no-op / wrapped stream)."""
    code = (
        f"import sys, io; sys.path.insert(0, {_SCRIPTS!r}); sys.stdout = io.StringIO(); "
        "from tausik_utils import fix_stdio_encoding; fix_stdio_encoding(); "
        "sys.stdout = sys.__stdout__; print('OK')"
    )
    r = _run([], code, _clean_env())
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


# --- Env / flag fixes target the LOCALE default (real Windows path) ----------
# These only bite when the interpreter's default stdout encoding is non-UTF-8,
# which is reliably true only on Windows. PYTHONUTF8 / -X utf8 do NOT override
# an explicit PYTHONIOENCODING, so we must NOT set it here.


@pytest.mark.skipif(
    sys.platform != "win32", reason="locale default is UTF-8 off-Windows; nothing to fix"
)
def test_locale_default_crashes_then_pythonutf8_fixes_it():
    """Wrapper path: bare run crashes on the locale default; PYTHONUTF8=1 fixes it."""
    bare = _run([], f"print({_UNICODE!r})", _clean_env())
    assert bare.returncode != 0, "expected locale-default stdout to fail on Unicode"
    fixed = _run([], f"print({_UNICODE!r})", _clean_env(PYTHONUTF8="1"))
    assert fixed.returncode == 0, fixed.stderr


@pytest.mark.skipif(
    sys.platform != "win32", reason="locale default is UTF-8 off-Windows; nothing to fix"
)
def test_x_utf8_flag_fixes_locale_default():
    """Hook path: `python -X utf8` fixes the locale default."""
    fixed = _run(["-X", "utf8"], f"print({_UNICODE!r})", _clean_env())
    assert fixed.returncode == 0, fixed.stderr


# --- The fixes are actually wired into the generated artifacts ---------------


def test_wrappers_set_pythonutf8():
    for name in ("tausik_wrapper.sh", "tausik_wrapper.cmd"):
        text = open(os.path.join(_ROOT, "bootstrap", name), encoding="utf-8").read()
        assert "PYTHONUTF8" in text, f"{name} does not set PYTHONUTF8"


def test_hook_command_builders_use_x_utf8():
    for name in ("bootstrap_generate.py", "bootstrap_qwen.py"):
        text = open(os.path.join(_ROOT, "bootstrap", name), encoding="utf-8").read()
        assert "-X utf8" in text, f"{name} _hook_cmd lost the -X utf8 flag"


def test_mcp_servers_call_fix_stdio_encoding():
    import glob

    servers = glob.glob(os.path.join(_ROOT, "harness", "*", "mcp", "*", "server.py"))
    assert servers, "no MCP server sources found"
    for path in servers:
        text = open(path, encoding="utf-8").read()
        assert "fix_stdio_encoding" in text, f"{path} entry does not call fix_stdio_encoding"


def test_bootstrap_uses_fix_stdio_encoding():
    text = open(os.path.join(_ROOT, "bootstrap", "bootstrap.py"), encoding="utf-8").read()
    assert "fix_stdio_encoding" in text, "bootstrap.py main() no longer calls fix_stdio_encoding"
