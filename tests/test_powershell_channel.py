"""The PowerShell channel reaches the same gates as the Bash channel.

`powershell-tool-bypasses-bash-firewall`. Every assertion here fails on the
code as it stood before that task: not because a rule was wrong, but because
the rules were only ever asked about one of the two shell tools the agent is
handed on win32 — the platform this project calls primary.

The negative pins matter as much as the positives. A gate that blocks honest
work teaches the agent to reach for the bypass (convention #291), and a brand
new dialect parser is exactly where over-blocking is most likely.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOOKS = os.path.join(_REPO_ROOT, "scripts", "hooks")
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

from pwsh_cmd_norm import scan_target  # noqa: E402
from pwsh_cmd_parse import Statement, split_statements, tokenize  # noqa: E402
from pwsh_write_parse import wiped_root, write_targets  # noqa: E402
from rm_wipe_detect import _WIPE_ROOTS, is_wipe_root, normalise_operand  # noqa: E402
from write_confidence import CONFIDENCE_PARSED, CONFIDENCE_REGEX_FALLBACK  # noqa: E402

# A single backslash, spelled so the test source stays readable. A raw string
# cannot end in one, which is itself a reminder of why the POSIX lexer — where
# `\` is an escape — cannot read this dialect.
BS = "\\"


def run_hook(script: str, payload: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, "CLAUDE_PROJECT_DIR": _REPO_ROOT}
    full_env.pop("TAUSIK_SKIP_HOOKS", None)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-X", "utf8", os.path.join(_HOOKS, script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=full_env,
        cwd=_REPO_ROOT,
    )


class TestTokenizerReadsTheDialect:
    """The POSIX lexer mis-reads these; that is why a second one exists."""

    def test_trailing_backslash_is_a_path_not_an_escape(self):
        assert tokenize("Remove-Item C:" + BS) == ["Remove-Item", "C:" + BS]

    def test_backtick_escapes_not_backslash(self):
        # A backtick before a space escapes it, so the two words are ONE token.
        assert tokenize("Write-Output a` b") == ["Write-Output", "a b"]
        # …and a backslash escapes nothing: it is an ordinary path character,
        # which is the single fact the POSIX lexer gets wrong about this shell.
        assert tokenize("Write-Output a" + BS + " b") == ["Write-Output", "a" + BS, "b"]

    def test_single_quotes_are_literal(self):
        assert tokenize("Write-Output 'a`nb'") == ["Write-Output", "a`nb"]

    def test_doubled_quote_is_an_escaped_quote(self):
        assert tokenize("Write-Output 'it''s'") == ["Write-Output", "it's"]

    def test_unbalanced_quote_reports_unparseable(self):
        assert tokenize("Write-Output 'oops") is None

    def test_newline_separates_statements_like_a_semicolon(self):
        assert len(split_statements(tokenize("Get-Date\nGet-Location"))) == 2

    def test_fd_prefix_stays_glued_to_its_redirect(self):
        assert "2>&1" in tokenize("Get-Process 2>&1")

    @pytest.mark.parametrize("smart", ["\u2018x\u2019", "\u201cx\u201d"])
    def test_smart_quotes_are_real_quotes(self, smart):
        assert tokenize(f"Write-Output {smart}") == ["Write-Output", "x"]


class TestParameterAbbreviation:
    """PowerShell binds any unambiguous prefix; a detector that only knows the
    long spelling knows nothing, because the short one is what gets typed."""

    @pytest.mark.parametrize("flag", ["-Recurse", "-recurse", "-Rec", "-rec", "-r", "-R"])
    def test_recurse_abbreviations_all_register(self, flag):
        stmt = Statement(tokenize(f"Remove-Item {flag} C:{BS}"))
        assert stmt.has_switch("recurse"), flag

    def test_colon_bound_switch_value(self):
        assert Statement(tokenize("Remove-Item -Recurse:$true x")).has_switch("recurse")

    def test_switch_does_not_swallow_the_operand(self):
        stmt = Statement(tokenize(f"Remove-Item -Recurse C:{BS}"))
        assert stmt.positionals == ["C:" + BS]

    def test_named_parameter_does_take_its_value(self):
        stmt = Statement(tokenize(f"Remove-Item -Path C:{BS} -Recurse"))
        assert stmt.param("path") == "C:" + BS


class TestWipeDetection:
    @pytest.mark.parametrize(
        "command",
        [
            "Remove-Item -Recurse -Force C:" + BS,
            "Remove-Item -Recurse -Force 'C:" + BS + "'",
            "Remove-Item C:" + BS + " -Recurse",
            "rm -Recurse -Force C:" + BS,
            "ri -rec -fo D:/",
            "del -Recurse C:" + BS + "*",
            "Remove-Item -Path C:" + BS + " -Recurse -Force",
            "Remove-Item -LiteralPath 'C:" + BS + "' -Recurse",
            "Remove-Item -Recurse -Force /",
            "Remove-Item -Recurse .",
            "Get-Date; Remove-Item -Recurse -Force C:" + BS,
        ],
    )
    def test_volume_and_tree_roots_are_caught(self, command):
        assert wiped_root(command) is not None, command

    @pytest.mark.parametrize(
        "command",
        [
            "powershell -Command 'Remove-Item -Recurse -Force C:" + BS + "'",
            "cmd /c 'rd /s /q C:" + BS + "'",
            "iex 'Remove-Item -Recurse C:" + BS + "'",
        ],
    )
    def test_wrapper_payloads_are_descended_into(self, command):
        assert wiped_root(command) is not None, command

    @pytest.mark.parametrize(
        "command",
        [
            "Remove-Item -Recurse -Force ." + BS + "build",
            "Remove-Item -Recurse -Force C:" + BS + "Users" + BS + "me" + BS + "proj",
            "Remove-Item -Recurse -Force node_modules",
            "Remove-Item C:" + BS,  # no -Recurse: cannot empty a non-empty tree
            "Get-ChildItem C:" + BS + " -Recurse",
            "Write-Output 'Remove-Item -Recurse -Force C:" + BS + " is dangerous'",
            "Get-Content notes.md | Select-String 'rm -rf /'",
            "Remove-Item -Recurse -Force $env:TEMP" + BS + "x",
        ],
    )
    def test_honest_work_is_not_blocked(self, command):
        assert wiped_root(command) is None, command


class TestOneJudgeTwoDialects:
    """AC-5/AC-9. The set of places that count as "everything" is answered
    once. A second copy is how `rm_wipe_detect` acquired three regressions in
    one session, and the differential run below is convention #298 in test
    form: the OLD judgement and the NEW one, over a shared corpus, with every
    divergence accounted for."""

    #: Exactly the divergence the change intends: Windows volume roots, which
    #: the POSIX-only judge could not name. Anything else appearing here is a
    #: regression, in either direction.
    INTENDED_WIDENING = ["C:" + BS, "C:/", "D:" + BS, "Z:/", "C:", "C:" + BS + "*"]
    UNCHANGED = [
        "/",
        "//",
        "/.",
        "/*",
        ".",
        "./",
        "./*",
        "..",
        "../*",
        ".venv",
        "/tmp/scratch",
        "build",
        "node_modules",
        "a/b/c",
        "C:" + BS + "Users",
        "C:/Windows/Temp",
        "." + BS + "build",
        "",
    ]

    def test_no_operand_stopped_being_judged_a_root(self):
        """The narrowing direction — must be empty."""
        regressed = [
            op
            for op in self.UNCHANGED
            if (normalise_operand(op) in _WIPE_ROOTS) and not is_wipe_root(op)
        ]
        assert regressed == []

    def test_widening_is_exactly_the_volume_roots(self):
        widened = [
            op
            for op in self.UNCHANGED + self.INTENDED_WIDENING
            if is_wipe_root(op) and normalise_operand(op) not in _WIPE_ROOTS
        ]
        assert sorted(widened) == sorted(self.INTENDED_WIDENING)

    def test_both_dialects_ask_the_same_judge(self):
        """A POSIX spelling and a PowerShell spelling of the same wipe agree."""
        import danger_patterns

        assert danger_patterns.wiped_root_any("rm -rf /") is not None
        assert danger_patterns.wiped_root_any("Remove-Item -Recurse -Force C:" + BS) is not None


class TestFindBasedWipes:
    """`find` carries the recursion itself, so `rm`'s operand is `{}` (or absent
    for `-delete`) and the root is a find START PATH. Judged by the SAME
    `is_wipe_root` as `rm` (firewall-find-exec-delete-uncovered) — the gap
    rm_wipe_detect.py's header filed to this task.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "find / -delete",
            "find . -delete",
            "find -delete",  # default search path is '.'
            "find / -exec rm -rf {} \\;",
            "find / -type f -exec rm -f {} +",
            "find / -execdir rm {} +",
            "find / -name '*.log' -delete",  # hard root blocks even name-scoped
            "find .. -delete",
            "find -L / -delete",  # leading option before the path
            "find / -exec /bin/rm -rf {} ;",  # rm named by full path
            "find /* -delete",  # glob folds to '/'
        ],
    )
    def test_deleting_find_at_a_root_is_blocked(self, command):
        import danger_patterns

        assert danger_patterns.wiped_root_any(command, command) is not None

    @pytest.mark.parametrize(
        "command",
        [
            "find . -name '*.pyc' -delete",  # routine dev idiom — scoped in cwd
            "find . -name x.py -delete",
            "find ./build -delete",  # named subdir, not a root
            "find src -exec rm {} +",
            "find /var/log/app -name '*.log' -exec rm {} +",
            "find / -type f -name qq",  # no deleting action
            "find . -type d",  # no deleting action
            "find ./node_modules -delete",
        ],
    )
    def test_scoped_or_non_root_find_is_allowed(self, command):
        import danger_patterns

        assert danger_patterns.wiped_root_any(command, command) is None

    def test_find_and_rm_share_one_root_judge(self):
        """No second 'what is root' ruleset — the find detector routes through
        the same is_wipe_root, so a spelling either both catch or neither does."""
        import danger_patterns

        for root in ("/", "..", "/./", "//"):
            assert is_wipe_root(root)
            assert danger_patterns.wiped_root_any(f"find {root} -delete") is not None


