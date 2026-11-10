"""Behavior tests for observed Codex payloads; these are not live-host evidence."""

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    assertion_from_session_start,
    consume_mcp_authorization,
    issue_execution_lease,
    reconcile_execution_lease_state,
)

_GATE = Path(__file__).resolve().parents[1] / "scripts/hooks/codex_write_gate.py"
_POST_GATE = _GATE.with_name("memory_preflight_posttool.py")
HOOKS_DIR = _GATE.parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from write_tools import MCP_SHELL_TOOLS, WRITE_TOOLS  # noqa: E402


def run_gate(root, event, state="no_task"):
    event = dict(event)
    directory = root / ".tausik"
    directory.mkdir(exist_ok=True)
    backend = SQLiteBackend(str(directory / "tausik.db"))
    try:
        if state != "no_task":
            backend._ex(
                """INSERT OR IGNORE INTO tasks(
                    slug, title, status, scope_paths, created_at, updated_at
                ) VALUES ('probe', 'Probe', 'active', ?, '2026-10-01', '2026-10-01')""",
                (json.dumps(["allowed.py"]),),
            )
        if state in {
            "active_unbound",
            "allowed",
            "allowed_preflight",
            "broken_preflight_store",
        }:
            event.setdefault("session_id", "thread-a")
            svc = ProjectService(backend)
            svc.task_update(
                "probe",
                complexity="medium",
                goal="exercise the observed write gate",
                acceptance_criteria="AC-1 allowed writes pass. Negative: out-of-scope writes fail.",
                scope="allowed.py",
                rollback_plan="delete the temporary fixture",
            )
            assertion = assertion_from_session_start(
                {"hook_event_name": "SessionStart", "session_id": "thread-a"},
                str(root),
                trusted_host="codex",
            )
            reconcile_execution_lease_state(svc, assertion)
            lease = issue_execution_lease(svc, assertion)
            if state != "active_unbound":
                svc.task_start("probe", include_memory=False, execution_lease_id=lease["id"])
            if state == "allowed_preflight":
                from memory_preflight import classify_action, issue_preflight

                lease = backend._q1("SELECT * FROM execution_leases WHERE id=?", (lease["id"],))
                svc._authorized_execution_lease = lease
                from codex_composite_mcp import parse_composite_calls

                calls = parse_composite_calls(event["tool_name"], event["tool_input"])
                actions = (
                    [(f"mcp__tausik-project__{call.route}", call.arguments) for call in calls]
                    if calls
                    else [(event["tool_name"], event["tool_input"])]
                )
                for action_tool, action_input in actions:
                    protected_kind = classify_action(action_tool, action_input)
                    if protected_kind is None:
                        continue
                    preview = issue_preflight(
                        svc,
                        protected_kind=protected_kind,
                        tool_name=action_tool,
                        tool_input=action_input,
                    )
                    issue_preflight(
                        svc,
                        protected_kind=protected_kind,
                        tool_name=action_tool,
                        tool_input=action_input,
                        acknowledged_ids=preview["acknowledge_ids"],
                        inspection_id=preview["inspection_id"],
                    )
            elif state == "broken_preflight_store":
                backend._ex("DROP TABLE memory_preflight_tokens")
    finally:
        backend.close()

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_OPEN")
    }
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(_GATE), "--project", str(root)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        encoding="utf-8",
        cwd=root.parent,  # host launch cwd is NOT project jurisdiction
        env=env,
        timeout=10,
    )


@pytest.mark.parametrize("route", ["patch", "powershell_as_bash"])
@pytest.mark.parametrize("state", ["no_task", "out_of_scope", "allowed"])
def test_observed_payloads_use_real_task_and_scope_gates(tmp_path, route, state):
    target = "outside.py" if state == "out_of_scope" else "allowed.py"
    if route == "patch":
        tool, command = (
            "apply_patch",
            f"*** Begin Patch\n*** Add File: {target}\n+VALUE = 1\n*** End Patch",
        )
    else:
        tool, command = "Bash", f"Set-Content -LiteralPath {target} -Value VALUE"
    result = run_gate(
        tmp_path,
        {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(tmp_path)},
        state,
    )
    assert result.returncode == 0, result.stderr
    if state == "allowed":
        assert not result.stdout
    else:
        assert_denied(result)


