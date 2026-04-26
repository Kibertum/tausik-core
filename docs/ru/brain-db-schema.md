[English](../en/brain-db-schema.md) | **Русский**

# Brain Notion Databases — Схема v1

Design-doc подсистемы `shared-brain`. Фиксирует структуру 4 Notion databases, которые образуют кросс-проектную базу знаний TAUSIK: `decisions`, `web_cache`, `patterns`, `gotchas`. Все проекты пишут сюда обобщаемые знания; приватная «суть» проекта остаётся в локальной `.tausik/tausik.db`.

Статус: реализовано в v1.3.0. См. также: [shared-brain.md](shared-brain.md), [architecture.md](architecture.md).

> Полная техническая спецификация (типы свойств, JSON-payload для `pages.create`, delta-pull механика, edge-cases) — на английском в [brain-db-schema.md](../en/brain-db-schema.md). Здесь приводится концептуальный обзор.

## 4 базы данных

| База | Назначение | Ключевые поля |
|---|---|---|
| **decisions** | Архитектурные решения, обобщаемые между проектами | `Title`, `Decision Date`, `Stack Tags`, `Source Project Hash`, `Confidence`, `Rationale` |
| **web_cache** | Кэш `WebFetch` ответов для повторного использования | `URL`, `Content Hash`, `Fetched At`, `Content`, `Source Project Hash` |
| **patterns** | Паттерны (best practices) применимые между проектами | `Title`, `Stack Tags`, `Severity`, `Code Sample`, `Source Project Hash` |
| **gotchas** | Подводные камни (anti-patterns) | `Title`, `Stack Tags`, `Severity`, `Repro`, `Source Project Hash` |

## Privacy

Имена проектов хешируются: `SHA256(canonical_name)[:16]` = 64 бита. В Notion никогда не уходит plaintext имени проекта — только hash. Канонизация: `unicodedata.normalize("NFC")` + `strip().lower()` + замена пробелов на `-`.

## Pull-sync

`scripts/brain_sync.py` делает delta-fetch по `last_edited_time` cursor. Single-tx upsert + WAL-mode для concurrent-read safety. На любую ошибку категории `last_error` пишется в `sync_state` table.

## Scrubbing

Перед записью в Notion `scripts/brain_scrubbing.py` проверяет:
- `private_url_patterns` — список regex'ов из `.tausik/config.json`
- `project_names_blocklist` — union с registry других проектов
- Homoglyph normalization для устойчивости к Unicode-confusables

См. также: [shared-brain.md](shared-brain.md) — пользовательский гайд + setup wizard.