class TestOneDialectTableNotTwo:
    """`shell_channel` keys two tables — parsers and scanners. Two tables of the
    same set is the shape this whole task is about, so they are pinned to each
    other rather than trusted to be edited together."""

    def test_every_dialect_has_both_a_parser_and_a_scanner(self):
        import shell_channel

        assert set(shell_channel._DIALECTS) == set(shell_channel._SCANNERS)
        assert set(shell_channel.SHELL_TOOLS) == set(shell_channel._SCANNERS)

    def test_the_firewall_does_not_spell_the_channel_list_itself(self):
        """The dispatch briefly WAS `== "PowerShell"` in the hook — a second
        copy of the list whose staleness caused the bug. Found by reviewing the
        fix, not the code it replaced (convention #276)."""
        src = open(os.path.join(_HOOKS, "bash_firewall.py"), encoding="utf-8").read()
        code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
        assert '"PowerShell"' not in code
        assert "shell_channel" in code


class TestCrossChannelWrappers:
    """Each dialect can invoke the other. A judge asked only about the tool name
    would reopen the hole one wrapper deep — the exact shape of the bypass that
    closed last session."""

    def test_a_powershell_wipe_launched_from_bash_is_blocked(self):
        r = run_hook(
            "bash_firewall.py",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "powershell -Command 'Remove-Item -Recurse -Force C:" + BS + "'"
                },
            },
        )
        assert r.returncode == 2, r.stderr

    def test_a_posix_wipe_launched_from_powershell_is_blocked(self):
        r = run_hook(
            "bash_firewall.py",
            {"tool_name": "PowerShell", "tool_input": {"command": "bash -c 'rm -rf /'"}},
        )
        assert r.returncode == 2, r.stderr

    @pytest.mark.parametrize(
        "command",
        [
            "git commit -m 'Remove-Item -Recurse -Force C:" + BS + " must be blocked'",
            "powershell -Command 'echo \"Remove-Item -Recurse -Force C:" + BS + "\"'",
            "tausik memory add 'never Remove-Item -Recurse -Force C:" + BS + "'",
        ],
    )
    def test_a_quoted_mention_survives_the_raw_line_judge(self, command):
        """Closing the wrapper hole above meant judging the RAW line as well as
        the scanned one, and the raw line still contains the quoted text. This
        is safe only because the PowerShell judge is STRUCTURAL — a mention
        inside quotes is one token and never forms a `Remove-Item` statement.
        These pin that, because the cheap version of the same fix (handing the
        raw line to the POSIX regex too) would block all three."""
        r = run_hook("bash_firewall.py", {"tool_name": "Bash", "tool_input": {"command": command}})
        assert r.returncode == 0, r.stderr


