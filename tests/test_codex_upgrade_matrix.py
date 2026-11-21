"""Published Codex consumer upgrades across every interactive risk boundary."""

from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(os.environ.get("TAUSIK_QUALIFICATION_ROOT", Path(__file__).resolve().parents[1]))
MANIFEST = Path(
    os.environ.get(
        "TAUSIK_QUALIFICATION_MANIFEST",
        ROOT / "tests" / "fixtures" / "codex_upgrade_matrix_v1.json",
    )
)
pytestmark = pytest.mark.slow


def _run(argv: list[str], cwd: Path, *, input_text: str | None = None, timeout: int = 180):
    return subprocess.run(
        argv,
        cwd=str(cwd),
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(cwd),
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONUTF8": "1",
        },
        check=False,
    )


def _step(argv: list[str], cwd: Path, label: str, *, input_text: str | None = None):
    result = _run(argv, cwd, input_text=input_text)
    assert result.returncode == 0, (
        f"{label} failed:\n{result.stdout[-1200:]}\n{result.stderr[-600:]}"
    )
    return result


def _git(repo: Path, *args: str) -> str:
    result = _run(["git", "-C", str(repo), *args], repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _entries() -> list[dict[str, str]]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["published"]


def _journey_cases() -> list[dict[str, str]]:
    versions = [
        {"tag": "clean-current", "boundary": "clean-current", "source": "current"},
        *({**entry, "source": "published"} for entry in _entries()),
    ]
    return [{**version, "host": host} for host in ("codex", "cursor") for version in versions]


def _publication_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["publication"]


def _verify_publication_lines(
    publication: dict[str, object], entries: list[dict[str, str]], output: str
) -> None:
    """Require one exact anonymous tag ref for every qualified snapshot."""
    observed: dict[str, list[str]] = {}
    for line in output.splitlines():
        try:
            object_id, ref = line.split("\t", 1)
        except ValueError as exc:
            raise ValueError("publication remote returned an invalid ref line") from exc
        observed.setdefault(ref, []).append(object_id)

    for entry in entries:
        ref = f"refs/tags/{entry['tag']}"
        object_id = entry["commit"]
        if len(object_id) != 40:
            raise ValueError(f"publication manifest has no immutable object for {ref}")
        if observed.get(ref) != [object_id]:
            raise ValueError(f"publication remote does not match {ref}")
    if set(observed) != {f"refs/tags/{entry['tag']}" for entry in entries}:
        raise ValueError("publication remote returned an unexpected ref set")


def _verify_anonymous_publication_remote() -> None:
    publication = _publication_manifest()
    remote_url = publication.get("anonymous_url")
    if not isinstance(remote_url, str) or not remote_url.startswith("https://github.com/"):
        raise ValueError("publication manifest has no anonymous HTTPS endpoint")
    refs = [f"refs/tags/{entry['tag']}" for entry in _entries()]
    result = _run(["git", "ls-remote", remote_url, *refs], ROOT, timeout=60)
    if result.returncode != 0:
        raise ValueError(f"publication remote could not be verified: {result.stderr.strip()}")
    _verify_publication_lines(publication, _entries(), result.stdout)


def _verify_pin(repo: Path, entry: dict[str, str]) -> None:
    commit = entry["commit"]
    if _git(repo, "rev-parse", f"{entry['tag']}^{{commit}}") != commit:
        raise ValueError("published tag does not resolve to the pinned commit")
    if _git(repo, "rev-parse", f"{commit}^{{tree}}") != entry["tree"]:
        raise ValueError("published commit does not resolve to the pinned tree")


def _extract(repo: Path, entry: dict[str, str], destination: Path) -> None:
    _verify_pin(repo, entry)
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", entry["commit"]],
        capture_output=True,
        timeout=60,
        check=True,
    ).stdout
    destination.mkdir()
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            assert destination.resolve() in target.parents or target == destination.resolve()
        bundle.extractall(destination)


@pytest.fixture(scope="session")
def published_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Fetch only the pinned anonymous release refs into a disposable object store."""
    trusted_objects = os.environ.get("TAUSIK_QUALIFICATION_OBJECTS")
    if trusted_objects:
        return Path(trusted_objects)
    repo = tmp_path_factory.mktemp("codex-publication") / "objects.git"
    _step(["git", "init", "--bare", str(repo)], repo.parent, "publication object store")
    remote_url = _publication_manifest()["anonymous_url"]
    refspecs = [f"+refs/tags/{entry['tag']}:refs/tags/{entry['tag']}" for entry in _entries()]
    _step(
        ["git", "-C", str(repo), "fetch", "--no-tags", "--depth=1", remote_url, *refspecs],
        repo.parent,
        "anonymous publication fetch",
    )
    return repo


_DEPLOY = """
import inspect, pathlib, sys
snapshot = pathlib.Path(sys.argv[1]).resolve()
consumer = pathlib.Path(sys.argv[2]).resolve()
host = sys.argv[3]
sys.path[:0] = [str(snapshot / 'bootstrap'), str(snapshot / 'scripts')]
from bootstrap_copy import copy_mcp, copy_scripts
from bootstrap_venv import install_cli_wrapper
target = consumer / f'.{host}'
copy_scripts(str(snapshot), str(target))
copy_mcp(str(snapshot), str(target), host)
if host == 'codex':
    from bootstrap_codex import scaffold_codex
    scaffold_codex(str(consumer), str(target), sys.executable, str(snapshot))
else:
    import bootstrap_generate
    bootstrap_generate.generate_cursorrules(
        str(consumer), 'upgrade-matrix', ['python']
    )
    bootstrap_generate.generate_cursor_mcp_json(
        str(consumer), str(target), sys.executable
    )
    if hasattr(bootstrap_generate, 'generate_cursor_hooks_json'):
        bootstrap_generate.generate_cursor_hooks_json(
            str(consumer), str(target), venv_python=sys.executable
        )
