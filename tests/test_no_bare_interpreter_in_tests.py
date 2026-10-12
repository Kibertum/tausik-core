"""A test must not name an interpreter and hope the PATH agrees.

`subprocess.run(["bash", "./probe.sh"])` reads as "use bash". On the
`windows-latest` image the first `bash` on PATH is `System32\\bash.exe`, the WSL
launcher, and with no distribution installed it exits 1 and prints — in UTF-16 —
that there are none. Three Windows lanes went red on 2026-08-25 and were still
red nine days later, while ubuntu, macos, lint and the full lane stayed green.
Nothing was wrong with the product. The tests were wrong about which program the
name denotes.

TWO GUARDS, because the incident had two halves.

The first is this ratchet: no test may pass a bare interpreter name as argv[0].
A rule over the whole tree, not a repair of the five tests that happened to
fail — the sixth such call, written tomorrow, goes red for its author instead of
nine days later on somebody else's lane. `git` is deliberately not in the set:
it is not shadowed by a launcher stub of a different program, and listing it
would turn a measured rule into a superstition.

The second is `conftest.posix_bash`, asserted below against a stub that behaves
the way the CI image's does — because this developer machine cannot reproduce
the CI condition on its own. WSL here HAS a distribution, so `System32\\bash.exe`
runs scripts and passes the probe; only the ORDER (Git Bash first) decides which
is used. The probe is what rejects the distro-less launcher, the order is what
settles a tie between two working shells, and each is tested for the thing it
actually does.
"""

from __future__ import annotations

import ast
import os
import stat
import subprocess
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

import conftest  # noqa: E402

#: What this file guards. It reads no product module — its subject is the TEST
#: tree itself — so without this declaration no change could ever select it and
#: the scoped runs would skip it silently, which is the failure mode
#: `test_crosscutting_registry` exists to refuse.
CROSSCUTTING_SCOPE = ["tests/"]

