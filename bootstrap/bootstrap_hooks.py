"""TAUSIK Claude Code hooks block builder.

Extracted from bootstrap_generate.py for filesize compliance
(v14b-filesize-debt-paydown). Public surface:

    build_hooks_dict(_hook_cmd) -> dict

Returns the same hooks block previously inlined in
generate_settings_claude. Caller passes a `_hook_cmd(script, suffix="")`
closure that knows how to format the absolute python path. The hooks
list / contract is unchanged — purely a relocation.
"""

from __future__ import annotations

import os
from typing import Any, Callable


class HooksNotDeployedError(RuntimeError):
    """The hooks a generated config would point at are not on disk."""


def deployed_hooks_dir(target_dir: str) -> str:
    """Where the hooks a generated config must point — the DEPLOYED copy.

    Not the library's `scripts/hooks`. In this repository the two are the same
    directory, because here TAUSIK *is* the project; in a consumer project the
    library is a submodule under `.tausik-lib`, and a submodule contributes ONE
    entry to the index — its gitlink. A clone without `--recurse-submodules`
    therefore has nothing at those paths, and every hook command in the
    generated settings points into an empty directory: no task gate, no secret
    scan, no push gate. The same bootstrap meanwhile writes a CLAUDE.md that
    declares Rule 1 enforced by a PreToolUse hook. Measured on a live consumer
    project: 22 hook commands into `.tausik-lib`, 1 file tracked there, and 26
    byte-identical hooks tracked under the deployed tree right next to it.

    This function only COMPUTES the path; it does not check the deploy. The
    check lives in `assert_hooks_deployed`, called once by the orchestrator
    after `copy_scripts`. Splitting them is deliberate: a generator asked for
    the correct address should answer, and a unit test inspecting the wiring of
    a generated config should not have to provision a hook tree to get one.
    Verifying that the deploy actually happened is the orchestrator's job,
    because only the orchestrator knows a deploy was supposed to have run.
    """
    return os.path.join(target_dir, "scripts", "hooks")


def assert_hooks_deployed(target_dir: str) -> str:
    """Refuse to leave a config naming hooks that are not on disk.

    `copy_scripts` runs before every generator (bootstrap.py), so the deployed
    tree is there by the time settings are written. If it is not, that is a
    broken bootstrap, and staying silent would leave behind a settings file
    that is indistinguishable from a working one — until the first edit slips
    through unguarded. Loud refusal is the only honest outcome.
    """
    hooks = deployed_hooks_dir(target_dir)
    scripts = [f for f in os.listdir(hooks) if f.endswith(".py")] if os.path.isdir(hooks) else []
    if not scripts:
        raise HooksNotDeployedError(
            f"hooks are not deployed at {hooks} — refusing to leave a config that names "
            "them. copy_scripts should have run before settings were generated; if this "
            "fires, the deploy step did not run or failed. A config naming hooks that are "
            "not there enforces nothing and looks identical to one that works."
        )
    return hooks


#: Every tool whose input is a shell command line, as a hook matcher.
#:
#: `powershell-tool-bypasses-bash-firewall`: this used to be the literal
#: `"Bash"`, written out at four separate registrations. On win32 — the
#: platform this project calls primary — the agent is also handed a `PowerShell`
#: tool, and it matched none of them. The firewall, the shell-write gate (QG-0 +
#: scope ACL) and the push gate all still worked perfectly; they simply were
#: never invoked for more than half the commands actually being run.
#:
#: The set of dialects is produced by `scripts/hooks/shell_channel.SHELL_TOOLS`.
#: It is not imported here — bootstrap must stay runnable without the hooks
#: package on `sys.path` — so `test_bootstrap_hooks_parity` asserts the two
#: agree instead. A dialect added to the parser without a matcher fails a test
#: rather than silently going ungated, which is the failure this constant is a
#: memorial to.
SHELL_MATCHER = "Bash|PowerShell"


