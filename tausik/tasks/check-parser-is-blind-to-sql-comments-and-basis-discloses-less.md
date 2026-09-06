---
slug: check-parser-is-blind-to-sql-comments-and-basis-discloses-less
title: "Парсер CHECK слеп к SQL-комментариям и даёт ложный ПАС, а блок basis раскрывает о §13.3.5 меньше, чем снятая оговорка"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: mandatory-clauses-are-constants-published-as-earned
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО ВНЕШНИМ L3 #40 (claude-sonnet-5), ОБА ПУНКТА ВОСПРОИЗВЕДЕНЫ МОИМ ПРОГОНОМ.

(1) HIGH, ЛОЖНЫЙ ПАС В ОХРАНЕ. scripts/renar_clause_closed_lists._values_until_close не знает о SQL-комментариях. Замер: CREATE TABLE t (type TEXT NOT NULL CHECK(type IN ('SEC','BR','SR' /* legacy ) trick */, 'FAKE'))) — SQLite РЕАЛЬНО допускает 'FAKE' (INSERT проходит), а check_domain возвращает ('SEC','BR','SR'). Значит closed_list_subchecks объявит «CHECK допускает ровно объявленное» на CHECK, который НЕ закрыт. Это ровно та вырожденность (ADR-021), ради устранения которой §13.3.4 и §13.3.7 переписывались, — и она в ПРИМИТИВЕ, который докстринг называет общим для всех закрытых перечней. Строчный комментарий -- до конца строки проверен отдельно: на нём парсер пока отвечает верно, но по совпадению, а не по устройству.

(2) HIGH, РАСКРЫТИЕ УМЕНЬШИЛОСЬ. Замер: git show 4a900ab:RENAR-CONFORMANCE.yaml (v17) упоминает ADR-013 в оговорке про tc-pos-neg-pairing ДВАЖДЫ и объясняет, почему храповик classes_appeared бессмыслен на чужой БД; в v18 и в renar/conformance.md упоминаний ADR-013 НОЛЬ (grep -c даёт 0/0). При этом scripts/renar_tc_premise.py:240-245 по-прежнему считает охранный тест ADR-013 несущим и прямо пишет, что он ПРОПУСКАЕТСЯ В CI (задача db-gated-ratchets-never-run-in-ci). Читатель одного лишь манифеста узнаёт о защите §13.3.5 МЕНЬШЕ, чем до починки, — против цели самой починки.

(3) MEDIUM: _best_closed_list считает пересечение регистрозависимо — перечисление в другом регистре (проверено: все одиннадцать типов SPEC строчными) даёт пересечение 0 и молча пропускается. (4) MEDIUM: scan_mcp_table_columns проверяет только cell.isdigit(), поэтому «128+» и «~128» молча считаются прозой, а конвенции нижней границы для этого столбца (аналога решения #182) нет. (5) LOW: перечисление, разорванное по границе ячейки таблицы, может дать два частичных совпадения — сегодня не воспроизводится, отмечено как упрочнение.

Root cause (edge-case): парсер писался против форм, которые встречаются в НАШЕМ DDL, а SQL допускает комментарий внутри списка значений; обе стороны сравнения регистра брались из источников, где регистр совпадает. Prevention: тест с комментарием, несущим несбалансированную скобку перед настоящим значением; тест на регистр; при снятии оговорки сверять, что новый носитель раскрытия несёт ВСЁ, что нёс старый (дифф двух версий артефакта, а не только наличие блока).

## Acceptance Criteria

## Plan

## Rollback

## Journal
