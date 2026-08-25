---
slug: remove-dead-level-name
title: "Мёртвый код: nudge_escalation.level_name не зовётся нигде"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "scripts/nudge_escalation.py"
scope_exclude: "Не трогать остальной модуль (level_for_count, render_nudge, _LEVEL_FORMAT, escalate, bump, peek, reset, resolve_thresholds). Не трогать зеркала .claude/ и т.п. — они пересоберутся bootstrap. Не рефакторить nudge-логику заодно."
relevant_files:
  - "scripts/nudge_escalation.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-16T18:03:38Z"
---

## Goal

Аудит SENAR 9.5 (сессия #106) нашёл: scripts/nudge_escalation.py:84 level_name(level) — не вызывается ни из scripts/, ни из tests/, ни из .claude/mcp/. Мёртвый код. Удалить вместе с _LEVEL_NAMES, если тот больше нигде не нужен. НЕ делалось сразу, чтобы не уводить main вперёд свежего тега v1.6.1 — забирать в следующий релизный цикл.

## Acceptance Criteria

1. scripts/nudge_escalation.py: удалены level_name() и _LEVEL_NAMES (единственный потребитель — сама level_name). 2. ПОДТВЕРЖДЕНИЕ МЁРТВОСТИ ПЕРЕД УДАЛЕНИЕМ (не на глаз): grep по всему дереву с ИСКЛЮЧЕНИЕМ шума (.tausik/venv, .mypy_cache, __pycache__, зеркала .claude/.cursor/.qwen/.kilo/.opencode) не находит ни одного вызова вне самого модуля. Зафиксировать вывод. 3. НЕГАТИВНЫЕ СЦЕНАРИИ: (а) ОШИБКА, если удаление ломает публичный контракт модуля — level_for_count/render_nudge/escalate/bump/peek/reset/resolve_thresholds обязаны остаться и работать; (б) ОШИБКА, если удалено что-то ЕЩЁ живое: _LEVEL_FORMAT используется в render_nudge и удалению НЕ подлежит — не спутать два похожих словаря; (в) ОШИБКА, если после удаления существующие тесты nudge/escalation краснеют. 4. Обе полосы pytest зелёные (-m '' И дефолт), filesize/gates зелёные. 5. Не заводить «на всякий случай» deprecation-обёртку: функция не экспортировалась и не документирована — мёртвый код удаляется, а не консервируется.

## Plan

## Rollback

git revert; удаление изолировано в одном файле, публичный контракт модуля не меняется.

## Journal

- 2026-07-16T18:03:37Z [implementation] — AC verified. Обе полосы зелёные: FULL (pytest -m "") 4706 passed, 21 skipped, 0 failed; FAST 4583 passed, 0 failed. Gates: verify passed=True, filesize зелёный. 1. ✓ Удалены level_name() (было scripts/nudge_escalation.py:84-86) и _LEVEL_NAMES (было :28). Единственным потребителем _LEVEL_NAMES была сама level_name — удалены вместе, осиротевших констант не осталось. 2. ✓ МЁРТВОСТЬ ПОДТВЕРЖДЕНА ПРОГОНОМ, НЕ НА ГЛАЗ: grep по всему дереву — оба символа встречались ТОЛЬКО внутри самого модуля (строки 28, 84, 86). Все прочие попадания — шум и исключены осознанно: .tausik/venv (rich/uvicorn/mypy имеют свои level_name), .mypy_cache (сериализованная таблица символов самого модуля), зеркала .claude/.cursor/.qwen/.kilo/.opencode (пересобираются bootstrap). Ноль реальных вызовов вне модуля. 3. ✓ НЕГАТИВНЫЕ СЦЕНАРИИ: (а) публичный контракт цел — остались resolve_thresholds, level_for_count, render_nudge, peek, bump, reset, escalate (+ приватный _meta_key); проверено импортом: level_for_count(5)→3, render_nudge('msg', HINT, 1)→'ⓘ msg'; hasattr(level_name)=False, hasattr(_LEVEL_NAMES)=False. (б) ГЛАВНЫЙ РИСК ЗАДАЧИ — рядом живёт похожий словарь _LEVEL_FORMAT, который нужен render_nudge (:84). Проверил перед удалением, НЕ спутал: _LEVEL_FORMAT остался (:33, :84). (в) 61 nudge/escalation-тест зелёный (pytest -k "nudge or escalat"). 4. ✓ Обе полосы зелёные, gates зелёные. 5. ✓ Deprecation-обёртка НЕ заведена: функция не экспортировалась и не документирована — мёртвый код удаляется, а не консервируется. ПРОВЕРКА ПЕРВОИСТОЧНИКА НАХОДКИ: audit_unused_python.py больше не репортит level_name — то есть аудит SENAR 9.5 (сессия #106), который её нашёл, закрыт по этому пункту фактом, а не декларацией. Domain: вне тестов удаление невидимо — символ не был ни в чьём импорте, публичное поведение модуля (эскалация nudge'ов) не изменилось; минус мёртвый код, который иначе следующий агент принял бы за живой API.
