"""Adapt Cursor-native hook payloads to TAUSIK's shared Claude hook scripts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_MCP_TOOL_NAMES = {
    "FileSystem": "mcp__windows-mcp__FileSystem",
    "PowerShell": "mcp__windows-mcp__PowerShell",
    "replace_symbol_body": "mcp__serena__replace_symbol_body",
    "replace_content": "mcp__serena__replace_content",
    "insert_after_symbol": "mcp__serena__insert_after_symbol",
    "insert_before_symbol": "mcp__serena__insert_before_symbol",
    "rename_symbol": "mcp__serena__rename_symbol",
    "safe_delete_symbol": "mcp__serena__safe_delete_symbol",
}
_SHARED_EVENTS = {
    "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse",
    "postToolUseFailure": "PostToolUse",
    "sessionStart": "SessionStart",
    "beforeSubmitPrompt": "UserPromptSubmit",
    "stop": "Stop",
    "sessionEnd": "SessionEnd",
}


def _cursor_mcp_tool(short: str) -> str:
    """Map Cursor's MCP display name to the canonical hook tool name."""
    if short in _MCP_TOOL_NAMES:
        return _MCP_TOOL_NAMES[short]
    route = short.rsplit(":", 1)[-1]
    if route.startswith("tausik_"):
        return f"mcp__tausik-project__{route}"
    return f"MCP:{short}"


def normalize_event(event: dict, event_name: str) -> dict:
    """Return the compatibility payload consumed by existing TAUSIK hooks."""
    normalized = dict(event)
    normalized.setdefault("session_id", normalized.get("conversation_id"))
    normalized.setdefault("turn_id", normalized.get("generation_id"))
    tool = normalized.get("tool_name")
    if tool == "Shell":
        normalized["tool_name"] = "PowerShell" if os.name == "nt" else "Bash"
    elif tool == "Delete":
        normalized["tool_name"] = "Write"
    elif isinstance(tool, str) and tool.startswith("MCP:"):
        short = tool.removeprefix("MCP:")
        normalized["tool_name"] = _cursor_mcp_tool(short)
    if event_name == "postToolUseFailure":
        failure_type = normalized.get("failure_type")
        message = normalized.get("error_message")
        normalized["tool_response"] = {
            "is_error": True,
            "error_code": failure_type,
            "error": message,
        }
    normalized["hook_event_name"] = _SHARED_EVENTS.get(event_name, event_name)
    project = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        normalized.setdefault("cwd", project)
    return normalized


def adapt_output(stdout: str, event_name: str, returncode: int) -> str:
    """Translate successful shared-hook output to Cursor's native response schema."""
    if returncode != 0:
        return stdout
    if not stdout.strip():
        if event_name == "preToolUse":
            return json.dumps({"permission": "allow"})
        if event_name == "stop":
            return "{}"
        return ""
    try:
        payload = json.loads(stdout)
    except (TypeError, json.JSONDecodeError):
        return stdout
    if not isinstance(payload, dict):
        return stdout
    nested = payload.get("hookSpecificOutput")
    if isinstance(nested, dict):
        if event_name == "preToolUse":
            decision = nested.get("permissionDecision")
            if decision in {"allow", "deny", "ask"}:
                native = {"permission": decision}
                reason = nested.get("permissionDecisionReason")
                if isinstance(reason, str) and reason:
                    native["user_message"] = reason
                    native["agent_message"] = reason
                if isinstance(nested.get("updatedInput"), dict):
                    native["updated_input"] = nested["updatedInput"]
                return json.dumps(native)
        context = nested.get("additionalContext")
        if isinstance(context, str) and context:
            if event_name in {"sessionStart", "postToolUse", "postToolUseFailure"}:
                return json.dumps({"additional_context": context})
        if event_name == "stop" and nested.get("decision") == "block":
            reason = nested.get("reason")
            if isinstance(reason, str) and reason:
                return json.dumps({"followup_message": reason})
    if event_name in {"postToolUse", "postToolUseFailure"} and isinstance(
        payload.get("systemMessage"), str
    ):
        return json.dumps({"additional_context": payload["systemMessage"]})
    if event_name == "stop" and payload.get("decision") == "block":
        reason = payload.get("reason")
        if isinstance(reason, str) and reason:
            return json.dumps({"followup_message": reason})
    return stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--script-arg", action="append", default=[])
    args = parser.parse_args()
    if Path(args.script).name != args.script or not args.script.endswith(".py"):
        raise ValueError("script must be a sibling Python basename")
    event = json.load(sys.stdin)
    if not isinstance(event, dict):
        raise ValueError("Cursor hook payload must be an object")
    script = Path(__file__).resolve().with_name(args.script)
    if not script.is_file():
        raise FileNotFoundError(script)
    command = [sys.executable, "-X", "utf8", str(script)]
    if args.script == "codex_write_gate.py":
        command.extend(["--project", args.project, "--trusted-host", "cursor"])
    if args.script in {
        "session_start.py",
        "user_prompt_submit.py",
        "can_stop_gate.py",
        "memory_preflight_posttool.py",
    }:
        command.extend(["--trusted-host", "cursor"])
    command.extend(args.script_arg)
    result = subprocess.run(
        command,
        input=json.dumps(normalize_event(event, args.event)),
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": args.project,
            "CURSOR_PROJECT_DIR": args.project,
        },
    )
    output = adapt_output(result.stdout, args.event, result.returncode)
    if output:
        sys.stdout.write(output)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
