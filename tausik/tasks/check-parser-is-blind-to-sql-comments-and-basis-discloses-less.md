---
slug: check-parser-is-blind-to-sql-comments-and-basis-discloses-less
title: "Парсер CHECK слеп к SQL-комментариям и даёт ложный ПАС, а блок basis раскрывает о §13.3.5 меньше, чем снятая оговорка"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: mandatory-clauses-are-constants-published-as-earned
scope: "scripts/renar_clause_closed_lists.py, scripts/renar_mandatory_clauses.py (TC_PREMISE_WATCH), scripts/doc_drift_scanners.py, tests/test_renar_clause_closed_lists.py, tests/test_renar_mandatory_clauses.py, tests/test_doc_closed_list_drift.py, RENAR-CONFORMANCE.yaml, renar/conformance.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "состав закрытых перечней; renar_tc_premise.pairing_clause (вердикт не меняется, меняется только строка раскрытия)"
relevant_files:
  - "scripts/renar_clause_closed_lists.py"
  - "scripts/renar_mandatory_clauses.py"
  - "scripts/doc_drift_scanners.py"
  - "tests/test_renar_clause_closed_lists.py"
  - "tests/test_renar_mandatory_clauses.py"
  - "tests/test_doc_closed_list_drift.py"
  - RENAR-CONFORMANCE.yaml
  - "renar/conformance.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-06T11:55:10Z"
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

НАЙДЕНО ВНЕШНИМ L3 #40 (claude-sonnet-5), ОБА ПУНКТА ВОСПРОИЗВЕДЕНЫ МОИМ ПРОГОНОМ.

(1) HIGH, ЛОЖНЫЙ ПАС В ОХРАНЕ. scripts/renar_clause_closed_lists._values_until_close не знает о SQL-комментариях. Замер: CREATE TABLE t (type TEXT NOT NULL CHECK(type IN ('SEC','BR','SR' /* legacy ) trick */, 'FAKE'))) — SQLite РЕАЛЬНО допускает 'FAKE' (INSERT проходит), а check_domain возвращает ('SEC','BR','SR'). Значит closed_list_subchecks объявит «CHECK допускает ровно объявленное» на CHECK, который НЕ закрыт. Это ровно та вырожденность (ADR-021), ради устранения которой §13.3.4 и §13.3.7 переписывались, — и она в ПРИМИТИВЕ, который докстринг называет общим для всех закрытых перечней. Строчный комментарий -- до конца строки проверен отдельно: на нём парсер пока отвечает верно, но по совпадению, а не по устройству.

(2) HIGH, РАСКРЫТИЕ УМЕНЬШИЛОСЬ. Замер: git show 4a900ab:RENAR-CONFORMANCE.yaml (v17) упоминает ADR-013 в оговорке про tc-pos-neg-pairing ДВАЖДЫ и объясняет, почему храповик classes_appeared бессмыслен на чужой БД; в v18 и в renar/conformance.md упоминаний ADR-013 НОЛЬ (grep -c даёт 0/0). При этом scripts/renar_tc_premise.py:240-245 по-прежнему считает охранный тест ADR-013 несущим и прямо пишет, что он ПРОПУСКАЕТСЯ В CI (задача db-gated-ratchets-never-run-in-ci). Читатель одного лишь манифеста узнаёт о защите §13.3.5 МЕНЬШЕ, чем до починки, — против цели самой починки.

