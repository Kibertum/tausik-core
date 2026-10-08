---
slug: crosscutting-scope-chitaetsya-ast-literal-eval-konstanta
title: "CROSSCUTTING_SCOPE читается ast.literal_eval — константа вместо литерала делает тест невидимым для scoped-прогона"
type: gotcha
tags:
  - gates
  - resolver
  - scope
  - tests
task: roadmap-artifact-predates-decision-256
edges: []
---

Написал CROSSCUTTING_SCOPE = ["scripts/", OUTPUT_FILENAME, ".gitignore"]. Резолвер модуль НЕ импортирует, он его ПАРСИТ: gate_test_resolver.read_crosscutting_scope делает ast.literal_eval и при ValueError/TypeError возвращает None. Имя вместо литерала читается как «ничего не объявлено», и весь файл становится невидимым для scoped-прогона: ни одно изменение его не выбирает, а первая настоящая красная приходит на полной полосе через дни и привязана не к тому изменению. Поймал ровно один контроль — test_crosscutting_registry::test_a_test_no_change_can_select_must_declare_or_be_baselined; при этом test_every_declared_prefix_points_at_a_real_path ЗЕЛЁНЫЙ, потому что он пропускает файлы без объявленной области. Пиши литералы, а связь литерала с константой модуля держи отдельным ассертом (assert OUTPUT_FILENAME in CROSSCUTTING_SCOPE), а не «красиво через имя».