def assert_denied(result):
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"]
    return decision["permissionDecisionReason"]


def rewritten_input(result):
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "allow"
    return decision["updatedInput"]


def run_post_gate(root, event):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(_POST_GATE), "--project", str(root)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        encoding="utf-8",
        cwd=root.parent,
        timeout=10,
    )


@pytest.mark.parametrize(
    "patch",
    [
        "*** Add File: allowed.py\n+ok\n*** Add File: outside.py\n+bad",
        "*** Update File: allowed.py\n*** Move to: outside.py\n@@\n-old\n+new",
        "*** Delete File: outside.py",
    ],
)
def test_every_patch_target_including_move_and_delete_is_checked(tmp_path, patch):
    result = run_gate(
        tmp_path,
        {
            "tool_name": "apply_patch",
            "cwd": str(tmp_path),
            "tool_input": {"command": f"*** Begin Patch\n{patch}\n*** End Patch"},
        },
        "active",
    )
    assert "outside.py" in assert_denied(result)


@pytest.mark.parametrize(
    "event",
    [
        [],
        {"tool_name": "apply_patch", "tool_input": {"command": "unrecognized patch"}},
        {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** End Patch"}},
        {"tool_name": "apply_patch", "tool_input": {}},
        {"tool_name": "Bash", "tool_input": {"command": "Set-Content"}},
    ],
)
def test_uncheckable_payloads_refuse_instead_of_appearing_protected(tmp_path, event):
    assert_denied(run_gate(tmp_path, event, "active"))


def test_payload_cwd_resolves_relative_patch_targets(tmp_path):
    child = tmp_path / "subdir"
    child.mkdir()
    event = {
        "tool_name": "apply_patch",
        "cwd": str(child),
        "tool_input": {
            "command": "*** Begin Patch\n*** Add File: allowed.py\n+content\n*** End Patch"
        },
    }
    result = run_gate(tmp_path, event, "active")
    assert_denied(result)  # subdir/allowed.py is not allowed.py


@pytest.mark.parametrize(
    "command", ["Get-Content allowed.py", "Write-Output 'Set-Content outside.py'"]
)
def test_read_or_quoted_write_text_is_not_promoted_to_a_write(tmp_path, command):
    event = {"tool_name": "Bash", "tool_input": {"command": command}}
    result = run_gate(tmp_path, event)
    assert result.returncode == 0
    assert not result.stdout


def test_trusted_pretool_authorization_is_consumed_once_by_mcp(tmp_path, monkeypatch):
    event = {
        "tool_name": "mcp__tausik-project__tausik_audit_mark",
        "tool_input": {},
        "session_id": "thread-a",
    }
    result = run_gate(tmp_path, event, "allowed_preflight")
    assert result.returncode == 0
    dispatched = rewritten_input(result)
    authorization = dispatched.pop("_tausik_authorization")

    mcp_dir = _GATE.parents[2] / "harness" / "claude" / "mcp" / "project"
    if str(mcp_dir) not in sys.path:
        sys.path.insert(0, str(mcp_dir))
    from handlers import handle_tool

    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
        with pytest.raises(Exception, match="IDENTITY_MISSING"):
            handle_tool(ProjectService(backend), "tausik_audit_mark", {})
        assert backend._q1(
            "SELECT COUNT(*) AS count FROM execution_authorizations WHERE consumed_at IS NULL"
        ) == {"count": 1}
        assert "Audit marked" in handle_tool(
            ProjectService(backend),
            "tausik_audit_mark",
            dispatched,
            authorization=authorization,
        )
        with pytest.raises(Exception, match="IDENTITY_MISSING"):
            handle_tool(ProjectService(backend), "tausik_audit_mark", {})
    finally:
        backend.close()


def test_production_composite_trace_dispatches_exact_inner_calls_once(tmp_path, monkeypatch):
    (tmp_path / "CLAUDE.md").write_text(
        "# Project\n\n<!-- DYNAMIC:START -->\nstale\n<!-- DYNAMIC:END -->\n",
        encoding="utf-8",
    )
    code = (
        "const a = await tools.mcp__tausik_project__tausik_session_open({});\n"
        "const b = await tools.mcp__tausik_project__tausik_update_claudemd({});"
    )
    event = {"tool_name": "exec", "tool_input": code, "session_id": "thread-a"}
    result = run_gate(tmp_path, event, "allowed_preflight")
    assert result.returncode == 0
    dispatched = rewritten_input(result)
    calls = __import__("codex_composite_mcp").parse_composite_calls(
        "exec", dispatched, accept_authorization=True
    )

    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        svc = ProjectService(backend)
        mcp_dir = _GATE.parents[2] / "harness" / "claude" / "mcp" / "project"
        if str(mcp_dir) not in sys.path:
            sys.path.insert(0, str(mcp_dir))
        from handlers import handle_tool

        monkeypatch.setenv("TAUSIK_ENFORCE_EXECUTION_LEASE", "1")
        before = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        for missing in (None, "stolen-correlation"):
            with pytest.raises(Exception, match="IDENTITY_MISSING"):
                handle_tool(svc, "tausik_update_claudemd", {}, authorization=missing)
            assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == before

        assert (
            "session"
            in handle_tool(
                svc, "tausik_session_open", {}, authorization=calls[0].authorization
            ).lower()
        )
        assert (
            "updated"
            in handle_tool(
                svc, "tausik_update_claudemd", {}, authorization=calls[1].authorization
            ).lower()
        )
        updated = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Current State" in updated
        assert updated != before
        with pytest.raises(Exception, match="IDENTITY_MISSING"):
            handle_tool(svc, "tausik_update_claudemd", {}, authorization=calls[1].authorization)
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == updated
    finally:
        backend.close()

    completed = run_post_gate(
        tmp_path, {**event, "tool_input": dispatched, "tool_response": {"isError": False}}
    )
    assert completed.returncode == 0 and not completed.stderr
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        assert backend._q1(
            "SELECT status FROM memory_preflight_tokens ORDER BY id DESC LIMIT 1"
        ) == {"status": "executed"}
    finally:
        backend.close()


@pytest.mark.parametrize(
    "code",
    [
        "const open = tools.mcp__tausik_project__tausik_session_open; await open({});",
        "await Promise.all([tools.mcp__tausik_project__tausik_session_open({})]);",
        "const { mcp__tausik_project__tausik_session_open: open } = tools; await open({});",
    ],
)
def test_composite_alias_and_wrapper_shapes_use_the_trusted_outer_thread(tmp_path, code):
    event = {"tool_name": "functions.exec", "tool_input": {"code": code}, "session_id": "thread-a"}
    result = run_gate(tmp_path, event, "allowed")
    assert result.returncode == 0
    dispatched = rewritten_input(result)
    call = __import__("codex_composite_mcp").parse_composite_calls(
        "functions.exec", dispatched, accept_authorization=True
    )[0]
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        consume_mcp_authorization(
            ProjectService(backend),
            route="tausik_session_open",
            arguments={},
            authorization=call.authorization,
        )
    finally:
        backend.close()


@pytest.mark.parametrize(
    "code",
    [
        "const args = {}; tools.mcp__tausik_project__tausik_session_open(args);",
        "const open = tools.mcp__tausik_project__tausik_session_open; wrapper(open);",
        "tools[`mcp__tausik_project__tausik_session_open`]({});",
        (
            "tools.mcp__tausik_project__tausik_session_open({});"
            "tools.mcp__tausik_project__tausik_session_open({});"
        ),
        (
            "fake.tools.mcp__tausik_project__tausik_session_open({});"
            'tools["mcp__tausik_project__tausik_session_open"]({});'
        ),
        (
            "const open = tools.mcp__tausik_project__tausik_update_claudemd;"
            "const obj = {open: args => "
            'tools["mcp__tausik_project__tausik_update_claudemd"](args)};'
            "obj.open({});"
        ),
    ],
)
def test_unbound_or_ambiguous_composite_shapes_fail_closed(tmp_path, code):
    event = {"tool_name": "exec", "tool_input": code, "session_id": "thread-a"}
    assert assert_denied(run_gate(tmp_path, event, "allowed"))
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        assert backend._q1(
            "SELECT COUNT(*) AS count FROM execution_authorizations WHERE consumed_at IS NULL"
        ) == {"count": 0}
    finally:
        backend.close()


def test_composite_read_only_calls_do_not_require_mutation_authority(tmp_path):
    event = {
        "tool_name": "exec",
        "tool_input": (
            'text(await tools.mcp__tausik_project__tausik_memory_search({"query":"alpha"}));'
        ),
    }
    result = run_gate(tmp_path, event)
    assert result.returncode == 0 and not result.stdout


def test_composite_wrong_thread_cannot_authorize_inner_mutation(tmp_path):
    event = {
        "tool_name": "exec",
        "tool_input": "tools.mcp__tausik_project__tausik_session_open({});",
        "session_id": "thread-b",
    }
    assert "LEASE_MISSING" in assert_denied(run_gate(tmp_path, event, "allowed"))


def test_composite_session_open_bootstraps_before_task_package_binding(tmp_path):
    event = {
        "tool_name": "exec",
        "tool_input": "tools.mcp__tausik_project__tausik_session_open({});",
        "session_id": "thread-a",
    }
    result = run_gate(tmp_path, event, "active_unbound")
    assert result.returncode == 0
    dispatched = rewritten_input(result)
    call = __import__("codex_composite_mcp").parse_composite_calls(
        "exec", dispatched, accept_authorization=True
    )[0]

    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        consume_mcp_authorization(
            ProjectService(backend),
            route="tausik_session_open",
            arguments={},
            authorization=call.authorization,
        )
    finally:
        backend.close()


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "env X=1 git push origin main",
        "cd repo && gh release create v1",
        ".tausik/tausik task block probe reason",
    ],
)
def test_protected_shell_and_cli_reserve_the_exact_preflight(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    assert "TOKEN_MISSING" in assert_denied(run_gate(tmp_path, event, "allowed"))
    allowed = run_gate(tmp_path, event, "allowed_preflight")
    assert allowed.returncode == 0
    assert not allowed.stdout


def test_wrong_thread_cannot_authorize_mcp_mutation(tmp_path):
    event = {
        "tool_name": "mcp__tausik-project__tausik_audit_mark",
        "tool_input": {},
        "session_id": "thread-b",
    }
    result = run_gate(tmp_path, event, "allowed")
    assert "LEASE_MISSING" in assert_denied(result)


def test_protected_action_fails_closed_when_token_store_is_unavailable(tmp_path):
    event = {
        "tool_name": "mcp__tausik-project__tausik_audit_mark",
        "tool_input": {},
        "session_id": "thread-a",
    }
    reason = assert_denied(run_gate(tmp_path, event, "broken_preflight_store"))
    assert "CAPABILITY_MISMATCH" in reason


@pytest.mark.parametrize("tool", [*WRITE_TOOLS, *MCP_SHELL_TOOLS])
def test_every_governed_codex_write_surface_requires_current_thread_lease(tmp_path, tool):
    tool_input = (
        {"command": "Set-Content -LiteralPath allowed.py -Value VALUE"}
        if tool in MCP_SHELL_TOOLS
        else {"file_path": "allowed.py"}
    )
    wrong_thread = {"tool_name": tool, "tool_input": tool_input, "session_id": "thread-b"}
    assert "LEASE_MISSING" in assert_denied(run_gate(tmp_path, wrong_thread, "allowed"))

    current_thread = {"tool_name": tool, "tool_input": tool_input, "session_id": "thread-a"}
    allowed = run_gate(tmp_path, current_thread, "allowed")
    assert allowed.returncode == 0
    assert not allowed.stdout


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik task log probe implementation note",
        "python scripts/project.py task log probe implementation note",
    ],
)
def test_codex_cli_mutations_require_the_event_thread_lease(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-b",
    }
    assert "LEASE_MISSING" in assert_denied(run_gate(tmp_path, event, "allowed"))


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik task log other note",
        "python scripts/project.py task log other note",
        ".tausik/tausik decide choice --task other",
        "python scripts/project.py decide choice --task other",
        ".tausik/tausik dead-end approach reason --task other",
        ".tausik/tausik dead-end approach reason --task=other",
        ".tausik/tausik verify --task other",
        ".tausik/tausik review record --task=other --type L1",
        ".tausik/tausik metrics log-usage --task-slug=other --tokens-input 1 --tokens-output 1 --tokens-total 2 --cost-usd 0",
        ".tausik/tausik task summary-back other summary",
        ".tausik/tausik spec link other spec-a implements",
        ".tausik/tausik spec unlink other spec-a implements",
        ".tausik/tausik memory add context title content --task other",
        ".tausik/tausik memory add context title content --task=other",
        ".tausik/tausik adapt link adapt-a task other",
        ".tausik/tausik actz link actz-a task other",
        ".tausik/tausik actz unlink actz-a task other",
    ],
)
def test_codex_cli_task_mutations_cannot_cross_the_bound_task(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    assert "TASK_BINDING_MISMATCH" in assert_denied(run_gate(tmp_path, event, "allowed"))


@pytest.mark.parametrize(
    "launcher",
    [
        ".tausik/tausik",
        "python scripts/project.py",
        "python3.11 scripts/project.py",
        "py -3 scripts/project.py",
        "python -u scripts/project.py",
        r'"C:\Python311\python.exe" "C:\repo\scripts\project.py"',
        "TAUSIK_X=1 python scripts/project.py",
        "env TAUSIK_X=1 python scripts/project.py",
        "command python scripts/project.py",
        "exec python scripts/project.py",
        "env -u TAUSIK_X python scripts/project.py",
        "env -C . python scripts/project.py",
        "env -S 'python scripts/project.py'",
    ],
)
def test_codex_cli_task_start_hands_its_exact_lease_to_the_cli(tmp_path, launcher, capsys):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": f"{launcher} task start probe"},
        "session_id": "thread-a",
    }
    allowed = run_gate(tmp_path, event, "allowed")
    assert allowed.returncode == 0 and not allowed.stdout
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        svc = ProjectService(backend)
        from project_cli_task import cmd_task

        cmd_task(
            svc,
            SimpleNamespace(task_cmd="start", slug="probe", package=False, force=False),
        )
        assert "resumed" in capsys.readouterr().out
        lease = svc.be._q1("SELECT * FROM execution_leases WHERE task_slug='probe'")
        assert lease is not None
        with pytest.raises(Exception, match="IDENTITY_MISSING"):
            consume_mcp_authorization(svc, route="cli_task_start", arguments={"slug": "probe"})
    finally:
        backend.close()


