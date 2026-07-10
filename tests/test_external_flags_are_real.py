"""Flags we hand to an external binary must be accepted by that binary.

Release 1.6.0 grew out of `--no-config`: a pip flag that exists in no version of
pip, which shipped across two minors because the only test mocked subprocess. A
mock pins our *belief* about a third party's contract, not the contract. These
tests ask the real binary.

Two probes, both offline:
  * git — a validating subcommand exits 129 "unknown option" on a bogus flag, so
    a real flag is anything that does NOT. rev-parse is lenient (passes unknown
    flags through) so its flags are checked behaviourally instead.
  * everything else — the flag token must appear in the tool's `--help` text.

A binary that is not installed is skipped, never passed by default. Each probe is
guarded by a known-bogus case, so a probe that has silently stopped working fails
loudly rather than green-lighting anything.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

_TIMEOUT = 30


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT,
        stdin=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# git — the flags this codebase assembles by hand (skill_git, supply_eol,
# skill_manager, cli_push_ok, risk_compute, verify_git_diff, bootstrap).
# ---------------------------------------------------------------------------


def _git_repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    for a in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "a@b.c"],
        ["config", "user.name", "t"],
    ):
        _run(["git", "-C", str(d), *a])
    (d / "f.txt").write_text("x", encoding="utf-8")
    _run(["git", "-C", str(d), "add", "-A"])
    _run(["git", "-C", str(d), "commit", "-qm", "one"])
    return d


# (subcommand, flag) for subcommands that reject unknown options with rc 129.
_GIT_VALIDATING = [
    ("ls-files", "-z"),
    ("ls-files", "--full-name"),
    ("cat-file", "--batch-check"),
    ("pull", "--ff-only"),
    ("config", "--local"),
    ("config", "--get"),
    ("branch", "--show-current"),
    ("diff", "--numstat"),
    ("diff", "--name-only"),
    ("log", "--name-only"),
    ("rev-parse", "--short"),  # rev-parse rejects unknown -- flags at parse for these
]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
class TestGitFlagsAreRealFlags:
    def _rc(self, tmp_path, sub, flag) -> tuple[int, str]:
        repo = _git_repo(tmp_path)
        r = _run(["git", "-C", str(repo), sub, flag])
        return r.returncode, r.stderr

    def test_probe_rejects_a_bogus_flag(self, tmp_path):
        """Guard: a validating subcommand must return 129 on nonsense."""
        rc, err = self._rc(tmp_path, "ls-files", "--totally-bogus-xyz")
        assert rc == 129 and "unknown option" in err.lower(), (
            "if this fails the probe can no longer say no — it is worthless"
        )

    @pytest.mark.parametrize("sub,flag", _GIT_VALIDATING, ids=lambda v: str(v))
    def test_real_flag_is_not_unknown(self, tmp_path, sub, flag):
        rc, err = self._rc(tmp_path, sub, flag)
        assert not (rc == 129 and "unknown option" in err.lower()), (
            f"git {sub} rejected {flag!r} as unknown"
        )

    def test_rev_parse_behavioural_flags(self, tmp_path):
        """rev-parse passes unknown flags through, so probe by behaviour."""
        repo = _git_repo(tmp_path)
        inside = _run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"])
        assert inside.stdout.strip() == "true"
        top = _run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"])
        assert top.returncode == 0 and top.stdout.strip()
        # --show-prefix: empty at root, "sub/" one level down.
        (repo / "sub").mkdir()
        pref = _run(["git", "-C", str(repo / "sub"), "rev-parse", "--show-prefix"])
        assert pref.stdout.strip() == "sub/"

    def test_eol_pins_are_accepted_by_clone(self, tmp_path):
        """`-c core.autocrlf=false -c core.eol=lf` — the CRLF fix's pins.

        git accepts any `-c key=val`, so this proves the clone form parses; that
        the keys DO something is proven behaviourally in test_skill_manager /
        test_supply_eol (the clone reproduces the publisher's bytes).
        """
        src = _git_repo(tmp_path)
        url = src.as_uri()
        dst = tmp_path / "clone"
        r = _run(
            ["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "clone", "-q", url, str(dst)]
        )
        assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------------------
# Stack-gate + universal-gate + formatter commands: the flag token must appear
# in the tool's --help. Skipped per-binary when the tool is absent.
# ---------------------------------------------------------------------------


def _gate_commands() -> list[tuple[str, str]]:
    """(source, command-string) for every gate command that carries a flag."""
    import glob
    import json
    import re

    out: list[tuple[str, str]] = []
    for path in sorted(
        glob.glob(os.path.join(os.path.dirname(__file__), "..", "stacks", "*", "stack.json"))
    ):
        with open(path, encoding="utf-8") as f:
            decl = json.load(f)
        for gname, gcfg in (decl.get("gates") or {}).items():
            cmd = gcfg.get("command") if isinstance(gcfg, dict) else None
            if cmd and re.search(r"(^|\s)--?[A-Za-z]", cmd):
                out.append((f"{os.path.basename(os.path.dirname(path))}:{gname}", cmd))
    # universal gates, hardcoded in Python
    from default_gates import UNIVERSAL_GATES

    for gname, gcfg in UNIVERSAL_GATES.items():
        cmd = gcfg.get("command")
        if cmd and re.search(r"(^|\s)--?[A-Za-z]", cmd):
            out.append((f"universal:{gname}", cmd))

    # auto-format hook: dict of ext -> argv list, deduped by binary+flags.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))
    from auto_format import FORMATTERS

    seen: set[str] = set()
    for argv in FORMATTERS.values():
        cmd = " ".join(argv)
        if cmd not in seen and any(t.startswith("-") for t in argv[1:]):
            seen.add(cmd)
            out.append((f"formatter:{argv[0]}", cmd))
    return out


def _flags_of(cmd: str) -> tuple[str, list[str]]:
    """(binary, flag-tokens) — drop the `2>&1 | head -N` truncation tail and
    placeholders, keep the leading `-x` / `--long` tokens on the primary stage."""
    stage = cmd.split("2>&1")[0].split("|")[0].split("&&")[0].strip()
    toks = [t for t in shlex.split(stage) if not t.startswith("{")]
    if not toks:
        return "", []
    binary = toks[0]
    flags = [t for t in toks[1:] if t.startswith("-") and t != "--"]
    return binary, flags


def _help_text(binary: str, subcommand: str | None) -> str:
    cmd = [binary]
    if subcommand and not subcommand.startswith("-"):
        cmd.append(subcommand)
    cmd.append("--help")
    try:
        r = _run(cmd)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return (r.stdout or "") + (r.stderr or "")


_GATE_COMMANDS = _gate_commands()


class TestGateCommandFlagsAreRealFlags:
    def test_surface_is_non_empty(self):
        """If this list ever empties, the parametrised probe below silently tests
        nothing — catch that here."""
        assert _GATE_COMMANDS, "no flagged gate commands discovered"

    def test_no_gate_command_has_a_smart_dash(self):
        """`cargo clippy — -D warnings` shipped with an em-dash (U+2014) instead
        of `--`, so `-D warnings` never reached the driver. No binary needed to
        catch it: the command string is simply wrong."""
        for source, cmd in _GATE_COMMANDS:
            assert "—" not in cmd and "–" not in cmd, (
                f"{source}: command has a unicode dash, not '--': {cmd!r}"
            )

    def test_flags_shlex_cleanly(self):
        for source, cmd in _GATE_COMMANDS:
            stage = cmd.split("2>&1")[0].split("|")[0].strip()
            shlex.split(stage)  # must not raise

    @pytest.mark.parametrize(
        "source,cmd", _GATE_COMMANDS, ids=lambda v: v if isinstance(v, str) else ""
    )
    def test_every_flag_is_in_the_tools_help(self, source, cmd):
        binary, flags = _flags_of(cmd)
        if not flags:
            pytest.skip("no leading flags on the primary stage")
        resolved = binary if os.path.isabs(binary) or "/" in binary else binary
        if shutil.which(resolved) is None:
            pytest.skip(f"{binary} not installed")
        # A subcommand-style token (e.g. `check`, `test`) may precede flags.
        toks = shlex.split(cmd.split("2>&1")[0].split("|")[0].strip())
        sub = (
            toks[1]
            if len(toks) > 1 and not toks[1].startswith("-") and not toks[1].startswith("{")
            else None
        )
        help_text = _help_text(binary, sub)
        if not help_text:
            pytest.skip(f"{binary} produced no help output")
        for flag in flags:
            name = flag.split("=", 1)[0]
            assert name in help_text, f"{source}: {binary} help does not mention {name!r}"
