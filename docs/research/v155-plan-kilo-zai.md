# TAUSIK v1.5.5 — Roadmap Plan (Kilo / z.ai Integration)

## Scope

Bump current `1.5.3` → **`1.5.5`**. The release contains two thematically linked EPICs:

1. **`v155-provider-abstraction`** — remove Claude-centrism from the core, making TAUSIK runtime-agnostic.
2. **`v155-kilo-bootstrap`** — add first-class Kilo code / z.ai bootstrap target.

No RENAR changes, no schema migration, no breaking public API. Pure additive refactor + new generator.

---

## Rationale (current state)

| Issue | Location | Impact |
|-------|----------|--------|
| `model_routing.py:31` hard-codes Claude transcript | `read_active_model_from_transcript` | Cannot reuse routing for z.ai / Cursor |
| `model_routing.py:66` discovers transcript via Claude-specific hook path | `_auto_find_transcript` → `hooks.session_metrics` | Fails under Kilo orchestration |
| `bootstrap_generate.py:18` — single IDE-specific generator per call | `generate_settings_claude` | No Kilo target |
| `_IDE_DIRS` in `bootstrap.py:82` | `{"claude", "cursor", "windsurf", "codex", "qwen"}` | No `"kilo"` |
| `model_routing_matrix.py` — model tiers & display names are hardcoded constants | `_MODEL_TIERS`, `_MODEL_DISPLAY` | Adding z.ai models requires code change |
| `bootstrap_templates.py` — 4 near-identical generators | `build_full_body` called 4× | Error-prone duplication |

The issues are independent; no migration path is needed because:
- `_IDE_DIRS` is append-only (new key = new directory)
- `scripts/` models are consumed by MCP server, never edited by IDE
- Kilo runs MCP server as plugin (separate launch context), not via `stdio` wrapper

---

## EPIC-1: `v155-provider-abstraction`

### Goal

Introduce a provider registry that abstracts Claude-specific runtime detection. Existing Claude Code host continues to work unchanged. Cursor / Qwen / Kilo / z.ai become simple registry entries.

