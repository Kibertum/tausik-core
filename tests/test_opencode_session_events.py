"""OpenCode opens and closes the TAUSIK session with its own session events (1.10)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

# This test imports no product module — it runs the plugin under Node, so no
# import edge selects it. Declared so a change to the plugin runs it.
CROSSCUTTING_SCOPE = ["harness/opencode/"]

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(REPO, "harness", "opencode", "plugins", "tausik-qg0.js")
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

DRIVER = r"""
import { TausikQG0 } from "%(plugin)s";
const scenario = JSON.parse(process.argv[2]);
const cmds = [];
const $ = (strings, ...values) => {
  let cmd = "";
  for (let i = 0; i < strings.length; i++) { cmd += strings[i]; if (i < values.length) cmd += String(values[i]); }
  return { quiet: () => ({ text: async () => { cmds.push(cmd.trim()); if (scenario.cliFails) throw new Error("cli down"); return ""; } }) };
};
const hooks = await TausikQG0({ $, directory: "/proj" });
let threw = false;
for (const ev of scenario.events) { try { await hooks.event({ event: ev }); } catch (e) { threw = true; } }
console.log(JSON.stringify({ cmds, threw }));
"""


def _run(tmp_path, events, cli_fails=False):
    driver = tmp_path / "d.mjs"
    url = "file:///" + os.path.abspath(PLUGIN).replace("\\", "/").lstrip("/")
    driver.write_text(DRIVER % {"plugin": url}, encoding="utf-8")
    proc = subprocess.run(
        [NODE, str(driver), json.dumps({"events": events, "cliFails": cli_fails})],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_created_and_deleted_open_and_close_the_host_session(tmp_path):
    out = _run(
        tmp_path,
        [
            {"type": "session.created", "properties": {"info": {"id": "ses_1"}}},
            {"type": "session.deleted", "properties": {"sessionID": "ses_1"}},
        ],
    )
    assert out["cmds"][0].endswith("session start --host-id ses_1")
    assert out["cmds"][1].endswith("session end --host-id ses_1")


def test_an_event_without_an_id_opens_nothing(tmp_path):
    """NEGATIVE: no id, no row guessed; other events are ignored."""
    out = _run(tmp_path, [{"type": "session.created", "properties": {}}, {"type": "session.idle"}])
    assert out["cmds"] == []


def test_a_failing_cli_never_throws_into_the_editor(tmp_path):
    """NEGATIVE: bookkeeping is not a gate."""
    out = _run(tmp_path, [{"type": "session.created", "properties": {"id": "x"}}], cli_fails=True)
    assert out["threw"] is False and len(out["cmds"]) == 1