class TestWriteTargets:
    @pytest.mark.parametrize(
        "command,expected",
        [
            ("Set-Content -Path notes.md -Value 'x'", ["notes.md"]),
            ("Set-Content notes.md 'x'", ["notes.md"]),
            ("'x' | Out-File -FilePath scripts" + BS + "a.py", ["scripts" + BS + "a.py"]),
            ("'x' > scripts" + BS + "a.py", ["scripts" + BS + "a.py"]),
            ("'x' >> CHANGELOG.md", ["CHANGELOG.md"]),
            ("Add-Content -Path CHANGELOG.md -Value 'y'", ["CHANGELOG.md"]),
            ("New-Item -ItemType File -Path src" + BS + "new.py", ["src" + BS + "new.py"]),
            ("ni src" + BS + "new.py", ["src" + BS + "new.py"]),
            ("Copy-Item a.txt b.txt", ["b.txt"]),
            ("Invoke-WebRequest http://x -OutFile payload.exe", ["payload.exe"]),
            ("Tee-Object -FilePath out.log", ["out.log"]),
            ('powershell -Command "Set-Content -Path hidden.py -Value 1"', ["hidden.py"]),
        ],
    )
    def test_write_vectors_are_seen(self, command, expected):
        assert sorted(write_targets(command)) == sorted(expected), command

    @pytest.mark.parametrize(
        "command",
        [
            "Get-Content notes.md",
            "Get-Process 2>&1",  # fd dup, not a file
            "Write-Output 'a > b'",  # a quoted mention is one token
            "Select-String -Pattern 'x' notes.md",
        ],
    )
    def test_reads_are_not_reported_as_writes(self, command):
        assert write_targets(command) == [], command

    def test_second_positional_of_set_content_is_content_not_a_file(self):
        """`Set-Content notes.md 'draft.md'` writes ONE file. Reporting the
        content string as a target would block a write to a file that is never
        touched — the false positive that trains the bypass."""
        assert write_targets("Set-Content notes.md 'draft.md'") == ["notes.md"]

    def test_unparseable_command_guesses_rather_than_reporting_nothing(self):
        """An empty list reads to every consumer as "writes nothing" — a silent
        allow, the worst failure shape for a gate. The POSIX parser already
        answered with a guess plus a flag; both channels must fail alike."""
        from pwsh_write_parse import write_targets_with_confidence

        targets, confidence = write_targets_with_confidence("Set-Content -Path a.py -Value 'oops")
        assert confidence == CONFIDENCE_REGEX_FALLBACK
        assert "a.py" in targets

    def test_parsed_command_reports_parsed(self):
        from pwsh_write_parse import write_targets_with_confidence

        assert write_targets_with_confidence("Set-Content a.py 'x'")[1] == CONFIDENCE_PARSED