def test_cli_start_binds_a_previously_unbound_exact_lease(tmp_path, capsys):
    directory = tmp_path / ".tausik"
    directory.mkdir()
    backend = SQLiteBackend(str(directory / "tausik.db"))
    try:
        svc = ProjectService(backend)
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "probe", "Probe", complexity="simple")
        svc.task_update(
            "probe",
            goal="bind exact lease",
            acceptance_criteria="AC-1 binds. Negative: missing authorization is refused.",
        )
        assertion = assertion_from_session_start(
            {"hook_event_name": "SessionStart", "session_id": "thread-a"},
            str(tmp_path),
            trusted_host="codex",
        )
        reconcile_execution_lease_state(svc, assertion)
        issued = issue_execution_lease(svc, assertion)
        assert issued["task_slug"] is None
    finally:
        backend.close()

    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "python scripts/project.py task start probe"},
        "session_id": "thread-a",
    }
    allowed = run_gate(tmp_path, event)
    assert allowed.returncode == 0 and not allowed.stdout
    backend = SQLiteBackend(str(directory / "tausik.db"))
    try:
        svc = ProjectService(backend)
        from project_cli_task import cmd_task

        cmd_task(
            svc,
            SimpleNamespace(task_cmd="start", slug="probe", package=False, force=False),
        )
        capsys.readouterr()
        bound = svc.be._execution_lease_by_nonce(issued["nonce"])
        assert bound["task_slug"] == "probe"
        assert bound["task_package_fingerprint"]
    finally:
        backend.close()


