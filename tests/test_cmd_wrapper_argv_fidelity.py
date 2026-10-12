"""The Windows .cmd wrapper must not hand the CLI a truncated argument.

Measured in session #209 on Python 3.11.2: through `.tausik/tausik.cmd`,
5 of 9 hostile arguments were corrupted; the same 9 passed straight to python
were all intact. Two corruptions were silent — `48->49` arrived as `48-` with
rc 0 and the output diverted into a stray file named `49`, and `a&b` arrived
as `a` with the tail executed as a command. Session #200 lost a handoff that
way: a truncated value was stored and the command reported success.

These tests pin both ends of the guard: it fires on the measured corruptions,
and it stays silent on the shapes that are not corruption — an interactive
shell where a human redirects deliberately, the POSIX wrapper that sets no
raw command line at all, and an argument whose quoting was merely rewritten.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from cmdline_fidelity import (  # noqa: E402
    EXIT_MANGLED,
    GUARD_ENV,
    RAW_ENV,
    argument_tail,
    describe_mismatch,
    enforce,
    redirection_targets,
)

_WRAPPER = r"C:\repo\.tausik\tausik.cmd"
_PREFIX = f"C:\\Windows\\system32\\cmd.exe /c {_WRAPPER}"


def _raw(tail: str) -> str:
    return f"{_PREFIX} {tail}"


# --- the guard fires: text left the command line -------------------------


def test_arrow_eaten_without_quotes_is_reported():
    """The session #200 shape: rc was 0 and the value was stored truncated."""
    message = describe_mismatch(["48-"], _raw("48->49"))
    assert message is not None
    assert "48->49" in message
    assert "48-" in message


def test_ampersand_truncation_is_reported():
    message = describe_mismatch(["a"], _raw("a&b"))
    assert message is not None
    assert "a&b" in message


def test_message_names_the_file_cmd_already_created():
    """cmd.exe opens the target at parse time — the stray file exists already."""
    message = describe_mismatch(["48-"], _raw("48->49"))
    assert "49" in message
    assert "delete it" in message


def test_message_offers_the_escape_hatch_and_a_working_route():
    message = describe_mismatch(["a"], _raw("a&b"))
    assert GUARD_ENV in message
    assert ".tausik/tausik" in message


# --- the guard stays silent: these are not corruption --------------------


def test_intact_argument_passes():
    assert describe_mismatch(["status"], _raw("status")) is None


def test_requoted_argument_passes():
    """Quoting is legitimately rewritten in transit; the payload is intact."""
    arg = 'say "hi" > victim'
    assert describe_mismatch([arg], _raw('"say \\"hi\\" > victim"')) is None


def test_multiple_arguments_pass():
    raw = _raw('task log slug "Negative: сценарий ошибки"')
    argv = ["task", "log", "slug", "Negative: сценарий ошибки"]
    assert describe_mismatch(argv, raw) is None


def test_interactive_shell_redirection_is_none_of_our_business():
    """A human typing `tausik status > out.txt` leaves no wrapper path in
    %CMDCMDLINE% — measured: the value is just `cmd.exe`."""
    assert describe_mismatch(["status"], "cmd.exe") is None


def test_posix_wrapper_sets_no_raw_line():
    assert describe_mismatch(["status"], None) is None
    assert describe_mismatch(["status"], "") is None


def test_argument_that_merely_mentions_the_wrapper_is_not_a_split_point():
    """The FIRST occurrence marks the wrapper path, not a later mention."""
    raw = _raw("search tausik.cmd")
    assert argument_tail(raw) == " search tausik.cmd"


# --- redirection targets --------------------------------------------------


@pytest.mark.parametrize(
    "tail,expected",
    [
        ("48->49", ["49"]),
        ("a > out.txt", ["out.txt"]),
        ("a >> log.txt", ["log.txt"]),
        ('a > "with space.txt"', ["with space.txt"]),
        ("a > first & b >> second", ["first", "second"]),
        ("no operators here", []),
    ],
)
def test_redirection_targets(tail, expected):
    assert redirection_targets(tail) == expected


# --- enforce(): process-level behaviour -----------------------------------


def test_enforce_exits_non_zero_on_a_mangled_line(capsys):
    env = {RAW_ENV: _raw("48->49")}
    with pytest.raises(SystemExit) as exc:
        enforce(argv=["48-"], env=env)
    # Literal, not `== EXIT_MANGLED`: comparing the exit code against the very
    # constant under test passes for any value, zero included — a mutation to
    # `EXIT_MANGLED = 0` survived that assertion and made the guard silent again.
    assert exc.value.code == 3
    assert EXIT_MANGLED == 3
    assert "48->49" in capsys.readouterr().err


def test_the_refusal_code_is_not_success_and_not_a_usage_error():
    """Zero would restore the silence this whole module exists to end; 2 is
    argparse's usage error and would read as 'your command was wrong'."""
    assert EXIT_MANGLED not in (0, 2)


def test_enforce_is_quiet_when_the_line_is_intact(capsys):
    enforce(argv=["status"], env={RAW_ENV: _raw("status")})
    assert capsys.readouterr().err == ""


def test_enforce_honours_the_escape_hatch():
    env = {RAW_ENV: _raw("48->49"), GUARD_ENV: "off"}
    enforce(argv=["48-"], env=env)  # must not raise


def test_enforce_consumes_the_variable_so_children_are_not_measured():
    """A subprocess the CLI spawns has its own argv; inheriting the wrapper's
    command line would make every child fail the comparison."""
    env = {RAW_ENV: _raw("status")}
    enforce(argv=["status"], env=env)
    assert RAW_ENV not in env