class TestHereStringBodyIsData:
    """`pwsh-here-string-body-parsed-as-commands` — found by dogfooding, on the
    commit that closed the task which introduced it.

    A PowerShell here-string (`@'…'@`, `@"…"@`) is DATA. Parsing its body as
    live shell makes any `->` in prose manufacture a redirect and a phantom
    write target, and the gate then blocks an honest `git commit -m @'…'@`.
    Its POSIX twin already carries `_strip_heredocs` for exactly this, with the
    symptom spelled out in the docstring — the new dialect got the detectors
    without the false-positive defences, which is channel parity by RULE and a
    gap by PROTECTION.

    A false BLOCK on the most routine multi-line operation there is costs more
    than a miss: the only exits it offers train the bypass (#291).
    """

    #: The literal body that blocked the real commit, trimmed to the offending
    #: shape. Pinned verbatim rather than invented — the parser must survive the
    #: text that actually broke it.
    REAL_BODY = (
        "bash_firewall 384 -> 128 lines, agent-contract.md 406 -> 302\n"
        "the bypass is recorded as a supervision event"
    )

    def test_a_here_string_commit_message_writes_nothing(self):
        command = "git commit -m @'\n" + self.REAL_BODY + "\n'@"
        assert write_targets(command) == []

    def test_interpolating_here_string_too(self):
        command = 'git commit -m @"\n' + self.REAL_BODY + '\n"@'
        assert write_targets(command) == []

    def test_terminator_is_only_recognised_at_line_start(self):
        """PowerShell closes a here-string only on a terminator that BEGINS a
        line. Accepting one mid-line would end the scan early and re-expose the
        rest of the body as live shell — the same defect the POSIX side hit on
        an indented pseudo-terminator."""
        body = "a quoted '@ inside prose must not close it\nx -> y"
        assert write_targets("git commit -m @'\n" + body + "\n'@") == []

    def test_a_real_target_after_a_here_string_is_still_seen(self):
        assert write_targets("@'\ntext -> more\n'@ | Out-File notes.md") == ["notes.md"]
        assert write_targets("Set-Content -Value @'\nx -> y\n'@ -Path notes.md") == ["notes.md"]

    def test_a_here_string_does_not_hide_a_command_from_the_firewall(self):
        """The body is data — but `iex` turns data into a command, and that
        path must stay open or the fix becomes a bypass."""
        from pwsh_write_parse import wiped_root

        assert wiped_root("iex @'\nRemove-Item -Recurse -Force C:" + BS + "\n'@") is not None

    @pytest.mark.parametrize("phrase", ["Format-Volume", "DROP TABLE users", "mkfs.ext4"])
    def test_a_dangerous_phrase_quoted_in_a_commit_message_is_not_a_command(self, phrase):
        """BLOCKED_PATTERNS match by SUBSTRING, so the same blindness would
        block a commit message that merely describes the danger (AC-4)."""
        command = "git commit -m @'\nwhy " + phrase + " is blocked: it wipes data\n'@"
        r = run_hook(
            "bash_firewall.py", {"tool_name": "PowerShell", "tool_input": {"command": command}}
        )
        assert r.returncode == 0, r.stderr


