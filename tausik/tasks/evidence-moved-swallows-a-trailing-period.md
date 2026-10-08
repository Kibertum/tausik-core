---
slug: evidence-moved-swallows-a-trailing-period
title: "Ответ EVIDENCE-MOVED молча не засчитывается, если за адресом стоит точка"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: closure-citations-rot-is-detected-but-never-acted-on
scope: null
scope_exclude: null
relevant_files:
  - "scripts/closure_amendments.py"
  - "tests/test_closure_amendments.py"
scope_paths:
  - "scripts/closure_amendments.py"
  - "tests/test_closure_amendments.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T10:20:41Z"
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

Ответ EVIDENCE-MOVED засчитывается, когда автор закончил предложение точкой. Разбор берёт адрес как \S+, поэтому точка после адреса уезжает В адрес, адрес перестаёт резолвиться, и ответ молча не считается — отказ без сообщения, ровно тот класс, который проект объявил нулевой толерантностью.

## Acceptance Criteria

1. Замер ДО воспроизведён тестом: строка 'EVIDENCE-MOVED: a => tests/x.py::test_y.' даёт адрес с точкой и НЕ засчитывается. 2. После правки та же строка засчитывается, адрес — без точки. 3. НЕГАТИВНЫЙ: точка ВНУТРИ адреса не теряется — tests/x.py::test_y остаётся с расширением .py, обрезается только пунктуация, завершающая предложение. 4. НЕГАТИВНЫЙ: EVIDENCE-RETIRED с причиной, заканчивающейся точкой, по-прежнему разбирается как раньше — причина есть текст, её обрезать нельзя. 5. Полная лента зелёная.

## Plan

## Rollback

git revert; правка разбора, поведение уже написанных журналов не меняется — они разбираются заново при каждом запуске аудита.

## Journal

- 2026-09-29T10:20:28Z [implementation] — AC-1 замер ДО воспроизведён и AC-2 после правки: ✓ tests/test_closure_amendments.py::TestAnAddressIsNotASentence::test_sentence_punctuation_after_an_address_is_not_part_of_it — четыре формы (точка, запятая, точка с запятой, нечего обрезать). Реальный отказ был не гипотетический: первый же ответ MOVED в задаче rotted-citations-above-the-declared-remainder не засчитался молча. AC-3 НЕГАТИВНЫЙ: ✓ ::test_a_dot_inside_an_address_is_load_bearing — tests/x.py сохраняет расширение; обрезка по ПОЗИЦИИ, а не по классу символов. AC-4 НЕГАТИВНЫЙ: ✓ ::test_a_reason_keeps_its_own_full_stop — причина есть свободный текст, её точка остаётся.
- 2026-09-29T10:20:28Z [implementation] — Root cause (edge-case): формат объявляет адрес как ссылку, а разбор брал его как \S+ — в прозе за ссылкой почти всегда стоит знак препинания, и он уезжал в адрес. Класс отказа хуже самой ошибки: адрес не резолвился, ответ не засчитывался, и никто об этом не сообщал. Prevention: тест на четырёх формах пунктуации плюс два негатива — точка ВНУТРИ адреса несущая, а точка в причине принадлежит автору. AC-5: ✓ полная лента 12231 прошли, 34 пропущены. Заодно поправлены два храповика на моих же правках: комментарий с меткой замера переписан без неё, а тест про пунктуацию-ссылку получил второе утверждение, чтобы отличаться формой.
