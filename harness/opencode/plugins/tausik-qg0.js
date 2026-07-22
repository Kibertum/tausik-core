// TAUSIK QG-0 gate for OpenCode — the enforcement layer, not a suggestion.
//
// Mirrors scripts/hooks/task_gate.py (Claude Code PreToolUse): a write with no
// active TAUSIK task is refused. Without this file, "OpenCode support" is just
// markdown the host is free to ignore — and it does (AGENTS.md is
// first-matching-file-wins, so a user's own file shadows ours forever).
//
// HARD RULE — ZERO IMPORTS. Not `require`, not `import`, not even a type-only
// import of `@opencode-ai/plugin`. That exact import is what killed the user's
// host: OpenCode tried to resolve a nonexistent @local version, threw
// ERR_MODULE_NOT_FOUND, and took the whole prompt loop down with it. Types come
// from JSDoc. This file must run with nothing installed.
//
// Runtime globals only: `process` (env, platform) and, when present, `Bun`
// (used solely to make the cache exact — see _dbSignature).

/** Tools that mutate the filesystem. Verbatim from opencode.ai/docs/tools —
 * note `apply_patch`, NOT `patch`. `todowrite` writes a todo list, not the
 * repo, so it is not gated. `bash` can write, but gating it would block the
 * very command that starts a task (`tausik task start`), so it is not gated —
 * same choice Claude Code's matcher makes. */
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
 * Returns null when `Bun` is absent (i.e. not running under OpenCode). A null
 * signature disables allow-caching entirely — see _verdict.
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

/** Record a supervision bypass/degradation, cross-harness parity with the
 * Python hooks (l26-bypass-telemetry-opencode-parity). The SAME weakening lives
 * in this Node harness as in scripts/hooks/task_gate.py, and the metric that
 * counts switch-offs (supervision_bypasses) is blind here unless we leave a row.
 *
 * Routes through the CLI (`events emit-supervision`) so the row is written by
 * the one Python emitter — identical entity_type/action/chain-safe contract,
 * never a second copy of it re-implemented in JS (a second producer would drift,
 * the very thing the metric's oracle rule forbids).
 *
 * Best-effort, and awaited so the record actually lands before the hook returns:
 * a failure to write is a MISSING row, never a thrown error — telemetry must not
 * brick the editor. In the fail-open case the CLI is already the thing that
 * broke, so this attempt usually fails too; that is the honest floor (a
 * degradation this cannot record is undercounted, never overcounted), the same
 * ceiling the Python side documents.
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
 * The CLI costs 300 ms warm / 1.1 s cold on Windows (measured), which is paid on
 * every single write — so a cache is not optional. But it may only ever err
 * toward STRICTNESS: a stale answer must never let through a write that should
 * have been blocked.
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
    const usable = sig !== null ? _cache.sig === sig : _cache.active === false;
    if (usable) return _cache.active;
  }
  const active = await _queryActive($, root);
  _cache = { sig, active, ts: now };
  return active;
}

// NOTE: this module exports exactly ONE symbol, and that is deliberate. OpenCode's docs
// say a plugin "exports one or more plugin functions" — the loader calls exports as plugin
// factories. A test-only helper like a cache-reset export would be invoked with the plugin
// context and its `undefined` return read for hooks: a TypeError during plugin init, i.e.
// the host dies at load because of a symbol that existed only for the test suite. That is
// the exact failure this file was written to prevent. Tests get a clean cache for free —
// each one spawns a fresh process, so the module (and `_cache`) is re-imported.

/**
 * @param {{project?: unknown, client?: unknown, $: Function, directory?: string, worktree?: string}} ctx
 */
export const TausikQG0 = async ({ $, directory, worktree }) => {
  const root = directory || worktree || process.cwd();

  return {
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

      if (process.env.TAUSIK_SKIP_HOOKS) {
        // The umbrella skip disables the gate — but never in silence. Record the
        // bypass so the supervision_bypasses metric is not blind on this harness.
        await _recordSupervision($, root, "bypass", "skip_hooks", "opencode_qg0");
        return;
      }

      const failSecure = Boolean(process.env.TAUSIK_HOOK_FAIL_SECURE);

      let active;
      try {
        active = await _verdict($, root);
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
        // Fail-open, but NEVER in silence. A gate that quietly stops gating is the
        // exact failure class this framework refuses to tolerate: without this line,
        // one broken CLI call disables QG-0 for the rest of the session and leaves no
        // trace for the user or an auditor.
        console.warn(
          `[TAUSIK QG-0] DEGRADED: could not reach the TAUSIK CLI (${reason}). ` +
            `Allowing '${input.tool}' WITHOUT an active-task check. ` +
            `Run \`tausik doctor\`; set TAUSIK_HOOK_FAIL_SECURE=1 to block instead of allow.`
        );
        // A visible warning tells THIS user; the supervision row makes the
        // degradation countable for an auditor (fail_open_%, a separate metric
        // bucket from intentional bypasses). Best-effort: the CLI is what broke,
        // so this often cannot land — an undercount, never a false clean.
        await _recordSupervision($, root, "degradation", "cli_unreachable", "opencode_qg0");
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
