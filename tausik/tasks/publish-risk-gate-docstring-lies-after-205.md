---
slug: publish-risk-gate-docstring-lies-after-205
title: "Докстринг гейта риска публикации утверждает «Only patterns/gotchas apply» после того, как решения в него завели (#205)"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: developer
stack: python
tier: light
call_budget: 18
defect_of: brain-decide-publishes-unclassified-rationale
scope: "scripts/brain_publish_flow.py (докстринги), docs/ru и docs/en при расхождении, tests/ (тест соответствия перечня реестру). После правки scripts/ обязателен bootstrap --ide all."
scope_exclude: "НЕ менять ветвления и состав _CLASSIFIER_CATEGORY — задача про истинность утверждения, а не про поведение. НЕ трогать решение #205 и его тесты."
relevant_files:
  - "scripts/brain_publish_flow.py"
scope_paths:
  - "scripts/brain_publish_flow.py"
  - "docs/ru/*"
  - "docs/en/*"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T19:31:54Z"
---

## Goal

Найдено в сессии #153 при ревизии kb-brain-deprecate.

scripts/brain_publish_flow.py:97 — докстринг maybe_block_high_risk_publish говорит «Return (blocked, message). Only patterns/gotchas apply.» Это перестало быть правдой в сессии #152: решением #205 категория decisions добавлена в _CLASSIFIER_CATEGORY (строка 14: {"patterns": "pattern", "gotchas": "gotcha", "decisions": "decision"}), и ветвление на строках 98-100 теперь пропускает решения в гейт наравне с остальными.

ПОЧЕМУ ЭТО НЕ ПРИДИРКА. Именно этот докстринг был УЛИКОЙ в расследовании brain-decide-publishes-unclassified-rationale: его цитировали как доказательство того, что решения из гейта исключены («докстринга прямо говорит Only patterns/gotchas apply»). Строка, работавшая свидетельством о поведении кода, продолжает свидетельствовать — теперь ложно. Следующий агент, читающий этот файл, сделает тот же вывод и на тех же основаниях, но вывод будет неверным.

Дополнительно проверить и поправить, если расходится: перечисление категорий в докстринге assess_publish_risk и упоминания гейта риска в docs/ru и docs/en.

## Acceptance Criteria

1. Докстринг maybe_block_high_risk_publish перестаёт утверждать «Only patterns/gotchas apply» и называет фактический состав категорий гейта после решения #205.
2. Утверждение о составе НЕ дублирует реестр прозой: докстринг либо ссылается на _CLASSIFIER_CATEGORY как на источник, либо перечень выводится из него. Конвенция #339 — перечень в прозе, дублирующий реестр, обязан выводиться из источника тестом.
3. Тест закрепляет соответствие: добавление категории в _CLASSIFIER_CATEGORY без обновления документирующего перечня валит тест. Падает до фикса на текущем состоянии.
4. Проверены и приведены в соответствие смежные утверждения: докстринг assess_publish_risk и упоминания состава гейта риска в docs/ru и docs/en. Для каждого проверенного места в журнале сказано «расходилось и исправлено» или «проверено, расхождения нет» — второе тоже доказательство, что место рассмотрено.
5. НЕГАТИВ: поведение кода НЕ меняется. Существующие тесты гейта риска (в том числе test_decisions_are_subject_to_the_publish_risk_gate и test_generic_decision_is_not_blocked_by_the_risk_gate) остаются зелёными без правки ожиданий; диф не содержит изменений в ветвлениях.
6. Полный pytest зелёный; ruff и mypy чистые; docs_lint чистый.
Записи в CHANGELOG НЕ ДОБАВЛЯЮТСЯ: пользовательского изменения нет, правится комментарий, описывающий уже отгруженное поведение. Закрытие идёт с --no-changelog, причина названа в журнале.

## Plan

## Rollback

git revert. Изменение затрагивает только докстринги, документацию и один тест соответствия; поведение не меняется, поэтому откат не может ничего сломать — он лишь возвращает ложное утверждение в код.

## Journal