### New files

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/providers/__init__.py` | 40 | Provider registry singleton |
| `scripts/providers/base.py` | 80 | Abstract base: `get_active_model()`, `get_transcript_path()`, `generate_ide_settings()` |
| `scripts/providers/claude.py` | 60 | Existing logic (extracted) |
| `scripts/providers/cursor.py` | 30 | Stub (row from current `bootstrap_generate`) |
| `scripts/providers/qwen.py` | 30 | Stub |
| `scripts/providers/kilo.py` | 50 | Reads `~/.config/kilo/kilo.json` + `.kilo/` for active model |
| `scripts/providers/zai.py` | 50 | Reads z.ai runtime metadata (websocket header, env, or config) |

### Modified files

| File | What changes | Lines |
|------|--------------|-------|
| `scripts/model_routing.py` | `read_active_model_from_transcript` → `provider_registry.get().get_active_model()`; `_auto_find_transcript` → same | ±20 |
| `scripts/model_routing_matrix.py` | `_MODEL_TIERS` / `_MODEL_DISPLAY` moved to `model_profiles` in `.tausik/config.json` (data, not code); `_load_model_profiles()` reader | +80, -40 hardcode |
| `scripts/bootstrap/bootstrap.py` | `_IDE_DIRS` gains `"kilo": ".kilo"`; calls `provider_registry.get(ide).bootstrap(target_dir, ...)` | ±10 |
| `scripts/bootstrap/bootstrap_generate.py` | Each `generate_*` function delegates to `provider.generate_settings()` | −150 |
| `scripts/bootstrap/bootstrap_qwen.py` | Same delegation pattern | −20 |
| `scripts/project_config.py` | Add `MODEL_PROFILES_PATH`, `load_model_profiles()`, `normalize_model_profiles()` | +60 |

### Tests

| File | What |
|------|------|
| `tests/test_providers.py` (new) | Registry, base contract, claude/cursor/qwen/kilo/zai entries |
| `tests/test_model_routing.py` | Existing tests gain `provider=` fixture; add kilo/zai cases |
| `tests/test_model_profiles_config.py` | Load/save/validate profiles JSON schema |
| `tests/test_config.py` | `auto_enable_gates` + new `normalize_model_profiles` |

### Commit sequence (merged into 1.5.5)

1. `feat(provider): registry + base + claude extract` (no behaviour change)
2. `feat(provider): cursor/qwen/kilo/zai stubs`
3. `refactor(model-routing): provider-aware active-model detection`
4. `refactor(model-routing): model profiles as data`
5. `refactor(bootstrap): provider.generate_settings()`

### Gates / Verification

- `pytest tests/test_providers.py tests/test_model_routing.py tests/test_model_profiles_config.py tests/test_config.py` — scoped
- `tausik doctor` — DB + MCP + skills + drift (no .claude dependency under Kilo)
- `tausik verify` — `pytest` + `ruff` + `mypy`
- CHANGELOG drift gate — update `docs/en/architecture.md` provider table

---

## EPIC-2: `v155-kilo-bootstrap`

### Goal

`python .tausik-lib/bootstrap/bootstrap.py --ide kilo` produces a functioning Kilo plugin/manifest that re-exposes the TAUSIK MCP server inside Kilo's runtime, with `.kilo/command/*.md` slash-commands and optional `kilo.json` merge.

### New files

| File | Lines | Purpose |
|------|-------|---------|
| `bootstrap/bootstrap_kilo.py` | 200 | `generate_kilo_config()`, `generate_kilo_commands()`, `generate_kilo_agents()` |
| `harness/overrides/kilo/` | — | Kilo-specific asset stubs (empty for now; future: theme, agent prompts) |
| `bootstrap/kilo_command_compiler.py` | 150 | Compile `harness/skills/<name>/SKILL.md` → `.kilo/command/<name>.md` |

### Modified files

| File | What changes | Lines |
|------|--------------|-------|
| `bootstrap/bootstrap.py` | `_IDE_DIRS` add `"kilo"`; `bootstrap_ide` calls `generate_kilo_*` when `ide == "kilo"` | +20 |
| `bootstrap/bootstrap_config.py` | `ALL_EXTENSION_SKILLS` stays the same (shared) | 0 |
| `scripts/project_config.py` | `normalize_kilo_config()` — merge `providers.kilo` into generated `kilo.json` | +40 |

### Generated artefacts (runtime, gitignored)

```
.kilo/
  commands/
    start.md       # compiled from harness/skills/start/SKILL.md
    plan.md
    ship.md
    task.md
    ...
  agent-manager.json  # Kilo own state
```

`kilo.json` merge (optional, at `~/.config/kilo/kilo.json` or project root):

```json
{
  "mcp": {
    "tausik-project": {
      "type": "local",
      "command": ["<venv-python>", "<lib>/harness/claude/mcp/project/server.py", "--project", "<cwd>"],
      "enabled": true
    }
  },
  "skills": {
    "paths": [".kilo/commands"]
  }
}
```

### Tests

| File | What |
|------|------|
| `tests/test_bootstrap_kilo.py` (new) | `generate_kilo_config` output shape, MCP server stanza, command stubs |
| `tests/test_kilo_command_compiler.py` (new) | Round-trip SKILL.md → command.md for 5 core skills |

### Commit sequence

6. `feat(bootstrap): --ide kilo generator`
7. `feat(bootstrap): kilo_command_compiler`

---

## Defensive / bundled changes in 1.5.5

| # | Change | File | Why |
|---|--------|------|-----|
| A | Bump `__version__` to `1.5.5` | `scripts/tausik_version.py` | Release |
| B | Regenerate `docs/_generated/constants.json` | `scripts/gen_doc_constants.py` | Doc-drift gate |
| C | Update CHANGELOG `[Unreleased]` → `[1.5.5]` | `CHANGELOG.md` + `CHANGELOG.ru.md` | Release hygiene |
| D | Update `pyproject.toml` version | root `pyproject.toml` | PyPI / pip consistency |
| E | Update QA doc counters (tests, MCP tools) | `docs/en/quickstart.md` / `docs/en/architecture.md` | Doc-drift gate |

### E2E refactor sanity

Before tagging, run:
- `pytest tests/test_providers.py tests/test_bootstrap_kilo.py tests/test_model_routing.py -v` — scoped new tests
- `pytest tests/test_e2e_workflow.py` — existing end-to-end (no regression)
- `python scripts/gen_doc_constants.py --check` — doc-drift must pass
- `python scripts/doc_drift_scanners.py` — version + tool-count scanners clean

---

## Release gate (`v155-release`)

1. `CHANGELOG.md` — fold `[Unreleased]` into `[1.5.5] — <date>`; both EN + RU mirror
2. `gen_doc_constants.py` — all counts green
3. `git tag v1.5.5`
4. `gh release create v1.5.5` — publish to GitHub mirror (same workflow as 1.5.2/1.5.3)
5. `docs/en/quickstart.md` — Kilo is added to supported-IDEs list (line ~33)
6. `docs/en/architecture.md` — cross-IDE table gains Kilo row

---

## What is NOT in 1.5.5

| Item | Reason |
|------|--------|
| RENAR-2 signed ADAPT | 2.0 scope (irreversible); out of scope |
| z.ai-specific quality gates | P2 — add per-stack gate via `.tausik/stacks/zai/stack.json` instead |
| Brain/Notion under Kilo | Deferred — Notion config still IDE-scoped; keep opt-in per `tausik brain init` |
| Skill → Kilo command compiler persistence | Skeleton only in 1.5.5; full caching / selective install is P2 |
| Context Assembler (template dedup) | Polished out to 1.6.0 unless spare budget |

---

## Test impact estimate

| Suite | Current | After 1.5.5 | Delta |
|-------|---------|--------------|-------|
| `tests/test_providers.py` | 0 | ~30 | new |
| `tests/test_bootstrap_kilo.py` | 0 | ~20 | new |
| `tests/test_kilo_command_compiler.py` | 0 | ~15 | new |
| `tests/test_model_routing.py` | existing | existing + ~10 | minor |
| `tests/test_config.py` | existing | +5 | minor |
| `tests/test_e2e_workflow.py` | existing | unchanged | — |
| **Total** | 4348 | ~4428 | **~+80** |

---

## Commit order (11 commits → 1.5.5)

```
feat(provider): registry + base + claude extract
feat(provider): cursor/qwen/kilo/zai stubs
refactor(model-routing): provider-aware active-model detection
refactor(model-routing): model profiles as data
refactor(bootstrap): provider.generate_settings()
feat(bootstrap): --ide kilo generator
feat(bootstrap): kilo_command_compiler
chore(version): bump 1.5.3 → 1.5.5
chore(changelog): fold [Unreleased] → [1.5.5] (+ RU mirror)
chore(docs): regen constants.json + update IDE lists + architecture
release(v1.5.5): tag + gh release
```

---

## Verification contract (QG-2 analog for the release)

| Step | Tool | What it proves |
|------|------|----------------|
| 1 | `pytest tests/test_providers.py -v` | Provider registry + stubs + base contract |
| 2 | `pytest tests/test_bootstrap_kilo.py tests/test_kilo_command_compiler.py -v` | Kilo generator produces valid artefacts |
| 3 | `pytest tests/test_model_routing.py tests/test_model_profiles_config.py tests/test_config.py -v` | Routing + config facade still sane |
| 4 | `tausik verify` (in repo root) | Heavy gates — pytest / ruff / mypy across full tree |
| 5 | `python scripts/gen_doc_constants.py --check` | CHANGELOG + architecture.md counters match reality |
| 6 | `python scripts/doc_drift_scanners.py` | Version string consistent across all hardcoded refs |
| 7 | `tausik doctor` | DB + MCP + skills + drift clean |
| 8 | Manual Kilo smoke: `python scripts/project.py --help` with a stub `kilo.json` | Integration path works end-to-end |

After all 8 steps pass → `git tag v1.5.5 && gh release create v1.5.5`.
