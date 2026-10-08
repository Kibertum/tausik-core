---
slug: rotted-citations-above-the-declared-remainder
title: "Регистр сгнивших цитат перестал быть пустым: две цитаты выше объявленного остатка"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_verify_first_contract.py"
scope_paths:
  - "tests/test_verify_first_contract.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T10:11:47Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

tausik coherence не показывает rotted_closure_evidence выше объявленного остатка. Заметки к выпуску 1.10 утверждают «регистр сгнивших цитат пуст», и выпуск с непустым регистром сделал бы это утверждение ложью в собственных заметках.

## Acceptance Criteria

1. Каждая из двух цитат получила ответ в журнале СВОЕЙ задачи: EVIDENCE-MOVED с новым адресом либо EVIDENCE-RETIRED с причиной и КОММИТОМ удаления. 2. НЕГАТИВНЫЙ: кандидат по похожести имени не принимается без чтения теста — если тест проверяет другое, это НЕ преемник, и ответ будет RETIRED, а не MOVED. 3. tausik audit evidence показывает ROTTED 0. 4. Объявленный остаток в tausik/gates.json НЕ поднимается: он может только уменьшаться, и рост — это сигнал, а не повод подвинуть число.

## Plan

## Rollback

Ответы пишутся в журнал задач, журнал append-only — откатывать нечего и нельзя; неверный ответ исправляется СЛЕДУЮЩЕЙ строкой журнала, а не удалением предыдущей.

## Journal

- 2026-09-29T10:10:23Z [implementation] — AC-1: ✓ обе цитаты получили ответ. test_brain_config.py — EVIDENCE-RETIRED в журналах всех ПЯТИ цитирующих задач, с причиной и КОММИТОМ 77703c4a (удалён вместе со своим предметом, транспорт Notion упразднён, решение #358). test_verify_first_contract.py::test_fallback_skipped_when_no_verify_row — EVIDENCE-MOVED на test_fallback_ignores_a_row_belonging_to_another_task. AC-2 НЕГАТИВНЫЙ: ✓ кандидат по похожести имени ОТВЕРГНУТ чтением — test_fallback_skipped_for_security_sensitive_paths проверяет другое; настоящий преемник назван в его собственном докстринге. AC-3: ✓ tausik audit evidence: ROTTED 0. AC-4: ✓ tausik/gates.json не тронут, остаток остался 0/0.
- 2026-09-29T10:10:31Z [implementation] — НАХОДКА В ХОДЕ РАБОТЫ, заведена отдельной задачей evidence-moved-swallows-a-trailing-period: первый мой ответ EVIDENCE-MOVED не засчитался молча — за адресом преемника стояла точка, и разбор (\S+) забрал её в адрес. Отказ без сообщения; поправлено СЛЕДУЮЩЕЙ строкой журнала, как и требует append-only. Это же и доказательство, что механизм ответов работает: вторая строка отменила первую без переписывания.
- 2026-09-29T10:22:19Z [done] — EVIDENCE-RETIRED: test_brain_config.py — файл удалён вместе со своим предметом коммитом 77703c4a (транспорт Notion, решение #358); преемника нет и быть не может
- 2026-09-29T10:22:20Z [done] — EVIDENCE-MOVED: test_verify_first_contract.py::test_fallback_skipped_when_no_verify_row => tests/test_verify_first_contract.py::test_fallback_ignores_a_row_belonging_to_another_task
- 2026-09-29T10:22:20Z [done] — НАБЛЮДЕНИЕ, стоившее второго захода: задача, которая ПИШЕТ про сгнившую цитату, сама становится её цитирующим. Находка снимается, только когда исход несёт КАЖДАЯ цитирующая задача, а моё описание работы упомянуло оба адреса прозой — и регистр снова показал 2. Это не дефект аудита: он считает упоминание упоминанием и прав. Вывод для следующего: вместе с ответами в чужих журналах ставь ответы и в своём.
