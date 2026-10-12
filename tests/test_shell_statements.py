"""Tests for scripts/hooks/shell_statements.py — the newline as a statement break.

write-gate-does-not-treat-a-newline-as-a-command-separator. `_SEPARATORS` has
always listed ``"\\n"``, and the entry could never match: tokens arrive from
``shlex(..., whitespace_split=True)``, which treats a newline as whitespace and
drops it. A separator declared but never delivered is dead code written for a
tokenization that does not happen — the same shape as the ``\\d*`` that #204
found in the redirection pattern, and the reason memory #505 says to read a
signal in the source text while it is still there.

The consequence was not a phantom target. It was a MISS: every token on the
second line was absorbed as a positional argument of the command on the first,
so a write below any other command was invisible to a BLOCKING containment gate.
Verified against the real hook, not this parser alone — a single-line write
outside the ACL was refused, and the same write with ``echo`` on a line above it
put 723996 bytes outside the declared scope.

The matrix below IS the pre-fix sweep — 9 separator forms x 10 writing commands
= 90 cells, of which the four newline-only forms lost the real target in 9 of 10
cells each, 36 in total. Asserted cell by cell rather than sampled, so a
regression names the exact form it returned in.

The second class of test is the one that keeps the cure from being worse than
the disease: a newline that bash does NOT treat as a boundary must not become
one here, or this module starts manufacturing commands out of prose — the very
false positive this project keeps having to remove.
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
_HOOKS = os.path.join(_SCRIPTS, "hooks")
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

from bash_write_parse import write_targets  # noqa: E402
from shell_statements import heredoc_bodies, split_statement_breaks  # noqa: E402

#: Destination every writer in the matrix aims at. A path under `tests/` rather
#: than a bare name so the string is a plausible in-tree target.
_DST = "tests/out.txt"

#: One invocation per writing command the gate knows, each writing to _DST.
_WRITERS = {
    "cp": f"cp src.txt {_DST}",
    "mv": f"mv src.txt {_DST}",
    "install": f"install src.txt {_DST}",
    "tee": f"tee {_DST}",
    "sed-i": f"sed -i s/a/b/ {_DST}",
    "dd": f"dd if=src.txt of={_DST}",
    "truncate": f"truncate -s 0 {_DST}",
    "touch": f"touch {_DST}",
    "redirect": f"echo hi > {_DST}",
    "curl-o": f"curl -o {_DST} https://example.invalid",
}

#: How the writer is joined to a harmless command before it. The four newline
#: forms are the ones that were broken; the operator forms are the control group
#: that always worked and must keep working.
_SEPARATOR_FORMS = {
    "semicolon": "echo lead; {w}",
    "and": "echo lead && {w}",
    "or": "false || {w}",
    "pipe": "echo lead | {w}",
    "newline": "echo lead\n{w}",
    "blank-line": "echo lead\n\n{w}",
    "newline-indented": "echo lead\n    {w}",
    "semicolon-then-newline": "echo lead;\n{w}",
    "crlf": "echo lead\r\n{w}",
}


@pytest.mark.parametrize("form", sorted(_SEPARATOR_FORMS))
@pytest.mark.parametrize("writer", sorted(_WRITERS))
def test_the_write_is_seen_whatever_separates_it_from_the_command_before(form, writer):
    """All 90 cells. Before the fix the four newline forms lost 9 of 10 each."""
    command = _SEPARATOR_FORMS[form].format(w=_WRITERS[writer])
    assert _DST in write_targets(command), (
        f"separator {form!r} + writer {writer!r}: the gate does not see the write to "
        f"{_DST}. A containment gate that misses a write is a hole, not a nuisance — "
        "this is the form that let 723996 bytes land outside a declared scope."
    )


def test_the_hole_exactly_as_it_was_reproduced():
    """The literal two-line command that walked through the live hook."""
    assert _DST in write_targets(f"echo probing\ncp CHANGELOG.md {_DST}")


class TestANewlineBashWouldNotHonourDoesNotBecomeABoundary:
    """The other direction. Splitting where bash would not split invents commands
    out of data, and a gate that blocks on invented commands is the false positive
    this project has had to remove more than once."""

    def test_a_newline_inside_double_quotes_is_data(self):
        """A multi-line commit message is ONE argument. If it split, every commit
        with a body would be read as a script and refused for what it quotes."""
        command = f'git commit -m "line one\ncp evil.txt {_DST}\nline three"'
        assert write_targets(command) == []

    def test_a_newline_inside_single_quotes_is_data(self):
        command = f"git commit -m 'line one\ncp evil.txt {_DST}'"
        assert write_targets(command) == []

    def test_a_backslash_continuation_joins_the_lines(self):
        """`cp src \\<newline> dst` is ONE command whose destination is on line two.
        Splitting it would drop the real target — a miss produced by the fix."""
        assert write_targets(f"cp src.txt \\\n {_DST}") == [_DST]

    def test_a_continuation_does_not_create_a_second_command(self):
        assert write_targets("echo lead \\\n trailing") == []

    def test_a_continuation_ending_in_CRLF_still_joins_the_lines(self):
        """This repo is checked out with CRLF, so a continuation arrives as
        backslash-CR-LF. Without the CR case the CR ends the escape, the LF is
        read as a boundary, and `cp src \\<crlf> dst` splits into two commands —
        the destination on line two stops being a destination at all. Measured:
        removing that case turns this into `cp src.txt \\\\\\r ; dst.txt`."""
        assert write_targets(f"cp src.txt \\\r\n {_DST}") == [_DST]

    def test_an_escaped_quote_does_not_open_a_quoted_region(self):
        r"""If `\"` were read as an opening quote, every newline after it would be
        treated as data and the write below would go unseen again."""
        assert _DST in write_targets(f'echo \\"x\ncp src.txt {_DST}')

    def test_a_heredoc_body_is_not_a_sequence_of_commands(self):
        """Bodies are stripped upstream; this pins that the boundary pass does not
        resurrect them."""
        command = f"cat > {_DST} <<EOF\ncp evil.txt stolen.txt\nEOF"
        assert write_targets(command) == [_DST]

    def test_bodies_keep_their_header_for_the_program_that_receives_stdin(self):
        command = "python - <<PY\nprint('x')\nPY"
        assert heredoc_bodies(command) == [("python - <<PY", "print('x')")]


def test_a_newline_inside_an_interpreter_payload_is_also_a_boundary():
    """Otherwise the bypass simply moves one level down: the same two lines,
    wrapped in `bash -c`, would hide the write again."""
    assert _DST in write_targets(f'bash -c "echo lead\ncp src.txt {_DST}"')


class TestTheTextTransformItself:
    """Unit-level subject: what the pass does to the text, independent of writers."""

    def test_a_bare_newline_becomes_a_separator(self):
        assert ";" in split_statement_breaks("echo a\necho b")

    def test_a_quoted_newline_survives_untouched(self):
        assert split_statement_breaks("echo 'a\nb'") == "echo 'a\nb'"

    def test_a_continuation_leaves_no_separator(self):
        assert ";" not in split_statement_breaks("echo a \\\n b")

    def test_an_escaped_quote_inside_a_quoted_string_does_not_close_it(self):
        r"""`"he said \"hi\" today<newline>more"` is ONE argument. If the escaped
        quote were read as the closing one, the rest of the message would be live
        shell and its newline a boundary.

        Asserted on the text rather than through `write_targets`, and that choice
        is measured: dropping this branch leaves the quotes unbalanced, which
        sends the parser into its regex fallback and yields the same empty target
        list for the wrong reason. The difference is real and it is visible here,
        so this is where the subject is tested.
        """
        text = 'git commit -m "he said \\"hi\\" today\nmore"'
        assert ";" not in split_statement_breaks(text)

    def test_a_backslash_inside_single_quotes_is_literal(self):
        """bash gives the backslash no special meaning in single quotes, so the
        quote that follows one still closes the string — and the newline after
        it is a real boundary."""
        assert ";" in split_statement_breaks("echo 'a\\'\necho b")

    def test_text_without_newlines_is_returned_unchanged(self):
        """The pass must be inert on the single-line commands that are most of
        what the gate sees — a transform that rewrites those would put every
        existing measurement in doubt."""
        for command in _WRITERS.values():
            assert split_statement_breaks(command) == command