def test_subshell_cli_start_authorizes_the_exact_route(tmp_path):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "(python scripts/project.py task start probe)"},
        "session_id": "thread-a",
    }
    allowed = run_gate(tmp_path, event, "allowed")
    assert allowed.returncode == 0 and not allowed.stdout
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        lease = consume_mcp_authorization(
            ProjectService(backend), route="cli_task_start", arguments={"slug": "probe"}
        )
        assert lease["task_slug"] == "probe"
    finally:
        backend.close()


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik task start --package probe",
        "python scripts/project.py task start --max-bytes 16384 probe",
        "python scripts/project.py task start --max-bytes=16384 probe --package",
    ],
)
def test_cli_start_options_before_slug_authorize_the_exact_task(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    allowed = run_gate(tmp_path, event, "allowed")
    assert allowed.returncode == 0 and not allowed.stdout
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        lease = consume_mcp_authorization(
            ProjectService(backend), route="cli_task_start", arguments={"slug": "probe"}
        )
        assert lease["task_slug"] == "probe"
    finally:
        backend.close()


@pytest.mark.parametrize(
    "command",
    [
        "exec -a alias python scripts/project.py task start probe",
        "env -a alias python scripts/project.py task start probe",
        "env --argv0 alias python scripts/project.py task start probe",
        "time python scripts/project.py task start probe",
        "nice python scripts/project.py task start probe",
        "! python scripts/project.py task start probe",
        "{ python scripts/project.py task start probe; }",
        "bash -c 'python scripts/project.py task start probe'",
    ],
)
def test_unsupported_tausik_shell_wrappers_fail_closed(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    denial = assert_denied(run_gate(tmp_path, event, "allowed"))
    assert "unsupported TAUSIK CLI invocation shape" in denial


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik task log other bad > allowed.py",
        "(.tausik/tausik task log other bad) > allowed.py",
        "Set-Content -LiteralPath allowed.py -Value ok; .tausik/tausik task log other bad",
    ],
)
def test_redirects_and_prior_writes_do_not_preempt_exact_task_binding(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    denial = assert_denied(run_gate(tmp_path, event, "allowed"))
    assert "TASK_BINDING_MISMATCH" in denial or "unsupported TAUSIK CLI" in denial


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            ".tausik/tausik task log probe ok; time .tausik/tausik task log other bad",
            "unsupported TAUSIK CLI invocation shape",
        ),
        (
            ".tausik/tausik task log probe ok && exec -a alias python scripts/project.py task log other bad",
            "unsupported TAUSIK CLI invocation shape",
        ),
        (
            ".tausik/tausik task log probe $(time .tausik/tausik task log other bad)",
            "unsupported nested shell substitution",
        ),
        (
            ".tausik/tausik task log probe `python scripts/project.py task log other bad`",
            "unsupported nested shell substitution",
        ),
        (
            ".tausik/tausik task start probe < <(.tausik/tausik task log probe bypass)",
            "unsupported nested shell substitution",
        ),
        (
            ".tausik/tausik task start probe > >(.tausik/tausik task log probe bypass)",
            "unsupported nested shell substitution",
        ),
        (
            '.tausik/tausik task log probe "apostrophe\' literal" $(.tausik/tausik task log other hidden)',
            "unsupported nested shell substitution",
        ),
    ],
)
def test_shell_composition_rejects_every_unclassified_tausik_invocation(
    tmp_path, command, expected
):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    denial = assert_denied(run_gate(tmp_path, event, "allowed"))
    assert expected in denial


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik task start probe > outside.py",
        ".tausik/tausik task start probe; time .tausik/tausik task log other bad",
    ],
)
def test_denied_composite_command_leaves_no_durable_authorization(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    assert_denied(run_gate(tmp_path, event, "allowed"))
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        count = backend._q1(
            "SELECT COUNT(*) AS count FROM execution_authorizations WHERE consumed_at IS NULL"
        )
        assert count == {"count": 0}
    finally:
        backend.close()


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik task log probe before; .tausik/tausik task start probe",
        ".tausik/tausik task start --package --max-bytes 1 probe; .tausik/tausik task log probe after",
        ".tausik/tausik task start probe; .tausik/tausik task start probe",
    ],
)
def test_recovery_start_must_be_the_only_tausik_action(tmp_path, command):
    setup = {"tool_name": "Bash", "tool_input": {"command": "Get-Content allowed.py"}}
    assert run_gate(tmp_path, setup, "allowed").returncode == 0
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        ProjectService(backend).task_update("probe", goal="make the bound package stale")
    finally:
        backend.close()

    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    denial = assert_denied(run_gate(tmp_path, event))
    assert "task start must be the only TAUSIK action" in denial
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        count = backend._q1(
            "SELECT COUNT(*) AS count FROM execution_authorizations WHERE consumed_at IS NULL"
        )
        assert count == {"count": 0}
    finally:
        backend.close()