wrapper_args = [str(snapshot / 'bootstrap'), str(consumer / '.tausik')]
if len(inspect.signature(install_cli_wrapper).parameters) >= 3:
    wrapper_args.append(host)
install_cli_wrapper(*wrapper_args)
"""

_ISSUE_PREFLIGHT = """
import json, pathlib, sys
consumer = pathlib.Path(sys.argv[1]).resolve()
thread_id = sys.argv[2]
tool_name = sys.argv[3]
tool_input = json.loads(sys.argv[4])
sys.path.insert(0, str(consumer / '.codex' / 'scripts'))
from memory_preflight import classify_action, issue_preflight
from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import normalize_project_identity
backend = SQLiteBackend(str(consumer / '.tausik' / 'tausik.db'))
try:
    lease = backend._execution_lease_current(
        normalize_project_identity(str(consumer)), 'codex', thread_id
    )
    if lease is None:
        raise RuntimeError('preflight fixture requires a live deployed Codex lease')
    service = ProjectService(backend)
    service._authorized_execution_lease = lease
    kind = classify_action(tool_name, tool_input)
    if kind is None:
        raise RuntimeError('preflight fixture action must be protected')
    preview = issue_preflight(
        service, protected_kind=kind, tool_name=tool_name, tool_input=tool_input
    )
    issue_preflight(
        service,
        protected_kind=kind,
        tool_name=tool_name,
        tool_input=tool_input,
        acknowledged_ids=preview['acknowledge_ids'],
        inspection_id=preview['inspection_id'],
    )
finally:
    backend.close()
"""

_MCP_CALL = """
import json, os, pathlib, sys
consumer = pathlib.Path(sys.argv[1]).resolve()
thread_id = sys.argv[2]
route = sys.argv[3]
arguments = json.loads(sys.argv[4])
host = sys.argv[5]
sys.path[:0] = [
    str(consumer / f'.{host}' / 'scripts'),
    str(consumer / f'.{host}' / 'mcp' / 'project'),
]
from handlers import handle_tool
from project_backend import SQLiteBackend
from project_service import ProjectService
from service_execution_lease import (
    authorize_mcp_mutation,
    normalize_project_identity,
)
backend = SQLiteBackend(str(consumer / '.tausik' / 'tausik.db'))
try:
    service = ProjectService(backend)
    lease = backend._execution_lease_current(
        normalize_project_identity(str(consumer)), host, thread_id
    )
    if lease is None:
        raise RuntimeError('deployed MCP call requires a live Codex lease')
    authorization = authorize_mcp_mutation(
        service,
        lease=lease,
        route=route,
        arguments=arguments,
        correlated=True,
    )
    os.environ['TAUSIK_ENFORCE_EXECUTION_LEASE'] = '1'
    print(handle_tool(service, route, arguments, authorization=authorization))
finally:
    backend.close()