#: Programs whose bare name can resolve to a DIFFERENT program on some host.
#: Shells and language interpreters, because those are the ones an OS or a
#: store app shadows with a launcher.
_SHADOWABLE = frozenset(
    {"bash", "sh", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd", "node", "perl", "ruby", "php"}
)

_SUBPROCESS_CALLS = frozenset({"run", "Popen", "check_output", "check_call", "call", "getoutput"})

#: Call sites that predate the rule. May only SHRINK — an entry that no longer
#: exists is stale and this file says so, rather than rotting into a list nobody
#: prunes.
#:
#: Both are in `test_wrapper_smoke.py` and both are measured, not waved through.
#: Its `bash` calls carry `skipif(os.name == "nt" or which("bash") is None)`, so
#: they never run on the platform where the name is ambiguous. Its `cmd` calls
#: carry `skipif(os.name != "nt")` and run ONLY there, where `cmd` is the real
#: `cmd` — no launcher stub of a different program takes that name.
#:
#: The `cmd` entry was found by this ratchet, not by the inventory that preceded
#: it: that inventory counted `bash` call sites and stopped at the name it was
#: looking for. Two counts of the same tree, one wider than the other.
_BASELINE = {
    ("test_wrapper_smoke.py", "bash"),
    ("test_wrapper_smoke.py", "cmd"),
}


def _test_files():
    return sorted(f for f in os.listdir(_TESTS) if f.startswith("test_") and f.endswith(".py"))


def _bare_interpreter_calls():
    """(file, name) for every subprocess call whose argv[0] is a bare name."""
    found = set()
    for fn in _test_files():
        path = os.path.join(_TESTS, fn)
        with open(path, encoding="utf-8") as fh:
            try:
                tree = ast.parse(fh.read(), filename=fn)
            except SyntaxError:  # pragma: no cover — a broken test file fails elsewhere
                continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fnode = node.func
            if not isinstance(fnode, ast.Attribute) or fnode.attr not in _SUBPROCESS_CALLS:
                continue
            argv = node.args[0]
            if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
                continue
            head = argv.elts[0]
            if isinstance(head, ast.Constant) and head.value in _SHADOWABLE:
                found.add((fn, head.value))
    return found


def test_no_test_passes_a_bare_interpreter_name_as_argv0():
    new = _bare_interpreter_calls() - _BASELINE
    assert not new, (
        "these tests name an interpreter and trust the PATH to agree — on "
        "windows-latest `bash` is the WSL launcher, not Git Bash. Resolve it "
        "with `conftest.require_posix_bash()` (or an equivalent probe) instead:\n  "
        + "\n  ".join(sorted("%s: %r" % pair for pair in new))
    )


def test_the_baseline_only_shrinks():
    stale = _BASELINE - _bare_interpreter_calls()
    assert not stale, (
        "remove these from _BASELINE — the call sites are gone, and a ratchet "
        "that never shrinks is just a list:\n  "
        + "\n  ".join(sorted("%s: %r" % pair for pair in stale))
    )


def test_the_detector_is_not_hollow():
    """A detector that finds nothing would pass vacuously forever."""
    assert _bare_interpreter_calls(), "the AST scan matched nothing — it likely broke"


class TestTheProbeRejectsALauncherStub:
    """The CI condition, reproduced rather than described.

    This machine's WSL has a distribution, so the real `System32\\bash.exe` runs
    scripts fine here. A stub is therefore built that behaves the way the CI
    image's launcher does — exit 1, a UTF-16 complaint, no script executed — and
    the resolver is pointed at it.
    """

    @staticmethod
    def _make_stub(directory):
        """A 'bash' that fails the way a distro-less WSL launcher fails."""
        name = "bash.exe" if os.name == "nt" else "bash"
        path = os.path.join(directory, name)
        # A Python script masquerading as bash on POSIX; on Windows the
        # resolver only needs a file that exists and misbehaves when run, and a
        # non-executable one misbehaves exactly so.
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!/usr/bin/env python3\n")
            fh.write("import sys\n")
            fh.write("sys.stdout.buffer.write('no installed distributions'.encode('utf-16-le'))\n")
            fh.write("sys.exit(1)\n")
        if os.name != "nt":
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return path

    def test_a_stub_that_runs_no_script_is_not_accepted(self, tmp_path):
        stub = self._make_stub(str(tmp_path))
        assert conftest._bash_runs_a_script(stub) is False

    def test_a_real_bash_is_accepted(self):
        found = conftest.posix_bash()
        if found is None:
            pytest.skip("no usable bash on this host")
        assert conftest._bash_runs_a_script(found) is True

    def test_the_resolver_skips_past_the_stub_to_a_working_shell(self, tmp_path, monkeypatch):
        """A stub FIRST on PATH must not become the answer."""
        real = conftest.posix_bash()
        if real is None:
            pytest.skip("no usable bash on this host")
        self._make_stub(str(tmp_path))
        monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + (os.environ.get("PATH") or ""))
        monkeypatch.setattr(conftest, "_POSIX_BASH_CACHE", [])
        chosen = conftest.posix_bash()
        assert chosen is not None
        assert os.path.dirname(chosen) != str(tmp_path)

    def test_a_host_with_no_usable_bash_skips_rather_than_fails(self, tmp_path, monkeypatch):
        """Going red about someone else's tooling is the failure being fixed."""
        self._make_stub(str(tmp_path))
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setattr(conftest, "_POSIX_BASH_CACHE", [])
        monkeypatch.setattr(conftest.shutil if hasattr(conftest, "shutil") else os, "sep", os.sep)
        assert conftest.posix_bash() is None
        with pytest.raises(BaseException) as excinfo:
            conftest.require_posix_bash()
        assert "Skipped" in type(excinfo.value).__name__ or "skip" in str(excinfo.value).lower()


def test_the_probe_actually_runs_a_script_file_not_dash_c():
    """The probe must exercise the shape the callers use.

    `bash -c` and `bash ./file.sh` are different capabilities — the second is
    what every caller does, and the one the launcher stub cannot do. Probing
    with `-c` would accept a shell that cannot run the callers' scripts.
    """
    source = subprocess.run(
        [
            sys.executable,
            "-c",
            "import inspect, sys; sys.path.insert(0, %r); "
            "import conftest; print(inspect.getsource(conftest._bash_runs_a_script))" % _TESTS,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    ).stdout
    assert "_bash_probe.sh" in source
    assert '"-c"' not in source
