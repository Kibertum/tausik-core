[English](/docs/skill-profiles) | **Русский**

# Skill profiles и `variants/` (v1.4 polish — B8-pre)

TAUSIK skills имеют один **`SKILL.md`** плюс опциональные **двухосные оверлеи**: per-IDE поведение и per-model стиль. Оси композируются независимо — `cursor-gpt-5` сессия использует тот же `model/gpt-5.md` overlay что и `claude-gpt-5` (DRY).

## Структура (актуальная)

```
harness/skills/<skill-name>/
  SKILL.md                  # Общие инструкции + YAML frontmatter
  variants/
    ide/
      claude.md             # Подмешивается когда активный IDE = claude
      cursor.md             # ...cursor
      qwen.md               # ...qwen
      codex.md              # ...codex
    model/
      opus.md               # Подмешивается когда активная модель = opus
      sonnet.md
      haiku.md
      gpt-4.md              # Добавлено в v14b-gpt-model-profile (B8)
      gpt-5.md              # то же
      gpt-5-5.md            # то же (форма `gpt-5.5` через точку нормализуется сюда)
      qwen.md
```

GPT overlays для `/plan`, `/task`, `/ship` намеренно **телеграфные** (≤25 строк каждый, императив, только delta — без перепечатывания base SKILL.md). Они подталкивают: агрессивные параллельные tool calls (особенно gpt-5/gpt-5-5), zero narrative reasoning, single-turn task completion. См. `harness/skills/{plan,task,ship}/variants/model/gpt-*.md`.

Старая плоская структура (`variants/<slug>.md`) всё ещё резолвится через `merge_skill_markdown(skill_dir, requested_profile=<slug>)` — оставлена для backward compatibility с внешними skill-репозиториями. Новые skills должны использовать двухосную структуру.

## Auto-detect на старте сессии

`scripts/hooks/session_start.py::_auto_rebuild_skills` резолвит `(ide, model)` по приоритету:

1. **Env override:** `TAUSIK_IDE_PROFILE`, `TAUSIK_MODEL_PROFILE`
2. **Project config:** `.tausik/config.json` ключи `ide_profile`, `model_profile`
3. **Auto-detect:** `scripts/skill_profile_detect.py` читает известные IDE env vars (`CLAUDE_CODE_*`, `CURSOR_*`, `QWEN_*`, `CODEX_*`) и model env vars (`ANTHROPIC_MODEL`, `OPENAI_MODEL`, `QWEN_MODEL` и др.). Модель часто `None` потому что Cursor/Qwen не выставляют активную модель в env — это нормально, IDE overlay всё равно применяется.

Hook сравнивает результат с `.tausik/.session.json`. На mismatch вызывает `rebuild_skills` — пересклеивает каждый `.claude/skills/<slug>/SKILL.md` на диске. **Cache hit (нет изменений) = no-op (микросекунды).** Re-merge идемпотентен — каждое склеивание сначала strip'ит существующие маркеры `<!-- tausik-profile:... -->` из base.

## Ручной override

```bash
tausik config show                              # показать (ide, model, source)
tausik config set ide_profile cursor            # сохранить override в .tausik/config.json
tausik config set model_profile gpt-5           # сохранить model override
tausik skill rebuild                            # ручной триггер; no-op когда нечего менять
tausik skill rebuild --force                    # переписать даже если sha256 совпадает
```

## Порядок merge

Двухосный merge (в этом порядке):

```
base SKILL.md  +  variants/ide/<ide>.md  +  variants/model/<model>.md
```

IDE constraints первыми (как host вызывает tools, runtime quirks). Model overlay последним (стилевые подсказки). Любой или оба overlay-а могут отсутствовать — молча пропускаются.

## Идемпотентность

`merge_skill_markdown` strip'ит всё начиная с первого маркера `<!-- tausik-profile:` перед re-merge. Это значит rebuild можно запускать многократно без накопления секций — merged файл всегда `base + ide + model`, никогда `base + ide + model + ide + model`.

## Frontmatter (legacy — только плоская структура)

| Поле | Значение |
|------|----------|
| `profile_fallback` | Когда `merge_skill_markdown(requested_profile=<slug>)` не находит `variants/<slug>.md`, пытается этот профиль для overlay lookup (только legacy flat — НЕ применяется к двухосной структуре). |

## Token economy

- Overlays должны быть **телеграфные** (≤30 строк каждый, императив). Длинные пояснения убивают экономию.
- Disk pre-merge → runtime cost = чтение файла. Никакого in-memory templating, никакого merge per-call.
- Anthropic API prompt caching: merged SKILL.md стабилен для (ide, model) tuple, повторные вызовы внутри сессии попадают в cache.

## Reference

- `scripts/skill_profile.py` — `merge_skill_markdown`, `resolve_variant_overlay`, `_strip_existing_overlays`
- `scripts/skill_profile_detect.py` — `detect_ide`, `detect_model`, `normalize_model_profile_slug`, `VALID_IDES`, `VALID_MODELS`
- `scripts/skill_profile_session.py` — `load_session_state`, `save_session_state`, `resolve_profile`
- `scripts/skill_profile_rebuild.py` — `rebuild_skills` с sha256 cache
- `scripts/hooks/session_start.py::_auto_rebuild_skills` — SessionStart hook интеграция

## Миграция со старой плоской структуры

Если вы поддерживаете TAUSIK skill repo на legacy flat `variants/<slug>.md`:

1. Решите, IDE-specific это overlay или model-specific.
2. Переместите `variants/<slug>.md` → `variants/ide/<slug>.md` или `variants/model/<slug>.md`.
3. Запустите `tausik skill rebuild --force` чтобы пересгенерить merged файлы.
4. Плоская структура всё ещё работает (backward compat) — миграция опциональна но рекомендована.
