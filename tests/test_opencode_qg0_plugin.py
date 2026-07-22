"""Tests for the OpenCode QG-0 plugin (task opencode-qg0-plugin).

Two layers:

* Static — the emitted artifact must have zero imports and must land in
  `plugins/` (plural). Both were real incidents: the `@opencode-ai/plugin`
  import killed a user's host with ERR_MODULE_NOT_FOUND, and a singular
  `plugin/` directory makes the gate vanish *silently*.
* Behavioural — the hook is actually executed under Node with a fake Bun shell,
  so "blocks without a task" is a run, not a claim. Node is a stand-in for Bun:
  the plugin deliberately depends on no runtime API beyond `process`, and treats
  a missing `Bun` global as "no cache signature available".
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

BOOTSTRAP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bootstrap")
sys.path.insert(0, BOOTSTRAP)

from bootstrap_opencode import (  # noqa: E402
    OpenCodePluginMissing,
    generate_opencode_plugin,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = os.path.join(REPO, "harness", "opencode", "plugins", "tausik-qg0.js")

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


@pytest.fixture()
def emitted(tmp_path):
    """Emit the plugin the way bootstrap does, from a lib dir."""
    lib = tmp_path / "lib"
    src_dir = lib / "harness" / "opencode" / "plugins"
    src_dir.mkdir(parents=True)
    shutil.copyfile(CANONICAL, src_dir / "tausik-qg0.js")
    target = tmp_path / "proj" / ".opencode"
    target.mkdir(parents=True)
    return generate_opencode_plugin(str(target), lib_dir=str(lib)), str(target)


class TestEmission:
    def test_lands_in_plugins_plural_not_singular(self, emitted):
        """`.opencode/plugin/` (singular) does not error — it silently never loads."""
        path, target = emitted
        assert path == os.path.join(target, "plugins", "tausik-qg0.js")
        assert os.path.isfile(path)
        assert not os.path.exists(os.path.join(target, "plugin"))

    def test_idempotent_when_source_is_the_destination(self, emitted):
        path, target = emitted
        before = open(path, encoding="utf-8").read()
        again = generate_opencode_plugin(target)  # no lib_dir: resolves the copy itself
        assert again == path
        assert open(path, encoding="utf-8").read() == before

    def test_missing_source_raises_loudly(self, tmp_path):
        """A project with no gate is a project with no QG-0. Never skip in silence."""
        target = tmp_path / ".opencode"
        target.mkdir()
        with pytest.raises(OpenCodePluginMissing):
            generate_opencode_plugin(str(target), lib_dir=str(tmp_path / "nope"))


class TestNoNpmDependencies:
    def test_no_import_or_require_anywhere(self, emitted):
        """The user's hand-rolled qg0.ts imported @opencode-ai/plugin and took the
        whole prompt loop down with ERR_MODULE_NOT_FOUND. Types come from JSDoc."""
        path, _ = emitted
        src = open(path, encoding="utf-8").read()
        code = "\n".join(
            line for line in src.splitlines() if not line.lstrip().startswith(("//", "*", "/*"))
        )
        assert not re.search(r"^\s*import\s", code, re.M), "static import"
        assert not re.search(r"\bimport\s*\(", code), "dynamic import()"
        assert not re.search(r"\brequire\s*\(", code), "require()"
        assert not re.search(r"\bfrom\s+['\"]", code), "bare `from '...'`"
        assert "@opencode-ai/plugin" not in code

    def test_exports_the_opencode_contract(self, emitted):
        path, _ = emitted
        src = open(path, encoding="utf-8").read()
        assert "export const TausikQG0 = async ({" in src
        assert '"tool.execute.before"' in src

    def test_exactly_one_export(self, emitted):
        """OpenCode's loader calls every export as a plugin factory ("a module that exports
        one or more plugin functions"). A test-only helper export would be invoked with the
        plugin context, and its `undefined` return read for hooks — a TypeError at plugin
        init, i.e. the host dies at load because of a symbol that exists only for pytest.
        That is precisely the failure class this plugin was written to prevent."""
        path, _ = emitted
        src = open(path, encoding="utf-8").read()
        exports = re.findall(r"^\s*export\s+(?:const|function|class|let|var)\s+(\w+)", src, re.M)
        assert exports == ["TausikQG0"], f"plugin must export exactly TausikQG0, got {exports}"
        assert "export default" not in src
        assert not re.search(r"^\s*export\s*\{", src, re.M), "re-export block found"


# --- behavioural: run the hook under Node ------------------------------------

DRIVER = r"""
// Exactly one import: the plugin exports exactly one symbol, and must keep doing so —
// OpenCode calls every export as a plugin factory (see TestNoNpmDependencies).
import { TausikQG0 } from "%(plugin)s";