def test_enforce_consumes_the_variable_even_when_it_refuses():
    env = {RAW_ENV: _raw("48->49")}
    with pytest.raises(SystemExit):
        enforce(argv=["48-"], env=env)
    assert RAW_ENV not in env


# --- the template is the source of truth ----------------------------------


def _cmd_template() -> str:
    with open(os.path.join(_ROOT, "bootstrap", "tausik_wrapper.cmd"), encoding="utf-8") as h:
        return h.read()


def test_wrapper_template_exports_the_raw_command_line():
    """Linux CI cannot run cmd.exe, but it can hold the template to account."""
    assert f'set "{RAW_ENV}=!CMDCMDLINE!"' in _cmd_template()


def test_wrapper_template_captures_it_with_delayed_expansion():
    """Measured: the plain `set "X=%CMDCMDLINE%"` form truncates the value.

    %CMDCMDLINE% carries quotes; they close the protecting pair early, so a `>`
    inside the value redirects the `set` line itself. `SCHEMA 48->49 next` was
    stored as `SCHEMA 48- next` and the guard then refused a healthy argument.
    """
    text = _cmd_template()
    assert "setlocal EnableDelayedExpansion" in text
    assert f'set "{RAW_ENV}=%CMDCMDLINE%"' not in text


def test_wrapper_template_turns_delayed_expansion_back_off():
    """Left on, it would eat an exclamation mark out of %* — `!PATH!` in an
    argument must reach python as those six characters."""
    text = _cmd_template()
    enable = text.index("setlocal EnableDelayedExpansion")
    disable = text.index("setlocal DisableDelayedExpansion")
    invoke = text.index('"%PYTHON%" "%SCRIPTS%\\project.py" %*')
    assert enable < disable < invoke


def test_posix_wrapper_template_does_not_need_the_guard():
    """`exec "$@"` cannot lose an argument, so the POSIX side stays untouched."""
    template = os.path.join(_ROOT, "bootstrap", "tausik_wrapper.sh")
    with open(template, encoding="utf-8") as handle:
        text = handle.read()
    assert RAW_ENV not in text
    assert 'exec "$PYTHON" "$SCRIPTS/project.py" "$@"' in text


# --- live, through the real wrapper ---------------------------------------


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe only exists on Windows")
def test_live_wrapper_refuses_the_shape_that_used_to_return_zero(tmp_path):
    """End-to-end: the measured silent corruption now exits non-zero.

    Runs the generated `.tausik/tausik.cmd`, so it is meaningful only after a
    bootstrap has rendered the current template; it is skipped when the
    wrapper is absent rather than failing for a reason it does not own.
    """
    wrapper = os.path.join(_ROOT, ".tausik", "tausik.cmd")
    if not os.path.exists(wrapper):
        pytest.skip("no generated wrapper in this checkout")
    result = subprocess.run(
        [wrapper, "48->49"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    stray = sorted(p.name for p in tmp_path.iterdir())
    stderr = result.stderr.decode("utf-8", "surrogateescape")
    assert result.returncode != 0, f"still silent; stray files: {stray}"
    assert "48->49" in stderr


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe only exists on Windows")
@pytest.mark.parametrize(
    "arg",
    [
        "SCHEMA 48->49 next",
        'say "hi" > victim',
        "кириллица и стрелка 48->49",
        "bang! here",
        "!PATH!",
        "100% done",
        "Negative: ошибка!",
        "AC-1: tests/x.py::test_y",
    ],
)
def test_live_wrapper_does_not_refuse_a_healthy_argument(tmp_path, arg):
    """The guard must not become the new way to lose a command.

    Each of these reached python verbatim before the guard existed, so each
    must still reach it. argparse rejecting the argument as a command name is
    the proof it arrived: the message quotes what it received.
    """
    wrapper = os.path.join(_ROOT, ".tausik", "tausik.cmd")
    if not os.path.exists(wrapper):
        pytest.skip("no generated wrapper in this checkout")
    result = subprocess.run([wrapper, arg], cwd=str(tmp_path), capture_output=True)
    stderr = result.stderr.decode("utf-8", "surrogateescape")
    assert "could not pass your arguments" not in stderr
    assert f"invalid choice: {arg!r}" in stderr
    assert not list(tmp_path.iterdir()), "the call left a stray file behind"


# --- input redirection creates nothing, so nothing is offered for deletion ---
# Fix review of session #209, record #26 (medium): `<` was in the operator set,
# so `describe_mismatch` told the operator that a file cmd.exe had merely
# OPENED FOR READING was "already created (delete it)". Wrong, and the advice
# destructive — the named file is one they still need.


def test_an_input_redirection_target_is_not_named_as_created():
    assert redirection_targets("a < input.txt") == []


def test_the_message_does_not_offer_to_delete_a_file_cmd_only_read():
    message = describe_mismatch(["a"], _raw("a < input.txt"))
    assert message is not None, "the mismatch itself is still reported"
    assert "delete it" not in message
    assert "already created" not in message


def test_an_output_redirection_target_is_still_named_and_still_deletable():
    """The other end: the fix must not silence the case that IS a stray file."""
    message = describe_mismatch(["a"], _raw("a > stray.txt"))
    assert "stray.txt" in message
    assert "delete it" in message


def test_a_mixed_line_names_only_what_was_created():
    assert redirection_targets("a < input.txt > stray.txt") == ["stray.txt"]
