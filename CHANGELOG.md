# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [1.3.0] — 2026-04-28 — Big release: MCP expansion + session discipline + plugin stacks

Single consolidated entry covering everything since v1.2.0 (40+ commits + an
independent 5-agent blind review hardening pass right before ship).

### 🧠 Shared Brain — cross-project knowledge base (Notion-backed)
- 4 Notion DBs (decisions, patterns, gotchas, web_cache) + local SQLite mirror with FTS5 (Cyrillic-aware).
- Notion REST client, stdlib-only, with retry/backoff + 350ms write throttle.
- Pull-sync engine with delta-fetch (`last_edited_time` cursor), atomic single-tx, WAL mode.
- `tausik brain init` wizard creates 4 DBs + atomic config in one shot.
- MCP server `tausik-brain` (7 tools) + skill `/brain` (query/store/show/status/move).
- Auto-route `tausik decide` via rule-based local↔brain classifier.
- PostToolUse `WebFetch` auto-cache hook → next fetch of same URL is blocked by mirror.
- Proactive lookup before WebSearch/WebFetch — instant hit from mirror.
- Privacy: project names hashed (SHA256[:16]) — no plaintext in Notion.
- Stale-lock recovery for SIGKILL'd wizard. NFC normalization for unicode-equivalent names.
- Brain schema migration scaffold (forward-only, single-tx).
- Qwen Code: brain MCP registered via bootstrap.

### 🧩 Plugin stack architecture (single source of truth)
- `stacks/<name>/{stack.json, guide.md}` declarative format (was: 5 hardcoded modules).
- JSON Schema (Draft-07) + actionable validator.
- `StackRegistry` with layered deep-merge: built-in ← `.tausik/stacks/<name>/` user override.
- 25 built-in stacks migrated (incl. 5 IaC: ansible/terraform/helm/k8s/docker).
- 6 consumers refactored to use registry with hardcoded fallback for boot safety.
- CLI: `tausik stack {list,info,export,diff,reset,lint,scaffold}` for full lifecycle.
- 5 MCP tools: `tausik_stack_{list,show,lint,diff,scaffold}` for agent-driven use.
- Bootstrap NEVER writes to `.tausik/stacks/` (test-enforced invariant).

### 🎭 Roles — first-class CRUD with hybrid storage
- New SQLite `roles` table (migration v18) — slug PK + title + description.
- Auto-seed from `DISTINCT tasks.role` on migration (no orphan task references).
- Hybrid storage: metadata in DB, markdown profile in `.tausik/roles/<slug>.md` (user) or `agents/roles/<slug>.md` (built-in).
- Bootstrap NEVER overwrites `.tausik/roles/` — user profiles survive re-bootstrap.
- CLI: `tausik role {list,show,create,update,delete,seed}` with `--extends` profile cloning.
- 6 MCP tools: `tausik_role_{list,show,create,update,delete,seed}` for CRUD.
- Delete refuses if tasks reference role (force=true → cascade NULL the references).

### ⏱️ Session active-time (gap-based) replaces wall clock
- Sessions exceeding 180-min SENAR Rule 9.2 are now measured by ACTIVE minutes, not wall clock.
- Activity counted via `events` table; gaps ≥ idle threshold (default 10 min) excluded as AFK.
- New PostToolUse hook `activity_event.py` writes one row per tool call so the metric works for any agent activity (not just MCP/CLI).
- `tausik status` shows both numbers: "Session: #N (X min active / Y min wall, Z% idle)".
- New CLI `tausik session recompute` retro-analyses prior sessions (real numbers vs claimed wall clock).
- Threshold tunable via `.tausik/config.json` `session_idle_threshold_minutes`.
- session_extend now respects project's configured `session_max_minutes` (was: hardcoded 180).

### 🔬 SENAR verification — scoped + cached
- Pytest gate runs ONLY tests for `relevant_files` (was: full suite always).
- `verification_runs` cache reuses green runs within 10-min TTL on same `files_hash`.
- Cache key includes resolved gate command — config changes invalidate stale entries.
- Security-sensitive files (auth/payment/jwt/oauth/sso/etc + .env/.pem/.key) bypass cache, always re-verify.
- Tier mapping fixed: simple→lightweight, medium→standard, complex→high (was hardcoded `lightweight`).
- v1.3 fix: `relevant_files=None` SKIPS instead of falling back to full suite (burned MCP 10s budget).
- Scoped-skip results NOT cached as verified — prevents silent QG-2 weakening.
- `tausik verify --task <slug>` for ad-hoc verification.

### 🎯 Agent-native planning (tool calls, not hours)
- Tier scale: trivial(≤10) / light(≤25) / moderate(≤60) / substantial(≤150) / deep(≤400+).
- `--call-budget` auto-derives tier; warning at 1.5×budget for re-calibration.
- `task start <slug> --force` bypasses session capacity gate (audit-logged).
- Custom stacks via `.tausik/config.json` (`custom_stacks`) without code changes.

### 🛡️ Memory Discipline — auto-memory protection
- PreToolUse hook blocks Write/Edit to `~/.claude/projects/*/memory/` from TAUSIK projects.
- Bypass via explicit `confirm: cross-project` marker in last user prompt.
- PostToolUse audit catches project-specific content that bypassed via regex (paths, slugs, tausik commands).
- Memory-block guard widened to ALL `~/.claude/**/memory/` (was: only `projects/<slug>/memory/`).

### 📦 Bootstrap deploy fix (CRITICAL — caught in v1.3 dogfooding)
- Built-in skills under `agents/skills/` are NOW source-of-truth — force-included in deploy.
- Was: explicit allowlist via `core_skills`/`extension_skills`/`installed_skills`. Saved config froze old list.
- Result: 9 missing core skills restored (review, brain, commit, debug, interview, markitdown, ship, skill-test, test).
- Smoke-test in `tests/test_bootstrap_skills_coverage.py` guards against future drift (4 cases).

### 🪝 Hooks
- `activity_event.py` (PostToolUse, broad matcher) — feeds active-time metric.
- `brain_post_webfetch.py` (PostToolUse, WebFetch) — auto-cache web responses.
- `brain_search_proactive.py` (PreToolUse, WebSearch|WebFetch) — mirror lookup before fetch.
- `memory_pretool_block.py` + `memory_posttool_audit.py` (Write|Edit|MultiEdit).
- Shared helpers in `_common.py`.
- Strip invisible separators (U+2028/2029/0085/VT/FF) before marker anchor matching.

### 🧪 DX & Framework Polish
- `task_done` accepts inline `--evidence` arg → log+done in one CLI call (was: two).
- `_verify_ac` accepts ✓/verified markers + literal "AC verified" — broader format tolerance.
- Refactored 4 files to stay under 400-line filesize gate: split session/role/stack subparsers + service helpers.
- 3 rounds of post-merge review: 5 HIGH + 11 MED + 4 LOW findings closed.
- Quality reviews + SENAR audit + adversarial critic spawn via `/review`.

### 📚 Docs
- `docs/en/{stacks, customization, upgrade, shared-brain}.md`.
- `docs/ru/shared-brain.md`.
- README EN/RU with v1.3 features.
- `references/anthropic-oss-applicability.md` — patterns survey.
- `references/markitdown-integration.md` — opt-in DOCX/PPTX/XLSX/HTML/EPUB.

### 🛠️ Misc
- `markitdown` opt-in capability (lazy import, zero-deps invariant preserved) + `tausik doc extract`.
- `tausik brain status` snapshot CLI.
- `tausik brain move <id> --to-brain|--to-local` cross-project ownership transfer.
- 5 SENAR Compliance table rows updated with v1.3 semantics.

### ⚙️ Config knobs (hardcode → `.tausik/config.json`)

Documented in `references/configuration.md`. Project-level overrides without forking:

- `verify_cache_ttl_seconds` (default 600) — verify-run reuse window.
- `session_warn_threshold_minutes` (default 150) — stop-hook reminder threshold.
- `session_idle_threshold_minutes` (default 10) — gap above which pause = AFK.
- `session_max_minutes` (default 180) — hard SENAR Rule 9.2 limit.
- `session_capacity_calls` (default 200) — per-session tool-call budget.
- `custom_stacks`, `gates`, `brain.*` — already documented in earlier tiers.

### 🩺 `tausik doctor` — health diagnostic
Single-command sanity check: venv + DB + MCP servers + core skills + bootstrap drift + config knobs + gates registry + active session. Exits 1 on any FAIL so CI can gate on it.

