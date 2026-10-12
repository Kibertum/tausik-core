"""Tests for the Kilo model-observation plugin (tausik-observe.js).

kilo-gate-plugin parametrized the two hosts' GATES plugin because they share
one contract. The OBSERVER is a different concern — Kilo-specific capability
(the gates plugin has no OpenCode counterpart to parametrize against) — so it
gets its own module: static checks (zero NPM deps, single export) plus
behavioural runs under Node against the REAL filesystem in a tmp tree.
"""

from __future__ import annotations

from pathlib import Path

import json
import os
import re
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = os.path.join(REPO, "harness", "kilo", "plugins", "tausik-observe.js")
RUNTIME_REL = os.path.join(".tausik", "runtime", "active_model.json")

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")

DRIVER = r"""
// Same import-by-name assertion as the gates driver: the module must really
// export its contract symbol.
const scenario = JSON.parse(process.argv[2]);
const mod = await import("%(plugin)s");
const factory = mod.TausikObserve;
if (typeof factory !== "function") {
  throw new Error(`no export TausikObserve: ${Object.keys(mod).join(",")}`);
}
const hooks = await factory({ directory: scenario.root });
const warnings = [];
console.warn = (...args) => warnings.push(args.join(" "));

const out = { events: [], shellEnv: null, warnings };
for (const step of scenario.steps) {
  if (step.kind === "chat") {
    try {
      await hooks["chat.message"]({ sessionID: "s1", model: step.model });
      out.events.push("ok");
    } catch (e) {
      out.events.push(`threw:${e.message}`);
    }
  } else if (step.kind === "shell") {
    const output = { env: {} };
    await hooks["shell.env"]({ cwd: scenario.root }, output);
    out.shellEnv = output.env;
  }
}
console.log(JSON.stringify(out));
"""


def _execute(tmp_path, scenario: dict) -> dict:
    plugin_url = "file:///" + CANONICAL.replace("\\", "/").lstrip("/")
    driver = tmp_path / "driver.mjs"
    driver.write_text(DRIVER % {"plugin": plugin_url}, encoding="utf-8")
    proc = subprocess.run(
        [NODE, str(driver), json.dumps(scenario)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env={**os.environ},
        check=False,
    )
    assert proc.returncode == 0, f"driver failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _chat(model) -> dict:
    return {"kind": "chat", "model": model}


class TestStatic:
    def test_zero_npm_dependencies(self):
        """node: built-ins only — the plugin must run under Node (tests) and Bun
        (the host) with nothing installed. A bare `from '...'` or any package
        import is refused."""
        src = Path(CANONICAL).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in src.splitlines() if not line.lstrip().startswith(("//", "*", "/*"))
        )
        for m in re.finditer(r"from\s+['\"]([^'\"]+)['\"]", code):
            assert m.group(1).startswith("node:"), f"non-builtin import: {m.group(1)}"
        assert not re.search(r"\brequire\s*\(", code), "require()"
        assert "@kilocode/plugin" not in code

    def test_single_named_export(self):
        src = Path(CANONICAL).read_text(encoding="utf-8")
        exports = re.findall(r"^\s*export\s+(?:const|function|class|let|var)\s+(\w+)", src, re.M)
        assert exports == ["TausikObserve"], exports
        assert "export default" not in src

    def test_runtime_path_matches_the_provider(self):
        """The plugin writes where scripts/providers/kilo.py reads. A path drift
        would silently unhook observation from detection."""
        from providers import kilo as kilo_provider

        src = Path(CANONICAL).read_text(encoding="utf-8")
        assert '"active_model.json"' in src
        assert str(kilo_provider._RUNTIME_FILE).replace("\\", "/").replace(".tausik/", "") in src

    def test_bootstrap_deploys_both_kilo_plugins_together(self, tmp_path):
        """Gates and observation are one deploy unit: a profile carrying the
        gate but not the observer would enforce without seeing the model — a
        half-wired host. generate_kilo_plugin must land both files."""
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(REPO), "bootstrap"))
        from bootstrap_kilo import generate_kilo_plugin

        lib = tmp_path / "lib"
        src_dir = lib / "harness" / "kilo" / "plugins"
        src_dir.mkdir(parents=True)
        shutil.copyfile(
            os.path.join(REPO, "harness", "kilo", "plugins", "tausik-gates.js"),
            src_dir / "tausik-gates.js",
        )
        shutil.copyfile(CANONICAL, src_dir / "tausik-observe.js")
        target = tmp_path / "proj" / ".kilo"
        target.mkdir(parents=True)
        deployed = generate_kilo_plugin(str(target), lib_dir=str(lib))
        names = sorted(os.path.basename(p) for p in deployed)
        assert names == ["tausik-gates.js", "tausik-observe.js"]
        assert (target / "plugins" / "tausik-observe.js").is_file()


