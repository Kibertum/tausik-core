"""Tests for scripts/hooks/shell_redirection.py — redirections as a write vector.

write-gate-takes-a-file-descriptor-number-as-a-write-target. The gate used to
read the `2` of `2>/dev/null` as one of the command's own arguments. For
`cp`/`mv`/`install`, whose destination is the last positional, that number BECAME
the destination as far as the gate could see: a file named `2` was reported and
the real path was not. A 150-cell sweep before the fix — 10 writer commands x 15
redirection forms — invented a target in 70 cells and lost the real one in 30.

The matrix below IS that sweep, asserted cell by cell rather than sampled, so a
regression names the exact form it came back in. Parameterizing by FORM
(descriptor x operator x writer) instead of writing a case per bug is the point:
the previous fix in this area closed the one form it had measured and left the
neighbours, which is how this defect reached a live session.
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
from shell_redirection import (  # noqa: E402
    split_redirections,
    strip_fd_prefixes,
)

# --- the sweep ---------------------------------------------------------------
#
# Each writer maps to the targets it writes on its OWN account, with no
# redirection attached; each redirection form maps to the file it creates (empty
# when it only duplicates or closes a descriptor). The expected answer for a
# cell is the union — which is exactly the property the gate needs and the only
# one that catches BOTH failure directions at once: a phantom shows up as an
# extra member, a lost destination as a missing one.

WRITERS: dict[str, list[str]] = {
    "cp a b": ["b"],
    "mv a b": ["b"],
    "install -m 644 a b": ["b"],
    "echo hi": [],
    "touch f": ["f"],
    "tee out.txt": ["out.txt"],
    "truncate -s0 f": ["f"],
    "sed -i s/x/y/ f": ["f"],
    "dd if=a of=b": ["b"],
    "curl -o out url": ["out"],
}

REDIRECTIONS: dict[str, list[str]] = {
    "": [],
    "2>/dev/null": ["/dev/null"],
    "2> /dev/null": ["/dev/null"],
    "1>log": ["log"],
    "1> log": ["log"],
    "2>>log": ["log"],
    "&>log": ["log"],
    "&>>log": ["log"],
    ">out": ["out"],
    ">> out": ["out"],
    "2>&1": [],  # descriptor duplication, not a file
    "1>&2": [],
    "3>trace": ["trace"],
    "2>|log": ["log"],
    "2>/dev/null 1>&2": ["/dev/null"],
}

MATRIX = [
    pytest.param(w, r, id=f"{w.split()[0]}-{r or 'bare'}") for w in WRITERS for r in REDIRECTIONS
]


class TestTheSweep:
    """AC1 + AC2: across every writer x redirection cell, nothing extra, nothing lost."""

    @pytest.mark.parametrize("writer,redirection", MATRIX)
    def test_targets_are_exactly_the_writers_own_plus_the_redirections(
        self, writer: str, redirection: str
    ) -> None:
        command = f"{writer} {redirection}".strip()
        expected = set(WRITERS[writer]) | set(REDIRECTIONS[redirection])
        assert set(write_targets(command)) == expected

    @pytest.mark.parametrize("writer,redirection", MATRIX)
    def test_no_descriptor_number_is_ever_a_target(self, writer: str, redirection: str) -> None:
        """AC3, stated on its own so it fails on its own subject.

        The sweep above would also catch this, but it would report it as 'the
        set differs'. A descriptor leaking into the answer is the specific
        defect, and it earns a specific red.
        """
        command = f"{writer} {redirection}".strip()
        leaked = [t for t in write_targets(command) if t.isdigit()]
        assert leaked == []


class TestDescriptorFormsInIsolation:
    """AC3 across the descriptor grid, including forms no writer test reaches."""

    @pytest.mark.parametrize("fd", ["0", "1", "2", "3", "10"])
    @pytest.mark.parametrize("op", [">", ">>", ">|"])
    def test_numbered_write_redirect_yields_only_the_file(self, fd: str, op: str) -> None:
        assert write_targets(f"cp a b {fd}{op}log") == ["log", "b"]

    @pytest.mark.parametrize("fd", ["1", "2", "3"])
    @pytest.mark.parametrize("other", ["1", "2", "3"])
    def test_descriptor_duplication_writes_nothing(self, fd: str, other: str) -> None:
        assert write_targets(f"cp a b {fd}>&{other}") == ["b"]

    @pytest.mark.parametrize("fd", ["0", "2"])
    def test_numbered_input_redirect_is_not_a_write(self, fd: str) -> None:
        """`<` was not a redirection to the old parser at all, so its target was
        read as one of the command's arguments: `cp a b <in` reported the INPUT
        file as written and lost `b`."""
        assert write_targets(f"cp a b {fd}<in") == ["b"]

    def test_closing_a_descriptor_writes_nothing(self) -> None:
        assert write_targets("cp a b 2>&-") == ["b"]

    def test_dup_operator_does_not_leak_as_a_candidate(self) -> None:
        """AC4: `touch f 2>&1` used to answer ['f', '2', '>&', '1']."""
        assert write_targets("touch f 2>&1") == ["f"]


class TestAdjacencyIsWhatDecides:
    """The descriptor is glued to the operator; a spaced number is a filename.

    Both tokenize identically, so this is the one distinction that cannot be
    recovered after tokenization — and the reason the fix edits the command text.
    """

    def test_glued_number_is_a_descriptor(self) -> None:
        assert write_targets("cp a b 2>out") == ["out", "b"]

    def test_spaced_number_is_the_destination(self) -> None:
        assert set(write_targets("cp a 2 >out")) == {"out", "2"}

    def test_a_number_ending_a_word_is_part_of_that_word(self) -> None:
        assert set(write_targets("cp a log2>x")) == {"x", "log2"}

    @pytest.mark.parametrize("quoted", ['cp a "b 2>x"', "cp a 'b 2>x'"])
    def test_a_redirect_inside_quotes_is_a_filename(self, quoted: str) -> None:
        assert write_targets(quoted) == ["b 2>x"]

    def test_an_escaped_redirect_is_not_a_redirection(self) -> None:
        assert write_targets("cp a b\\2\\>x") == ["b2>x"]


class TestArgumentsSurviveARedirectionAnywhere:
    def test_argument_after_a_redirection_is_still_an_argument(self) -> None:
        """The old parser truncated the argument list at the first redirection,
        so `b` was never seen. Real shells do not care where it stands."""
        assert set(write_targets("cp a >log b")) == {"log", "b"}

    def test_process_substitution_still_ends_the_argument_list(self) -> None:
        assert set(write_targets("tee out.txt >(cat > x)")) == {"out.txt", "x"}

    def test_flag_value_destination_survives_a_redirection(self) -> None:
        assert set(write_targets("cp -t dst a b 2>/dev/null")) == {"dst", "/dev/null"}

    def test_end_of_options_survives_a_redirection(self) -> None:
        assert set(write_targets("cp -- -a.txt b.txt 2>/dev/null")) == {"b.txt", "/dev/null"}

    def test_each_sub_command_keeps_its_own_destination(self) -> None:
        got = set(write_targets("cat a > b && cp c d 2>/dev/null"))
        assert got == {"b", "d", "/dev/null"}

    def test_destination_inside_a_shell_payload_survives(self) -> None:
        assert set(write_targets('bash -c "cp x y 2>/dev/null"')) == {"y", "/dev/null"}


class TestStripFdPrefixes:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("cp a b 2>/dev/null", "cp a b >/dev/null"),
            ("cp a b 10>>log", "cp a b >>log"),
            ("cp a b 2>|log", "cp a b >|log"),
            ("cp a b 2>&1", "cp a b >&1"),
            ("cp a b 0<in", "cp a b <in"),
            # untouched: the number is a word, not a descriptor
            ("cp a 2 >out", "cp a 2 >out"),
            ("cp a log2>x", "cp a log2>x"),
            ("cp a b/2>x", "cp a b/2>x"),
            ("cp a b-2>x", "cp a b-2>x"),
            # untouched: quoting and escaping
            ('cp a "b 2>x"', 'cp a "b 2>x"'),
            ("cp a 'b 2>x'", "cp a 'b 2>x'"),
            ("cp a b\\2>x", "cp a b\\2>x"),
            # nothing to do
            ("cp a b", "cp a b"),
            ("echo hi > out", "echo hi > out"),
        ],
    )
    def test_only_a_glued_standalone_number_is_removed(self, raw: str, expected: str) -> None:
        assert strip_fd_prefixes(raw) == expected


class TestSplitRedirections:
    @pytest.mark.parametrize(
        "tokens,targets,words",
        [
            (["cp", "a", "b"], [], ["cp", "a", "b"]),
            (["cp", "a", "b", ">", "out"], ["out"], ["cp", "a", "b"]),
            (["cp", "a", ">", "out", "b"], ["out"], ["cp", "a", "b"]),
            (["cp", "a", "b", ">&", "1"], [], ["cp", "a", "b"]),
            (["cp", "a", "b", "<", "in"], [], ["cp", "a", "b"]),
            (["cp", "a", "b", "&>", "log"], ["log"], ["cp", "a", "b"]),
            (["cp", "a", "b", ">", "&2"], [], ["cp", "a", "b"]),
            # `> -` writes a file named '-'; only `>&-` closes a descriptor,
            # and that operator records nothing in the first place.
            (["cp", "a", "b", ">", "-"], ["-"], ["cp", "a", "b"]),
            # a trailing operator has no target and contributes no word
            (["cp", "a", "b", ">"], [], ["cp", "a", "b"]),
            # process substitution is not a redirection here
            (["tee", "f", ">(", "cat", ">", "x", ")"], ["x"], ["tee", "f", ">(", "cat", ")"]),
        ],
    )
    def test_redirections_are_lifted_out_of_the_word_list(
        self, tokens: list[str], targets: list[str], words: list[str]
    ) -> None:
        assert split_redirections(tokens) == (targets, words)
