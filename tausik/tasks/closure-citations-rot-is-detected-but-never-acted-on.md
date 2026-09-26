---
slug: closure-citations-rot-is-detected-but-never-acted-on
title: "Сорок четыре ссылки на доказательства в закрытых задачах не разрешаются, и детектор третью смену подряд сообщает об этом впустую"
status: active
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/audit_closure_evidence.py"
  - "scripts/closure_amendments.py"
  - "scripts/project_cli_audit.py"
  - "scripts/repo_coherence_collectors.py"
  - "tausik/gates.json"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР АУДИТА SENAR 9.5, СМЕНА #227, МЕХАНИЧЕСКИ. Просканированы ВСЕ 1362 закрытые задачи; в 630 из них найдено 3812 ссылок на доказательства (1490 уникальных), из которых разрешились 1433. Остаток: 26 ГНИЛЫХ (файл есть, имени в нём больше нет) и 18 НЕ СУЩЕСТВОВАВШИХ НИКОГДА (git такого имени не помнит), плюс 13 распознанных как пример-заглушка и справедливо не считаемых.

ЧТО ЭТО ЗНАЧИТ: 44 квитанции закрытия ссылаются на доказательство, которого по указанному адресу нет. Читатель, проверяющий закрытие, упирается в мёртвую ссылку и вынужден верить на слово — ровно то состояние, ради выхода из которого гейт закрытия требует ссылок вида путь::имя. Восемнадцать из них были неверны УЖЕ В МОМЕНТ НАПИСАНИЯ, что хуже гнили: это не деградация от переименования, а ссылка, которую никто не проверил, когда ставил.

ПОЧЕМУ ЗАДАЧА НУЖНА, ХОТЯ ДЕТЕКТОР УЖЕ ЕСТЬ. Детектор построен задачей closure-evidence-references-rot-and-nothing-notices и работает: он и дал эти числа. Но он ТОЛЬКО СООБЩАЕТ. Находка висит в выводе `tausik coherence` третью сверку подряд, и никто по ней не действует, поэтому каждая следующая сверка тратит время на повторное открытие того же. Детектор без адресата — это предупреждение, которое научились не замечать.

ЧТО ОБЛЕГЧАЕТ РАБОТУ: коллектор уже вычисляет successor_candidate для большинства гнилых ссылок — например tests/test_at.py::test_route_at_tc_ -> test_route_at_tc_red_red_is_code_defect, tests/test_otel_export.py::TestExportEnabled -> TestExportToggle, tests/test_cost_pricing.py::test_opus_1m_explicit_entry -> test_1m_explicit_entry. То есть для гнилых лечение механическое: ДОПИСАТЬ в журнал задачи заметку, называющую преемника (переписывать историю нельзя — квитанция подписана). Для восемнадцати не существовавших преемника нет, и каждую надо смотреть отдельно: либо покрытие есть под другим именем, либо его нет вовсе, и тогда это не гниль ссылки, а НЕДОКАЗАННОЕ ЗАКРЫТИЕ.

