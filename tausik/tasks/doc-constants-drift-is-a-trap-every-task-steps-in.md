---
slug: doc-constants-drift-is-a-trap-every-task-steps-in
title: "test_count в doc-constants делает набор красным после КАЖДОЙ задачи с новыми тестами, а суженный гейт этого не ловит"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: full-pytest-hangs-while-scoped-pytest-is-green
scope: "scripts/gen_doc_constants.py (сравнение test_count → lower-bound), scripts/doc_drift_scanners.py (scan_test_counts → lower-bound), docs/_generated/constants.json (регенерация), tests/ (рост OK / усадка fail / overclaim fail)"
scope_exclude: "Не трогать сравнение version/MCP tool counts/code counts (остаются exact-pin — это DECLARED, не измерение). --skip-test-count для CI-variance сохранить."
relevant_files:
  - "scripts/gen_doc_constants.py"
  - "scripts/doc_drift_scanners.py"
  - "tests/test_gen_doc_constants.py"
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T22:37:12Z"
---

## Goal

Найдено в сессии #135 при первом за три сессии полном прогоне pytest. Падал tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync: docs/_generated/constants.json держал test_count=5913, а фактическое число тестов было 5923 — сессия #134 добавила файл тестов и не перегенерировала константы.

ЭТО НЕ РАЗОВЫЙ ПРОМАХ, А ЛОВУШКА КОНСТРУКЦИИ. test_count меняется от ЛЮБОЙ задачи, которая добавляет или удаляет хоть один тест, то есть почти от каждой. Ловит расхождение один тест — test_check_docs_hook.py. Суженный pytest-гейт сопоставляет relevant_files с файлами тестов по basename, и на этот файл не отображается ничего, кроме правки самого scripts/check_docs.py. Значит нормальный ход событий такой: задача добавляет тесты -> закрывается зелёным подписанным чеком -> полный набор становится красным -> никто не узнаёт до следующего полного прогона (а он идёт девять минут и запускается раз в несколько сессий). За эту сессию я наступил на это ДВАЖДЫ подряд, добавив свои файлы тестов.