### 🛡️ `/zero-defect` skill (Maestro-inspired)
Session-scoped precision mode: 8 rules (read-before-write, verify-before-claim, no API hallucination, etc) for high-stakes work. Inspired by [Maestro](https://github.com/sharpdeveye/maestro) `/zero-defect`.

### 🔒 Hardening Pass (post-cycle audits)

6 audit cycles, 35+ findings closed:

- **Newline injection** scrubbed across epic/story/task/role/memory write paths via shared `safe_single_line` helper.
- **role_create** writes profile FS-first via temp+rename, then DB INSERT — no orphan files on either failure path.
- **role_delete** uses begin_tx/commit_tx (not raw BEGIN) so audit `event_add` honors transaction; cascade-NULLs `tasks.role` on `force=true`.
- **Migration v18** auto-seeds `roles` from `DISTINCT tasks.role` with normalization (lowercase, strip, space→hyphen) and rewrites `tasks.role` in-place — no orphan rows. `v18_seeded` meta flag set in BEGIN IMMEDIATE tx WITH the seed (atomic, idempotent across concurrent inits).
- **Bootstrap rmtree** now uses `onexc=` on Python 3.12+, `onerror=` legacy fallback, with chmod-and-retry for Windows readonly files.
- **Stack scaffold** atomic write retries on Windows `PermissionError` (4×100ms); cleans up `.tmp` on any failure path.
- **Doctor** ASCII fallback (`OK`/`WARN`/`FAIL`) when stdout encoding lacks UTF-8 (Windows cp1251); CRLF normalization in drift compare; pre-svc DB existence captured to surface "never initialized" cases.
- **Activity hook** uses `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` to reduce per-call fsync overhead.
- **session_warn_threshold** clamped to `max(1, …)`.
- **Quality-gate WARN** when scoped-skip fires with no `relevant_files` (visible to user, not silent).
- **MCP handlers** parity: claude+cursor byte-identical for `_handle_stack_scaffold` (catches `ValueError`/`KeyError`).

### 🔐 Independent 6-agent review pass — 31 findings closed

After cycle-6 SHIP verdict, ran a SEPARATE round of 6 parallel independent reviewers (architecture / public API / security / performance / docs / cross-platform). Closed 31 additional findings across waves:

**Security (Wave 1)**
- `git push` gate now uses regex matching `(?:^|[\s;&|()` + variant`])git push\b` — catches `cd && git push`, `(git push)`, `/usr/bin/git push`, `git -c x=y push`. Old token-split bypass eliminated.
- Memory pretool block resolves symlinks/junctions: `os.path.realpath(parent)` after the literal-path check — symlink-into-`~/.claude/**/memory/` is now blocked.
- `TAUSIK_SKIP_HOOKS` no longer disables security gates blanket. Per-hook scoped: `TAUSIK_SKIP_PUSH_HOOK=1` / `TAUSIK_SKIP_MEMORY_HOOK=1`.
- Vendor skill `requires` validated against PEP 508 simple-spec regex; rejects entries starting with `-`. `pip install --` separator added so positional args can't be re-interpreted as flags.

**Data integrity (Wave 2)**
- `brain_project_registry._normalize_path` adds `unicodedata.normalize('NFC', ...)` — fixes macOS HFS+ NFD double-registration.
- `bootstrap_config.save_tausik_config` writes to `*.tmp` then `os.replace` — atomic, SIGINT-safe.

**Truth (Wave 3)**
- README badges and stat lines updated: 35 → 38 skills, 82 → 100 MCP tools, 13 → 19 hooks, 1095 → 2246 tests.
- CLAUDE.md "Команды" section expanded with full top-level command list.

**Performance (Wave 4)**
- `compute_active_minutes` SQL drops `julianday()` from WHERE clause — events `created_at` index now used. ~50× speedup on 100k-row tables.
- `bootstrap copy_dir` byte-compares before write — no-op re-bootstrap is now near-instant on Windows+AV.

**API parity (Wave 5)**
- `--group` → `--story` rename for `task add` (with `--group` deprecated alias for back-compat).
- 4 new MCP tools: `tausik_doctor`, `tausik_verify`, `tausik_stack_reset`, `tausik_stack_export` — close CLI/MCP parity gap.

**Operations (Wave 6-7)**
- File logging: `RotatingFileHandler` at `.tausik/tausik.log` (5MB × 3 backups) for WARNING+. Errors no longer disappear in MCP context.
- CI matrix expanded to `[ubuntu, windows, macos]` × `[3.11, 3.12, 3.13]` — Windows-only bugs caught.
- CI now runs mypy + bandit (warning-only) alongside ruff.

### 🔬 Independent 5-agent blind review hardening pass (pre-ship)

Before tagging 1.3.0 we ran an independent blind review with five parallel
agents (architecture / security / agent UX / documentation truth / quality
gates). 50 findings: 16 HIGH / 21 MED / 13 LOW. The pre-ship pass closes
all HIGH and the most-impactful MED findings — the rest are tracked for
v1.3.x patch releases.

**QG-2 enforcement holes closed**

- **`tausik_task_update status=done` bypass** — the most serious finding.
  A single MCP call could close any task, skipping QG-2, AC verification,
  scoped pytest, cascade, and `call_actual` recording. Now refused with
  explicit `ServiceError` pointing at the lifecycle method (`task_done` /
  `task_start` / `task_block` / `task_review`). The "QG-2 cannot be
  bypassed (--force removed)" claim is now end-to-end true.
- **All-skipped scoped pytest passing as green** — when `relevant_files`
  was supplied but no `tests/test_<basename>.py` matched (source file
  with deleted or missing test), gates returned `passed=True` and QG-2
  closed silently. Now returns synthetic FAIL with
  `status="no-test-mapped"` and a notes line pointing at the missing
  tests.

**Security pattern gaps closed**

- **Brain plaintext leak via `tags`/`stack`/`domain`/`severity`** — only
  named text fields (name/context/decision/rationale) were scrubbed; tags
  arrays passed through verbatim, so `tags=["princess", "kibertum.ru"]`
  would leak the project name into Notion despite the SHA256-hash privacy
  claim. Now ALL string-valued props per category join the scrub haystack.
- **`memory_pretool_block` Linux/macOS bypass via case** — the
  `"memory" in segments` check was case-folded only on Windows.
  `~/.claude/projects/foo/MEMORY/x.md` (uppercase) slipped through on
  every other platform. Now lowercase unconditionally.
- **Security-sensitive token list extended** — `_SECURITY_PATH_TOKENS` and
  `_SECURITY_BASENAMES` now cover `webhook`, `csrf`, `xsrf`, `mfa`, `2fa`,
  `totp`, `api_key`, `apikey`, `permissions`, `acl`, `iam`, `rbac`, `jwt`,
  `oauth`, `session`, `signup`, `login` as bare tokens (match files at
  any depth, not just inside same-named directories).

**Agent UX — RAG discoverability fully closed**

User report: *"Claude grepping over the codebase instead of using our RAG"*.
Root cause was structural — the framework wires `codebase-rag` MCP into
`.mcp.json` but never tells the agent it exists. Closed across four layers:

- **Tool routing rubric in templates** — `bootstrap_templates.py` adds a
  TOOL_ROUTING block with a Need / Primary / Fallback table directing
  agents to `mcp__codebase-rag__search_code` first, `Grep` only as
  fallback. Propagates to all four IDE configs (CLAUDE.md / AGENTS.md /
  .cursorrules / QWEN.md).
- **Skill word swaps** — `agents/skills/zero-defect/SKILL.md` rule 3 and
  `agents/skills/debug/SKILL.md` Phase 0 step 5 previously said "grep
  the codebase" — now point at `search_code` first, with Grep as fallback.
- **`session_start.py` injects RAG status** — agent sees
  `RAG: N chunks indexed` / `RAG: empty — full reindex spawned in
  background` / `RAG: not initialised — reindex spawned` at every new
  session.
- **Auto-incremental reindex** — every SessionStart spawns
  `index_incremental` in a detached background process (returns in
  ~3 ms, never blocks the agent); pre-commit hook runs incremental with
  5-second timeout so committed changes land in the index before the
  next session. First run on a fresh project triggers `index_full`
  automatically. The agent no longer needs to know about `reindex`
  at all.

**Architecture — drift hazard removed**

- **`_FALLBACK_STACK_GATES` (190 LOC) dropped** from `default_gates.py`.
  This was a hardcoded copy of every stack-scoped gate that silently
  activated when `stack_registry` import failed — any change to
  `stacks/<name>/stack.json` would not appear if the registry hiccupped.
  Now: failure logs WARNING and returns empty dict; universal gates
  (filesize, ruff, mypy, bandit, tdd_order) remain hardcoded since
  they're not stack-scoped. File shrinks 290→101 LOC.

**Documentation truth — counts reconciled**

- **MCP tool count** corrected from "106 (96 project + 10 brain)" to the
  actual **100 (90 project + 10 brain)**. The "96" was an aspirational
  number that matched no reality. Updated in 12+ files.
- **Test count** corrected from "2232" / "2226" / "2235" (mixed across
  files) to the empirical **2246** (`pytest --collect-only`).
- **`docs/en/doctor.md`** intro fixed to "eight checks" and the critical
  skills list synced to the actual `project_cli_doctor.py` set:
  `{start, end, task, plan, review, brain, ship, checkpoint}`.

**Filesize gate compliance**

Four modules compacted to stay under the 400-line limit while adding new
guards: `service_task.py` 419→400, `service_verification.py` 413→358,
`brain_mcp_write.py` 437→375, `default_gates.py` 290→101.

**Tests added**

- `tests/test_v131_blind_review.py` — 11 regression tests covering each
  closed finding.
- `tests/test_hud_cli.py` updated to use `be.task_update` for direct
  status manipulation (the QG-2 path the test exercises is meant to
  bypass — now explicit via the backend layer).

**Tracked for v1.3.x patch releases (still open from review):** verify-
cache cross-check against git diff, CLI-into-backend layer cleanup,
6-finding hook hardening batch, 5-finding QG-2 hardening batch, 13 LOW
polish items.

### 📊 Stats
- **2246 tests passing** (1183 → 2246 over the cycle, +11 new from blind-review hardening).
- **100 MCP tools** (90 project + 10 brain), up from 80 in v1.2.0.
- **13 core skills + 25+ official/vendor on demand** — v1.3 lean-core split: workflow primitives auto-deploy, niche/opt-in skills (`/zero-defect`, `/markitdown`, `/skill-test`, `/audit`, `/docs`, ...) install via `tausik skill install <name>`. Up from 29 unconditionally-deployed skills in v1.2.
- **19 hooks** (was 13 — added `activity_event`, `memory_pretool_block`, `memory_posttool_audit`, `brain_post_webfetch`, `brain_search_proactive`, `task_call_counter`).
- **25 stacks** (was 20 — added 5 IaC: ansible, terraform, helm, kubernetes, docker).
- Schema version: 17 → 18 (added `roles`, `session_activity`, `verification_runs` tables).
- 11 new modules (4 service helpers, 3 parser splits, 2 hooks, 1 CLI handler, 1 doctor).

### Compatibility
- No breaking changes. Existing `.tausik/config.json` merges cleanly.
- Re-bootstrap recommended to pull deployed scripts/MCP servers/skills up to date.
- Migration v18 auto-seeds `roles` table from `DISTINCT tasks.role` — no manual setup needed.
- After upgrade the first session sees `RAG: not initialised — full reindex spawned in background` and auto-builds the index.

---

## [1.3.0-detail-stacks] — historical detail (folded into 1.3.0 above)

> Per-story detail of plugin stack architecture work. Shipped as part of v1.3.0 — listed here for archive only.

### Added — Stack plugin foundation (Story 1, plugin-foundation)

- **`stacks/_schema.json`** — JSON Schema (Draft-07) for stack declarations. Fields: `name` (required), `version`, `extends` (`builtin:NAME`), `detect` (list of `{file,type,keyword}` with `type ∈ exact|glob|dir-marker`), `extensions`, `filenames`, `path_hints`, `gates` (with `null` to disable), `guide_path`, `extensions_extra` (additive merge).
- **`scripts/stack_schema.py`** — `validate_decl(decl, source) -> list[str]` returns actionable errors per offending field; never silently skips. 12 edge-cases covered via smoke harness.
- **`scripts/stack_registry.py`** — `StackRegistry` class with `load_builtin`/`load_user`/`reload`, layered deep-merge (extensions_extra additive, gates per-key override + null disable), and accessors `signatures_for`/`extensions_for`/`filenames_for`/`path_hints_for`/`gates_for`/`guide_path_for`. Source tracking: `source_for(name)` returns `'builtin'|'user'|'overridden'|None`; `is_user_overridden(name)` for user-override detection.
- **`tests/test_stack_registry.py`** — 27 tests across `TestLoadBuiltin`, `TestUserOverrides`, `TestReload`, `TestAccessors`, `TestSourceTracking`.

### Added — 25 built-in stacks migrated to plugin layout (Story 2, migrate-builtins)

Each stack is now `stacks/<name>/{stack.json, guide.md}`. Source of truth shifted from 5 hardcoded modules to a single declarative file.

- **Python family** ([stacks/python/](stacks/python/), fastapi, django, flask) — pytest gate owns stacks=[python,fastapi,django,flask].
- **Frontend** (react, next, vue, nuxt, svelte, typescript, javascript) — typescript owns `tsc`; javascript owns `eslint`+`js-test`. Both gates list all 6 frontend frameworks in `stacks` field.
- **Native** (go, rust, java, kotlin, swift, flutter) — go owns `go-vet`+`golangci-lint`+`go-test`; rust owns `cargo-check`+`clippy`+`cargo-test`; java owns `javac`; kotlin owns `ktlint`.
- **PHP family** (php, laravel, blade) — php owns `phpstan`+`phpcs`+`phpunit`; blade extension `.blade.php` is union'd with `.php` stacks via compound-extension logic in dispatch.
- **IaC** (ansible, terraform, helm, kubernetes, docker) — each stack owns its lint gate (ansible-lint / terraform-validate / helm-lint / kubeval / hadolint). All three detect forms exercised: `exact` (Dockerfile, Chart.yaml), `glob` (`*.tf`), `dir-marker` (playbooks/, roles/, k8s/, manifests/, .kube/).
- **`agents/stacks/*.md`** removed; legacy fallback in bootstrap still finds these for partial-migration repos.

### Changed — 6 consumers refactored to use the registry (Story 3, refactor-consumers)

Hardcoded data moved to defensive registry lookups with hardcoded fallbacks for boot safety.

- **[scripts/project_types.py](scripts/project_types.py)** — `DEFAULT_STACKS` now computed from `default_registry().all_stacks()`; `_FALLBACK_STACKS` retains the pre-plugin hardcoded set. `VALID_STACKS` remains an alias for back-compat.
- **[bootstrap/bootstrap_config.py](bootstrap/bootstrap_config.py)** — `STACK_SIGNATURES` built via `_load_stack_signatures()`. Each registry `{file, type, keyword}` entry is rendered to the `(filename, keyword)` tuple form `_signature_match()` understands; `dir-marker` types get the trailing `/` they need.
- **[scripts/gate_stack_dispatch.py](scripts/gate_stack_dispatch.py)** — `_EXT_TO_STACKS`, `_FILENAME_TO_STACKS`, `_PATH_HINTS` invert per-stack registry data via `_build_dispatch_tables()`. Compound `.blade.php` keeps its `.blade.php ∪ .php` semantics.
- **[scripts/default_gates.py](scripts/default_gates.py)** — split into `UNIVERSAL_GATES` (5 hardcoded: filesize, tdd_order, ruff, mypy, bandit) ∪ `_build_stack_scoped_gates()` (20 from registry). Gate ownership lives in each `stacks/<name>/stack.json`; first-stack-wins for duplicate names (alphabetical iteration). `DEFAULT_GATES` is the merged total — consumers untouched.
- **[scripts/project_config.py](scripts/project_config.py)** — `STACK_GATE_MAP` is registry-derived transitively via DEFAULT_GATES; no code change needed.
- **[agents/{claude,cursor}/mcp/project/tools.py](agents/claude/mcp/project/tools.py)** — 4 inline JSON-Schema stack enums replaced by `_STACKS_ENUM` constant under fenced `# === BEGIN/END STACKS_ENUM ===` markers. Bootstrap regenerates the constant from the registry via `bootstrap_stacks.regenerate_mcp_stack_enums()`. Also adds the 5 IaC stacks (ansible, terraform, helm, kubernetes, docker) which were missing from the legacy hardcoded list.

### Added — User customization layer (Story 4, user-customization)

- **`.tausik/stacks/<name>/`** is a first-class layered registry. `extends: "builtin:NAME"` deep-merges over a built-in entry; missing `extends` with a known name is full replace; new names are standalone stacks. `null` gate value disables an inherited gate. `extensions_extra` is additive.
- **`bootstrap/bootstrap_stacks.py`** — extracted `copy_stacks` and added `regenerate_mcp_stack_enums()`. Bootstrap NEVER writes inside `.tausik/`; **`tests/test_bootstrap_non_destructive.py`** asserts this with 5 cases (override-untouched, override-of-builtin-name-untouched, target-isolation, no-`.tausik`-paths-written, idempotent across runs).
- **CLI: `tausik stack {export,diff,reset,lint}`** ([scripts/project_cli_stack.py](scripts/project_cli_stack.py)) — `export` prints the resolved decl; `diff` shows unified diff between built-in and user override; `reset` removes `.tausik/stacks/<name>/` (with `--yes`); `lint` validates every user override against the schema. `info` and `list` retain previous behaviour.
- **Bootstrap printout** — surfaces `.tausik/stacks/` overrides on every run; first-time users see a guidance line directing customization to the safe path.

### Added — Documentation (Story 5, documentation-overhaul)

- **[docs/en/stacks.md](docs/en/stacks.md)** — plugin layout, schema reference, adding new stacks, registry consumer table.
- **[docs/en/customization.md](docs/en/customization.md)** — override rules, merge semantics, validation tools, do/don't list.
- **[docs/en/upgrade.md](docs/en/upgrade.md)** — bootstrap-owned vs user-owned tree, upgrade workflow, breakage scenarios + recovery.
- CLAUDE.md QG-2 description amended for scoped-skip behaviour and `.tausik/stacks/` invariant.

### Fixed — pytest gate scoped-skip (defect of stack-schema-design)

- **Scoped pytest gate must skip, not fall back to full suite** ([scripts/gate_runner.py](scripts/gate_runner.py)) — Previously, when `relevant_files` was non-empty but `resolve_test_files_for_relevant()` returned no matches (e.g. a brand-new module without `tests/test_<basename>.py` yet), the gate substituted `tests/` and ran the **entire** 900+ test suite as a "regression-safe fallback". This silently turned every `task_done` on a new module into a 60s+ wait and defeated the scoping promise in CLAUDE.md ("гонит только `tests/test_<basename>.py` для каждого relevant_files"). Fix: introduced `_SCOPED_SKIP_SENTINEL` returned by `run_command_gate` when scoped resolution fails; `run_gates` translates it to a `skipped=True` result with message `"No test file maps to relevant_files via tests/test_<basename>.py heuristic; gate skipped (scoped run)."`. Empty `relevant_files` (no scoping data at all) still falls back to the full suite — that path is regression-safe and unchanged. (`pytest-gate-must-skip-when-scoped-relevant-files-h`)

### Test Coverage — pytest gate scoped-skip

- **3 new + 1 rewritten** in [tests/test_gates.py](tests/test_gates.py) class `TestPytestGateScopeSubstitution`: `test_scoped_run_with_no_test_mapping_skips` asserts the sentinel is returned and `subprocess.run` is **not** invoked; `test_unscoped_call_falls_back_to_full_suite` covers the empty-relevant_files path; `test_run_gates_translates_scoped_skip_into_skipped_result` verifies end-to-end conversion to `skipped=True` result entries.

### Added — Backlog finish (4 final planning tasks)

Last 4 planning tasks shipped — backlog drained to **388/388 done** (100%):

- **Brain status CLI + skill** ([scripts/brain_status.py](scripts/brain_status.py), [agents/skills/brain/SKILL.md](agents/skills/brain/SKILL.md)) — `tausik brain status [--json]` снапшот состояния brain: enabled, mirror path/size/last-modified, per-category row counts + last_pull_at + last_error from `sync_state`, registered projects (name/canonical/hash), last web_cache write. `collect_status()` graceful: missing mirror / unreadable config / empty registry → consistent dict с `error` field, без crash. Skill SKILL.md документирует. (`brain-skill-status`)
- **Brain move CLI + skill** ([scripts/brain_move.py](scripts/brain_move.py)) — `tausik brain move <id> --to-brain --kind <decision|pattern|gotcha>` или `--to-local --category <decisions|patterns|gotchas>`. Cross-project ownership check (source_project_hash должен совпадать с current project's hash; `--force` override). Web_cache → refused (no local counterpart). На to-local после успеха: archive Notion page (`pages.update(archived=true)`) + delete from mirror, unless `--keep-source`. Story `brain-tausik-integration` + epic `shared-brain` auto-closed. (`brain-skill-move`)
- **Anthropic OSS research** ([references/anthropic-oss-applicability.md](references/anthropic-oss-applicability.md)) — Surveyed 7 наиболее релевантных Anthropic OSS репозиториев (knowledge-work-plugins, anthropic-cli, agent-sdk-workshop, original_performance_takehome, skills, claude-code-action, financial-services-plugins). Identified 9 applicable patterns (5 simple, 3 medium, 1 complex). Top 3 recommended next tasks: `tausik-skill-manifest` (skill.yaml registry), `tausik-metrics-tiers` (bronze/silver/gold/platinum), `tausik-brain-swappable-backend` (decouple from Notion). (`research-anthropic-repos`)
- **markitdown opt-in integration** ([scripts/doc_extract.py](scripts/doc_extract.py), [agents/skills/markitdown/SKILL.md](agents/skills/markitdown/SKILL.md), [references/markitdown-integration.md](references/markitdown-integration.md)) — Discovery: TAUSIK не имел "ручных парсеров документов" — pdf/excel skills делегируют Claude Code `Read` tool. markitdown добавлен как **opt-in** capability (convention #19 zero-deps сохранён): lazy import + graceful `None` если не установлен. CLI `tausik doc extract <file>` + Python API `extract_to_markdown(path)`. Когда использовать: DOCX/PPTX/XLSX/HTML/EPUB. PDF redirect → `/pdf` skill. Future hook: `brain_post_webfetch` мог бы использовать для HTML conversion (noted, not implemented). (`markitdown-integration`)

### Test Coverage — Backlog finish

- **+39 tests** — `test_brain_status.py` (9 tests: disabled, config_load_error, missing_mirror, enabled_empty/with_data, registered_projects, registry_missing, format_status×2), `test_brain_move.py` (19 tests: TestMoveToBrain×10 включая happy paths + scrub_blocked + notion_error + token_missing + brain_disabled + bad_input + not_found + keep_source; TestMoveToLocal×8 включая cross-project ownership × force, web_cache refused, mirror archive), `test_doc_extract.py` (11 tests + 1 skipif integration: is_available, happy path, format_hint, falls_back_to_markdown_attr, missing markitdown/path/empty/exception/unexpected shape).

### Fixed — Review findings MED/LOW (story review-findings-mlow-fix, 11 issues)

Follow-up to the 5 HIGH fixes — 11 MEDIUM/LOW findings from the same multi-agent review:

- **A7 MED** ([scripts/gate_runner.py](scripts/gate_runner.py) `resolve_test_files_for_relevant`) — Resolver теперь использует `os.walk(tests/)` вместо `os.listdir`. Tests в nested dirs (`tests/integration/`, `tests/unit/scoped/`) корректно матчатся вместо silent fallback на full suite. Single-pass index by basename, дедуп между путями. (`review-mlow-resolver-recursive`)
- **B6+B7 MED** ([scripts/brain_schema.py](scripts/brain_schema.py) `_migrate`) — Добавлен `PRAGMA foreign_keys=OFF/ON` envelope (insurance для будущих FK-touching migrations) + `PRAGMA foreign_key_check` после COMMIT (raise on violations). Docstring документирует irreversibility контракт ("failed batch only rolls back current; previously committed migrations stay applied"). (`review-mlow-brain-safety`)
- **B2 MED** ([scripts/brain_project_registry.py](scripts/brain_project_registry.py) `_acquire_lock`) — Docstring документирует "single reclaim per call (reclaimed flag)" контракт + acknowledge небольшой TOCTOU window между `_is_stale_lock` и `os.unlink`. (`review-mlow-brain-safety`)
- **A5 LOW** ([scripts/service_verification.py](scripts/service_verification.py) `run_gates_with_cache`) — `append_notes_fn` теперь типизирован `Callable[[str, str], None] | None` (был `Any`). (`review-mlow-polish-batch`)
- **A6 LOW** ([scripts/project_cli_verify.py](scripts/project_cli_verify.py) `cmd_verify`) — На cache HIT пишется `events` row `action='verify_cache_hit'` для telemetry. Best-effort try/except — никогда не блокирует verify. (`review-mlow-polish-batch`)
- **B4 LOW** ([scripts/brain_init.py](scripts/brain_init.py) `create_brain_databases`) — Per-category try/except. Новый `PartialCreateError(NotionError)` с `created_ids` attribute — partial-create surface'ит реально-созданные ids в orphan-cleanup guidance вместо `<missing>`. (`review-mlow-polish-batch`)
- **B5 LOW** ([scripts/brain_init.py](scripts/brain_init.py) `CliIO.prompt`) — EOF/KeyboardInterrupt branches: `KeyboardInterrupt` → "Aborted by user (Ctrl+C)", `EOFError` → "Aborted: no input available (stdin closed/piped)". Раньше — общее "Aborted by user" вне зависимости от типа. (`review-mlow-polish-batch`)
- **C-L3 LOW** ([tests/test_brain_notion_client.py](tests/test_brain_notion_client.py) `test_token_not_in_retry_log`) — Добавлен `assert len(caplog.records) >= 1` чтобы поймать silent-pass на пустом caplog (дрейф logger config). (`review-mlow-polish-batch`)
- **A2 docstring** ([scripts/service_verification.py](scripts/service_verification.py) `run_gates_with_cache`) — Concurrency note: "WAL safe but duplicate rows accepted; BEGIN IMMEDIATE worse" — accepted limitation. (`review-mlow-polish-batch`)
- **A3 docstring** ([scripts/service_verification.py](scripts/service_verification.py) `compute_files_hash`) — mtime resolution caveat: NTFS 100ns / ext4 1μs / HFS+ 1s / FAT 2s — false cache hits possible на быстрых правках на FAT/HFS+, recommendation для таких FS. (`review-mlow-polish-batch`)

### Test Coverage — Review fixes

- **+8 hardening tests** — `test_gates.py` (+4 TestResolveTestFilesForRelevant: glob_subdirectory_test_files, glob_subdirectory_with_suffix_variants, dedup_when_test_appears_in_multiple_dirs, missing_tests_dir_returns_empty), `test_brain_init.py` (+3 partial create + EOF distinct messages), `test_brain_notion_client.py` (+1 caplog non-empty assertion).

### Fixed — Review findings (story review-findings-fix, 5 HIGH issues)

Multi-agent review caught 5 HIGH-severity findings post-merge of the SENAR verify redesign + hooks widening; addressed in this batch:

- **C1** ([scripts/hooks/memory_pretool_block.py](scripts/hooks/memory_pretool_block.py)) — Memory guard regression: `~/.claude/projects/abc/memory` (directory-form path, no trailing file) больше НЕ блокировался. `os.path.normpath` срезает trailing slash, потом `[:-1]` slice исключает `'memory'` из проверки. Старый guard `rest[1] == 'memory'` это ловил. Fix: `'memory' in segments` без `[:-1]` — basename `memory.md` всё ещё False (segment exact compare), но bare `memory` ловится. (`review-fix-c1-memory-guard-dir`)
- **A9** ([scripts/service_gates.py](scripts/service_gates.py) `_run_quality_gates`) — Tier mapping регрессия: scope hardcoded в `'lightweight'` для ВСЕХ задач. Нарушал SENAR Rule 5 — auditor querying `verification_runs WHERE scope='critical'` получал 0 строк. Fix: scope резолвится через `_determine_checklist_tier(task)` (simple→lightweight, medium→standard, complex→high), `is_security_sensitive(relevant_files)` override → `'critical'`. (`review-fix-a9-tier-mapping`)
- **A4** ([scripts/service_verification.py](scripts/service_verification.py)) — Security bypass дыры: `auth.py`/`payment.py`/`billing.py` в корне НЕ матчатся (требовало `/auth/` со слэшами). Также не покрыты oauth/sso/saml/crypto/secrets/keys/admin/rbac/webhook/jwt/session/2fa/mfa/signup/login/password. `.env`/`.pem`/`.key`/`.p12`/`.pfx`/`.crt`/`.asc`/`.gpg` extensions тоже игнорировались. Fix: `_SECURITY_PATH_TOKENS` расширен +16 tokens; новые `_SECURITY_BASENAMES` frozenset для root-level `*.py/.ts/.go`; новый `_SECURITY_EXTENSIONS` frozenset; `is_security_sensitive` объединяет 3 проверки. (`review-fix-a4-security-bypass-tokens`)
- **A1** ([scripts/service_verification.py](scripts/service_verification.py), [scripts/project_cli_verify.py](scripts/project_cli_verify.py)) — Cache key не включал резолвенный gate command. Изменение `project_config.DEFAULT_GATES['pytest']['command']` оставляло старые зелёные runs валидными → стейл-кэш с НОВОЙ командой. Fix: новый `resolve_gate_signature(trigger)` — sha256 over sorted gate name+command+severity tuples, 16-char hex; `cache_command` теперь `f'trigger=task-done|sig={sig}|files=...'`. На load_config failure → fallback `'unavailable'` (не блокирует verification). (`review-fix-a1-cache-key-includes-cmd`)
- **H2** ([tests/test_service_verification.py](tests/test_service_verification.py)) — Integration test gap: `run_gates_with_cache` (главный orchestrator) тестировался только через примитивы. Регрессия в `cache_command` formatting прошла бы незаметно. Fix: новая `TestRunGatesWithCacheIntegration` с 6 end-to-end сценариями (miss-then-hit, security bypass, mtime invalidation, red run, append_notes на hit/miss). (`review-fix-h2-cache-integration-test`)

### Added — SENAR verify redesign (epic senar-verify-redesign)

- **Scoped per-task pytest gate** ([scripts/gate_runner.py](scripts/gate_runner.py), [scripts/project_config.py](scripts/project_config.py)) — новый `{test_files_for_files}` substitution + `resolve_test_files_for_relevant(relevant_files)` (basename heuristic + glob `tests/test_<stem>_*.py` варианты + test-file passthrough). Default pytest gate command изменён на `pytest -x -q {test_files_for_files}`. Без `relevant_files` substitution выдаёт `tests/` — fallback на полный suite (regression-safe). Раньше: full pytest на каждом `task done` (~3 мин), что нарушало SENAR Rule 5 tiering и делало Rule 9.5 audit redundant. Теперь: scoped по relevant_files задачи (`senar-verify-tiered`, Phase 1) — Pytest gate теперь scoped, не full suite
- **Verification cache (verification_runs table + lookup)** ([scripts/service_verification.py](scripts/service_verification.py), schema v16) — `compute_files_hash` (SHA256 over canonical path + mtime_ns + size, sorted), `record_run`, `lookup_recent_for_task` (misses on red/files_hash mismatch/command mismatch/stale ≥10 мин), `is_security_sensitive` (hooks/, /auth/, /payment/, /payments/, /billing/ → cache disabled). `service_gates._run_quality_gates` теперь делает lookup до запуска gates — cache hit пропускает их + лог в notes "Gates: cache hit (verify run #X)". Security-sensitive файлы всегда re-verify, не доверяем cache (`senar-verify-tiered`, Phase 2) — Cache reuse: повторный task done на тех же файлах в окне 10 мин — мгновенно
- **`tausik verify` CLI** ([scripts/project_parser.py](scripts/project_parser.py), [scripts/project_cli_extra.py](scripts/project_cli_extra.py)) — `tausik verify [--task slug] [--scope {lightweight,standard,high,critical,manual}]` запускает gates scoped к relevant_files задачи (или unscoped) и записывает результат в `verification_runs`. Полезно для ad-hoc проверки в середине работы (`senar-verify-tiered`, Phase 2) — Ad-hoc verify CLI с записью в кэш
- **CLAUDE.md QG-2/Rule 5 переписаны** — раздел "QG-2 Implementation Gate" (`Ограничения`) явно описывает scoped pytest + cache window + security bypass; раздел "Rule 5 Verification Checklist" в SENAR Compliance таблице обновлён с упоминанием scope-by-relevant_files; Архитектура секция добавляет `service_verification.py` к Gates слою (`senar-verify-tiered`, Phase 3) — Документация QG-2 отражает новый scoped + cache flow

### Test Coverage — SENAR verify

- **+30 unit tests** в `test_service_verification.py` — `compute_files_hash` (empty, none, mtime change, order-independent, missing sentinel, file appearance, skip non-string), `is_security_sensitive` (5 positive paths, 4 negative, empty/none, any-match), `record_run` + `lookup_recent_for_task` (hit, no-runs, files_hash mismatch, command mismatch, red run, stale, takes most recent, empty slug), `is_cache_allowed` (safe/security/empty)
- **+13 unit tests** в `test_gates.py` — `TestResolveTestFilesForRelevant` (empty, basename match, glob suffixes, no match, test-file passthrough, dedup, nonexistent paths, non-string entries, Windows backslash) + `TestPytestGateScopeSubstitution` (substitution uses mapped tests, falls back to full suite, default uses new substitution token)

## [1.3.0-detail-brain] — historical detail (folded into 1.3.0 above)

> Per-story detail of Shared Brain work. Shipped as part of v1.3.0 — listed here for archive only.

Cross-project knowledge layer backed by Notion, complementing the per-project `.tausik/tausik.db`. Only knowledge flagged as *generalizable* reaches the brain; project-specific traces stay local. Read-path fully implemented and offline-tested end-to-end; write-path and MCP tooling are the next story. 6 tasks done from epic `shared-brain` / 22 total. Кросс-проектный слой знаний на базе Notion.

### Added / Добавлено

- **Design doc** ([references/brain-db-schema.md](references/brain-db-schema.md)) — full spec of 4 Notion databases (`decisions`, `web_cache`, `patterns`, `gotchas`): property types + obligation, JSON `pages.create` payload for each, delta-pull mechanics (`last_edited_time` high-water mark), rate-limit handling, 7 trade-offs discussed, 8 negative-scenario fallbacks, privacy model (`SHA256(project_name_canonical)[:16]`) — Design-doc, без которого остальные задачи бы плавали
- **Local SQLite mirror** ([scripts/brain_schema.py](scripts/brain_schema.py)) — 4 tables mirroring Notion properties 1:1, FTS5 virtual tables with `unicode61 remove_diacritics 2` tokenizer (Cyrillic works), AI/AD/AU triggers per table, CHECK constraints for `generalizable` / `confidence` / `severity` / `sync_state.category`, 13 indexes covering delta-pull and dedup hot paths — Локальное FTS5-зеркало с поддержкой кириллицы
- **Brain config section** ([scripts/brain_config.py](scripts/brain_config.py)) — `DEFAULT_BRAIN` with safe defaults (enabled=false, mirror path, token env name, empty db-ids), `load_brain` / `is_brain_enabled` / `validate_brain` (returns error list, strict only when enabled=true) / `get_brain_mirror_path` (expands `~` and `$ENV`) / `compute_project_hash` (canonicalize then SHA256[:16]). Token is never stored in config — only the env-var name — Секция конфига с приватностью
- **Notion REST client** ([scripts/brain_notion_client.py](scripts/brain_notion_client.py)) — stdlib-only (urllib + http), zero external deps. Public API: `pages_create` / `pages_retrieve` / `pages_update` / `databases_query` / `iter_database_query` (auto-pagination iterator) / `search`. Write-side throttle 350 ms, 429/5xx retry with `Retry-After` and exponential backoff (2^n ± 20% jitter, cap 30 s), auth/not-found bypass retry, injected `urlopen`/`clock`/`sleep` for deterministic tests — REST-клиент без внешних зависимостей
- **Pull-sync engine** ([scripts/brain_sync.py](scripts/brain_sync.py)) — `open_brain_db` (creates parent dir, applies schema), per-category mapper (Notion `title`/`rich_text`/`multi_select`/`select`/`date`/`checkbox`/`url`/`number` → SQLite columns), `upsert_page` (INSERT OR REPLACE by `notion_page_id`), `sync_category` (delta filter by `last_pull_at`, ascending sort, advances high-water mark, records `last_error` on failure and re-raises), `sync_all` (continues after a single-category failure) — Делта-синк Notion → local
- **Local FTS5 search** ([scripts/brain_search.py](scripts/brain_search.py)) — `sanitize_fts_query` (neutralizes FTS5 operators via phrase-quoting; escapes inner `"` as `""`), `search_local` (bm25 ranking, global sort across 4 categories, `limit`/`offset`, category filter), `get_by_id` (exact lookup), SQL `snippet()` with `[...]` markers — Быстрый поиск по локальному зеркалу
- **Docs** — EN [docs/en/shared-brain.md](docs/en/shared-brain.md) and RU [docs/ru/shared-brain.md](docs/ru/shared-brain.md): philosophy (generalizable only), ASCII architecture diagram, manual setup steps (parent page → 4 databases → integration → token env → config → smoke-test), privacy contract, 7-row edge-cases table covering revoked token / rate-limit / offline / oversized content / scrubbing miss / schema drift / hash collision. README EN/RU have a short "Shared Brain" section linking to docs — Документация EN/RU + секции в README
- **PostToolUse WebFetch auto-cache hook** ([scripts/hooks/brain_post_webfetch.py](scripts/hooks/brain_post_webfetch.py)) — парный к PreToolUse `brain_search_proactive`: каждый успешный `WebFetch` автоматически уходит в `brain_web_cache` через `brain_mcp_write.store_record`, так что следующий fetch того же URL блокируется читающим хуком. Non-blocking (exit 0); пропускает приватные URL (`brain.private_url_patterns`), HTTP ≥ 400, пустые ответы, уже-свежие URL в зеркале, использует `response.url` вместо `input.url` после редиректа, обрезает content по 200 KB и stdin по 1 MiB. Scrubbing-блоки (private_urls / project_names_blocklist) тихо скипятся — это ожидаемое поведение, а не баг. Диагностика через `TAUSIK_BRAIN_HOOK_DEBUG=1`. `WebSearch` намеренно не кэшируется: в ответе несколько URL в одном блобе, нет канонического ключа; поисковые запросы обслуживаются FTS5 по контенту, записанному через `WebFetch` — PostToolUse хук для auto-cache web результатов
- **Brain runtime write helper** ([scripts/brain_runtime.py](scripts/brain_runtime.py)) — `try_brain_write_web_cache(url, content, cfg, *, query, title)` повторяет контракт `try_brain_write_decision`: `(True, page_id)` на `ok`/`ok_not_mirrored`, `(False, reason)` на token missing / scrub block / notion error / exception. Используется хуком и будущими callers (brain-skill-ui). Также выделен shared `_format_scrub_detectors` — surface только detector names, никогда raw `match` — Раннтайм-хелпер записи web_cache
- **Shared brain-hook utilities** ([scripts/brain_hook_utils.py](scripts/brain_hook_utils.py)) — `parse_iso_to_epoch`, `lookup_exact_url`, `is_fresh` вынесены из `brain_search_proactive.py`, чтобы пара Pre+Post хуков WebFetch делила одну реализацию mirror-lookup и TTL-семантики. `lookup_exact_url` корректно разбирает смешанные ISO-форматы (`Z` vs `.000Z`) — сортирует по parsed epoch, а не лексикографически по TEXT — Общие хелперы для brain-хуков
- **Hook registration** — `bootstrap_generate.py` регистрирует `brain_post_webfetch.py` на PostToolUse с matcher=`WebFetch`, timeout=10s. PreToolUse matcher `WebSearch|WebFetch` остался за `brain_search_proactive.py` — Регистрация в bootstrap
- **`/brain` skill** ([agents/skills/brain/SKILL.md](agents/skills/brain/SKILL.md)) — conversational UI над brain MCP tools: `/brain query <text>` → `brain_search`, `/brain store <type> <text>` → `tausik decide` или `brain_store_*`, `/brain show <id> <category>` → `brain_get`. Документирует bypass-маркеры (`refresh: web_cache`, `confirm: cross-project`), поведение при disabled brain, правила scrubbing. Не изобретает tool names — каждая подкоманда мапится на существующий MCP tool или CLI. `move` и `status` подкоманды вынесены в follow-up tasks `brain-skill-move` + `brain-skill-status` (нужны новые backend'ы) — `/brain` skill для query/store/show
- **`brain_runtime.open_brain_deps()`** ([scripts/brain_runtime.py](scripts/brain_runtime.py)) — shared `(conn, client, cfg)` primitive с None-семантикой: `(None, None, cfg)` если brain disabled, `(conn, None, cfg)` если token env unset, `(conn, client, cfg)` happy path. Fold: `_open_deps` + `_build_client` удалены из `agents/claude/mcp/brain/handlers.py` и `agents/cursor/mcp/brain/handlers.py` — оба импортируют из brain_runtime. Устраняет дубликат ~20 строк × 2 файла. Также добавлен `_FAST_FALLBACK_TIMEOUT = 5.0` как shared константа — Общий helper setup'а brain-зависимостей

### Fixed / Исправлено — Storage hardening batch

Пакет из 6 MED-исправлений в `brain_sync` + `brain_config` + `brain_runtime`, найденных при review2:

- **WAL mode** ([scripts/brain_sync.py](scripts/brain_sync.py) `open_brain_db`) — `PRAGMA journal_mode=WAL` сразу после connect, перед `apply_schema`. Устраняет SQLITE_BUSY между concurrent sync'ом и MCP read'ом на одном mirror'е. WAL — best-effort: `:memory:` / read-only FS / сетевые диски silently откатываются к default rollback journal, не raise (`brain-schema-wal-mode`) — WAL для параллельного чтения и записи
- **ISO timestamp compare** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — max_edited вычисляется через `_iso_epoch` (parsed UTC seconds), не лексикографически. Исправлен баг: `"...10:00:00Z"` > `"...10:00:00.000Z"` в ASCII-сравнении, но это ТОТ ЖЕ момент. Без фикса cursor мог регрессировать, если в батче смешаны форматы. Использует `brain_hook_utils.parse_iso_to_epoch` (shared с brain-search-proactive) (`brain-sync-iso-timestamp-compare`) — Корректный temporal compare смешанных ISO-форматов
- **Single-transaction atomicity** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — success path: один `conn.commit()` после всех upsert'ов и cursor-update'а. Error path: `conn.rollback()` снимает partial upsert'ы, затем отдельная best-effort tx пишет `last_error` в `sync_state`. Раньше было 2 commit'а в except-ветке — partial state при падении между ними (`brain-sync-transaction-atomicity`) — Атомарная single-tx sync-операция
- **Strict `after` cursor filter** ([scripts/brain_sync.py](scripts/brain_sync.py) `_make_filter`) — `{"last_edited_time": {"after": cursor}}` вместо `on_or_after`. Boundary-страница (edited == cursor) больше не re-fetches на каждом sync'е (`brain-sync-cursor-advance`) — Исключение boundary re-fetch
- **NFC normalization** ([scripts/brain_config.py](scripts/brain_config.py) `compute_project_hash`) — `unicodedata.normalize("NFC", name)` перед canonicalize/hash. Фикс: precomposed é (U+00E9) и decomposed e+U+0301 давали разные project_hash → двойная регистрация одного проекта (`brain-config-unicode-nfc`) — Единый hash для NFC и NFD имён
- **Mirror-path contract** ([scripts/brain_runtime.py](scripts/brain_runtime.py) `try_brain_write_*`) — оба wrapper'а теперь зовут `get_brain_mirror_path()` без аргумента. Раньше передавали уже-merged brain dict → `load_brain(merged).get("brain", {})` = `{}` → user's `local_mirror_path` silently отбрасывался, использовался DEFAULT. Regression-тесты с patched `load_config` + captured `open_brain_db` arg (`brain-config-mirror-path-contract`) — Пользовательский mirror path больше не теряется

### Changed / Изменено

- **brain_sync split** — Notion property readers + per-category mappers (`_concat_text`, `_read_prop`, `_prop_*`, `map_decision` / `map_web_cache` / `map_pattern` / `map_gotcha` + `MAPPERS_BY_CATEGORY`) вынесены в новый [scripts/brain_notion_props.py](scripts/brain_notion_props.py) (~142 lines). `brain_sync.py` сократился до 328 lines — под 400-line filesize gate. `map_page_to_row` остался в brain_sync как dispatcher — Выделение Notion parsers в отдельный модуль

### Fixed / Исправлено — review3 pass

4 findings from the third defensive review pass on commits af0a156 / 4a24c1a / 2e56a64:

- **[M1] `get_brain_mirror_path` shape detection** ([scripts/brain_config.py](scripts/brain_config.py)) — функция теперь принимает три формы: `None` (consults load_config), top-level `{"brain": {...}}`, и already-merged brain dict `{"enabled": ..., "local_mirror_path": ...}`. Детектит merged по отсутствию ключа `"brain"` + наличию любого из merged-shape маркеров (`enabled` / `local_mirror_path` / `database_ids`). Устраняет footgun: предыдущий фикс в `brain_runtime.try_brain_write_*` обходил баг через `get_brain_mirror_path()` без аргумента, но сама функция оставалась миной для будущих callers. Regression-тесты для обеих shapes — Контракт функции поддерживает обе shape
- **[M1 docs] docs/en|ru/shared-brain.md** — smoke-test snippet упрощён: `load_brain()` + `validate_brain()` + `get_brain_mirror_path()` все без аргументов, плюс параграф про три поддерживаемые формы входа — Документация смоук-теста без ambiguous cfg
- **[M2] Hoisted import** ([scripts/brain_sync.py](scripts/brain_sync.py)) — `from brain_hook_utils import parse_iso_to_epoch` на module scope. Раньше импорт был внутри `_iso_epoch` (вызывается per-page в sync loop) — per-call attribute lookup на холодном sync'е тысяч страниц — Импорт вынесен из hot loop
- **[L1] auto-BEGIN invariant comment** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — inline-комментарий фиксирует инвариант: `conn.rollback()` в except-ветке полагается на implicit BEGIN от первого `upsert_page`. Если рефакторинг добавит DML раньше в `_get_sync_state`, rollback boundary изменится — Комментарий защищает rollback-инвариант
- **[L2] Dead test удалён** ([tests/test_brain_storage_hardening.py](tests/test_brain_storage_hardening.py)) — `test_memory_db_falls_back_silently` не вызывал `open_brain_db`, тестировал поведение sqlite3 напрямую. `test_wal_failure_does_not_raise` покрывает настоящий контракт — Лишний тест сняли

### Added — MCP write/read hardening batch

- **Token-missing warning in MCP read handlers** ([agents/{claude,cursor}/mcp/brain/handlers.py](agents/claude/mcp/brain/handlers.py)) — `handle_brain_search` и `handle_brain_get` теперь явно сигналят пользователю когда `cfg.enabled=true` но `client=None` (token env unset): инжектят warning с именем env-переменной из `cfg.notion_integration_token_env` в первый слот `result.warnings`. Раньше handler молча пропускал Notion fallback — пользователь не отличал offline от no-token. Generic fallback текст когда `notion_integration_token_env` отсутствует/пуст. Disabled brain не получает warning (status quo) (`brain-mcp-token-missing-warning`) — Явный warning о ненастроенном токене вместо тихого пропуска

### Fixed — MCP write/read hardening batch

- **Dead category-fallback removed** ([scripts/brain_mcp_write.py](scripts/brain_mcp_write.py) `format_store_result`) — `cat = result.get("error_category") or result.get("category") or "unknown"` упрощено до `result.get("error_category") or "unknown"`. `store_record` пишет только `error_category` — мёртвая ветка скрывала бы будущие typos (`brain-mcp-write-dead-code-cleanup`) — Убрана defensive ветка, скрывавшая typos

### Changed — Hooks widening batch

- **Memory-block guard расширен на .claude/\*\*/memory/** ([scripts/hooks/memory_pretool_block.py](scripts/hooks/memory_pretool_block.py)) — `_is_in_claude_memory` теперь матчит любой `memory` сегмент под `~/.claude/`, а не только `projects/<slug>/memory/`. Silently-unguarded paths (`~/.claude/memory/`, `~/.claude/agents/<name>/memory/`, `~/.claude/plugins/.../memory/`) теперь блокируются. `memory_posttool_audit` расширяется автоматически (импортирует `is_in_claude_memory`). BLOCKED stderr обновлён. Файл с именем `memory.md` (не под директорией `memory/`) не блокируется. Substring `somememory/` / `memoryold/` тоже не ложноблокируются (`hooks-pretool-block-path-patterns`) — Гвард памяти теперь ловит все поддиректории memory под .claude/
- **Slug regex расширен с {2,} до {1,}** ([scripts/hooks/memory_markers.py](scripts/hooks/memory_markers.py)) — `_SLUG_RE` ловит 2-сегментные slug'и (`my-app`, `brain-init`, `hystolab-ru`), но `detect_markers` применяет precision guard: 2-seg slug попадает в результат только при корреляции с higher-precision детектором (`abs_path` / `src_file` / `tausik_cmd`) или 3+ seg slug'ом в том же тексте. Standalone 2-seg slug → empty (консервативно, английские kebab-compounds типа `kebab-case` / `ts-node` / `switch-case` / `double-quoted` / `single-quoted` не флагуются) (`hooks-markers-slug-regex-widen`) — Ловим короткие project slug'и при корреляции, не шумим на English kebab

### Added — Misc hardening batch (Batch 4)

- **Qwen Code brain MCP registration** ([bootstrap/bootstrap_qwen.py](bootstrap/bootstrap_qwen.py)) — `generate_settings_qwen` теперь регистрирует `tausik-brain` MCP server параллельно `tausik-project`/`codebase-rag` (тот же pattern что в `bootstrap_generate.py:241-246`). Раньше Qwen users молча оставались без brain. Silent skip когда `target_dir/mcp/brain/server.py` отсутствует — не ломает чистые qwen-only проекты (`bootstrap-qwen-brain-mcp`) — Qwen users теперь получают brain MCP при bootstrap
- **Brain schema migration path** ([scripts/brain_schema.py](scripts/brain_schema.py)) — `apply_schema` теперь читает `brain_meta.schema_version` после CREATE TABLE; если db_version > SCHEMA_VERSION → `RuntimeError("Brain DB schema vN newer than code v1; update tausik-lib")` (newer-code guard); если db_version < SCHEMA_VERSION → запускает новый `_migrate(conn, from_version)` helper. `BRAIN_MIGRATIONS = {}` placeholder dict с docstring контракта (sorted-by-key, single-tx, irreversible, bump после успешного COMMIT). Раньше `SCHEMA_VERSION=1` записывался но никогда не читался — нет ALTER strategy для будущих v2/v3 (`brain-schema-migration-path`) — Foundation для будущих brain schema bump'ов

### Added — Init/registry hardening batch

- **Orphan database cleanup guidance** ([scripts/brain_init.py](scripts/brain_init.py) `run_wizard`) — пост-create секция (register_project + all_project_names + config_ops.save) обёрнута в try/except. На любую ошибку после успешного `create_brain_databases` новый helper `_print_orphan_cleanup_guidance` печатает все 4 `category: db_id (title)` с инструкцией Archive via Notion UI, затем raise `WizardError("Post-create step failed ...")`. Раньше пользователь получал orphan Notion databases и не знал какие именно архивировать. Покрытие: registry RegistryLockError, config_ops.save OSError, happy path не регрессирует (`brain-init-orphan-cleanup`) — Видимая cleanup-инструкция вместо тихих orphan-ов
- **CliIO EOF/KeyboardInterrupt → WizardError** ([scripts/brain_init.py](scripts/brain_init.py)) — default `CliIO` поднята на module-level (раньше локальный `_CliIO` в `cmd_brain`); `prompt()` оборачивает `input()` в `try/except (EOFError, KeyboardInterrupt)` → raise `WizardError("Aborted by user.")` вместо raw traceback. project_cli_ops.cmd_brain использует `brain_init.CliIO`. Покрывает: piped stdin (EOFError) и Ctrl+C (KeyboardInterrupt) во время interactive wizard prompt'ов (`brain-init-input-error-handling`) — Чистый abort вместо traceback при piped stdin / Ctrl+C
- **Stale-lock recovery** ([scripts/brain_project_registry.py](scripts/brain_project_registry.py) `_acquire_lock`) — SIGKILL'нутый wizard оставлял `.lock` файл навсегда: новые `init`/`register_project` зависали до timeout. Новые `_pid_alive(pid)` (OS-агностичный через `os.kill(pid,0)`, корректно обрабатывает ProcessLookupError/PermissionError/Windows ERROR_INVALID_PARAMETER) + `_is_stale_lock(lock_path)` (stale если pid мёртв ИЛИ mtime > `_STALE_LOCK_AGE_S=30s`). На FileExistsError проверяем stale → unlink + log warning + retry (ровно 1 раз через `reclaimed` flag). Регрессия: live + fresh lock всё ещё блокирует. Boundary cases: malformed lock content fall-back на mtime, read OSError → not stale (conservative) (`brain-registry-stale-lock-recovery`) — Wizard recovery от orphan locks без manual cleanup

### Test Coverage / Тесты

- **+102 new tests** — `test_brain_schema.py` (17), `test_brain_config.py` (20), `test_brain_notion_client.py` (26), `test_brain_sync.py` (15), `test_brain_search.py` (24). Entire brain-suite green in 2 s; no network I/O (client tests inject `_Recorder`/`_ClockSleep`). Pre-existing 918 tests unaffected.
- **+19 hardening tests** — `test_brain_mcp_handlers.py` (+6 token-missing warning + boundary), `test_brain_mcp_write.py` (+3 NotionAuthError/RateLimitError(retry_after=42)/RateLimitError(retry_after=None default) + 2 ok_not_mirrored on upsert/map_page_to_row failure + 1 typo `category` → unknown), `test_brain_notion_client.py` (+7 secret-leak defense: `_LEAK_TOKEN` not in `repr(client)`, `NotionAuthError`/`NotionNotFoundError`/`NotionRateLimitError`/`NotionServerError`/`NotionNetworkError` strings + `caplog` retry log) (`brain-mcp-write-error-class-tests`, `brain-mcp-write-ok-not-mirrored-test`, `brain-notion-client-secret-leak-test`)
- **+9 hooks widening tests** — `test_memory_pretool_block_hook.py` (+3 new block paths: bare_claude_memory, agents_memory, deeply_nested_memory + 3 negatives: memory.md file, somememory/, memoryold/), `test_memory_markers.py` (+6 TestTwoSegmentSlugs: standalone 2-seg dropped, corroborated with abs_path/src_file/tausik_cmd/3seg-slug kept, 3-seg alone regression) (`hooks-pretool-block-path-patterns`, `hooks-markers-slug-regex-widen`)
- **+10 init/registry tests** — `test_brain_init.py` (+3: registry_failure_prints_orphan_guidance, config_save_failure_prints_orphan_guidance, happy_path_prints_no_orphan_guidance), `test_brain_project_registry.py` (+7: dead_pid_reclaimed, expired_mtime_reclaimed, live_fresh_not_reclaimed regression, malformed_reclaimed_after_ttl, malformed_fresh_blocks boundary, is_stale_lock_missing_returns_false, pid_alive_rejects_nonpositive) (`brain-init-orphan-cleanup`, `brain-registry-stale-lock-recovery`)
- **+3 CliIO tests** — `test_brain_init.py` (TestCliIOPrompt: returns_input_normally, eof_raises_wizard_error, keyboard_interrupt_raises_wizard_error) (`brain-init-input-error-handling`)
- **+3 qwen MCP tests** — `test_bootstrap_qwen.py` (qwen_registers_brain_when_server_present, qwen_skips_brain_when_server_missing, qwen_preserves_user_added_servers) (`bootstrap-qwen-brain-mcp`)
- **+5 brain schema migration tests** — `test_brain_schema.py` (BRAIN_MIGRATIONS dict exists, apply_schema idempotent when migrations empty, raises_when_db_newer guard, migrate_applies_pending_versions, migrate_skips_already_applied, migrate_rolls_back_on_failure) (`brain-schema-migration-path`)

### Knowledge Captured / Накоплено знаний

- **Decision #30** — 4 Notion databases, not one flat table (UX outweighs sync overhead)
- **Decision #31** — `SHA256(canonical)[:16]` privacy hash (64 bits, no plaintext project names)
- **Decision #32** — separate `Content Hash` column for `web_cache` dedup (URL changes over time)
- **Decision #33** — inject `urlopen` / `clock` / `sleep` via constructor instead of global monkeypatch
- **Gotcha #34** — FTS5 MATCH treats `-` as column-qualifier; wrap queries in `"..."` or avoid hyphens in markers
- **Convention #35** — `brain-*` modules are separate files (`brain_config.py`, `brain_schema.py`, ...), never folded into `project_config.py` — the 400-line file limit is real

## [1.3.0-pre] — 2026-04-23 — Memory Discipline (folded into 1.3.0 release above)

### Memory-Discipline Epic — auto-memory protection

Protects Claude's cross-project auto-memory (`~/.claude/projects/*/memory/`) from accidental project-specific writes. Project knowledge belongs in TAUSIK's per-project SQLite store (`tausik memory add`); the user's home memory is for cross-project preferences only. 8 tasks shipped across 3 stories. Защита Claude auto-memory от случайного проектного контекста.

### Added / Добавлено

- **PreToolUse memory block** (`scripts/hooks/memory_pretool_block.py`) — blocks Write/Edit/MultiEdit to `~/.claude/projects/*/memory/` from any TAUSIK project with a guidance message. Bypass via the `confirm: cross-project` marker in the user's latest prompt — hook parses the Claude Code transcript JSONL, honors both flat-string and list-of-content-blocks message shapes, and skips tool_result turns when finding the real user message — Блокирует записи в auto-memory с escape-маркером для кросс-проектных случаев
- **PostToolUse memory audit** (`scripts/hooks/memory_posttool_audit.py`) — safety-net that runs after every auto-memory write, scans the file with a regex marker set (absolute paths, kebab slugs ≥3 parts, `.tausik/tausik` commands, `scripts/*.py` file refs), emits a stderr warning listing up to 5 matches. Warning-only (exit 0) — catches content that bypassed the marker by accident — Аудит после записи с детектом проектных markers
- **Memory marker regex module** (`scripts/hooks/memory_markers.py`) — stdlib-only `detect_markers(text) -> list[Match]` with 4 precision-tuned pattern kinds (`abs_path`, `slug`, `tausik_cmd`, `src_file`); tuned against 14 cross-project preference strings ("user prefers Russian", "likes pytest", "uses VS Code", kebab-case lookalikes) to keep false positives at zero. Shared with upcoming brain-scrubbing pipeline — Отдельный модуль regex для переиспользования
- **Memory Policy rule in context injection** — `build_memory_block()` now begins with a ⚠ warning line explaining the TAUSIK-vs-auto-memory split, visible to the agent on every session start and `/checkpoint`. `session_start.py` Reminders gain a matching bullet so fresh projects (empty DB) still see the rule — Правило политики памяти в инжекте сессии
- **Hook registration** — `bootstrap_generate.py` + `bootstrap_qwen.py` wire both new hooks into PreToolUse / PostToolUse under matcher `Write|Edit|MultiEdit` for Claude Code and Qwen Code alike — Регистрация в bootstrap для обоих IDE

### Changed / Изменено

- **Hook count:** 11 → 13 (added `memory_pretool_block`, `memory_posttool_audit`) — 13 hook-ов в сумме
- **`is_in_claude_memory`** public alias added to `memory_pretool_block.py` so other hooks can import a stable name instead of the underscore-prefixed internal — Стабильный public API между hook-ами

### Fixed / Исправлено

- **Windows stderr encoding** — hook block messages used unicode arrows (`→`) that rendered as literal `→` on cp1251 consoles; replaced with ASCII `->` in user-facing warning text — Windows consoles больше не портят сообщения hook-ов

### Test Coverage / Тесты

- **+78 new tests** — 1105 → 1183 passing. `test_memory_pretool_block_hook.py` (30 cases: block/allow/bypass/tool_result/settings), `test_memory_markers.py` (29 cases: positive × kind, negatives × 14 preferences, dedup, edge, perf budget), `test_memory_posttool_audit_hook.py` (21+ cases: detection, silence on clean writes, non-audited paths, graceful, truncation `...and N more`, binary content, tool_input variants, settings registration)

## [1.2.0] — 2026-04-17

### Claude-Hardening Epic — anti-drift infrastructure

Inspired by [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) (staged pipelines, Ralph mode, keyword-detector), [prompt-master](https://github.com/nidhinjs/prompt-master) (load-bearing text, Memory Block, 9 dimensions of intent), and the leaked Claude Code architecture analysis on Habr (KAIROS always-on assistant, Dream System memory consolidation). Addresses the real-world problem that agents "drift" — ignore the framework, skip task creation, forget conventions between sessions. 18 tasks shipped across 4 stories (P0/P1/P2/P3).

### Added / Добавлено

- **Load-bearing CLAUDE.md / AGENTS.md / .cursorrules / QWEN.md templates** — generated IDE instructions went from ~30 lines to ~104 lines each, with 13 hard constraints, workflow graph, memory types table, SENAR rules reference, DYNAMIC block. All four IDE files share a single source of truth in `bootstrap/bootstrap_templates.py` (no more drift between IDEs) — Единый источник CLAUDE/AGENTS/cursorrules/QWEN
- **SessionStart hook** (`scripts/hooks/session_start.py`) — auto-injects TAUSIK state (status, active tasks, blocked tasks, Memory Block) into every new Claude Code / Qwen Code session; no manual `/start` needed — SessionStart хук с автоинъекцией состояния
- **UserPromptSubmit hook** (`scripts/hooks/user_prompt_submit.py`) — detects coding-intent keywords in user prompts (EN+RU) and nudges the agent to check for an active task before writing code — Детектор coding-intent с напоминанием
- **Stop hooks** — `scripts/hooks/keyword_detector.py` (drift-announcement detection in agent's last message — blocks stop if "I'll implement" without active task) and `scripts/hooks/session_cleanup_check.py` (warns about open exploration, review-tasks, session timeout) — Два Stop hook'а: keyword detector и session hygiene
- **PostToolUse verify-fix-loop hook** (`scripts/hooks/task_done_verify.py`) — after every successful `task_done`, 5 rule-based heuristics audit the AC evidence (file paths, ✓ markers, test counts, file refs, lint status); 2+ failures trigger a `/review` recommendation — Rule-based Ralph-mode-lite
- **Memory Block re-injection** — new `memory_block()` method + `tausik memory block` CLI + `tausik_memory_block` MCP tool returning compact markdown (recent decisions + conventions + dead ends, ≤50 lines) consumed by `/start`, `/checkpoint`, SessionStart hook — Повторная инъекция проектной памяти для anti-drift
- **`tausik memory compact`** CLI + `tausik_memory_compact` MCP — Dream-System-inspired aggregation of recent `task_logs` into phases / top opening words / top files mentioned — Консолидация логов в паттерны
- **QG-0 9-dimension intent completeness** — `qg0_dimensions_score()` in `service_gates.py` scores every task against {goal, acceptance_criteria, scope, scope_exclude, role, stack, complexity, story_link, evidence_plan}; <5 dims triggers a "CONTEXT" warning (prompt-master principle) — QG-0 расширен до 9 измерений
- **Adversarial critic in `/review`** — new sixth parallel review agent `agents/skills/review/agents/critic.md` hunting for exactly 3 weaknesses the other 5 agents miss (hidden failure modes, silent contract drift, assumption gaps); opt-in "deep mode" runs two critic passes — Adversarial критик в /review
- **`/interview` skill** — Socratic Q&A before complex tasks (max 3 clarifying questions, prompt-master principle) — Сократический Q&A скилл
- **`tausik hud`** CLI — one-screen live dashboard (session + active task + recent logs + gates) inspired by oh-my-claudecode HUD — Live HUD
- **`tausik suggest-model`** CLI + `scripts/model_routing.py` — model recommendation by complexity tier (simple→Haiku 4.5, medium→Sonnet 4.6, complex→Opus 4.7) for manual application via `/fast` — Cost-aware model routing
- **Webhook notifications** (`scripts/notifier.py` + `scripts/hooks/notify_on_done.py`) — Slack / Discord / Telegram webhooks fired on `task_done`; configured via `TAUSIK_SLACK_WEBHOOK` / `TAUSIK_DISCORD_WEBHOOK` / `TAUSIK_TELEGRAM_WEBHOOK` env vars — Webhook-уведомления в 3 канала
- **`CLAUDE_PLUGIN_DATA` env support** — `scripts/plugin_data.py` respects Claude Code's plugin-data convention for skill persistent state; falls back to `.tausik/plugin_data/` — Поддержка CLAUDE_PLUGIN_DATA
- **Mandatory Gotchas section lint** — `tests/test_skills_have_gotchas.py` enforces every SKILL.md has a "## Gotchas" section with real content (Habr recommendation) — Обязательная секция Gotchas
- **No-boilerplate lint** — `tests/test_skills_no_boilerplate.py` blocks re-introduction of "Always respond in user's language" in SKILLs (already covered by CLAUDE.md) — Лин для boilerplate

### Changed / Изменено

- **Bootstrap no longer copies `lib/AGENTS.md`** (which was dogfooding-specific, referenced `scripts/`/`agents/` structure); `generate_agents_md()` now produces a universal AGENTS.md with shared hard constraints — AGENTS.md теперь генерируется, не копируется из lib
- **Skills cleanup** — 12 SKILL.md files had "Always respond in the user's language" boilerplate removed (duplicate of CLAUDE.md Response Language section) — Чистка boilerplate в 12 skill-файлах
- **Shared hook helpers** — `scripts/hooks/_common.py` extracts `tausik_path()`, `has_active_task()`, `is_task_done_invocation()`, `extract_task_done_slug_from_bash()` previously duplicated across 5 hooks (convention #2: Mixin composition) — Рефакторинг общих helper-ов hooks
- **`bootstrap/bootstrap_venv.py`** gets `install_cli_wrapper()` helper (extracted from bootstrap.py to stay under 400-line gate) — CLI wrapper install вынесен
- **Skills count:** 34 → 35 (added `/interview`) — 35 скиллов
- **MCP tools:** 80 → 82 (added `tausik_memory_block`, `tausik_memory_compact`) — 82 MCP инструмента

### Fixed / Исправлено

- **H1 — Bash `"task done"` false-positive** — PostToolUse hooks (`notify_on_done`, `task_done_verify`) used substring match that triggered on `echo "task done today"`, `git log --grep="task done"`, etc. Replaced with a proper regex anchored to the actual `tausik[.cmd] task done <slug>` CLI shape in `_common.py`
- **H2 — `_check_ac_checkmarks` matched too loosely** — `"complete"` substring fired on `incomplete`/`completion`/`completeness`, and the heuristic ran on the full `task show` output (title + goal) rather than notes. Fixed with word-boundary regex `[✓✔]|\b(passed|verified|ok|complete[d]?)\b` plus `_extract_notes_section()`

### Test Coverage / Тесты

- **+177 new tests** — 918 → 1095 passing. Every new module (hooks, templates, routing, aggregates) ships with its own test file.

## [1.1.0] — 2026-04-12

### DX & Adoption Improvements

Inspired by ideas from [Molyanov AI Dev Framework](https://github.com/pavel-molyanov/molyanov-ai-dev) — two-phase planning, TDD enforcement, skill auto-testing. Community request for Qwen Code support ([#1](https://github.com/Kibertum/tausik-core/issues/1)).

### Added / Добавлено

- **Qwen Code (GigaCode) support** — full IDE integration: `.qwen/` directory, `QWEN.md` rules file, MCP config + SENAR hooks in `.qwen/settings.json`, 80 MCP tools + 4 enforcement hooks (task gate, bash firewall, push gate, auto-format) ([#1](https://github.com/Kibertum/tausik-core/issues/1)) — Полная поддержка Qwen Code CLI с хуками
- **TDD enforcement gate** — optional `tdd_order` quality gate verifies test files are modified alongside source code; disabled by default, enable via config — Опциональный gate для TDD-контроля
- **Two-phase planning** — `/plan` now starts with an interview phase (3+ clarifying questions) before decomposition; skip with `--skip-interview` — Двухфазное планирование с интервью
- **Auto-docs update on /ship** — after commit, `/ship` checks for structural changes and suggests updating `references/` documentation — Автообновление документации при /ship
- **`/skill-test` skill** — auto-generates 3-5 test scenarios for any skill and validates them through subagents — Автотестирование скиллов
- **IDE-aware skill catalog** — `skill-catalog.md` now uses correct IDE directory paths instead of hardcoded `.claude/` — Параметризованный каталог скиллов

### Changed / Изменено

- **`--smart` is now default** — stack detection and skill auto-enable run automatically; use `--no-detect` to skip — `--smart` теперь по умолчанию
- **`--init` no longer requires a name** — project name auto-derived from directory; `--init my-name` still works — `--init` без обязательного имени
- `bootstrap.py --ide` now accepts `qwen` and includes it in `all` — Qwen добавлен в выбор IDE
- Supported IDEs: Claude Code, Cursor, **Qwen Code**, Windsurf, Codex — 5 IDE
- Skills count: 33 → 34 (added `/skill-test`) — 34 скилла
- Filesize gate exempts `agents/qwen/mcp/` directory — Исключение для qwen mcp
## [1.1.1] — 2026-04-14

### Fixed

- **MCP tags coercion** — `tausik_dead_end` and `tausik_memory_add` now accept `tags` as both JSON array and string. MCP clients (Claude Code) may serialize array params as JSON strings; added `_coerce_tags()` helper to handle both formats gracefully.

## [1.0.0] — 2026-04-05

### Public Release / Публичный релиз

First public release of TAUSIK. Cross-IDE AI agent framework implementing [SENAR v1.3 Core](https://senar.tech).
Первый публичный релиз TAUSIK. Кросс-IDE фреймворк для AI-агентов, реализующий [SENAR v1.3 Core](https://senar.tech).

### Highlights / Основное

- **Cross-IDE support** — Claude Code, Cursor, Windsurf, Codex with unified skill/role/stack system — Поддержка Claude Code, Cursor, Windsurf, Codex с единой системой скиллов/ролей/стеков
- **31 skills** — from `/start` to `/ship`, covering the full development lifecycle — 31 скилл, покрывающих полный цикл разработки
- **SENAR v1.3 Core compliance (100%)** — Quality gates, metrics, dead ends, explorations, verification checklists — Полное соответствие SENAR v1.3 Core
- **Graph memory** — Project knowledge base with edges, soft-invalidation, FTS5 search — Графовая память проекта с рёбрами, soft-invalidation, FTS5 поиском
- **Autonomous batch mode** — `/run plan.md` executes multi-task plans with subagents — Автономный batch-режим для выполнения планов

### Added / Добавлено

- **Quality Gates** — QG-0 (context gate: goal + AC + negative scenario) and QG-2 (implementation gate: evidence + tests + ac-verified) — Quality gates с жёстким enforcement
- **Claude Code Hooks** — task gate, bash firewall, git push gate, auto-format — Хуки для контроля в реальном времени
- **SENAR Metrics** — Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task — Автоматические метрики
- **Multi-language gates** — pytest, ruff, go-vet, clippy, phpstan, eslint, tsc, and more — Gates для 10+ языков
- **5-agent review pipeline** — quality, implementation, testing, simplification, documentation agents with iterative cycle — 5 параллельных review-агентов с итеративным циклом
- **Dead ends & explorations** — `dead-end` for documenting failures, `explore` for time-bounded research — Документирование тупиков и исследования
- **Graph memory** — Polymorphic edges between memory/decision nodes, 4 relation types, recursive CTE traversal — Полиморфные рёбра, 4 типа связей, обход графа через CTE
- **Structured task logs** — `task_logs` table with phase tracking and FTS5 index — Структурированные логи задач
- **Vendor skills** — `skills.example.json` + `skill activate/deactivate` for third-party extensions — Поддержка сторонних скиллов
- **Bootstrap** — `bootstrap.py --smart --init` for one-command setup with stack detection — Настройка одной командой с детекцией стека
- **Apache 2.0 license** — Open source license — Лицензия Apache 2.0
- **Bilingual docs** — Full documentation in English and Russian — Полная документация на EN и RU
- **CONTRIBUTING.md** — Contributor guide — Гайд для контрибьюторов
- **837 tests** — Comprehensive test suite — Полный набор тестов
