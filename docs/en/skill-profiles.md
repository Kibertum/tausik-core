**English** | [Русский](/ru/docs/skill-profiles)

# Skill profiles and `variants/` (v1.4 polish — B8-pre)

TAUSIK skills ship a single **`SKILL.md`** plus optional **two-axis overlays**: per-IDE behaviour and per-model style. The two axes compose independently — a `cursor-gpt-5` session reuses the same `model/gpt-5.md` overlay as a `claude-gpt-5` session (DRY).

## Layout (current)

```
harness/skills/<skill-name>/
  SKILL.md                  # Shared instructions + YAML frontmatter
  variants/
    ide/                    # Currently shipped only on the _profile-demo skill;
      claude.md             # the production /plan, /task, /ship skills carry the
      cursor.md             # model axis only. Adding ide/ overlays to a workflow
      qwen.md               # skill is supported by the merge logic but not yet wired.
      codex.md
    model/                  # Shipped on /plan, /task, /ship.
      sonnet.md             # Appended when active model = sonnet
      haiku.md              # ...haiku
      gpt-4.md              # GPT family (added in v14b-gpt-model-profile)
      gpt-5.md
      gpt-5-5.md            # Dot-form `gpt-5.5` normalizes to this slug
```

`opus` and `qwen` slugs are **resolved by the detector** but currently fall back to the base SKILL.md — no `opus.md` / `qwen.md` ship for the workflow skills. Add them under `variants/model/` if you want a dedicated overlay; the merge picks them up on the next `tausik skill rebuild`.

GPT overlays for `/plan`, `/task`, `/ship` are intentionally **telegraphic** (≤25 lines each, imperative voice, delta-only — no base SKILL.md restatement). They nudge: aggressive parallel tool calls (esp. gpt-5/gpt-5-5), zero narrative reasoning, single-turn task completion. See `harness/skills/{plan,task,ship}/variants/model/gpt-*.md`.

The legacy flat layout (`variants/<slug>.md`) still resolves via `merge_skill_markdown(skill_dir, requested_profile=<slug>)` — kept for backward compatibility with external skill repos that haven't migrated. New skills should use the two-axis layout.

## Auto-detect on session start

`scripts/hooks/session_start.py::_auto_rebuild_skills` resolves `(ide, model)` via this precedence:

1. **Env override:** `TAUSIK_IDE_PROFILE`, `TAUSIK_MODEL_PROFILE`
2. **Project config:** `.tausik/config.json` keys `ide_profile`, `model_profile`
3. **Auto-detect:** `scripts/skill_profile_detect.py` reads well-known IDE env vars (`CLAUDE_CODE_*`, `CURSOR_*`, `QWEN_*`, `CODEX_*`) and model env vars (`ANTHROPIC_MODEL`, `OPENAI_MODEL`, `QWEN_MODEL`, etc.). Model is often `None` because Cursor/Qwen don't expose the active model in env — that's fine, IDE overlay still applies.

The hook compares the resolved tuple with `.tausik/.session.json`. On mismatch, `rebuild_skills` re-merges every `.claude/skills/<slug>/SKILL.md` on disk. **Cache hit (no change) = no-op (microseconds).** Re-merging is idempotent because each merge strips existing `<!-- tausik-profile:... -->` markers from the base before re-applying overlays.

## Manual override

```bash
tausik config show                              # print resolved (ide, model, source)
tausik config set ide_profile cursor            # persist override into .tausik/config.json
tausik config set model_profile gpt-5           # persist model override
tausik skill rebuild                            # manual trigger; no-op when nothing changed
tausik skill rebuild --force                    # rewrite even if sha256 matches
```

## Merge order

Two-axis merge (in this order):

```
base SKILL.md  +  variants/ide/<ide>.md  +  variants/model/<model>.md
```

IDE constraints come first (how the host invokes tools, runtime quirks). Model overlay last (style nudges). Either or both overlays may be missing — silently skipped.

## Idempotency

`merge_skill_markdown` strips everything from the first `<!-- tausik-profile:` marker onward before re-merging. This means rebuild can run repeatedly without accumulating overlay sections — the merged file is always `base + ide + model`, never `base + ide + model + ide + model`.

## Frontmatter (legacy — flat layout only)

| Field | Meaning |
|--------|---------|
| `profile_fallback` | When `merge_skill_markdown(requested_profile=<slug>)` finds no `variants/<slug>.md`, try this profile once for overlay lookup (legacy flat layout only — does NOT apply to two-axis layout). |

## Token economy notes

- Overlays should be **telegraphic** (≤30 lines each, imperative voice). Long prose negates the savings.
- Disk pre-merge means runtime cost is just a file read — no in-memory templating, no per-call merge overhead.
- Anthropic API prompt caching benefits: the merged SKILL.md is stable for the (ide, model) tuple, so repeated invocations within a session hit the cache.

## Reference implementation

- `scripts/skill_profile.py` — `merge_skill_markdown`, `resolve_variant_overlay`, `_strip_existing_overlays`
- `scripts/skill_profile_detect.py` — `detect_ide`, `detect_model`, `normalize_model_profile_slug`, `VALID_IDES`, `VALID_MODELS`
- `scripts/skill_profile_session.py` — `load_session_state`, `save_session_state`, `resolve_profile`
- `scripts/skill_profile_rebuild.py` — `rebuild_skills` with sha256 cache
- `scripts/hooks/session_start.py::_auto_rebuild_skills` — SessionStart hook integration

## Migration from flat layout

If you maintain a TAUSIK skill repo using the legacy flat `variants/<slug>.md`:

1. Decide whether each overlay is **IDE-specific** or **model-specific**.
2. Move `variants/<slug>.md` → `variants/ide/<slug>.md` or `variants/model/<slug>.md`.
3. Run `tausik skill rebuild --force` to regenerate merged files.
4. The flat layout still works (backward compat) — migration is optional but recommended.