Варианты, между которыми надо выбрать (не угадывать заранее): (а) считать test_count производной величиной и не хранить его в constants.json вовсе — держать в документации формулировку без точного числа; (б) перегенерировать константы автоматически в PostToolUse-хуке на запись в tests/*; (в) поднять проверку дрейфа из теста в гейт, который идёт ВСЕГДА, а не по basename-сопоставлению (как gate_bootstrap_drift); (г) допустить дрейф test_count как некритичный и проверять только остальные поля. У (а) и (г) цена — теряется факт «в проекте столько-то тестов» как проверяемая величина; у (б) — хук пишет в git-tracked файл за спиной у агента; у (в) — плюс девять секунд к каждому verify.

Смежное: в этой же сессии задача full-pytest-hangs-while-scoped-pytest-is-green добавила pytest-гейту строку SCOPE с знаменателем — она делает разрыв ВИДНЫМ, но не закрывает его. Здесь нужно именно закрытие.

## Acceptance Criteria

AC1. РЕШЕНИЕ (не угадано): test_count трактуется как НИЖНЯЯ ГРАНИЦА ('N+ тестов'), а не exact-pin. Рост набора (stored ≤ live) НЕ является дрейфом; падает только усадка ниже записанного числа (stored > live) — реальный сигнал регрессии. Version/tool/code counts остаются exact-pin (DECLARED). Обоснование задокументировано в комментарии кода + tausik_decide.
AC2. `doc constants --check` на dev-боксе после добавления тестов (live растёт) возвращает 0 — трап закрыт. Тест воспроизводит: constants.json test_count=N, live=N+k (k>0) → exit 0.
AC3. НЕГАТИВ сохранён: (а) doc-число, ПРЕВЫШАЮЩее live (overclaim, found>expected), флагается scan_test_counts; (б) constants.json test_count СТРОГО больше live (усадка) → --check exit 1 с внятным сообщением.
AC4. scan_test_counts: README/architecture числа трактуются как lower-bound (found ≤ live OK). Живая БД: текущие расхождения (README 6227, architecture 6096, live 6254) больше НЕ дают красный, пока doc-число ≤ live.
AC5. constants.json регенерирована (test_count текущий). Полный test_check_docs_hook.py зелёный. --skip-test-count (CI-variance) не сломан. Добавлены тесты на рост/усадку/overclaim.

## Plan

## Rollback

git revert; изменение — семантика сравнения test_count. Откат возвращает exact-pin (и трап). constants.json регенерируется штатной командой.

## Journal

- 2026-07-26T22:36:17Z [implementation] — AC-1: ✓ РЕШЕНИЕ #182 — test_count как lower-bound, задокументировано в gen_doc_constants.py комментарии + tausik_decide #182. Version/tool/code counts остаются exact-pin (left/right сравнение исключает только test_count). AC-2: ✓ Трап закрыт — tests/test_gen_doc_constants.py::test_run_main_test_count_growth_is_not_drift (recorded 3000 ≤ live 3200 → exit 0). ДОКАЗАНО на живой БД: добавил тесты (live 6254→6257), constants.json=6254 stale, `doc constants --check` GREEN. AC-3: ✓ НЕГАТИВ: (а) overclaim tests/test_gen_doc_constants.py::test_scan_test_counts_flags_overclaim (found 3500 > 3050 → flagged 'OVERCLAIM') + test_scan_test_counts_flags_pytest_suite_overclaim (9999); (б) усадка test_run_main_test_count_shrink_is_drift (recorded 3200 > live 3000 → exit 1 с сообщением 'suite shrank below floor'). AC-4: ✓ scan_test_counts lower-bound — test_scan_test_counts_clean_when_doc_below_live_lower_bound (2590 < 3050 → []). Живая БД: README 6227 / architecture 6096 / live 6257 больше НЕ красный (6227,6096 ≤ 6257). AC-5: ✓ constants.json регенерирована (test_count 6227→6254). Полный test_check_docs_hook.py + test_gen_doc_constants.py + test_doc_drift_scanners.py 75 passed. --skip-test-count не сломан (test_run_main_test_count_shrink проверяет skip → 0). mypy 2 файла Success. Verify run #1452 scoped pytest PASS. Domain: гейт различает ИЗМЕРЕНИЕ (растёт → не провал) и ЗАЯВКУ (doc обещает больше тестов чем есть → провал) — проверяемый факт сохранён в осмысленном направлении (регрессия=усадка). CHANGELOG EN+RU + decision #182.
- 2026-07-26T22:36:35Z [implementation] — Root cause (logic-error): test_count — производное ИЗМЕРЕНИЕ (меняется почти от каждой задачи с тестами), но проверялось механизмом для ЗАДЕКЛАРИРОВАННЫХ констант (exact-pin), одинаковым с version/tool counts. Exact-равенство на растущей величине → красный после каждого добавления теста, невидимый до 9-мин полного прогона (суженный pytest-гейт не мапит test_check_docs_hook по basename). Prevention: различать DECLARED intent (exact-pin) и DERIVED measurement (lower-bound); измерение проверять только в осмысленном направлении (усадка/overclaim), не на точное совпадение. Решение #182.
- 2026-07-26T22:36:43Z [implementation] — AC-1..5 верифицированы (см. предыдущий task log + evidence). Root cause залогирован (logic-error). Verify run #1452 scoped pytest PASS. Трап доказан закрытым на живой БД: live 6257 > recorded 6254, --check GREEN. 75 passed в doc-constants suite. mypy 2 файла Success. CHANGELOG EN+RU + decision #182.
- 2026-07-26T22:37:10Z [implementation] — AC-1..5 верифицированы (task log + evidence выше). Root cause залогирован (logic-error). Knowledge: decision #182 + convention #325 (DECLARED vs DERIVED). Verify run #1452 scoped pytest PASS; трап закрыт на живой БД (live 6257 > recorded 6254, --check GREEN); 75 passed в doc-constants suite; mypy 2 файла Success. CHANGELOG EN+RU.