@pytest.mark.parametrize(
    "command",
    [
        "python3 scripts/projec?.py task log other bad",
        "python3 scripts/proj''ect.py task log other bad",
        r"python3 scripts/project\.py task log other bad",
        "python3 scripts/projec{t,x}.py task log other bad",
        'python3 "$TAUSIK_SCRIPT" task log other bad',
    ],
)
def test_shell_expansion_cannot_hide_a_possible_tausik_entrypoint(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    denial = assert_denied(run_gate(tmp_path, event, "allowed"))
    assert "unsupported TAUSIK CLI invocation shape" in denial


def test_redirected_same_task_cli_still_authorizes_both_effects(tmp_path):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": ".tausik/tausik task log probe ok > allowed.py"},
        "session_id": "thread-a",
    }
    allowed = run_gate(tmp_path, event, "allowed_preflight")
    assert allowed.returncode == 0 and not allowed.stdout


@pytest.mark.parametrize(
    "launcher",
    [
        ".tausik/tausik",
        "python scripts/project.py",
        "python3.11 scripts/project.py",
        "py -3 scripts/project.py",
        "python -u scripts/project.py",
        r'"C:\Python311\python.exe" "C:\repo\scripts\project.py"',
        "TAUSIK_X=1 python scripts/project.py",
        "env TAUSIK_X=1 python scripts/project.py",
        "command python scripts/project.py",
        "exec python scripts/project.py",
        "env -u TAUSIK_X python scripts/project.py",
        "env -C . python scripts/project.py",
        "env -S 'python scripts/project.py'",
    ],
)
def test_codex_cli_task_start_recovers_a_stale_bound_package(tmp_path, launcher):
    setup = {"tool_name": "Bash", "tool_input": {"command": "Get-Content allowed.py"}}
    assert run_gate(tmp_path, setup, "allowed").returncode == 0
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        svc = ProjectService(backend)
        svc.task_update("probe", goal="changed after package binding")
    finally:
        backend.close()

    event = {
        "tool_name": "Bash",
        "tool_input": {"command": f"{launcher} task start probe"},
        "session_id": "thread-a",
    }
    allowed = run_gate(tmp_path, event)
    assert allowed.returncode == 0 and not allowed.stdout
    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        svc = ProjectService(backend)
        from project_cli_task import cmd_task

        cmd_task(
            svc,
            SimpleNamespace(task_cmd="start", slug="probe", package=False, force=False),
        )
        lease = svc.be._q1("SELECT * FROM execution_leases WHERE task_slug='probe'")
        assert (
            svc.be._execution_lease_by_nonce(lease["nonce"])["task_package_fingerprint"]
            == svc.be._q1("SELECT fingerprint FROM task_context_packages WHERE task_slug='probe'")[
                "fingerprint"
            ]
        )
    finally:
        backend.close()