def build_hooks_dict(hook_cmd: Callable[..., str]) -> dict[str, Any]:
    """Build the `hooks` block of .claude/settings.json.

    `hook_cmd(script, suffix="")` returns the formatted command string
    (`python <abs path>/<script><suffix>`).
    """
    return {
        "PreToolUse": [
            {
                # l26-hook-contract-review: MultiEdit and NotebookEdit also
                # write files and were ungated by QG-0. bash_write_gate.py (on
                # the Bash matcher below) covers the shell-write vector.
                "matcher": "Write|Edit|MultiEdit|NotebookEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("task_gate.py"),
                        "timeout": 10,
                    }
                ],
            },
            {
                # v15-scope-enforce-write (SENAR Rule 2): when any active task
                # declares scope_paths, writes outside the union of declared
                # ACLs are blocked. l26-hook-contract-review AC3: a co-active
                # undeclared task no longer nullifies a sibling's ACL; +
                # NotebookEdit added (it was ungated).
                "matcher": "Write|Edit|MultiEdit|NotebookEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("scope_write_gate.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # memory-route-gate: the shell tools are on the matcher because
                # a heredoc (`cat >> ~/.claude/.../memory/x.md <<EOF`) or a
                # `Set-Content` writes the exact content the Write path refuses.
                # Same hole l26-hook-contract-review closed for QG-0; leaving it
                # open would make the Write block a formality.
                "matcher": f"Write|Edit|MultiEdit|{SHELL_MATCHER}",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("memory_pretool_block.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # SENAR Rule 10.12 (r14-senar-context-hygiene):
                # Warn (or block under TAUSIK_SECRET_SCAN_STRICT=1) when
                # the agent is about to write a likely secret to disk.
                # Shell tools are on the matcher for the same reason
                # memory_pretool_block is (secret-scan-covers-no-shell-channel,
                # Decision #178): a heredoc or a `Set-Content -Value 'AKIA...'`
                # carries the exact secret the Write path would warn on, and
                # leaving it off one channel re-splits the two.
                "matcher": f"Write|Edit|MultiEdit|{SHELL_MATCHER}",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("secret_scan.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                "matcher": SHELL_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("bash_firewall.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # l26-hook-contract-review (Decision #162): close the shell-write
                # bypass of QG-0 + scope-ACL. Parses the command for file-write
                # targets (redirections, tee/dd/sed -i/cp/mv, python open(), and
                # on the PowerShell side Set-Content/Out-File/New-Item) and
                # applies the SAME verdict the Write gates apply. Documented
                # residual: obfuscated writes (see docs/ru/agent-contract.md).
                "matcher": SHELL_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("bash_write_gate.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                "matcher": "WebSearch|WebFetch",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("brain_search_proactive.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # The `"if": "Bash(git push *)"` clause that used to narrow this
                # registration is gone. It was a SECOND, dialect-specific copy
                # of a decision the hook already makes for itself
                # (`_command_invokes_git_push`), and the two could only ever
                # drift apart — which they did: the clause named one shell, so a
                # push issued through the PowerShell tool reached no gate at all.
                # The hook returns 0 in microseconds when the line is not a push,
                # so dropping the pre-filter costs nothing and removes the copy.
                "matcher": SHELL_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("git_push_gate.py"),
                        "timeout": 5,
                    }
                ],
            },
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("auto_format.py"),
                        "timeout": 15,
                    }
                ],
            },
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("memory_posttool_audit.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # v14b-task-done-rename-drop-v2: single tausik_task_done MCP tool.
                # Was a `tausik_task_done|tausik_task_done_v2` alternation pre-1.4
                # when both names existed; rename consolidated them.
                "matcher": "mcp__tausik-project__tausik_task_done",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("task_done_verify.py"),
                        "timeout": 6,
                    }
                ],
            },
            {
                "matcher": "WebFetch",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("brain_post_webfetch.py"),
                        "timeout": 10,
                    }
                ],
            },
            {
                # HIGH-5 review fix: only Write/Edit/MultiEdit + the shell tools
                # count toward call_actual. Read/Grep/Glob are research, not
                # work — including them inflates the calibration drift metric.
                "matcher": f"Write|Edit|MultiEdit|{SHELL_MATCHER}",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("task_call_counter.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                # v1.4 (B4): per-tool usage_events row attributed to the
                # active task — feeds `tausik metrics cost`. Wide matcher
                # because we want every tool invocation to count, not
                # just write-heavy ones. Best-effort: stays silent if
                # harness payload doesn't carry token usage.
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("posttool_usage.py"),
                        "timeout": 4,
                    }
                ],
            },
            {
                # v1.3: writes one row per tool call to the events table
                # so backend_session_metrics.compute_active_minutes
                # actually has data to sum. Without it the 180-min SENAR
                # Rule 9.2 active-time gate never trips on read-heavy
                # work. Wide matcher (covers Read/Grep/Glob too) — and it
                # must name every shell tool, or a session spent working
                # through the uncounted one reads as idle and the duration
                # limit silently stops applying.
                "matcher": (
                    f"Write|Edit|MultiEdit|{SHELL_MATCHER}|Read|Grep|Glob|WebFetch|WebSearch"
                ),
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("activity_event.py"),
                        "timeout": 2,
                    }
                ],
            },
            {
                # v14b-start-lite-tool-truncation: coaching nudge when a
                # tool's textual output exceeds the configured threshold
                # (default 250 lines, override in
                # .tausik/config.json::tool_output_truncation_threshold).
                # Does NOT modify tool output — just emits stderr so the
                # agent reads it next turn and adjusts strategy.
                "matcher": f"Read|Grep|Glob|{SHELL_MATCHER}",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("tool_output_truncation_nudge.py"),
                        "timeout": 3,
                    }
                ],
            },
            {
                # v14c-token-budget-task: cost/token budget runaway
                # protection. Reads usage_events sum for the active task,
                # emits stderr WARN at 1.5× / BLOCKER at 2.0× of
                # cost_budget_usd or token_budget. Throttled per
                # (slug, level) via .tausik/.cost_budget_throttle.json.
                # Wide matcher (every tool call) since cost can spike on
                # any single Bash/Read; silent no-op when no active task
                # has a budget set.
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("task_cost_budget_check.py"),
                        "timeout": 3,
                    }
                ],
            },
        ],
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("session_start.py"),
                        "timeout": 6,
                    }
                ],
            }
        ],
        "UserPromptSubmit": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("user_prompt_submit.py"),
                        "timeout": 5,
                    }
                ],
            }
        ],
        "Stop": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("keyword_detector.py"),
                        "timeout": 5,
                    },
                    {
                        "type": "command",
                        "command": hook_cmd("session_cleanup_check.py"),
                        "timeout": 5,
                    },
                ],
            }
        ],
        "SessionEnd": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("session_metrics.py", " --auto --record 2>&1 || true"),
                    }
                ],
            }
        ],
    }
