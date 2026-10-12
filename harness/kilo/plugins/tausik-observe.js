// TAUSIK model observation for Kilo — provider-agnostic live model telemetry.
//
// The gates plugin (tausik-gates.js) enforces; THIS plugin observes. Kilo runs
// any provider — z.ai, Ollama, LM Studio, vLLM, whatever — and the session's
// model is visible to the host in every `chat.message` event as
// `{providerID, modelID}`. TAUSIK's provider chain (scripts/providers/kilo.py)
// cannot see host UI state from outside, so this plugin records the
// observation to `.tausik/runtime/active_model.json` and injects
// `TAUSIK_AGENT_MODEL` into bash sessions via `shell.env` — the one variable
// agent_model_source already ranks first.
//
// ZERO NPM DEPENDENCIES: only node: built-ins, which exist identically under
// Node (tests) and Bun (the host). A missing hook payload, an unwritable file
// or a malformed model id must NEVER throw into the host — observation is
// best-effort by contract; enforcement lives in the gates plugin.
//
// Honest status: harness-verified by executing the hooks under Node
// (tests/test_kilo_observe_plugin.py). The live round-trip — Kilo actually
// firing chat.message and the model landing in `task start` output — needs one
// host restart and is documented as pending, not claimed.

import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import path from "node:path";

/** Where the provider chain looks (scripts/providers/kilo.py::_RUNTIME_FILE). */
const RUNTIME_REL = path.join(".tausik", "runtime", "active_model.json");

/** Same length bound as agent_model_source._MAX_LEN on the reading side. The
 * character-class validation itself is NOT duplicated here — the Python
 * sanitise() is the one oracle for what is a legal model id; this file only
 * avoids writing obvious garbage (empty, oversized). */
const MAX_LEN = 120;

/** @type {{provider_id: string, model_id: string, updated_at: string}|null} */
let _lastSeen = null;

/** Persist the observation. Best-effort: any failure is swallowed AFTER a loud
 * warning — a broken observation must not brick the editor, but it must also
 * never fail silently (the provider would report "unknown" with no trace).
 *
 * @param {string} root project directory
 * @param {string} providerId
 * @param {string} modelId
 */
function _record(root, providerId, modelId) {
  const payload = {
    provider_id: providerId,
    model_id: modelId,
    source: "kilo-plugin",
    updated_at: new Date().toISOString(),
  };
  const file = path.join(root, RUNTIME_REL);
  try {
    mkdirSync(path.dirname(file), { recursive: true });
    writeFileSync(file, JSON.stringify(payload, null, 2) + "\n", "utf-8");
  } catch (e) {
    console.warn(
      `[TAUSIK observe] could not write ${RUNTIME_REL} (${e instanceof Error ? e.message : e}); ` +
        `model detection stays on env/config.`
    );
  }
}

/** A model id worth recording: a non-empty string within the length bound. */
function _plausible(v) {
  return typeof v === "string" && v.trim().length > 0 && v.length <= MAX_LEN ? v.trim() : null;
}

// NOTE: exactly ONE export — host loaders may call every export as a plugin
// factory; a helper export would be invoked with the plugin context and blow
// up at init (see the gates plugin for the full failure story).

/**
 * @param {{directory?: string, worktree?: string}} ctx
 */
export const TausikObserve = async ({ directory, worktree }) => {
  const root = directory || worktree || process.cwd();

  return {
    /**
     * @param {{model?: {providerID?: string, modelID?: string}}} input
     */
    "chat.message": async (input) => {
      const model = input && input.model;
      if (!model) return; // no model in the event: nothing to observe, no guess
      const modelId = _plausible(model.modelID);
      const providerId = _plausible(model.providerID) || "unknown";
      if (!modelId) return;
      _lastSeen = { provider_id: providerId, model_id: modelId, updated_at: new Date().toISOString() };
      _record(root, providerId, modelId);
    },

    /**
     * `shell.env` runs before every bash session: hand it the observed model so
     * `agent_model_source.from_env` sees TAUSIK_AGENT_MODEL even mid-session.
     * Last resort when nothing was observed this run: the runtime file itself
     * (a previous session's observation), read defensively.
     *
     * @param {unknown} _input
     * @param {{env: Record<string, string>}} output
     */
    "shell.env": async (_input, output) => {
      let modelId = _lastSeen ? _lastSeen.model_id : null;
      if (!modelId) {
        try {
          const raw = readFileSync(path.join(root, RUNTIME_REL), "utf-8");
          const data = JSON.parse(raw);
          modelId = _plausible(data && data.model_id);
        } catch {
          modelId = null; // no observation anywhere — set nothing, guess nothing
        }
      }
      if (modelId && output && output.env && typeof output.env === "object") {
        output.env.TAUSIK_AGENT_MODEL = modelId;
      }
    },
  };
};
