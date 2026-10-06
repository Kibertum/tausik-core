// TAUSIK QG-0 gate for Kilo Code — the enforcement layer, not a suggestion.
//
// Port of harness/opencode/plugins/tausik-qg0.js (QG-0 for OpenCode). The
// verdict machinery is shared BY DESIGN: both hosts ask the same CLI the same
// question (`status --compact`), so the gate cannot drift from what Claude
// Code's task_gate.py enforces — there is no second copy of the truth, only a
// second caller. Kilo-specific parts are marked KILO below.
//
// Why a file copy and not an import: HARD RULE — ZERO IMPORTS. Not `require`,
// not `import`, not even a type-only import of `@kilocode/plugin`. OpenCode
// died exactly this way (ERR_MODULE_NOT_FOUND resolving a nonexistent @local
// version took the whole prompt loop down). Kilo loads this file from
// `.kilo/plugins/` where no node_modules is guaranteed. Types come from JSDoc.
// This file must run with nothing installed.
//
// Runtime globals only: `process` (env, platform) and, when present, `Bun`
// (Kilo runs plugins on Bun; `Bun` is used solely to make the cache exact —
// see _dbSignature).
//
// Live-host status (honest): the CLI verdict this gate consults is measured
// (same binary the doctor's MCP probe exercises), but a live denial inside a
// running Kilo session has not been observed yet — it needs one host restart
// after bootstrap. Until then this gate's enforcement is pending, not proven.

/** Tools that mutate the filesystem. KILO: a superset across Kilo versions —
 * `edit` and `write` are the built-in mutators (the permission list names
 * `edit`; `write` exists on current builds), `apply_patch` keeps OpenCode
 * parity. Gating a name the host does not have is a no-op; NOT gating one it
 * does is the forbidden direction. `bash` can write, but gating it would block
 * the very command that starts a task (`tausik task start`), so it is not
 * gated — the same choice Claude Code's matcher and the OpenCode port make. */
const WRITE_TOOLS = new Set(["write", "edit", "apply_patch"]);

/** Upper bound on how long a verdict may be reused. Caps any clock/fs weirdness. */
const CACHE_TTL_MS = 2000;

/** @type {{sig: string|null, active: boolean, ts: number}|null} */
let _cache = null;

/** Signature of the TAUSIK DB: any task-state change moves it.
 *
 * WAL is included on purpose — `task start` / `task done` land in
 * `tausik.db-wal` first, so a signature over `tausik.db` alone would go on
 * reporting the old verdict.
 *
 * Returns null when `Bun` is absent. A null signature disables allow-caching
 * entirely — see _verdict.
 *
 * @param {string} root project directory
 * @returns {Promise<string|null>}
 */
async function _dbSignature(root) {
  if (typeof Bun === "undefined") return null;
  const parts = [];
  for (const rel of [".tausik/tausik.db", ".tausik/tausik.db-wal"]) {
    try {
      const f = Bun.file(`${root}/${rel}`);
      parts.push((await f.exists()) ? `${f.size}:${f.lastModified}` : "-");
    } catch {
      return null;
    }
  }
  return parts.join("|");
}

/** Path to the CLI wrapper. Windows gets the .cmd — the bare `tausik` file is a
 * bash script and Bun's shell has no bash to hand it to.
 * @param {string} root
 */
function _cliPath(root) {
  const win = typeof process !== "undefined" && process.platform === "win32";
  return `${root}/.tausik/tausik${win ? ".cmd" : ""}`;
}

/** Ask the CLI whether any task is active.
 *
 * The CLI is the only sanctioned reader of the DB (framework rule: no direct DB
 * access). Throws on any failure so the caller can apply the fail-open /
 * fail-secure policy explicitly rather than by accident.
 *
 * @param {Function} $ Bun shell from the plugin context
 * @param {string} root
 * @returns {Promise<boolean>}
 */
async function _queryActive($, root) {
  const out = await $`${_cliPath(root)} status --compact`.quiet().text();
  const parsed = JSON.parse(out);
  const n = parsed.tasks_active;
  if (typeof n !== "number") throw new Error("status --compact lacks tasks_active");
  return n > 0;
}