class TestPushGateFollowsTheToolsDialect:
    """`push-gate-ors-two-dialects-and-false-blocks` — the second dogfood find,
    on the commit after the first one.

    Closing the PowerShell channel had made the push gate try BOTH tokenizers
    and block if either saw a push. Sound against evasion, wrong in practice:
    the POSIX lexer does not know a here-string, breaks out at the first
    apostrophe, and reads the `git push` in a commit message's PROSE as a
    command. Of two judges, the one that cannot read the language wins every
    disagreement.
    """

    #: The real shape that blocked the real commit: an apostrophe (so the POSIX
    #: lexer breaks out) followed by the words in prose.
    BODY = "PowerShell's escape is a backtick\n- git push --force reached NO gate\n"

    def _commit(self, tool):
        command = "git commit -m @'\n" + self.BODY + "'@"
        return run_hook("git_push_gate.py", {"tool_name": tool, "tool_input": {"command": command}})

    def test_a_here_string_commit_message_is_not_a_push(self):
        assert self._commit("PowerShell").returncode == 0, self._commit("PowerShell").stderr

    @pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
    def test_a_real_push_is_still_gated_on_both_channels(self, tool):
        r = run_hook(
            "git_push_gate.py",
            {"tool_name": tool, "tool_input": {"command": "git push --force"}},
            env={"TAUSIK_PUSH_TICKET_PATH": os.path.join(_REPO_ROOT, ".tausik", "nope.json")},
        )
        assert r.returncode == 2, r.stderr

    @pytest.mark.parametrize(
        "command",
        [
            'tausik memory add "note: never git push --force"',
            "python -c \"print('git push')\"",
        ],
    )
    def test_a_mention_is_not_a_push(self, command):
        """The second case is load-bearing: it fails if the fix routes through
        `scan_target`, which joins an interpreter's payload back RAW. That
        would have traded this false block for a different one."""
        r = run_hook("git_push_gate.py", {"tool_name": "Bash", "tool_input": {"command": command}})
        assert r.returncode == 0, r.stderr

    def test_the_gate_does_not_choose_a_dialect_by_hand(self):
        src = open(os.path.join(_HOOKS, "git_push_gate.py"), encoding="utf-8").read()
        code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
        assert "from pwsh_cmd_parse import" not in code
        assert "shell_channel" in code


