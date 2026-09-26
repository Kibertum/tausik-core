---
slug: closure-citations-rot-is-detected-but-never-acted-on
title: "Сорок четыре ссылки на доказательства в закрытых задачах не разрешаются, и детектор третью смену подряд сообщает об этом впустую"
status: done
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
relevant_files:
  - "scripts/closure_amendments.py"
  - "scripts/audit_closure_evidence.py"
  - "scripts/project_cli_audit.py"
  - "tests/test_closure_amendments.py"
  - "tests/test_closure_evidence_remainder.py"
scope_paths:
  - "scripts/closure_amendments.py"
  - "scripts/audit_closure_evidence.py"
  - "scripts/project_cli_audit.py"
  - "tests/test_closure_amendments.py"
  - "tests/test_closure_evidence_remainder.py"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-26T19:11:18Z"
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
- 2026-09-26T18:51:31Z [implementation] — 95 поправок EVIDENCE-RETIRED применены машинально, и причина каждой ВЗЯТА ИЗ GIT, а не сочинена: имя коммита, удалившего файл. Четыре коммита-виновника, крупнейший 77703c4a — отказ от Notion.
- 2026-09-26T18:51:31Z [implementation] — РАЗБОР ВЫПОЛНЕН, смена #277. Счётчики до: rotted 108, never_existed 39. После: rotted 38, never_existed 0, retired 87, unproven 22. Объявленный остаток опущен с 99/36 до 38/0.
- 2026-09-26T18:51:32Z [implementation] — ГЛАВНАЯ НАХОДКА РАЗБОРА, и она про сам аудит: из 39 цитат класса never_existed 27 обвинялись в выдумке НАПРАСНО. Аудит разрешает путь буквально, а цитата вида 'test_brain_config.py' без каталога не совпадает ни с одним путём git — при том что tests/test_brain_config.py существовал и удалён тем же 77703c4a. Вердикт never_existed есть обвинение прошлого закрытия в фабрикации, и ошибка в эту сторону дороже пропуска настоящей выдумки: незаслуженное обвинение обесценивает весь регистр. Заведена audit-calls-a-bare-basename-invented.
- 2026-09-26T18:51:32Z [implementation] — ДВА СЛЕДСТВИЯ РАЗБОРА В ТЕСТАХ. test_база_объявлена_и_названа_числом требовал остаток СТРОГО больше нуля — требование писалось при ненулевом остатке и после разбора запрещало бы успех. Ноль теперь допущен как законное и притом сильнейшее значение: он означает, что класс разобран, а не что его перестали считать.
- 2026-09-26T18:51:32Z [implementation] — ОСТАЛОСЬ 38 rotted, и они НЕ размечены намеренно: файл жив, узел переименован, успешник предлагается по схожести имени. Записать его исходом значило бы утвердить покрытие, которого никто не читал, — а сам аудит прямо говорит 'confirm it by reading the test'. Это работа на чтение, не на скрипт.
- 2026-09-26T19:05:15Z [implementation] — AC-1 ✓ замер до правки записан выше: rotted 108, never_existed 39 при остатке 99/36. AC-2 ✓ грамматика применена, находка гаснет по наличию поправки в КАЖДОЙ цитирующей задаче. AC-3 ✓ вывод audit evidence даёт готовую команду на каждую непогашенную находку.
- 2026-09-26T19:05:15Z [implementation] — AC-4 ✓ ВЫПОЛНЕН БУКВАЛЬНО: rotted 0, never_existed 0. Разложено на 24 reconciled (MOVED с РАЗРЕШАЮЩЕЙСЯ ссылкой), 102 retired, 22 unproven; 16 illustrative — отдельная корзина примеров в прозе. Объявленный остаток в gates.json опущен до 0/0, дальше любой рост есть high.
- 2026-09-26T19:05:15Z [implementation] — AC-5 ✓ проверено на живом дереве: MOVED на неразрешающуюся ссылку находку НЕ гасит — три цитаты с параметризованным суффиксом [en] остались rotted после первой поправки, потому что узел pytest не есть член AST. Переведены на член без суффикса, тогда погасли.
- 2026-09-26T19:05:15Z [implementation] — AC-6 ✓ поправка лишь в одной из цитирующих задач не гасит: manifest-publishes-confirmations-we-know-are-unearned цитировал два разных ref, и находка держалась, пока не был разобран второй.
- 2026-09-26T19:05:16Z [implementation] — Negative: ни одна причина не сочинена. У RETIRED назван коммит из git (git log -S для члена, git log --diff-filter=D для файла), у MOVED успешник подтверждён чтением докстринга — и несколько из них сами называют прежнее имя, то есть подтверждение авторское, а не моё.
- 2026-09-26T19:05:16Z [implementation] — СВОЯ ОШИБКА НАЙДЕНА И ИСПРАВЛЕНА, и она того класса, против которого вся эта осторожность: я перевёл цитату на test_header_paragraph_matches_the_registry_state внутри TestPublishedManifest, а он лежит на уровне МОДУЛЯ. Ссылка не разрешилась, находка не погасла — то есть механизм поймал меня. Верный успешник в классе оказался test_section_matches_the_registry_including_when_it_is_empty. Исправлено ДОПИСЫВАНИЕМ: журнал append-only, а parse строит словарь по старой ссылке, поэтому последняя строка побеждает.
- 2026-09-26T19:05:16Z [implementation] — ТРИ ПРЕДЛОЖЕНИЯ АУДИТА ОТВЕРГНУТЫ ЧТЕНИЕМ, и это главное содержание работы: TestAppendTokenRows -> TestExtractTokenRows (append и extract — разные операции), test_mirror_partner_protected -> test_no_partner_for_root (защита партнёра против его отсутствия), test_confirm_fails_fast -> test_confirm_idempotent (быстрый отказ против идемпотентности). Принять их пачкой значило бы перевести три цитаты на тесты, которые их не покрывают.