- 2026-08-03T19:27:12Z [implementation] — AC4, поимённо, каждое место ОТКРЫТО и проверено. РАСХОДИЛОСЬ И ИСПРАВЛЕНО: (1) модульный докстринг brain_publish_flow.py, первая строка говорила '(patterns/gotchas)' — та же ложь, что и в maybe_block_high_risk_publish, только строкой выше и незамеченная в постановке задачи; (2) maybe_block_high_risk_publish — 'Only patterns/gotchas apply'. ДОБАВЛЕНО, ГДЕ НЕ БЫЛО: (3) assess_publish_risk докстринга не имел вовсе — ложного утверждения там не было, но и верного тоже; теперь называет реестр и объясняет, что 'low' для незарегистрированной категории означает 'классификатора нет', а НЕ 'содержимое проверено и безопасно'. ПРОВЕРЕНО, РАСХОЖДЕНИЯ НЕТ: (4) docs/ru/shared-brain.md:280 и docs/en/shared-brain.md:281 — описывают РОЛЬ классификатора, исчерпывающего перечня категорий не содержат; (5) docs/ru/memory-merge-guidelines.md:7,23 и англоязычное зеркало — то же; (6) docs/ru/mcp.md и docs/en/mcp.md — утверждений о составе гейта риска нет. Правок в доках не потребовалось, и это результат проверки, а не пропуск. AC5: диф содержит ТОЛЬКО докстринги — фильтр по строкам с if/return/= на дифе пуст, 55 тестов гейта зелёные без правки ожиданий. AC3: тест ПРОВЕРЕН на красноту — возврат ложного предложения валит две проверки из восьми, возврат правки делает их зелёными. Без CHANGELOG сознательно: пользовательского изменения нет, правится комментарий о уже отгруженном поведении.
- 2026-08-03T19:30:58Z [implementation] — СВЕРХ ЗАДАЧИ, найдено при проверке самой проверки. Убедившись, что verify зелёный, я спросил РЕЗОЛВЕР, какие тесты он вообще сопоставил модулю: девять файлов, ни один не касается гейта публикации. Единственное поведенческое покрытие brain_publish_flow (включая test_decisions_are_subject_to_the_publish_risk_gate, названный в AC5 этой задачи) живёт в tests/test_decide_classifies_what_it_publishes.py — файл сохранил историческое имя намеренно по решению #221 и CROSSCUTTING_SCOPE не объявлял, а маппер идёт от ИМЕНИ. То есть мой зелёный verify по этому модулю не означал ничего. Экземпляр закрыт здесь: CROSSCUTTING_SCOPE объявлен, маппинг проверен ЗАПУСКОМ резолвера (файл теперь в наборе), 10 тестов зелёные. Общая форма заведена отдельной задачей verify-certifies-a-run-that-touched-no-test-of-the-subject и ВЫНЕСЕНА В 1.9 решением #229 — поимённо, не молчанием: чинить резолвер верификации в день выпуска значит обесценить все замеры, которыми измерен остальной релиз.
- 2026-08-03T19:31:35Z [implementation] — AC-1: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_every_gated_category_is_named AC-2: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_the_registry_is_what_the_code_actually_branches_on AC-2: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_decisions_really_are_in_the_registry AC-3: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_no_docstring_claims_the_gate_is_narrower_than_it_is AC-4: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_every_gated_category_is_named AC-5: ✓ tests/test_decide_classifies_what_it_publishes.py::test_decisions_are_subject_to_the_publish_risk_gate AC-5: ✓ tests/test_decide_classifies_what_it_publishes.py::test_generic_decision_is_not_blocked_by_the_risk_gate AC-6: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_the_registry_is_what_the_code_actually_branches_on AC-3 ПРОВЕРЕН НА КРАСНОТУ, а не объявлен зелёным: возврат предложения «Only patterns/gotchas apply» валит две проверки из восьми (test_every_gated_category_is_named и test_no_docstring_claims_the_gate_is_narrower_than_it_is для maybe_block_high_risk_publish); возврат правки делает их зелёными. AC-4 поимённо. РАСХОДИЛОСЬ И ИСПРАВЛЕНО: модульный докстринг brain_publish_flow.py (говорил «(patterns/gotchas)» — та же ложь строкой выше, в постановке задачи не названа); maybe_block_high_risk_publish. ДОБАВЛЕНО, ГДЕ НЕ БЫЛО: assess_publish_risk докстринга не имел вовсе. ПРОВЕРЕНО, РАСХОЖДЕНИЯ НЕТ: docs/ru/shared-brain.md:280, docs/en/shared-brain.md:281, docs/ru/memory-merge-guidelines.md:7 и :23, англоязычное зеркало, docs/ru/mcp.md, docs/en/mcp.md — все описывают РОЛЬ классификатора и исчерпывающего перечня категорий не содержат. AC-5 доказан ДИФОМ, а не только тестами: фильтр дифа по строкам, содержащим if/return/=, пуст — изменены только докстринги. 55 тестов области зелёные без правки ожиданий. Домен: перечень в прозе выведен из реестра ТЕСТОМ, а не переписан руками, поэтому четвёртая категория в _CLASSIFIER_CATEGORY уронит проверку, а не разойдётся с ней молча (конвенция #339). CHANGELOG сознательно не трогается: пользовательского изменения нет, правится комментарий об уже отгруженном поведении.
- 2026-08-03T19:31:51Z [implementation] — Root cause (documentation): реестр _CLASSIFIER_CATEGORY получил третью категорию (decisions, решение #205), а три докстринга, ПЕРЕЧИСЛЯВШИЕ его состав прозой, остались на двух — прозаический перечень был вторым источником истины, ничем не связанным с первым. Вред нанесён не самой неточностью, а тем, что строку ЦИТИРОВАЛИ как доказательство поведения при расследовании brain-decide-publishes-unclassified-rationale: предложение, однажды служившее уликой, продолжает читаться как улика после того, как перестало быть правдой. Prevention: перечень, дублирующий реестр, обязан выводиться из реестра ТЕСТОМ, а не поддерживаться руками (конвенция #339) — добавлен tests/test_publish_risk_gate_docs_match_registry.py, который валится при добавлении категории без правки слов и запрещает саму форму 'Only X and Y apply'; тест проверен на красноту до фикса.
- 2026-08-03T19:31:52Z [implementation] — AC-1: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_every_gated_category_is_named AC-2: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_the_registry_is_what_the_code_actually_branches_on AC-2: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_decisions_really_are_in_the_registry AC-3: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_no_docstring_claims_the_gate_is_narrower_than_it_is AC-4: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_every_gated_category_is_named AC-5: ✓ tests/test_decide_classifies_what_it_publishes.py::test_decisions_are_subject_to_the_publish_risk_gate AC-5: ✓ tests/test_decide_classifies_what_it_publishes.py::test_generic_decision_is_not_blocked_by_the_risk_gate AC-6: ✓ tests/test_publish_risk_gate_docs_match_registry.py::test_the_registry_is_what_the_code_actually_branches_on AC-3 ПРОВЕРЕН НА КРАСНОТУ, а не объявлен зелёным: возврат предложения «Only patterns/gotchas apply» валит две проверки из восьми (test_every_gated_category_is_named и test_no_docstring_claims_the_gate_is_narrower_than_it_is для maybe_block_high_risk_publish); возврат правки делает их зелёными. AC-4 поимённо. РАСХОДИЛОСЬ И ИСПРАВЛЕНО: модульный докстринг brain_publish_flow.py (говорил «(patterns/gotchas)» — та же ложь строкой выше, в постановке задачи не названа); maybe_block_high_risk_publish. ДОБАВЛЕНО, ГДЕ НЕ БЫЛО: assess_publish_risk докстринга не имел вовсе. ПРОВЕРЕНО, РАСХОЖДЕНИЯ НЕТ: docs/ru/shared-brain.md:280, docs/en/shared-brain.md:281, docs/ru/memory-merge-guidelines.md:7 и :23, англоязычное зеркало, docs/ru/mcp.md, docs/en/mcp.md — все описывают РОЛЬ классификатора и исчерпывающего перечня категорий не содержат. AC-5 доказан ДИФОМ, а не только тестами: фильтр дифа по строкам, содержащим if/return/=, пуст — изменены только докстринги. 55 тестов области зелёные без правки ожиданий. Домен: перечень в прозе выведен из реестра ТЕСТОМ, а не переписан руками, поэтому четвёртая категория в _CLASSIFIER_CATEGORY уронит проверку, а не разойдётся с ней молча (конвенция #339). CHANGELOG сознательно не трогается: пользовательского изменения нет, правится комментарий об уже отгруженном поведении.