class TestScanTargetSeparatesCommandFromProse:
    def test_a_quoted_mention_is_not_a_command(self):
        scanned = scan_target("Write-Output 'never run git push --force'")
        assert "--force" not in scanned

    def test_a_real_command_survives_scanning(self):
        assert "--force" in scan_target("git push --force origin main")

    def test_a_payload_one_wrapper_deep_is_rescanned(self):
        assert "--force" in scan_target("powershell -Command 'git push --force'")


class TestGatesActuallyFireOnTheChannel:
    """End-to-end through the hook processes — the part that was missing.
    Each of these returned 0 (allow) before the task, for one reason only:
    the hook was never asked about `tool_name: PowerShell`."""

    def test_firewall_blocks_a_volume_wipe(self):
        r = run_hook(
            "bash_firewall.py",
            {
                "tool_name": "PowerShell",
                "tool_input": {"command": f"Remove-Item -Recurse -Force C:{BS}"},
            },
        )
        assert r.returncode == 2, r.stderr
        assert "BLOCKED" in r.stderr

    def test_firewall_blocks_force_push_on_the_powershell_channel(self):
        r = run_hook(
            "bash_firewall.py",
            {"tool_name": "PowerShell", "tool_input": {"command": "git push --force origin main"}},
        )
        assert r.returncode == 2, r.stderr

    def test_firewall_allows_ordinary_powershell(self):
        r = run_hook(
            "bash_firewall.py",
            {
                "tool_name": "PowerShell",
                "tool_input": {"command": "Get-ChildItem scripts -Recurse"},
            },
        )
        assert r.returncode == 0, r.stderr

    def test_firewall_still_reads_bash_as_bash(self):
        """The dialect switch must not cost the channel that already worked."""
        r = run_hook(
            "bash_firewall.py", {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
        )
        assert r.returncode == 2, r.stderr

    def test_push_gate_sees_a_push_from_powershell(self):
        r = run_hook(
            "git_push_gate.py",
            {"tool_name": "PowerShell", "tool_input": {"command": "git push --force"}},
            env={
                "TAUSIK_PUSH_TICKET_PATH": os.path.join(_REPO_ROOT, ".tausik", "nonexistent.json")
            },
        )
        assert r.returncode == 2, r.stderr
        assert "push ticket" in r.stderr

    def test_push_gate_ignores_a_quoted_mention(self):
        r = run_hook(
            "git_push_gate.py",
            {
                "tool_name": "PowerShell",
                "tool_input": {"command": "Write-Output 'git push is gated'"},
            },
        )
        assert r.returncode == 0, r.stderr

    def test_write_gate_reads_a_powershell_write(self):
        """No active task in the harness env -> QG-0 blocks, and the message
        must name the channel the agent actually used, not 'Bash'."""
        r = run_hook(
            "bash_write_gate.py",
            {
                "tool_name": "PowerShell",
                "tool_input": {"command": "Set-Content -Path scripts/zzz.py -Value 1"},
            },
        )
        if r.returncode == 2:
            assert "Bash command" not in r.stderr
            assert "PowerShell" in r.stderr
        else:
            # A task IS active in this working copy; then the scope ACL decides
            # and the gate legitimately allows. Either way it must have PARSED
            # the command rather than ignored the channel.
            assert write_targets("Set-Content -Path scripts/zzz.py -Value 1") == ["scripts/zzz.py"]