(3) MEDIUM: _best_closed_list считает пересечение регистрозависимо — перечисление в другом регистре (проверено: все одиннадцать типов SPEC строчными) даёт пересечение 0 и молча пропускается. (4) MEDIUM: scan_mcp_table_columns проверяет только cell.isdigit(), поэтому «128+» и «~128» молча считаются прозой, а конвенции нижней границы для этого столбца (аналога решения #182) нет. (5) LOW: перечисление, разорванное по границе ячейки таблицы, может дать два частичных совпадения — сегодня не воспроизводится, отмечено как упрочнение.

Root cause (edge-case): парсер писался против форм, которые встречаются в НАШЕМ DDL, а SQL допускает комментарий внутри списка значений; обе стороны сравнения регистра брались из источников, где регистр совпадает. Prevention: тест с комментарием, несущим несбалансированную скобку перед настоящим значением; тест на регистр; при снятии оговорки сверять, что новый носитель раскрытия несёт ВСЁ, что нёс старый (дифф двух версий артефакта, а не только наличие блока).

## Acceptance Criteria

AC-1: _values_until_close знает о SQL-комментариях — строчном (-- до конца строки) и блочном (/* … */): скобки и кавычки внутри комментария не считаются. Тест с комментарием, несущим НЕСБАЛАНСИРОВАННУЮ скобку перед настоящим значением; тот же случай через живой CHECK и живой INSERT, доказывающий, что SQLite действительно допускает значение, которое парсер раньше терял.
AC-2 (negative, ложный ПАС закрыт): на том же DDL closed_list_subchecks даёт КРАСНОЕ (лишнее значение названо), а не «CHECK допускает ровно объявленное»; мутация «снять учёт комментариев» убивается этим тестом.
AC-3: раскрытие §13.3.5 в манифесте не меньше прежнего — premise-watched-by называет и renar_tc_premise.classes_appeared, и охранный тест ADR-013 с оговоркой, что он пропускается в CI; grep по RENAR-CONFORMANCE.yaml и renar/conformance.md находит ADR-013. Negative: тест краснеет, если в watch-строке нет упоминания ADR-013 либо CI-оговорки.
AC-4: _best_closed_list сравнивает без учёта регистра, сообщение сохраняет исходное написание; тест на перечисление строчными буквами (сегодня даёт пересечение 0 и молча пропускается).
AC-5: ячейки вида «128+» и «~128» либо проверяются числом, либо исключение ОБЪЯВЛЕНО в докстринге с причиной; выбор записан в журнал.
AC-6: полный прогон, bootstrap --check, gen_doc_constants --check, регенерация манифеста по порядку (правка → тесты → bootstrap --ide all → --check → renar conformance --write → renar export); мутации объявлены и убиты по ветви либо объявлены эквивалентными; CHANGELOG в обоих файлах.

## Plan

## Rollback

git revert коммита задачи; манифест перевыпускается следующей регенерацией (номера версий не переиспользуются).

## Journal

- 2026-09-06T11:52:17Z [implementation] — ПОЧИНКА. (1) _values_until_close пропускает SQL-комментарии — строчный до перевода строки и блочный до */ — ТОЛЬКО вне строки; незакрытый комментарий любой формы даёт None («нечитаемо»), а не пустой список. Замер после правки: блочный комментарий с несбалансированной скобкой даёт ('SEC','BR','SR','FAKE') — то, что реально допускает SQLite; строчный даёт ('A','B'); значения 'a--b' и 'c/*d' сохраняются целиком. (2) TC_PREMISE_WATCH называет ОБА храповика — classes_appeared и охранный тест ADR-013 — и прямо говорит, что второй пропускается в CI (задача db-gated-ratchets-never-run-in-ci). Манифест регенерирован по порядку (bootstrap --ide all → --check → conformance --write → renar export) до v19, replaces v18; grep ADR-013 даёт 1 и в RENAR-CONFORMANCE.yaml, и в renar/conformance.md (было 0/0). (3) _best_closed_list и сравнение состава — без учёта регистра, сообщение сохраняет написание доки. (4) Ячейки «128+»/«~128» остаются пропущенными, но теперь как ОБЪЯВЛЕННОЕ исключение с причиной в докстринге: у этого столбца нет конвенции нижней границы, какая есть у test_count (#182), и изобретать её внутри сканера значит писать политику там, где её не ищут; тест это закрепляет. ТЕСТЫ: 59 зелёных в трёх файлах при одиночном запуске. МУТАЦИИ 7/7 УБИТЫ ПО ВЕТВИ: B1 блочные комментарии не пропускаются, B2 строчные, B3 пропуск залезает в строку, B4 незакрытый комментарий как пустой список, B5 пересечение снова регистрозависимо, B6 состав снова регистрозависим, B7 второй храповик выброшен из раскрытия.
- 2026-09-06T11:55:08Z [implementation] — AC-1: ✓ tests/test_renar_clause_closed_lists.py::test_a_comment_inside_the_check_does_not_end_the_list (обе формы комментария, плюс живой INSERT, доказывающий, что SQLite допускает значение, которое парсер терял), tests/test_renar_clause_closed_lists.py::test_comment_markers_inside_a_value_are_ordinary_characters (мутации B1, B2, B3 убиты) AC-2 (negative): ✓ tests/test_renar_clause_closed_lists.py::test_the_hidden_value_reds_the_substrate_subcheck — CHECK с контрабандным значением за комментарием даёт КРАСНОЕ с именем значения, а не «допускает ровно объявленное»; tests/test_renar_clause_closed_lists.py::test_an_unterminated_comment_is_unreadable_not_empty (мутация B4 убита) AC-3: ✓ tests/test_renar_mandatory_clauses.py::test_the_vacuous_clause_names_every_watch_it_rests_on — premise-watched-by называет classes_appeared, ADR-013 и оговорку про CI; манифест v19 и renar/conformance.md содержат ADR-013 (было 0/0, замер в журнале); мутация B7 убита AC-4: ✓ tests/test_doc_closed_list_drift.py::test_a_lowercase_quotation_is_still_our_list — полная цитата строчными молчит, цитата строчными без двух значений краснеет с именами в исходном написании (мутации B5, B6 убиты) AC-5: ✓ исключение объявлено в докстринге scan_mcp_table_columns с причиной (нет конвенции нижней границы для этого столбца, в отличие от test_count по решению #182) и закреплено tests/test_doc_closed_list_drift.py::test_a_decorated_cell_is_a_declared_exclusion AC-6: ✓ порядок регенерации соблюдён (правка → тесты → bootstrap --ide all → --check → renar conformance --write → renar export), манифест v19 replaces v18; полный прогон ленты; мутации 7 объявлено, 7 убито; CHANGELOG.md и CHANGELOG.ru.md Root cause (edge-case): парсер писался против форм НАШЕГО DDL, где комментариев внутри CHECK нет, а обе стороны сравнения регистра брались из источников, где регистр совпадает; при снятии оговорки новый носитель раскрытия не сверялся с прежним построчно. Prevention: тест с комментарием, несущим несбалансированную скобку перед настоящим значением; тест на регистр; при переносе раскрытия сверять ДИФФОМ двух версий артефакта, а не наличием блока. Domain: RENAR §13.3.4/§13.3.7 (закрытые перечни по схеме), §13.4.2 (манифест и раскрытие оснований), дрейф документации.