@needs_node
class TestObservation:
    def test_chat_event_writes_the_runtime_file(self, tmp_path):
        root = str(tmp_path)
        out = _execute(
            tmp_path,
            {
                "root": root,
                "steps": [_chat({"providerID": "zai-coding-plan", "modelID": "glm-4.7"})],
            },
        )
        assert out["events"] == ["ok"]
        data = json.loads((tmp_path / RUNTIME_REL).read_text(encoding="utf-8"))
        assert data["model_id"] == "glm-4.7"
        assert data["provider_id"] == "zai-coding-plan"
        assert data["source"] == "kilo-plugin"
        assert "updated_at" in data

    def test_no_model_in_event_writes_nothing(self, tmp_path):
        """THE negative: no observation, no guess — the file must not exist."""
        root = str(tmp_path)
        out = _execute(tmp_path, {"root": root, "steps": [_chat(None), _chat({})]})
        assert out["events"] == ["ok", "ok"]
        assert not (tmp_path / RUNTIME_REL).exists()

    @pytest.mark.parametrize("model_id", ["", "   ", "x" * 200, None, 42])
    def test_implausible_model_id_writes_nothing(self, tmp_path, model_id):
        root = str(tmp_path)
        _execute(
            tmp_path, {"root": root, "steps": [_chat({"providerID": "p", "modelID": model_id})]}
        )
        assert not (tmp_path / RUNTIME_REL).exists(), f"garbage recorded: {model_id!r}"

    def test_second_event_overwrites_with_the_new_model(self, tmp_path):
        root = str(tmp_path)
        _execute(
            tmp_path,
            {
                "root": root,
                "steps": [
                    _chat({"providerID": "zai", "modelID": "glm-4.7"}),
                    _chat({"providerID": "ollama", "modelID": "qwen3:8b"}),
                ],
            },
        )
        data = json.loads((tmp_path / RUNTIME_REL).read_text(encoding="utf-8"))
        assert data["model_id"] == "qwen3:8b"  # live beats stale: last event wins
        assert data["provider_id"] == "ollama"  # ...including the provider switch

    def test_unwritable_root_warns_loudly_and_does_not_throw(self, tmp_path):
        """Best-effort means never throwing into the host — and never failing in
        silence: the provider would report 'unknown' with no trace otherwise."""
        root = tmp_path / "locked"
        root.mkdir()
        blocker = root / ".tausik"  # a FILE where the runtime DIR must go
        blocker.write_text("occupied", encoding="utf-8")
        out = _execute(
            tmp_path,
            {"root": str(root), "steps": [_chat({"providerID": "zai", "modelID": "glm-4.7"})]},
        )
        assert out["events"] == ["ok"], "the hook must swallow the fs error"
        assert out["warnings"] and "could not write" in out["warnings"][0]


@needs_node
class TestShellEnvInjection:
    def test_observed_model_reaches_bash_sessions(self, tmp_path):
        root = str(tmp_path)
        out = _execute(
            tmp_path,
            {
                "root": root,
                "steps": [
                    _chat({"providerID": "zai", "modelID": "glm-4.7"}),
                    {"kind": "shell"},
                ],
            },
        )
        assert out["shellEnv"]["TAUSIK_AGENT_MODEL"] == "glm-4.7"

    def test_no_observation_sets_nothing(self, tmp_path):
        """No runtime file, no chat event: `shell.env` must NOT invent a model."""
        root = str(tmp_path)
        out = _execute(tmp_path, {"root": root, "steps": [{"kind": "shell"}]})
        assert "TAUSIK_AGENT_MODEL" not in out["shellEnv"]

    def test_previous_session_observation_is_picked_up(self, tmp_path):
        """A fresh host process has no _lastSeen; the runtime file from a
        PREVIOUS session still carries a real observation — use it, the file is
        the same channel the provider reads."""
        root = tmp_path
        runtime = root / ".tausik" / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "active_model.json").write_text(
            json.dumps({"model_id": "glm-4.6", "provider_id": "zai"}), encoding="utf-8"
        )
        out = _execute(tmp_path, {"root": str(root), "steps": [{"kind": "shell"}]})
        assert out["shellEnv"]["TAUSIK_AGENT_MODEL"] == "glm-4.6"
