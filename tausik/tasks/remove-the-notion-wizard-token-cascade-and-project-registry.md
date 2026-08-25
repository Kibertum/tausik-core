---
slug: remove-the-notion-wizard-token-cascade-and-project-registry
title: "[1.9] Удалить мастер настройки Notion, каскад из трёх способов хранения токена и реестр проектов"
status: planning
epic: shared-knowledge
story: kb-notion
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Вынесено из kb-notion-publisher решением #220, потому что не влезает в её бюджет и не даёт пользователю ничего наблюдаемого. Это ГИГИЕНА, а не возможность.

ОБЪЁМ, ИЗМЕРЕННЫЙ РАЗВЕДКОЙ, А НЕ ОЦЕНЁННЫЙ:
- Удалить целиком 6 файлов, 1425 строк: brain_init.py (368), brain_discovery.py (258), brain_project_registry.py (285), brain_init_join.py (190), brain_init_schemas.py (186), brain_init_create.py (138).
- Править ~9 файлов, ~200 строк: brain_runtime (_parse_dotenv 21 строка + resolve_brain_token 38), brain_config (compute_project_hash, валидация токена, ключи DEFAULT_BRAIN), brain_cli_ops (ветка init ~70), project_parser_brain (подпарсер ~60), brain_mcp_write (_resolve_project_name и project_hash), brain_scrubbing/brain_classifier/brain_status/brain_move, MCP handlers.
- Тесты: ~2200 строк. Целиком уходят test_brain_init.py (69 тестов, 1565 строк), test_brain_project_registry.py (29 тестов), test_brain_token_resolve.py (7 тестов); частично затронуты ещё 6-8 файлов.
- Документация: 18 файлов с ЗЕРКАЛАМИ ru/en, и в репозитории есть audit_translation_drift.py, который расхождение поймает.

ЛОВУШКА, НАЙДЕННАЯ РАЗВЕДКОЙ: реестр проектов нужен НЕ ТОЛЬКО мастеру. all_project_names() даёт union-блоклист скрабберу (brain_scrubbing, флаг union_with_registry), классификатору и brain_status — чтобы проект A не слил имя проекта B в общую вики. Удалять реестр, не заменив этот блоклист, значит ОСЛАБИТЬ приватность на границе публикации. Это отдельное решение внутри задачи, а не деталь.

ВТОРАЯ ЛОВУШКА: tests/conftest.py даёт фикстуру изоляции реестра для всего, что идёт через scrub_with_config(union_with_registry=True) — общий узел, ломает больше, чем видно по грепу. И tests/test_crosscutting_registry.py держит baseline из 30 записей с правилом «может только уменьшаться»: удаление файла из baseline способно его уронить.

НЕГАТИВНЫЙ СЦЕНАРИЙ ОБЯЗАТЕЛЕН: после удаления проект БЕЗ настроенного Notion обязан работать так же, как сейчас, а проект С настроенным — публиковать без мастера. Тест должен проверять ОБЕ ветки, иначе «удалили и вроде работает» окажется «удалили и тихо сломали публикацию у тех, кто ей пользуется».

## Acceptance Criteria

## Plan

## Rollback

## Journal
