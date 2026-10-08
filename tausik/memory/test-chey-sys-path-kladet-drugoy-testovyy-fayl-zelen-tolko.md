---
slug: test-chey-sys-path-kladet-drugoy-testovyy-fayl-zelen-tolko
title: "Тест, чей sys.path кладёт ДРУГОЙ тестовый файл, зелен только по порядку сборки — проверяй новый тест ОДИНОЧНЫМ запуском"
type: gotcha
tags:
  - mutation
  - pytest
  - review
  - sys.path
task: mandatory-clauses-are-constants-published-as-earned
edges: []
---

#213, найдено ревью: tests/test_renar_mandatory_clauses.py импортировал bootstrap_hooks, а путь bootstrap/ в sys.path клал только tests/test_bootstrap_hooks_parity.py (модульный уровень). Он сортируется раньше, поэтому полный прогон был зелёным, а `pytest tests/test_renar_mandatory_clauses.py` падал ModuleNotFoundError — и цифры «303 passed / мутации убиты» были получены под маской: названный храповик и его негативный тест не выполнялись. conftest.py кладёт только scripts/. Правило: каждый новый тестовый файл прогоняй ОТДЕЛЬНО (pytest <file>) до объявления зелёным; любой импорт вне scripts/ требует своей вставки sys.path в этом же файле. Мутационный прогон это не ловит: он запускает названного убийцу в одиночку и видит «failed» — то есть ошибку импорта принимает за убийство.