// scenario = { withBun: bool, steps: [{tool, active, cliFails, dbMtime}] }
// Each step invokes the hook once. `state` is what the fake CLI currently reports,
// so a step can flip the world (task done, DB touched) between hook calls.
const scenario = JSON.parse(process.argv[2]);
let calls = 0;
let state = scenario.steps[0];

// Reconstruct the command so the fake can tell a `status` query (counted in
// `calls`, the load-bearing cost the cache tests pin) from a supervision emit
// (recorded in `emits`, cross-harness telemetry). Conflating them would make
// every existing exact-`calls` assertion ambiguous.
const emits = [];
const $ = (strings, ...values) => {
  let cmd = "";
  for (let i = 0; i < strings.length; i++) {
    cmd += strings[i];
    if (i < values.length) cmd += String(values[i]);
  }
  const isEmit = cmd.includes("emit-supervision");
  return {
    quiet: () => ({
      text: async () => {
        if (isEmit) {
          emits.push(cmd.trim());  // the attempt happened, recorded before any failure
          if (state.cliFails) throw new Error("cli unavailable");
          return "";
        }
        calls++;
        if (state.cliFails) throw new Error("cli unavailable");
        return JSON.stringify({ tasks_active: state.active ? 1 : 0 });
      },
    }),
  };
};

if (scenario.withBun) {
  globalThis.Bun = {
    file: () => ({
      exists: async () => true,
      size: 10,
      lastModified: state.dbMtime ?? 1000,
    }),
  };
}

// No cache reset needed: each scenario runs in a fresh node process, so the module —
// and its module-level cache — is imported anew.
const hooks = await TausikQG0({ $, directory: "/proj" });
const before = hooks["tool.execute.before"];

// Capture the degraded-mode warning so a test can prove fail-open is not silent.
const warnings = [];
console.warn = (...args) => warnings.push(args.join(" "));

