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

from typing import Any, Callable


def build_hooks_dict(hook_cmd: Callable[..., str]) -> dict[str, Any]:
    """Build the `hooks` block of .claude/settings.json.

    `hook_cmd(script, suffix="")` returns the formatted command string
    (`python <abs path>/<script><suffix>`).
    """
    return {
        "PreToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("task_gate.py"),
                        "timeout": 10,
                    }
                ],
            },
            {
                "matcher": "Write|Edit|MultiEdit",
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
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("secret_scan.py"),
                        "timeout": 5,
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("bash_firewall.py"),
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
                "matcher": "Bash",
                "if": "Bash(git push *)",
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
                # v1.4 (r14-task-done-verify-v2): cover both v1 and the
                # structured-response v2 MCP tool. Falling off v2 would
                # silently disable the verify-fix-loop hook.
                "matcher": (
                    "mcp__tausik-project__tausik_task_done|mcp__tausik-project__tausik_task_done_v2"
                ),
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
                # HIGH-5 review fix: only Write/Edit/MultiEdit/Bash count
                # toward call_actual. Read/Grep/Glob are research, not work
                # — including them inflates the calibration drift metric.
                "matcher": "Write|Edit|MultiEdit|Bash",
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
                # work. Wide matcher (covers Read/Grep/Glob too).
                "matcher": "Write|Edit|MultiEdit|Bash|Read|Grep|Glob|WebFetch|WebSearch",
                "hooks": [
                    {
                        "type": "command",
                        "command": hook_cmd("activity_event.py"),
                        "timeout": 2,
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