"""


def _deploy(snapshot: Path, consumer: Path, host: str) -> None:
    _step(
        [sys.executable, "-c", _DEPLOY, str(snapshot), str(consumer), host],
        consumer,
        f"{host} projection",
    )


def _upgrade_current(consumer: Path, host: str) -> None:
    _step(
        [
            sys.executable,
            str(ROOT / "bootstrap" / "bootstrap.py"),
            "--lib-dir",
            str(ROOT),
            "--project-dir",
            str(consumer),
            "--ide",
            host,
            "--no-detect",
        ],
        consumer,
        "current production bootstrap",
    )


def _initialize(snapshot: Path, consumer: Path, host: str) -> None:
    consumer.mkdir()
    (consumer / "src").mkdir()
    (consumer / "tests").mkdir()
    (consumer / "src" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    (consumer / "tests" / "test_calc.py").write_text(
        "from src.calc import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n",
        encoding="utf-8",
    )
    _step(["git", "init", "-q", "."], consumer, "git init")
    _step(["git", "add", "-A"], consumer, "git add")
    _step(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        consumer,
        "git commit",
    )
    _step(
        [
            sys.executable,
            str(snapshot / "scripts" / "project.py"),
            "init",
            "--name",
            "upgrade-matrix",
        ],
        consumer,
        "published init",
    )
    if host == "cursor":
        hooks = consumer / ".cursor" / "hooks.json"
        hooks.parent.mkdir(parents=True, exist_ok=True)
        hooks.write_text(
            json.dumps(
                {
                    "version": 1,
                    "hooks": {"preToolUse": [{"command": "user-owned-hook", "matcher": "Shell"}]},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    _deploy(snapshot, consumer, host)


def _cli(consumer: Path, host: str) -> list[str]:
    return [sys.executable, str(consumer / f".{host}" / "scripts" / "project.py")]


def _installed_hook_argv(consumer: Path, host: str, event: str, script: str) -> list[str]:
    """Resolve one hook from the installed registration the host actually reads."""
    hooks_path = consumer / f".{host}" / "hooks.json"
    document = json.loads(hooks_path.read_text(encoding="utf-8"))
    groups = document.get("hooks", {}).get(event, [])
    if host == "codex":
        commands = [
            hook.get("command")
            for matcher in groups
            for hook in matcher.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
    else:
        commands = [entry.get("command") for entry in groups if isinstance(entry, dict)]
        commands = [command for command in commands if isinstance(command, str)]
    hooks_dir = consumer / f".{host}" / "scripts" / "hooks"
    sys.path.insert(0, str(hooks_dir))
    try:
        if host == "codex":
            from codex_capability import split_hook_command
        else:
            from cursor_command import split_cursor_command as split_hook_command
    finally:
        sys.path.pop(0)
    matches = []
    for command in commands:
        argv = split_hook_command(command)
        argv = [part.replace("${workspaceFolder}", str(consumer)) for part in argv]
        if argv[:1] == ["&"]:
            argv = argv[1:]
        if any(Path(part).name == script for part in argv):
            matches.append(argv)
    assert len(matches) == 1, (
        f"installed {hooks_path} must register exactly one {event}/{script}; found {len(matches)}"
    )
    return matches[0]


def _hook(consumer: Path, host: str, name: str, payload: dict[str, object]):
    events = {
        "codex": {
            "session_start.py": "SessionStart",
            "user_prompt_submit.py": "UserPromptSubmit",
            "can_stop_gate.py": "Stop",
            "memory_preflight_posttool.py": "PostToolUse",
        },
        "cursor": {
            "session_start.py": "sessionStart",
            "user_prompt_submit.py": "beforeSubmitPrompt",
            "keyword_detector.py": "stop",
            "memory_preflight_posttool.py": "postToolUseFailure",
            "codex_write_gate.py": "preToolUse",
        },
    }
    event = events[host][name]
    return _step(
        _installed_hook_argv(consumer, host, event, name),
        consumer,
        f"{host} {name}",
        input_text=json.dumps(payload),
    )


def _issue_preflight(consumer: Path, thread_id: str, tool: str, tool_input: dict[str, object]):
    _step(
        [
            sys.executable,
            "-c",
            _ISSUE_PREFLIGHT,
            str(consumer),
            thread_id,
            tool,
            json.dumps(tool_input),
        ],
        consumer,
        "deployed memory preflight",
    )


def _mcp_call(consumer: Path, host: str, thread_id: str, route: str, arguments: dict[str, object]):
    return _step(
        [
            sys.executable,
            "-c",
            _MCP_CALL,
            str(consumer),
            thread_id,
            route,
            json.dumps(arguments),
            host,
        ],
        consumer,
        f"deployed MCP {route}",
    )


def _host_pretool(consumer: Path, host: str, payload: dict[str, object]):
    return _step(
        _installed_hook_argv(
            consumer,
            host,
            "PreToolUse" if host == "codex" else "preToolUse",
            "codex_write_gate.py",
        ),
        consumer,
        f"{host} codex_write_gate.py",
        input_text=json.dumps(payload),
    )


def _seed_historical_state(consumer: Path, host: str) -> dict[str, object]:
    """Create ordinary user state through the published CLI before migration."""
    config_path = consumer / ".tausik" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("updates", {})["check"] = False
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    cli = _cli(consumer, host)
    for title, goal in (
        ("historical dependency", "Preserve a dependency predecessor"),
        ("historical planned work", "Preserve unfinished user work"),
    ):
        _step(
            cli
            + [
                "task",
                "quick",
                title,
                "--goal",
                goal,
                "--ac",
                "AC-1: historical state survives framework upgrade. Negative: invalid state is refused.",
            ],
            consumer,
            f"published task quick: {title}",
        )
    _step(
        cli + ["task", "plan", "historical-planned-work", "Preserve this plan step"],
        consumer,
        "published task plan",
    )
    _step(
        cli + ["task", "plan", "historical-planned-work", "Preserve the next plan step"],
        consumer,
        "published next task plan",
    )
    _step(
        cli
        + [
            "task",
            "update",
            "historical-planned-work",
            "--complexity",
            "complex",
            "--scope-paths",
            "src/historical.py",
            "--rollback-plan",
            "Restore the matched pre-upgrade backup",
            "--call-budget",
            "20",
            "--assurance-profiles",
            '["executable"]',
            "--assurance-impact",
            json.dumps(
                {
                    "level": "medium",
                    "blast_radius": "local",
                    "reversibility": "reversible",
                    "data_change": "none",
                    "security_boundary": False,
                    "governance_boundary": False,
                    "privileged": False,
                    "owner_escalation": False,
                }
            ),
        ],
        consumer,
        "published strict task contract",
    )
    _step(
        cli
        + [
            "task",
            "depends",
            "historical-planned-work",
            "--after",
            "historical-dependency",
        ],
        consumer,
        "published task dependency",
    )
    _step(
        cli + ["task", "log", "historical-planned-work", "historical-log-sentinel"],
        consumer,
        "published task log",
    )
    _step(
        cli + ["session", "start", "--host-id", "historical-host-session"],
        consumer,
        "published session start",
    )
    db = consumer / ".tausik" / "tausik.db"
    with sqlite3.connect(db) as conn:
        supported = {
            table: conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            is not None
            for table in ("execution_leases", "can_stop_turns", "task_continuity_state")
        }
    if supported["execution_leases"]:
        _step(cli + ["task", "start", "historical-planned-work"], consumer, "published task start")
        session = (
            {"hook_event_name": "SessionStart", "session_id": "historical-upgrade-thread"}
            if host == "codex"
            else {
                "conversation_id": "historical-upgrade-thread",
                "generation_id": "historical-session",
            }
        )
        _hook(consumer, host, "session_start.py", session)
        if supported["task_continuity_state"]:
            _step(
                cli
                + [
                    "task",
                    "step",
                    "historical-planned-work",
                    "1",
                    "--evidence",
                    "artifact:sha256:" + "a" * 64,
                ],
                consumer,
                "published continuity step",
            )
        turn = (
            {
                "session_id": "historical-upgrade-thread",
                "turn_id": "historical-upgrade-turn",
                "prompt": "finish historical planned work",
            }
            if host == "codex"
            else {
                "conversation_id": "historical-upgrade-thread",
                "generation_id": "historical-upgrade-turn",
                "prompt": "finish historical planned work",
            }
        )
        _hook(consumer, host, "user_prompt_submit.py", turn)
        if host == "codex" and supported["can_stop_turns"]:
            blocked = _hook(consumer, host, "can_stop_gate.py", turn)
            assert json.loads(blocked.stdout)["decision"] == "block"
        elif host == "cursor":
            _hook(consumer, host, "keyword_detector.py", turn)
    state = _historical_state(db)
    state["supported_before_upgrade"] = supported
    if supported["execution_leases"]:
        assert state["durable"]["execution_leases"]["rows"]
    if host == "codex" and supported["can_stop_turns"]:
        assert state["durable"]["can_stop_turns"]["rows"]
    if host == "codex" and supported["task_continuity_state"]:
        assert state["durable"]["task_continuity_state"]["rows"]
    return state


def _historical_state(db: Path) -> dict[str, object]:
    """Stable user-owned fields that migrations must preserve exactly."""
    with sqlite3.connect(db) as conn:
        state: dict[str, object] = {
            "tasks": conn.execute(
                "SELECT slug,title,status,goal,acceptance_criteria,plan,notes "
                "FROM tasks WHERE slug LIKE 'historical-%' ORDER BY slug"
            ).fetchall(),
            "dependencies": conn.execute(
                "SELECT task_slug,depends_on_slug FROM task_deps "
                "WHERE task_slug LIKE 'historical-%' ORDER BY task_slug,depends_on_slug"
            ).fetchall(),
            "logs": conn.execute(
                "SELECT task_slug,message FROM task_logs "
                "WHERE message='historical-log-sentinel' ORDER BY id"
            ).fetchall(),
            "sessions": conn.execute(
                "SELECT host_session_id,ended_at,summary FROM sessions "
                "WHERE host_session_id='historical-host-session' ORDER BY id"
            ).fetchall(),
        }
        durable: dict[str, object] = {}
        filters = {
            "execution_leases": ("thread_id=?", ("historical-upgrade-thread",)),
            "can_stop_turns": ("thread_id=?", ("historical-upgrade-thread",)),
            "task_continuity_state": ("task_slug=?", ("historical-planned-work",)),
        }
        for table, (where, parameters) in filters.items():
            if (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                is None
            ):
                continue
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            rows = conn.execute(
                f"SELECT {','.join(columns)} FROM {table} WHERE {where} ORDER BY rowid",
                parameters,
            ).fetchall()
            durable[table] = {"columns": columns, "rows": rows}
        state["durable"] = durable
        if "execution_leases" in durable:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(sessions)")]
            rows = conn.execute(
                f"SELECT {','.join('s.' + column for column in columns)} FROM sessions s "
                "JOIN execution_leases e ON e.session_id=s.id "
                "WHERE e.thread_id='historical-upgrade-thread' ORDER BY s.id"
            ).fetchall()
            state["lease_sessions"] = {"columns": columns, "rows": rows}
        return state


def _assert_historical_state(db: Path, expected: dict[str, object]) -> None:
    """Compare pre-upgrade rows through their original column projection."""
    current = _historical_state(db)
    for key in ("tasks", "dependencies", "logs", "sessions"):
        assert current[key] == expected[key]
    with sqlite3.connect(db) as conn:
        for table in ("execution_leases", "can_stop_turns", "task_continuity_state"):
            assert (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                is not None
            )
        for table, projection in expected["durable"].items():
            columns = projection["columns"]
            where = (
                "thread_id='historical-upgrade-thread'"
                if table != "task_continuity_state"
                else "task_slug='historical-planned-work'"
            )
            rows = conn.execute(
                f"SELECT {','.join(columns)} FROM {table} WHERE {where} ORDER BY rowid"
            ).fetchall()
            assert rows == projection["rows"]
        if "lease_sessions" in expected:
            projection = expected["lease_sessions"]
            columns = projection["columns"]
            rows = conn.execute(
                f"SELECT {','.join('s.' + column for column in columns)} FROM sessions s "
                "JOIN execution_leases e ON e.session_id=s.id "
                "WHERE e.thread_id='historical-upgrade-thread' ORDER BY s.id"
            ).fetchall()
            assert rows == projection["rows"]


def _schema_signature(db: Path) -> dict[str, object]:
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        table_metadata = {}
        for table in sorted(tables):
            indexes = []
            for index in conn.execute(f'PRAGMA index_list("{table}")'):
                indexes.append(
                    (
                        index[1],
                        index[2],
                        index[3],
                        index[4],
                        tuple(conn.execute(f'PRAGMA index_xinfo("{index[1]}")')),
                    )
                )
            table_metadata[table] = {
                "columns": tuple(conn.execute(f'PRAGMA table_xinfo("{table}")')),
                "foreign_keys": tuple(sorted(conn.execute(f'PRAGMA foreign_key_list("{table}")'))),
                "indexes": tuple(sorted(indexes)),
                "sql": _normalized_schema_sql(
                    conn.execute(
                        "SELECT sql FROM sqlite_schema WHERE type='table' AND name=?",
                        (table,),
                    ).fetchone()[0]
                ),
            }
        table_list = tuple(
            sorted(
                tuple(row)
                for row in conn.execute("PRAGMA table_list")
                if not str(row[1]).startswith("sqlite_")
            )
        )
        programmable = tuple(
            sorted(
                (kind, name, table, " ".join((sql or "").split()))
                for kind, name, table, sql in conn.execute(
                    "SELECT type,name,tbl_name,sql FROM sqlite_master "
                    "WHERE type IN ('view','trigger') AND name NOT LIKE 'sqlite_%'"
                )
            )
        )
        return {
            "tables": table_metadata,
            "table_list": table_list,
            "programmable": programmable,
        }


def _normalized_schema_sql(sql: str) -> str:
    """Remove formatting only; retain order, CHECKs, STRICT and rowid semantics."""
    import re

    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"\bIF\s+NOT\s+EXISTS\b", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+", " ", sql)
    sql = re.sub(r"\s*([(),])\s*", r"\1", sql)
    return sql.strip().casefold()


def _fresh_signature(tmp_path: Path) -> dict[str, object]:
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from project_backend import SQLiteBackend

    backend = SQLiteBackend(str(tmp_path / "fresh" / ".tausik" / "tausik.db"))
    backend.close()
    return _schema_signature(tmp_path / "fresh" / ".tausik" / "tausik.db")


@pytest.mark.parametrize("entry", _entries(), ids=lambda row: row["tag"])
def test_published_objects_are_exact_commit_and_tree_pins(published_repo, entry):
    _verify_pin(published_repo, entry)


def test_tampered_tree_pin_refuses_before_materialization(published_repo, tmp_path):
    entry = dict(_entries()[0])
    entry["tree"] = "0" * 40
    target = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="pinned tree"):
        _extract(published_repo, entry, target)

    assert not target.exists()


def test_anonymous_publication_remote_matches_immutable_observation():
    _verify_anonymous_publication_remote()


@pytest.mark.parametrize("failure", ["missing", "mismatch", "duplicate"])
def test_publication_attestation_fails_closed(failure):
    publication = _publication_manifest()
    entries = _entries()
    lines = []
    for entry in entries:
        lines.append(f"{entry['commit']}\trefs/tags/{entry['tag']}")
    if failure == "missing":
        lines.pop()
    elif failure == "mismatch":
        lines[-1] = f"{'0' * 40}\trefs/tags/{entries[-1]['tag']}"
    else:
        lines.append(lines[-1])

    with pytest.raises(ValueError, match="publication remote"):
        _verify_publication_lines(publication, entries, "\n".join(lines))


@pytest.mark.parametrize(("host", "event"), [("codex", "SessionStart"), ("cursor", "sessionStart")])
def test_journey_refuses_when_installed_session_start_registration_is_missing(
    tmp_path, host, event
):
    consumer = tmp_path / "consumer"
    _initialize(ROOT, consumer, host)
    hooks_path = consumer / f".{host}" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    hooks["hooks"][event] = []
    hooks_path.write_text(json.dumps(hooks), encoding="utf-8")

    with pytest.raises(AssertionError, match="register exactly one"):
        _installed_hook_argv(consumer, host, event, "session_start.py")


def test_real_bootstrap_subprocess_skips_markerless_foreign_agents(tmp_path):
    consumer = tmp_path / "consumer"
    _initialize(ROOT, consumer, "codex")
    markerless = consumer / "AGENTS.md"
    markerless.write_text("# user-owned markerless instructions\n", encoding="utf-8")

    result = _run(
        [
            sys.executable,
            str(ROOT / "bootstrap" / "bootstrap.py"),
            "--lib-dir",
            str(ROOT),
            "--project-dir",
            str(consumer),
            "--ide",
            "codex",
            "--no-detect",
        ],
        consumer,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "REFUSED: post-bootstrap dynamic-state refresh failed" not in result.stderr
    markerless_text = markerless.read_text(encoding="utf-8")
    assert markerless_text.startswith("# user-owned markerless instructions\n")
    assert "<!-- DYNAMIC:START -->" not in markerless_text


@pytest.mark.skipif(os.name != "nt", reason="native Cursor PowerShell contract is Windows-only")
def test_windows_native_cursor_upgrade_executes_registered_session_start_after_reload(
    published_repo, tmp_path
):
    entry = next(row for row in _entries() if row["tag"] == "v1.11.7")
    snapshot = tmp_path / "published"
    consumer = tmp_path / "cursor consumer with spaces"
    _extract(published_repo, entry, snapshot)
    _initialize(snapshot, consumer, "cursor")
    historical = _seed_historical_state(consumer, "cursor")
    hooks_path = consumer / ".cursor" / "hooks.json"
    hooks_path.write_bytes(hooks_path.read_text(encoding="utf-8").replace("\n", "\r\n").encode())
    user_rule = consumer / ".cursor" / "rules" / "team.mdc"
    user_rule.parent.mkdir(parents=True, exist_ok=True)
    expected_rule = b"---\r\nalwaysApply: true\r\n---\r\nuser-owned\r\n"
    user_rule.write_bytes(expected_rule)
    assert b"\r\n" in hooks_path.read_bytes()
    _upgrade_current(consumer, "cursor")

    assert user_rule.read_bytes() == expected_rule
    assert not (consumer / ".cursorrules").exists()
    db = consumer / ".tausik" / "tausik.db"
    _assert_historical_state(db, historical)
    _step(
        _cli(consumer, "cursor")
        + [
            "task",
            "obsolete",
            "historical-planned-work",
            "--reason",
            "Historical upgrade fixture verified after migration",
        ],
        consumer,
        "retire historical canary task",
    )
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    command = next(
        row["command"]
        for row in hooks["hooks"]["sessionStart"]
        if "session_start.py" in row.get("command", "")
    )
    result = _run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        consumer,
        input_text=json.dumps(
            {"conversation_id": "windows-reload-thread", "generation_id": "reload-turn"}
        ),
    )

    assert result.returncode == 0, result.stderr
    db = consumer / ".tausik" / "tausik.db"
    with sqlite3.connect(db) as conn:
        lease = conn.execute(
            "SELECT host_instance,thread_id,task_slug FROM execution_leases "
            "WHERE thread_id='windows-reload-thread' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert lease == ("cursor", "windows-reload-thread", None)


@pytest.mark.parametrize("entry", _journey_cases(), ids=lambda row: f"{row['host']}-{row['tag']}")
def test_host_consumer_completes_clean_or_upgraded_journey(published_repo, tmp_path, entry):
    snapshot = tmp_path / "published"
    consumer = tmp_path / "consumer"
    host = entry["host"]
    historical_state = None
    if entry["source"] == "current":
        _initialize(ROOT, consumer, host)
    else:
        _extract(published_repo, entry, snapshot)
        _initialize(snapshot, consumer, host)
        historical_state = _seed_historical_state(consumer, host)
        _upgrade_current(consumer, host)
    cli = _cli(consumer, host)
    db = consumer / ".tausik" / "tausik.db"
    if historical_state is not None:
        _assert_historical_state(db, historical_state)
        _step(
            cli
            + [
                "task",
                "obsolete",
                "historical-planned-work",
                "--reason",
                "Historical upgrade fixture verified after migration",
            ],
            consumer,
            "retire historical canary task",
        )

    _hook(
        consumer,
        host,
        "session_start.py",
        (
            {"hook_event_name": "SessionStart", "session_id": "matrix-thread-a"}
            if host == "codex"
            else {"conversation_id": "matrix-thread-a", "generation_id": "matrix-session"}
        ),
    )
    with sqlite3.connect(db) as conn:
        unbound = conn.execute(
            "SELECT id,nonce,task_slug FROM execution_leases "
            "WHERE thread_id='matrix-thread-a' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert unbound is not None and unbound[2] is None

    _mcp_call(
        consumer,
        host,
        "matrix-thread-a",
        "tausik_task_add",
        {
            "slug": "upgrade-journey",
            "title": "upgrade journey",
            "goal": f"Prove the upgraded {host} lifecycle remains operational",
            "acceptance_criteria": (
                "AC-1 lifecycle completes. AC-2 Negative: work Stop blocks before done."
                if host == "codex"
                else (
                    "AC-1 lifecycle completes. AC-2 Negative: Cursor keyword_detector "
                    "path runs; can_stop_gate is not deployed on this host."
                )
            ),
            "role": "developer",
            "stack": "python",
            "complexity": "simple",
            "scope_paths": ["src/calc.py", "tests/test_calc.py"],
            "relevant_files": ["src/calc.py", "tests/test_calc.py"],
        },
    )
    with sqlite3.connect(db) as conn:
        stored_files = conn.execute(
            "SELECT relevant_files FROM tasks WHERE slug='upgrade-journey'"
        ).fetchone()[0]
    assert json.loads(stored_files) == ["src/calc.py", "tests/test_calc.py"]
    _mcp_call(
        consumer,
        host,
        "matrix-thread-a",
        "tausik_task_start",
        {"slug": "upgrade-journey"},
    )
    with sqlite3.connect(db) as conn:
        bound = conn.execute(
            "SELECT id,nonce,task_slug FROM execution_leases "
            "WHERE thread_id='matrix-thread-a' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert bound == (unbound[0], unbound[1], "upgrade-journey")
    if host == "codex":
        read_turn = {
            "session_id": "matrix-thread-a",
            "turn_id": "matrix-read",
            "prompt": "Which tasks are open?",
        }
        _hook(consumer, host, "user_prompt_submit.py", read_turn)
        assert _hook(consumer, host, "can_stop_gate.py", read_turn).stdout == ""
        assert _hook(consumer, host, "can_stop_gate.py", read_turn).stdout == ""

        work_turn = {
            "session_id": "matrix-thread-a",
            "turn_id": "matrix-work",
            "prompt": "finish the upgrade journey",
        }
        _hook(consumer, host, "user_prompt_submit.py", work_turn)
        blocked = _hook(consumer, host, "can_stop_gate.py", work_turn)
        assert json.loads(blocked.stdout)["decision"] == "block"
        blocked_again = _hook(consumer, host, "can_stop_gate.py", work_turn)
        assert json.loads(blocked_again.stdout)["decision"] == "block"
    else:
        cursor_turn = {
            "conversation_id": "matrix-thread-a",
            "generation_id": "matrix-work",
            "prompt": "finish the upgrade journey",
        }
        _hook(consumer, host, "user_prompt_submit.py", cursor_turn)
        _hook(consumer, host, "keyword_detector.py", cursor_turn)

    _step(
        cli
        + [
            "verify",
            "--task",
            "upgrade-journey",
            "--relevant-files",
            "src/calc.py",
            "tests/test_calc.py",
        ],
        consumer,
        "verify",
    )
    ac_lines = ["AC-1: ✓ tests/test_calc.py::test_add"]
    if host == "codex":
        ac_lines.append("AC-2: ✓ production work Stop returned block")
    else:
        # Cursor does not install can_stop_gate; do not claim a Stop block.
        ac_lines.append(
            "AC-2: ✓ Cursor keyword_detector path exercised; can_stop_gate not deployed"
        )
    for line in ac_lines:
        _step(cli + ["task", "log", "upgrade-journey", line], consumer, "AC evidence")
    _step(
        cli + ["task", "done", "upgrade-journey", "--ac-verified", "--no-changelog"],
        consumer,
        "task done",
    )
    _step(
        cli
        + [
            "task",
            "quick",
            "next lifecycle",
            "--goal",
            "Prove a second lifecycle starts after terminal unbind",
            "--ac",
            "AC-1 next task starts. Negative: stale binding is not reused.",
        ],
        consumer,
        "next task quick",
    )
    _step(cli + ["task", "start", "next-lifecycle"], consumer, "next task start")

    assert _schema_signature(db) == _fresh_signature(tmp_path)
    if host == "codex":
        _assert_boundary_postconditions(entry["boundary"], consumer, cli, db)
    else:
        _assert_cursor_postconditions(consumer, db)


def _assert_cursor_postconditions(consumer: Path, db: Path) -> None:
    hooks = json.loads((consumer / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert any(
        entry.get("command") == "user-owned-hook" for entry in hooks["hooks"].get("preToolUse", [])
    )
    with sqlite3.connect(db) as conn:
        task = conn.execute("SELECT status FROM tasks WHERE slug='next-lifecycle'").fetchone()
        assert task == ("active",)
        lease = conn.execute(
            "SELECT host_instance,task_slug FROM execution_leases "
            "WHERE thread_id='matrix-thread-a' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert lease == ("cursor", None)


def _assert_boundary_postconditions(
    boundary: str, consumer: Path, cli: list[str], db: Path
) -> None:
    """Prove the named risk boundary on the migrated consumer, not a mock DB."""
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        if boundary == "clean-current":
            task = conn.execute("SELECT status FROM tasks WHERE slug='next-lifecycle'").fetchone()
            assert task is not None and task["status"] == "active"
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM can_stop_turns WHERE turn_id IN ('matrix-read','matrix-work')"
                ).fetchone()[0]
                == 2
            )
        elif boundary == "pre-lease-stop-regression":
            assert _historical_state(db)["tasks"]
            lease = conn.execute(
                "SELECT task_slug FROM execution_leases "
                "WHERE thread_id='matrix-thread-a' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert lease is not None and lease[0] is None
        elif boundary == "lease-and-stop-baseline":
            kinds = tuple(
                row[0]
                for row in conn.execute("SELECT request_kind FROM can_stop_turns ORDER BY id")
            )
            assert kinds[-2:] == ("read_only", "work")
        elif boundary == "lease-completion":
            lease = conn.execute(
                "SELECT task_slug,revoked_at FROM execution_leases "
                "WHERE thread_id='matrix-thread-a' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert lease is not None and lease["task_slug"] is None
            assert (
                conn.execute("SELECT mode FROM execution_lease_state WHERE singleton=1").fetchone()[
                    0
                ]
                == "ready"
            )
        elif boundary == "obsolete-unbind":
            _hook(
                consumer,
                "codex",
                "session_start.py",
                {"hook_event_name": "SessionStart", "session_id": "matrix-obsolete-thread"},
            )
            _step(
                cli
                + [
                    "task",
                    "obsolete",
                    "next-lifecycle",
                    "--reason",
                    "upgrade boundary fixture supersedes this task",
                ],
                consumer,
                "obsolete terminal unbind",
            )
            lease = conn.execute(
                "SELECT task_slug,revoked_at FROM execution_leases "
                "WHERE thread_id='matrix-obsolete-thread' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert lease is not None and lease["task_slug"] is None
        elif boundary == "terminal-unbind-next-lifecycle":
            _hook(
                consumer,
                "codex",
                "session_start.py",
                {"hook_event_name": "SessionStart", "session_id": "matrix-next-thread"},
            )
            status = conn.execute("SELECT status FROM tasks WHERE slug='next-lifecycle'").fetchone()
            assert status is not None and status["status"] == "active"
            assert (
                conn.execute(
                    "SELECT task_slug FROM execution_leases "
                    "WHERE thread_id='matrix-next-thread' ORDER BY id DESC LIMIT 1"
                ).fetchone()[0]
                == "next-lifecycle"
            )
        elif boundary == "post-tool-failure":
            thread = "matrix-posttool-thread"
            _hook(
                consumer,
                "codex",
                "session_start.py",
                {"hook_event_name": "SessionStart", "session_id": thread},
            )
            before = tuple(
                conn.execute("SELECT slug,status FROM tasks WHERE slug='next-lifecycle'").fetchone()
            )
            tool = "Bash"
            tool_input = {"command": "git push unavailable-origin HEAD"}
            action = {
                "session_id": thread,
                "tool_name": tool,
                "tool_input": tool_input,
            }
            _issue_preflight(consumer, thread, tool, tool_input)
            _host_pretool(consumer, "codex", action)
            completed = _hook(
                consumer,
                "codex",
                "memory_preflight_posttool.py",
                {
                    **action,
                    "tool_response": {"is_error": True, "error_code": "FILE_NOT_FOUND"},
                },
            )
            assert json.loads(completed.stdout)["continue"] is True
            after = tuple(
                conn.execute("SELECT slug,status FROM tasks WHERE slug='next-lifecycle'").fetchone()
            )
            assert after == before
            assert (
                conn.execute(
                    "SELECT task_slug FROM execution_leases "
                    "WHERE thread_id=? ORDER BY id DESC LIMIT 1",
                    (thread,),
                ).fetchone()[0]
                == "next-lifecycle"
            )
            token = conn.execute(
                "SELECT status,failure_code FROM memory_preflight_tokens ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert token is not None and tuple(token) == ("failed", "TOOL_FAILED")
            attempt = conn.execute(
                "SELECT task_slug,event_kind,status,detail_json FROM task_attempt_events "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert attempt is not None
            assert tuple(attempt[:3]) == ("next-lifecycle", "capability", "unavailable")
            assert json.loads(attempt["detail_json"])["observed_code"] == "FILE_NOT_FOUND"
        elif boundary == "repeated-stop":
            decisions = tuple(
                row[0]
                for row in conn.execute(
                    "SELECT decision FROM can_stop_turns WHERE turn_id='matrix-work'"
                )
            )
            assert decisions == ("CONTINUE",)
        elif boundary == "handoff":
            thread = "matrix-handoff-thread"
            _hook(
                consumer,
                "codex",
                "session_start.py",
                {"hook_event_name": "SessionStart", "session_id": thread},
            )
            turn = {
                "session_id": thread,
                "turn_id": "matrix-handoff-work",
                "prompt": "continue the active work",
            }
            _hook(consumer, "codex", "user_prompt_submit.py", turn)
            lease = conn.execute(
                "SELECT id,session_id FROM execution_leases "
                "WHERE thread_id=? ORDER BY id DESC LIMIT 1",
                (thread,),
            ).fetchone()
            resume = ".tausik/tausik task start next-lifecycle --package"
            conn.execute(
                "UPDATE execution_leases SET revoked_at=datetime('now') WHERE id=?", (lease["id"],)
            )
            conn.execute(
                "UPDATE sessions SET handoff=? WHERE id=?",
                (f"Resume: {resume}", lease["session_id"]),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                (f"host_context_hard_lease:{lease['id']}", resume),
            )
            conn.commit()
            assert _hook(consumer, "codex", "can_stop_gate.py", turn).stdout == ""
            assert (
                conn.execute(
                    "SELECT decision FROM can_stop_turns WHERE turn_id='matrix-handoff-work'"
                ).fetchone()[0]
                == "ALLOW_HANDOFF"
            )
        elif boundary == "call-budget-recovery-retirement":
            thread = "matrix-budget-thread"
            package = conn.execute(
                "SELECT fingerprint FROM task_context_packages WHERE task_slug='next-lifecycle'"
            ).fetchone()
            previous_lease = conn.execute(
                "SELECT id FROM execution_leases ORDER BY id DESC LIMIT 1"
            ).fetchone()
            now = "2026-01-01T00:00:00Z"
            conn.execute(
                "INSERT INTO task_continuity_state(task_slug,package_fingerprint,"
                "pending_requirement,recovery_lease_id,recovery_issued_at,updated_at) "
                "VALUES(?,?,?,?,?,?) ON CONFLICT(task_slug) DO UPDATE SET "
                "pending_requirement=excluded.pending_requirement,"
                "recovery_lease_id=excluded.recovery_lease_id,"
                "recovery_issued_at=excluded.recovery_issued_at,updated_at=excluded.updated_at",
                (
                    "next-lifecycle",
                    package["fingerprint"],
                    "call_budget_exhausted",
                    previous_lease["id"],
                    now,
                    now,
                ),
            )
            conn.commit()
            _hook(
                consumer,
                "codex",
                "session_start.py",
                {"hook_event_name": "SessionStart", "session_id": thread},
            )
            probe = (
                "import pathlib,sys; "
                "root=pathlib.Path(sys.argv[1]); "
                "sys.path[:0]=[str(root/'.codex/scripts/hooks'),str(root/'.codex/scripts')]; "
                "from execution_lease_gate import require_live_lease; "
                "ok,reason=require_live_lease({'session_id':sys.argv[2]},str(root),"
                "route='tausik_task_log',arguments={'slug':'next-lifecycle'},"
                "authorize=False,trusted_host='codex'); "
                "assert ok,reason"
            )
            _step([sys.executable, "-c", probe, str(consumer), thread], consumer, "retire recovery")
            retired = conn.execute(
                "SELECT pending_requirement,recovery_lease_id,recovery_issued_at,recovery_action "
                "FROM task_continuity_state WHERE task_slug='next-lifecycle'"
            ).fetchone()
            assert retired is not None and tuple(retired) == (None, None, None, None)
            turn = {
                "session_id": thread,
                "turn_id": "matrix-budget-work",
                "prompt": "continue the active work",
            }
            _hook(consumer, "codex", "user_prompt_submit.py", turn)
            assert (
                json.loads(_hook(consumer, "codex", "can_stop_gate.py", turn).stdout)["decision"]
                == "block"
            )
            decision = conn.execute(
                "SELECT decision FROM can_stop_turns WHERE turn_id='matrix-budget-work'"
            ).fetchone()[0]
            assert decision == "CONTINUE"
        else:
            raise AssertionError(f"unhandled upgrade boundary {boundary}")


def test_1118_corrupt_maintenance_upgrade_refuses_without_losing_records(published_repo, tmp_path):
    entry = next(row for row in _entries() if row["tag"] == "v1.11.8")
    snapshot = tmp_path / "published"
    consumer = tmp_path / "consumer"
    _extract(published_repo, entry, snapshot)
    _initialize(snapshot, consumer, "codex")
    old_cli = _cli(consumer, "codex")
    _step(
        old_cli
        + [
            "task",
            "quick",
            "preserved work",
            "--goal",
            "Preserve work through explicit maintenance refusal",
            "--ac",
            "AC-1 data survives. Negative: ambiguous maintenance refuses.",
        ],
        consumer,
        "old task seed",
    )
    _hook(
        consumer,
        "codex",
        "session_start.py",
        {"hook_event_name": "SessionStart", "session_id": "maintenance-thread"},
    )
    db = consumer / ".tausik" / "tausik.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE execution_lease_state SET mode='ready',reason=NULL,projection_build='1.11.8' "
            "WHERE singleton=1"
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES('execution_lease_maintenance',?)",
            ("PostToolUse audit failure: ValueError",),
        )
        conn.commit()
        before = _preserved_records(conn)

    _upgrade_current(consumer, "codex")
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from project_backend import SQLiteBackend
    from project_service import ProjectService
    from service_execution_lease import (
        ExecutionLeaseError,
        assertion_from_session_start,
        reconcile_execution_lease_state,
    )

    backend = SQLiteBackend(str(db))
    service = ProjectService(backend)
    assertion = assertion_from_session_start(
        {"hook_event_name": "SessionStart", "session_id": "maintenance-thread"},
        str(consumer),
        trusted_host="codex",
    )
    try:
        with pytest.raises(ExecutionLeaseError, match="LEASE_MAINTENANCE"):
            reconcile_execution_lease_state(service, assertion)
        assert _preserved_records(backend._conn, baseline=before) == before
        assert backend._execution_lease_state()["mode"] == "ready"
        assert (
            backend._q1("SELECT value FROM meta WHERE key='execution_lease_maintenance'")
            is not None
        )
        assert tuple(backend._conn.execute("PRAGMA integrity_check").fetchone()) == ("ok",)
        assert backend._conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        backend.close()


def _preserved_records(
    conn: sqlite3.Connection, *, baseline: dict[str, dict[str, object]] | None = None
) -> dict[str, dict[str, object]]:
    """Snapshot every pre-upgrade column for maintenance-protected rows."""
    selections = {
        "tasks": ("tasks", "", (), "slug"),
        "sessions": ("sessions", "", (), "id"),
        "execution_leases": ("execution_leases", "", (), "id"),
        "execution_lease_state": ("execution_lease_state", "", (), "singleton"),
        "maintenance_meta": (
            "meta",
            "WHERE key LIKE 'execution_lease_%' OR key LIKE 'host_context_%'",
            (),
            "key",
        ),
    }
    snapshot: dict[str, dict[str, object]] = {}
    for name, (table, where, params, order) in selections.items():
        columns = (
            tuple(baseline[name]["columns"])
            if baseline is not None
            else tuple(row[1] for row in conn.execute(f'PRAGMA table_info("{table}")'))
        )
        projection = ",".join(f'"{column}"' for column in columns)
        rows = tuple(
            tuple(row)
            for row in conn.execute(
                f'SELECT {projection} FROM "{table}" {where} ORDER BY "{order}"', params
            )
        )
        snapshot[name] = {"columns": columns, "rows": rows}
    return snapshot