const results = [];
for (const step of scenario.steps) {
  state = step;
  const callsBefore = calls;
  try {
    await before({ tool: step.tool }, { args: {} });
    results.push({ blocked: false, message: "", queried: calls > callsBefore });
  } catch (e) {
    results.push({ blocked: true, message: e.message, queried: calls > callsBefore });
  }
}
console.log(JSON.stringify({ results, calls, warnings, emits }));
"""


def _run(tmp_path, plugin_path: str, steps: list[dict], with_bun=False, env=None) -> dict:
    """Execute the hook once per step under Node. Returns {results, calls}."""
    driver = tmp_path / "driver.mjs"
    plugin_url = "file:///" + os.path.abspath(plugin_path).replace("\\", "/").lstrip("/")
    driver.write_text(DRIVER % {"plugin": plugin_url}, encoding="utf-8")
    scenario = {"withBun": with_bun, "steps": steps}
    proc = subprocess.run(
        [NODE, str(driver), json.dumps(scenario)],
        capture_output=True,
        text=True,
        # Node emits UTF-8; the block message is Russian. Without this, Windows
        # decodes it as cp1252 and the test dies on the very message it asserts.
        encoding="utf-8",
        timeout=30,
        env={**os.environ, **(env or {})},
        check=False,
    )
    assert proc.returncode == 0, f"driver failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _run_hook(tmp_path, plugin_path: str, step: dict, env: dict | None = None) -> dict:
    """Single-step convenience wrapper."""
    out = _run(tmp_path, plugin_path, [step], with_bun=step.get("withBun", False), env=env)
    return {
        **out["results"][0],
        "calls": out["calls"],
        "warnings": out["warnings"],
        "emits": out["emits"],
    }


@needs_node
class TestGateSemantics:
    def test_write_without_active_task_is_blocked(self, tmp_path, emitted):
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": "write", "active": False})
        assert res["blocked"]
        assert "task start" in res["message"]

    @pytest.mark.parametrize("tool", ["write", "edit", "apply_patch"])
    def test_every_write_tool_is_gated(self, tmp_path, emitted, tool):
        """`apply_patch` — the real OpenCode name. `patch` does not exist."""
        path, _ = emitted
        assert _run_hook(tmp_path, path, {"tool": tool, "active": False})["blocked"]

    def test_write_with_active_task_passes(self, tmp_path, emitted):
        path, _ = emitted
        assert not _run_hook(tmp_path, path, {"tool": "write", "active": True})["blocked"]

    @pytest.mark.parametrize("tool", ["read", "grep", "glob", "bash", "webfetch", "todowrite"])
    def test_read_only_tools_pass_without_a_task(self, tmp_path, emitted, tool):
        """Gating `bash` would block the very command that starts a task."""
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": tool, "active": False})
        assert not res["blocked"]
        assert res["calls"] == 0, "read-only tool must not even pay for the CLI call"


@needs_node
class TestFailurePolicy:
    def test_cli_unavailable_fails_open(self, tmp_path, emitted):
        """A broken CLI must never brick someone's editor (mirrors task_gate.py)."""
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": "write", "cliFails": True})
        assert not res["blocked"]

    def test_fail_open_is_never_silent(self, tmp_path, emitted):
        """Fail-open is a policy, not an excuse to say nothing.

        A gate that quietly stops gating is the failure class this framework refuses to
        tolerate: without a warning, one broken CLI call disables QG-0 for the rest of
        the session and leaves no trace for the user or an auditor.
        """
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": "write", "cliFails": True})
        assert not res["blocked"]
        assert res["warnings"], "fail-open happened in total silence"
        warning = res["warnings"][0]
        assert "DEGRADED" in warning
        assert "TAUSIK_HOOK_FAIL_SECURE" in warning, "the warning must name the way out"

    def test_healthy_path_stays_quiet(self, tmp_path, emitted):
        """No crying wolf: a working gate must not spam the log on every write."""
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": "write", "active": True})
        assert not res["warnings"]

    def test_cli_unavailable_fails_secure_when_flagged(self, tmp_path, emitted):
        path, _ = emitted
        res = _run_hook(
            tmp_path,
            path,
            {"tool": "write", "cliFails": True},
            env={"TAUSIK_HOOK_FAIL_SECURE": "1"},
        )
        assert res["blocked"]
        assert "TAUSIK_HOOK_FAIL_SECURE" in res["message"]

    def test_skip_hooks_disables_the_gate(self, tmp_path, emitted):
        path, _ = emitted
        res = _run_hook(
            tmp_path,
            path,
            {"tool": "write", "active": False},
            env={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert not res["blocked"]
        assert res["calls"] == 0, "skip must not pay for the active-task status query"


@needs_node
class TestSupervisionTelemetryParity:
    """l26-bypass-telemetry-opencode-parity: the SAME weakenings the Python hooks
    record must leave a countable row on THIS harness too, or supervision_bypasses
    lies by omission. The plugin cannot call the Python emitter in-process (Node),
    so it shells the CLI `events emit-supervision` — the row's contract stays in
    one place."""

    def test_skip_hooks_emits_bypass(self, tmp_path, emitted):
        path, _ = emitted
        res = _run_hook(
            tmp_path,
            path,
            {"tool": "write", "active": False},
            env={"TAUSIK_SKIP_HOOKS": "1"},
        )
        assert not res["blocked"]
        assert len(res["emits"]) == 1, res["emits"]
        cmd = res["emits"][0]
        assert "events emit-supervision" in cmd
        assert "--kind bypass" in cmd
        assert "--vector skip_hooks" in cmd
        assert "--source opencode_qg0" in cmd

    @pytest.mark.parametrize("tool", ["read", "grep", "todowrite"])
    def test_read_only_tools_never_emit_under_skip(self, tmp_path, emitted, tool):
        """Scope parity with task_gate's write-only matcher: a skip on a read must
        NOT count as a bypass, or the metric wildly over-reports."""
        path, _ = emitted
        res = _run_hook(
            tmp_path, path, {"tool": tool, "active": False}, env={"TAUSIK_SKIP_HOOKS": "1"}
        )
        assert not res["blocked"]
        assert res["emits"] == [], "a read-only tool must not emit bypass telemetry"

    def test_fail_open_emits_degradation(self, tmp_path, emitted):
        """A silent fail-open is a degradation — recorded under fail_open_%, its own
        metric bucket, distinct from an intentional bypass."""
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": "write", "cliFails": True})
        assert not res["blocked"]
        assert len(res["emits"]) == 1, res["emits"]
        cmd = res["emits"][0]
        assert "--kind degradation" in cmd
        assert "--vector cli_unreachable" in cmd
        assert "--source opencode_qg0" in cmd

    def test_healthy_write_emits_nothing(self, tmp_path, emitted):
        """No weakening, no row: an active-task write must not spam supervision."""
        path, _ = emitted
        res = _run_hook(tmp_path, path, {"tool": "write", "active": True})
        assert not res["blocked"]
        assert res["emits"] == []

    def test_fail_secure_blocks_without_emitting_degradation(self, tmp_path, emitted):
        """FAIL_SECURE flips fail-open to a BLOCK before the degradation path — the
        guard worked, so there is nothing to record as weakened."""
        path, _ = emitted
        res = _run_hook(
            tmp_path,
            path,
            {"tool": "write", "cliFails": True},
            env={"TAUSIK_HOOK_FAIL_SECURE": "1"},
        )
        assert res["blocked"]
        assert res["emits"] == []


@needs_node
class TestCacheErrsTowardStrictness:
    """The CLI costs ~300 ms warm / 1.1 s cold on Windows (measured), paid on every
    write — so the verdict is cached. A cache that errs toward permissiveness would
    silently reopen the hole the gate exists to close, so these tests pin the
    direction, not just the speedup."""

    def test_repeated_writes_hit_the_cache_while_the_db_is_unchanged(self, tmp_path, emitted):
        path, _ = emitted
        steps = [{"tool": "write", "active": True, "dbMtime": 1000}] * 3
        out = _run(tmp_path, path, steps, with_bun=True)
        assert [r["blocked"] for r in out["results"]] == [False, False, False]
        assert out["calls"] == 1, "3 writes must cost 1 CLI call, not 3"
        assert [r["queried"] for r in out["results"]] == [True, False, False]

    def test_task_done_invalidates_a_cached_allow(self, tmp_path, emitted):
        """THE load-bearing test. `task done` writes the WAL, so the DB signature moves
        and the cached 'active' verdict cannot survive it. If this ever regresses, a
        closed task keeps granting write access for the rest of the TTL."""
        path, _ = emitted
        steps = [
            {"tool": "write", "active": True, "dbMtime": 1000},  # task active
            {"tool": "write", "active": False, "dbMtime": 2000},  # task done: WAL moved
        ]
        out = _run(tmp_path, path, steps, with_bun=True)
        assert out["results"][0]["blocked"] is False
        assert out["results"][1]["blocked"] is True, "stale allow survived task done"
        assert out["results"][1]["queried"] is True
        assert out["calls"] == 2

    def test_without_a_signature_an_allow_is_never_reused(self, tmp_path, emitted):
        """No Bun -> no DB signature -> no way to know the task is still active.
        Re-query every time rather than risk a stale allow."""
        path, _ = emitted
        steps = [{"tool": "write", "active": True}] * 3
        out = _run(tmp_path, path, steps, with_bun=False)
        assert [r["blocked"] for r in out["results"]] == [False, False, False]
        assert out["calls"] == 3, "an allow was cached without a signature to justify it"

    def test_without_a_signature_a_block_may_be_reused(self, tmp_path, emitted):
        """A stale block is over-strict — the safe direction — so it is cacheable."""
        path, _ = emitted
        steps = [{"tool": "write", "active": False}] * 3
        out = _run(tmp_path, path, steps, with_bun=False)
        assert all(r["blocked"] for r in out["results"])
        assert out["calls"] == 1


# --- CLI oracle: the row the JS plugin shells out to write -------------------

import sqlite3  # noqa: E402
import types  # noqa: E402

_SCRIPTS = os.path.join(REPO, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


class TestEmitSupervisionCLI:
    """The `events emit-supervision` command is the single producer both harnesses
    share. Test it directly (no node) so its row contract is pinned even where
    node is absent — and so a JS-side change can never quietly redefine the row."""

    def _project(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        tdir = tmp_path / ".tausik"
        tdir.mkdir()
        be = SQLiteBackend(str(tdir / "tausik.db"))
        return ProjectService(be), be

    def _rows(self, be):
        return [
            tuple(r)
            for r in be._conn.execute(
                "SELECT entity_type, entity_id, action, details FROM events "
                "WHERE entity_type='supervision' ORDER BY id"
            ).fetchall()
        ]

    def test_bypass_kind_writes_bypass_action(self, tmp_path):
        from project_cli_events import cmd_events_emit_supervision

        svc, be = self._project(tmp_path)
        args = types.SimpleNamespace(
            kind="bypass", vector="skip_hooks", sup_source="opencode_qg0", details=None
        )
        cmd_events_emit_supervision(svc, args)
        assert self._rows(be) == [("supervision", "opencode_qg0", "bypass_skip_hooks", None)]

    def test_degradation_kind_writes_fail_open_action(self, tmp_path):
        from project_cli_events import cmd_events_emit_supervision

        svc, be = self._project(tmp_path)
        args = types.SimpleNamespace(
            kind="degradation",
            vector="cli_unreachable",
            sup_source="opencode_qg0",
            details="cli unavailable",
        )
        cmd_events_emit_supervision(svc, args)
        assert self._rows(be) == [
            ("supervision", "opencode_qg0", "fail_open_cli_unreachable", "cli unavailable")
        ]

    def test_row_is_chain_safe_raw_insert(self, tmp_path):
        """Parity with the Python emitter: a raw INSERT leaves entry_hash NULL,
        sealed lazily later — never eagerly hashed by a divergent second path."""
        from project_cli_events import cmd_events_emit_supervision

        svc, be = self._project(tmp_path)
        args = types.SimpleNamespace(
            kind="bypass", vector="skip_hooks", sup_source="opencode_qg0", details=None
        )
        cmd_events_emit_supervision(svc, args)
        row = be._conn.execute(
            "SELECT entry_hash FROM events WHERE entity_type='supervision'"
        ).fetchone()
        assert row[0] is None

    def test_cli_reports_failure_when_write_does_not_land(self, tmp_path, capsys):
        """s128 review HIGH-1: a best-effort write that fails must NOT be reported
        as 'Recorded' — the one command the cross-harness parity depends on has to
        make a swallowed miss distinguishable (stderr WARNING + non-zero exit)."""
        import pytest

        from project_cli_events import cmd_events_emit_supervision

        svc, be = self._project(tmp_path)
        be.close()  # release the handle, then corrupt the sink so the write fails
        (tmp_path / ".tausik" / "tausik.db").write_bytes(b"not a sqlite database")
        args = types.SimpleNamespace(
            kind="bypass", vector="skip_hooks", sup_source="opencode_qg0", details=None
        )
        with pytest.raises(SystemExit) as ei:
            cmd_events_emit_supervision(svc, args)
        assert ei.value.code == 1
        err = capsys.readouterr().err
        assert "NOT recorded" in err
        assert "Recorded supervision event" not in err

    def test_counts_in_bypasses_metric_not_detections(self, tmp_path):
        """The whole point: the shelled row lands in the SAME metric bucket as the
        Python-side bypass, so supervision_bypasses is no longer blind on opencode."""
        from project_cli_events import cmd_events_emit_supervision

        svc, be = self._project(tmp_path)
        cmd_events_emit_supervision(
            svc,
            types.SimpleNamespace(
                kind="bypass", vector="skip_hooks", sup_source="opencode_qg0", details=None
            ),
        )
        assert be.supervision_bypasses_summary()["by_action"]["bypass_skip_hooks"] == 1
        assert be.supervision_detections_summary()["total"] == 0