/** Record a supervision bypass/degradation — parity with the Python hooks and
 * the OpenCode port (l26-bypass-telemetry-opencode-parity). The SAME weakening
 * lives in this Node harness as in scripts/hooks/task_gate.py, and the metric
 * that counts switch-offs (supervision_bypasses) is blind here unless we leave
 * a row.
 *
 * Routes through the CLI (`events emit-supervision`) so the row is written by
 * the one Python emitter — identical entity_type/action/chain-safe contract,
 * never a second copy of it re-implemented in JS.
 *
 * Best-effort, and awaited so the record actually lands before the hook
 * returns: a failure to write is a MISSING row, never a thrown error.
 *
 * @param {Function} $
 * @param {string} root
 * @param {"bypass"|"degradation"} kind
 * @param {string} vector
 * @param {string} source
 */
async function _recordSupervision($, root, kind, vector, source) {
  try {
    await $`${_cliPath(root)} events emit-supervision --kind ${kind} --vector ${vector} --source ${source}`
      .quiet()
      .text();
  } catch {
    // swallow — best-effort telemetry, never blocks or bricks the editor
  }
}

/** Cached active-task verdict.
 *
 * The CLI costs 300 ms warm / 1.1 s cold on Windows (measured on the OpenCode
 * port; same CLI, same machine class), which is paid on every single write —
 * so a cache is not optional. But it may only ever err toward STRICTNESS: a
 * stale answer must never let through a write that should have been blocked.
 *
 * Two independent guards give that:
 *   1. The verdict is bound to the DB signature. `task done` changes the WAL, so
 *      the old "active" verdict cannot survive it.
 *   2. A TTL caps reuse regardless.
 * When no signature is available (no Bun), only a `false` (blocking) verdict is
 * cached — reusing a stale `true` there would be exactly the forbidden direction.
 *
 * @param {Function} $
 * @param {string} root
 * @returns {Promise<boolean>}
 */
async function _verdict($, root) {
  const sig = await _dbSignature(root);
  const now = Date.now();
  if (_cache && now - _cache.ts < CACHE_TTL_MS) {
    if (_cache.unreachable) {
      // A broken CLI is a STABLE condition. Cache the unreachable verdict too,
      // under the SAME signature guard as an active verdict: reuse only while a
      // real DB signature is unchanged. No signature (no Bun) => don't reuse —
      // reusing a fail-open verdict is the LENIENT direction, forbidden without
      // a signature to justify it. The reused throw carries freshProbe:false so
      // the caller records the degradation once per real probe, not once per
      // write.
      if (sig !== null && _cache.sig === sig) {
        throw _unreachableError(_cache.reason, false);
      }
    } else {
      const usable = sig !== null ? _cache.sig === sig : _cache.active === false;
      if (usable) return _cache.active;
    }
  }
  let active;
  try {
    active = await _queryActive($, root);
  } catch (e) {
    const reason = e instanceof Error ? e.message : String(e);
    _cache = { sig, unreachable: true, reason, ts: now };
    throw _unreachableError(reason, true);
  }
  _cache = { sig, active, ts: now };
  return active;
}

/** Build the throw that signals "CLI unreachable" to tool.execute.before.
 *
 * `freshProbe` distinguishes a real, just-observed probe failure (record the
 * degradation) from a reused cached verdict within the TTL window (the SAME
 * episode — do NOT re-shell the broken emit on every write).
 *
 * @param {string} reason
 * @param {boolean} freshProbe
 */
function _unreachableError(reason, freshProbe) {
  const err = new Error(reason);
  err.cliUnreachable = true;
  err.freshProbe = freshProbe;
  return err;
}

// NOTE: this module exports exactly ONE symbol, and that is deliberate. Host
// loaders may call every export as a plugin factory; a test-only helper export
// would be invoked with the plugin context and its `undefined` return read for
// hooks — a TypeError during plugin init, i.e. the host dies at load because of
// a symbol that existed only for the test suite. Tests get a clean cache for
// free — each one spawns a fresh process, so the module (and `_cache`) is
// re-imported.

/**
 * KILO: the Kilo SDK example exports a named async factory returning the hooks
 * object (`export const ExamplePlugin = async (ctx) => ({ ... })`), so this
 * file matches that shape rather than OpenCode's bare factory call — same
 * contract, spelled the way this host's own example spells it.
 *
 * @param {{project?: unknown, client?: unknown, $?: Function, directory?: string, worktree?: string}} ctx
 */
