---
slug: km-retrieval-baseline-eval
title: "Базовый замер retrieval памяти: одна воспроизводимая цифра до любых изменений"
status: done
epic: shared-knowledge
story: km-knowledge-layer
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: "NEW scripts/eval_memory_retrieval.py (harness + committed content-based question set); tests/test_eval_memory_retrieval.py (determinism + id-independence + hit/miss); CHANGELOG.md + CHANGELOG.ru.md. Read-only over the memory table (FTS5). Baseline number recorded in the task log."
scope_exclude: null
relevant_files:
  - "scripts/eval_memory_retrieval.py"
  - "tests/test_eval_memory_retrieval.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/eval_memory_retrieval.py"
  - "tests/test_eval_memory_retrieval.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T14:15:18Z"
---

## Goal

Шаг 1 из 6 в переработке слоя знаний (решение #143, эпик shared-knowledge). Блокирует осмысленную приёмку шагов 3 и 6.

Зачем. Исследование (рой, сессия #115) показало: публичных доказательств, что консолидация знаний в темы улучшает качество ответов, НЕТ. Все крупные цифры за консолидацию меряны против полноконтекстного соломенного чучела, а единственный контролируемый контраст в обратную сторону (MemDelta 42% против 47%) сам опровергнут по мощности выборки. Никто не мерил именно нашу базовую линию: FTS5-поиск по 227 плоским записям. Поэтому переработку нельзя обосновывать качеством — обоснование это командное слияние и сокращение инъецируемого контекста. Но чтобы через полгода знать, не стало ли хуже, цифра нужна СЕЙЧАС, до изменений.

Задача: scripts/eval_memory_retrieval.py плюс зафиксированный в репозитории набор ~50 вопросов, на которые свежий агент должен уметь ответить из существующей памяти (по мотивам реальных ситуаций: «чем откатывать мутацию», «почему прогон по затронутым файлам не доказательство», «где живут внутренние исследования»). Скрипт печатает ОДНУ цифру точности и детализацию по вопросам.

Критерий приёмки: скрипт воспроизводимо печатает единственную цифру точности по закоммиченному набору вопросов; цифра записана в журнал задачи как базовая линия.

Негативный сценарий: набор вопросов не должен зависеть от конкретных id записей (они изменятся при консолидации) — только от содержания.

## Acceptance Criteria

1. scripts/eval_memory_retrieval.py воспроизводимо печатает ЕДИНСТВЕННУЮ цифру точности по закоммиченному набору ~50 вопросов плюс детализацию по вопросам. 2. Цифра записана в журнал задачи как базовая линия. 3. Набор вопросов не зависит от конкретных id записей — только от содержания (после реиндексации/смены id цифра не меняется). 4. НЕГАТИВ/граница: при ПУСТОЙ памяти или недоступной/битой БД скрипт не падает — печатает 0.0 точности (0 попаданий) с явным сообщением, а пустой запрос/вопрос без ожидаемого маркера обрабатывается как промах, а не как ошибка.

## Plan

## Rollback

git revert — NEW scripts/eval_memory_retrieval.py + committed question set + tests/test_eval_memory_retrieval.py + changelog. Read-only measurement tool over the memory table; no schema/data/behavior change, so deleting the files fully reverts.

## Journal

- 2026-07-27T14:13:51Z [implementation] — BASELINE (AC1/AC2): scripts/eval_memory_retrieval.py over a committed 49-question, content-keyed set → 100.0% (49/49) at top-5, 98.0% (48/49) at top-1, over the current 325-entry flat memory store (FTS5 + bm25). PROTOCOL: each query is the 2-3 distinctive concept tokens a recalling agent would type; a hit = an expected content marker appears in the top-K. INTERPRETATION (honest): this is a CEILING measurement for KEYWORD-ANCHORED facts — TAUSIK's memory titles are keyword-rich (fail-open, scan-target, relevant_files, capability-rank, знаменатель, канал…) so a distinctive-term FTS search retrieves them near-perfectly. This directly SUPPORTS decision #143's framing: the topic-consolidation rework is NOT justified by retrieval accuracy on these facts (already at ceiling) — its justification is command-merge + smaller injected context. VALUE as a regression probe: fixed queries + content markers, id-independent (test proves same score after an id shift), so re-running after consolidation detects any DROP below top-5. CAVEAT (future work, noted in script): a harder natural-language-paraphrase set — queries independent of the entry's own tokens, and in the corpus language (RU) — would stress ranking more; the FTS is implicit-AND with no stemming, so verbose/wrong-inflection queries retrieve nothing (a real property, not a harness flaw).
- 2026-07-27T14:14:59Z [implementation] — AC verified: 1. ✓ AC1: scripts/eval_memory_retrieval.py prints ONE accuracy number + per-question detail over a committed 49-question set. Reproducible: test_deterministic asserts identical output across runs. Live: 100.0% top-5 / 98.0% top-1 over 325 entries. 2. ✓ AC2: baseline recorded in task log (100% top-5, 98% top-1) with honest interpretation (ceiling for keyword-anchored facts; supports decision #143). 3. ✓ AC3 (id-independence): questions keyed on content markers, never ids. test_id_independent inserts the same content at DIFFERENT ids (decoys first) and asserts identical accuracy. test_marker_matching_is_case_insensitive confirms content-based hits. 4. ✓ AC4 (negative/boundary): test_empty_store_is_zero_not_crash (empty DB → 0.0, no crash), test_committed_set_runs_without_error_on_empty_store (real 49-set runs end-to-end → 0.0, no crash), main() catches unreadable-DB → prints 0.0. Per-question search error caught → miss, not crash.
- 2026-07-27T14:15:10Z [implementation] — AC-1: ✓ tests/test_eval_memory_retrieval.py::test_single_accuracy_number + test_deterministic. AC-3: ✓ tests/test_eval_memory_retrieval.py::test_id_independent + test_marker_matching_is_case_insensitive. AC-4: ✓ tests/test_eval_memory_retrieval.py::test_empty_store_is_zero_not_crash + test_committed_set_runs_without_error_on_empty_store. Negative: empty/unreadable store → 0.0 accuracy, never crash (test_empty_store_is_zero_not_crash).
- 2026-07-27T14:15:16Z [implementation] — AC-1 ✓ test_single_accuracy_number/test_deterministic; AC-2 ✓ baseline logged (100% top-5); AC-3 ✓ test_id_independent; AC-4 ✓ test_empty_store_is_zero_not_crash. See prior task logs for full evidence.