ПОЧЕМУ НЕ В 1.9: ни одно из двух обещаний релиза на этом не держится. Это гигиена доказательств — работа настоящая, но состав 1.9 она не проходит (решение #337).

## Acceptance Criteria

1. Замер до правки в журнале: числа tausik audit evidence сегодня и объявленный остаток в tausik/gates.json.
2. У находки есть исход: дописанная в журнал задачи поправка EVIDENCE-MOVED <старая> => <новая> (новая обязана разрешаться), EVIDENCE-RETIRED <ссылка> — <причина> (предмет удалён намеренно) или EVIDENCE-UNPROVEN <ссылка> — <причина> (закрытие не доказано). Аудит гасит находку, когда поправка есть в КАЖДОЙ задаче, которая её цитирует; погашенные считаются отдельными корзинами и видны в выводе.
3. У детектора есть адресат: вывод audit evidence даёт для каждой непогашенной находки готовую команду task log с шаблоном поправки.
4. Все находки сегодняшнего замера получили исход; непогашенных ROTTED и NEVER_EXISTED — 0; объявленный остаток в gates.json опущен до 0, дальше любой рост — high.
5. НЕГАТИВНЫЙ: MOVED на ссылку, которая не разрешается, находку НЕ гасит.
6. НЕГАТИВНЫЙ: поправка лишь в одной из двух цитирующих задач находку НЕ гасит.

## Plan

## Rollback

git revert <commit>. Работа состоит из ДОПИСАННЫХ заметок в журналах задач: подписанные квитанции закрытия не переписываются. Откат данных не требуется; при массовой правке журналов делается копия .tausik/tausik.db.

## Journal

- 2026-09-24T08:37:30Z [implementation] — AC-1 measurement before (tausik audit evidence, 2026-09-24): 1604 closed tasks, 4505 citations / 2295 unique, 2132 resolve; ROTTED 108, NEVER_EXISTED 39, UNKNOWN 0, ILLUSTRATIVE 16. Declared remainder in tausik/gates.json: rotted 99, never_existed 36 - ALREADY EXCEEDED by 9 and 3 (growth). Known limitation stated in audit_closure_evidence docstring: an appended reconciliation note does not retire a finding.
- 2026-09-24T08:40:51Z [implementation] — CHECKPOINT (stopped by owner, token budget). DONE, uncommitted: scripts/closure_amendments.py (grammar EVIDENCE-MOVED/RETIRED/UNPROVEN), audit_closure_evidence.py (_apply_outcomes, successor_ref, buckets reconciled/retired/unproven), project_cli_audit.py (answer: command per finding), tests/test_closure_amendments.py 7 green; old audit tests 41 green. NEXT: (1) regenerate triage plan from tausik audit evidence --json; rule order: same name elsewhere in tests => MOVED; rotted candidate introduced by the removing commit => MOVED; file/test deleted by a named commit => RETIRED with that commit; never_existed => UNPROVEN. Last run: 185 task-ref pairs = 110 RETIRED (84 from 77703c4a Notion removal), 23 MOVED, 52 UNPROVEN. Before applying: 15 never_existed with class-rename candidates (TestNoLaneExcludesByPath~TestNoCiLaneExcludesTestFiles, otel TestExportEnabled~TestExportToggle, knowledge_export TestTheDestinationMustBeLocal~TestRemoteDestinationsAreRefused) - MOVED when the exact method exists under the candidate class. (2) apply via tausik task log per pair (check task log accepts done tasks). (3) re-run audit: open rotted/never_existed = 0; tausik/gates.json closure_evidence.baseline to 0/0; adjust tests/test_closure_evidence_remainder.py. (4) mutation, CHANGELOG EN/RU (github#150), AC-1..6 evidence, Root cause line, close.sh, commit.
- 2026-09-25T18:02:49Z [implementation] — Смена #275: scripts/audit_closure_evidence.py оставался неотформатированным и ронял tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks на всём дереве. Применён ruff format — правка несемантическая, сделана соседней задачей, чтобы не держать дерево красным.
- 2026-09-26T16:40:57Z [implementation] — ЗАМЕР РЕВЬЮ смены #277, важный для этой задачи: неразрешимых цитат 107 в 60 задачах, храповик объявлял 99+36. РОСТ НЕ ОТ ПЕРЕИМЕНОВАНИЙ — проверено: у трёх задач, закрытых в этой смене, все цитаты разрешаются. Верхушка списка — brain-decide-publishes-unclassified-rationale (9), kb-brain-deprecate (8), publish-risk-gate-docstring-lies-after-205 (6), r14-brain-metrics (4), kb-notion-publisher (4). То есть цитаты осиротели от УДАЛЕНИЯ файлов тестов при отказе от Notion и brain (решение #358), а не от порчи. Это меняет предмет задачи: часть остатка — не гниль, а ожидаемое следствие принятого удаления, и объявлять её надо с этой причиной, отдельно от настоящей порчи.
