---
slug: v14b-brain-universality-heuristic
title: "B3: heuristic для brain artifact universality (RBAC/JWT/rate-limit auto-suggest)"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/brain_universality.py (new), scripts/service_knowledge.py, scripts/brain_runtime.py, tests/test_brain_universality.py (new), tests/test_service_knowledge.py (or new integration test file), docs/{en,ru}/memory-merge-guidelines.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/brain_classifier.py (routing logic не меняется, добавляем suggestion поверх), brain_scrubbing.py, MCP layer (B3 — heuristic в pipeline, not CLI command)"
relevant_files:
  - "scripts/brain_universality.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_knowledge_hygiene.py"
  - "scripts/service_knowledge_exploration.py"
  - "scripts/brain_runtime.py"
  - "tests/test_brain_universality.py"
  - "tests/test_brain_universality_integration.py"
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T23:54:07Z"
---

## Goal

Добавить простой anti-pattern matcher в brain pipeline: regex/keyword detector для RBAC, JWT, OAuth, rate-limit, pagination, retry. При detect → suggest пользователю запустить `tausik brain propose-artifact`. Закрывает gap «эвристика для universality» из original задачи 1.

## Acceptance Criteria

1. New scripts/brain_universality.py с pure-функцией detect_universal_patterns(content: str) -> list[str], без deps. 2. Покрывает 8+ топиков: rbac, jwt, oauth, rate-limit, pagination, retry, idempotency, webhook (regex/keyword based, case-insensitive, word-boundary aware). 3. Возвращает unique sorted slugs, [] если ничего не подошло. 4. Helper format_universality_hint(topics) -> str; emits 'Universal pattern(s) detected: ... — consider promoting via `brain_draft_artifact` (or skip with `confirm: cross-project`).' Empty list → ''. 5. service_knowledge.memory_add и decide вызывают detect и печатают hint в stderr (не блокирует) когда классификатор маршрутизировал в brain И detect нашёл patterns. 6. brain_runtime.try_brain_write_* (decision/memory) — те же hints в success path. 7. Tests/test_brain_universality.py: ≥10 кейсов (positive для каждого топика, negative для project-specific текста, false-positive guard для substring 'rate' внутри 'aggregate', empty/whitespace, multi-topic dedup). 8. tests/test_service_knowledge.py или test_brain_classifier.py: integration тест что hint появляется в stderr при memory_add brain-routed с universal content. 9. Docs/{en,ru}/memory-merge-guidelines.md: упоминание heuristic + список топиков. 10. CHANGELOG.md + CHANGELOG.ru.md. 11. Negative: hint никогда не блокирует write; не выходит при empty input. 12. ruff + mypy + pytest + filesize green.

## Plan

[{"step": "Build scripts/brain_universality.py with detect_universal_patterns + format_universality_hint", "done": true}, {"step": "Wire hint into service_knowledge.memory_add + decide brain-routed paths (stderr, non-blocking)", "done": true}, {"step": "Wire hint into brain_runtime.try_brain_write_decision + try_brain_write_memory success paths", "done": true}, {"step": "Write tests/test_brain_universality.py (~12 cases: per-topic positive, negatives, dedupe)", "done": true}, {"step": "Add integration test for service_knowledge hint emission", "done": true}, {"step": "Update docs/{en,ru}/memory-merge-guidelines.md with heuristic mention", "done": true}, {"step": "CHANGELOG en+ru", "done": true}, {"step": "ruff + mypy + pytest + filesize gates", "done": true}]

## Rollback

## Journal

- 2026-05-06T23:39:56Z [implementation] — SCOPE FINDING: try_brain_write_memory не существует. Реальные точки emission: (1) brain_runtime.try_brain_write_decision success path; (2) brain_runtime.try_brain_write_web_cache success path; (3) service_knowledge.memory_add — всегда (там нет brain routing вовсе). decide() НЕ дублирует — оно идёт через try_brain_write_decision. AC #5/#6 переформулированы по факту, дух сохранён.
- 2026-05-06T23:54:07Z [implementation] — AC verified: 1. ✓ scripts/brain_universality.py detect_universal_patterns(content) pure stdlib, zero deps (только re) 2. ✓ _TOPIC_PATTERNS покрывает 8 slugs: rbac, jwt, oauth, rate-limit, pagination, retry, idempotency, webhook; все регексы re.IGNORECASE + word boundaries 3. ✓ return sorted(found) — sorted unique; tests test_empty_string_returns_empty_list, test_multi_topic_sorted_and_unique 4. ✓ format_universality_hint выдаёт точно AC-формат с brain_draft_artifact и confirm: cross-project; empty list to empty string. Тесты test_format_* 5. ✓ RE-SCOPED (см. task_log): try_brain_write_memory не существует. memory_add не auto-роутит в brain — hint emit ВСЕГДА (service_knowledge.py memory_add). decide() идёт через try_brain_write_decision и hint поступает оттуда (см. AC#6). Дух AC сохранён, буква переформулирована честнее под реальную архитектуру. 6. ✓ RE-SCOPED: hint emit в success-путях try_brain_write_decision (brain_runtime.py) и try_brain_write_web_cache (brain_runtime.py). try_brain_write_memory не существовало — task_log зафиксировал решение. 7. ✓ tests/test_brain_universality.py: 33 кейса (16 per-topic positives, 4 negatives, 4 false-positive guards для aggregate/oauthorization/jwt-substring/retry-substring, 3 multi-topic dedupe/sort/case, 4 format helper, 1 pathological input). pytest 33/33 passed. 8. ✓ tests/test_brain_universality_integration.py: 8 кейсов — memory_add emission, brain_runtime decision/web_cache success path emission, false-positive guard для aggregate, blow-up детектора не ломает write. pytest 8/8 passed. 9. ✓ docs/en/memory-merge-guidelines.md и docs/ru/memory-merge-guidelines.md — секция Universality heuristic (B3, v1.4 polish) с описанием 8 топиков и word-boundary защиты 10. ✓ CHANGELOG.md и CHANGELOG.ru.md — запись v14b-brain-universality-heuristic в Unreleased/v1.4.0 polish 11. ✓ emit_universality_hint обёрнут try/except Exception: pass — never raises. test_memory_add_succeeds_when_hint_emission_fails и test_brain_runtime_hint_failure_does_not_break_write подтверждают что blow-up детектора возвращает True/page-id и не ломает write. format_universality_hint([]) пустой — empty input silent. 12. ✓ ruff All checks passed; mypy Success no issues found in 5 source files; pytest 3047 passed full sweep после regen constants.json; filesize gate green после side-split (service_knowledge.py 431 to 364 через extract в service_knowledge_hygiene.py и service_knowledge_exploration.py)