@pytest.mark.parametrize(
    "command",
    [
        ".tausik/tausik verify --tasks probe other",
        ".tausik/tausik verify --story story-a",
        ".tausik/tausik verify --epic=epic-a",
        ".tausik/tausik review cohort-open --tasks probe other",
        ".tausik/tausik review cohort-status 10",
        ".tausik/tausik review cohort-status 10 > allowed.py",
        ".tausik/tausik review cohort-record 10 --round 1 --results-json x --packet-digest d --author-model a --reviewer-model r",
        ".tausik/tausik review cohort-decide 10 --action repair-open --owner o --reason r",
    ],
)
def test_codex_cli_project_level_verification_needs_project_level_lease(tmp_path, command):
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "thread-a",
    }
    assert "TASK_BINDING_SCOPE" in assert_denied(run_gate(tmp_path, event, "allowed"))


@pytest.mark.parametrize(
    "argv",
    [
        ["decide", "choice", "--ta", "other"],
        ["dead-end", "attempt", "reason", "--tas", "other"],
        ["review", "record", "--ta", "other", "--type", "L1"],
        ["metrics", "log-usage", "--task", "other"],
        ["verify", "--sto", "story-a"],
    ],
)
def test_cli_rejects_abbreviated_long_options(argv):
    from project_parser import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)
