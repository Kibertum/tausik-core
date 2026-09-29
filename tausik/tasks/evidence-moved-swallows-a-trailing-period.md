---
slug: evidence-moved-swallows-a-trailing-period
title: "Ответ EVIDENCE-MOVED молча не засчитывается, если за адресом стоит точка"
status: planning
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
relevant_files: []
scope_paths:
  - "scripts/closure_amendments.py"
  - "tests/test_closure_amendments.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
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