export const TausikGates = async ({ $, directory, worktree }) => {
  const shell = /** @type {Function} */ ($);
  const root = directory || worktree || process.cwd();

  return {
    // KILO: no `event`/session-lifecycle hook here yet. OpenCode's port syncs
    // TAUSIK sessions via `session.created`/`session.deleted`, but those event
    // names are OpenCode's union, and Kilo's Event names are not verified in
    // this repository. A gate that guesses event names risks a TypeError at
    // plugin load — the exact failure class this file exists to prevent. Rule 1
    // enforcement does not depend on session sync; add the hook only after the
    // names are measured in a live host.

    /**
     * @param {{tool: string}} input
     * @param {{args: Record<string, unknown>}} _output
     */
    "tool.execute.before": async (input, _output) => {
      // WRITE_TOOLS filter FIRST: read-only tools are never gated and must not
      // emit bypass telemetry either — that keeps the count scoped to the same
      // write surface Claude Code's task_gate matcher (Write|Edit|MultiEdit)
      // sees. A skip that fired on every read would wildly over-count.
      if (!WRITE_TOOLS.has(input.tool)) return;
      if (typeof shell !== "function") {
        // No Bun shell in the plugin input: the gate cannot ask the CLI. The
        // honest behavior is the OpenCode fail-open path with a loud warning —
        // NOT a silent pass-through that looks like enforcement.
        console.warn(
          `[TAUSIK QG-0] DEGRADED: plugin context has no shell; allowing ` +
            `'${input.tool}' WITHOUT an active-task check. ` +
            `Set TAUSIK_HOOK_FAIL_SECURE=1 to block instead of allow.`
        );
        if (process.env.TAUSIK_HOOK_FAIL_SECURE) {
          throw new Error(
            "QG-0: TAUSIK_HOOK_FAIL_SECURE=1 is set, but the plugin context has " +
              "no shell to reach the TAUSIK CLI. Fix the host or unset the flag."
          );
        }
        return;
      }

      if (process.env.TAUSIK_SKIP_HOOKS) {
        // The umbrella skip disables the gate — but never in silence. Record the
        // bypass so the supervision_bypasses metric is not blind on this harness.
        await _recordSupervision(shell, root, "bypass", "skip_hooks", "kilo_gates");
        return;
      }

      const failSecure = Boolean(process.env.TAUSIK_HOOK_FAIL_SECURE);

      let active;
      try {
        active = await _verdict(shell, root);
      } catch (e) {
        const reason = e instanceof Error ? e.message : String(e);
        // Default fail-open: a broken CLI must not brick someone's editor.
        // TAUSIK_HOOK_FAIL_SECURE=1 flips it for shared/CI contexts where a
        // silent bypass is the worse failure.
        if (failSecure) {
          throw new Error(
            `QG-0: TAUSIK_HOOK_FAIL_SECURE=1 is set, but the task gate could not ` +
              `reach the TAUSIK CLI (${reason}). Fix the CLI or unset the flag.`
          );
        }
        // Fail-open, but NEVER in silence. A gate that quietly stops gating is
        // the exact failure class this framework refuses to tolerate.
        console.warn(
          `[TAUSIK QG-0] DEGRADED: could not reach the TAUSIK CLI (${reason}). ` +
            `Allowing '${input.tool}' WITHOUT an active-task check. ` +
            `Run \`tausik doctor\`; set TAUSIK_HOOK_FAIL_SECURE=1 to block instead of allow.`
        );
        // The supervision row shells the (broken) CLI — a slow spawn. Emit it
        // only on a FRESH probe: a reused cached-unreachable verdict is the SAME
        // degradation episode within the TTL window, already recorded. Unknown
        // errors (freshProbe undefined) are treated as fresh so an unexpected
        // failure is never silently uncounted.
        if (e && e.freshProbe === false) return;
        await _recordSupervision(shell, root, "degradation", "cli_unreachable", "kilo_gates");
        return;
      }

      if (active) return;

      throw new Error(
        "QG-0: нет активной задачи. Выполни `tausik task start <slug>` " +
          "перед изменением кода (SENAR Rule 9.1). " +
          "Список задач: `tausik task list --status planning`."
      );
    },
  };
};
