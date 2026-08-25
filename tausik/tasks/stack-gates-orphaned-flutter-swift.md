---
slug: stack-gates-orphaned-flutter-swift
title: "Flutter и Swift объявлены стеками, но не имеют ни одного гейта — verify зеленеет, ничего не проверив"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "stacks/{django,fastapi,flask,react,next,nuxt,vue,svelte,laravel,blade}/ — эти девять покрыты родительскими гейтами, правка была бы шумом. scripts/ и harness/ — задача не меняет диспетчер, только данные стеков и проверку на класс."
relevant_files:
  - "stacks/flutter/stack.json"
  - "stacks/swift/stack.json"
  - "tests/test_stack_gate_coverage.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CLAUDE.md
  - "tests/test_ddl_fixture_parity.py"
  - "tests/test_reasoning_steps.py"
scope_paths:
  - "stacks/flutter/stack.json"
  - "stacks/swift/stack.json"
  - "tests/test_stack_gate_coverage.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-20T15:42:10Z"
---

## Goal

ЗАПРОС ВЛАДЕЛЬЦА (сессия #121): «для flutter не оказалось гейтов — сделай доработку по этому стеку так же в 1.8».

ЗАМЕР, А НЕ ВПЕЧАТЛЕНИЕ. Обойдены все 26 каталогов stacks/: у ДВЕНАДЦАТИ нет ключа gates. Но это не один класс, и чинить надо не все двенадцать.

Девять из двенадцати покрыты РОДИТЕЛЕМ, и это законно: django/fastapi/flask ловит pytest из python (гейт перечисляет их в stacks); react/next/nuxt/vue/svelte ловят eslint, js-test и tsc из javascript и typescript; laravel ловит phpstan/phpcs/phpunit из php; blade покрыт на уровне файлов — .blade.php отображается в {blade, laravel, php}, поэтому php-гейты к нему применяются.

СИРОТ ДВА: flutter и swift. У .dart кандидатный стек ровно {flutter}, у .swift ровно {swift}, и НИ ОДИН гейт во всём реестре не перечисляет их в своём stacks. Значит для задачи с дартовыми или свифтовыми файлами не запускается ни линтер, ни компилятор, ни тесты — отрабатывают только универсальные встроенные (filesize, renar drift), и task done рапортует зелено.

ПОЧЕМУ ЭТО ИМЕННО НАШ КЛАСС ДЕФЕКТА. Это не «нет фичи», это ЗЕЛЁНЫЙ ВЕРДИКТ, НЕ ОЗНАЧАЮЩИЙ НИЧЕГО — ровно то, против чего написаны verify-summary-reports-skipped-as-pass и verify-no-test-mapped-dead-end. Причём здесь хуже: там прогон хотя бы честно помечался skipped, а тут гейтов нет вовсе, и отличить «проверено» от «проверять было нечем» нельзя ни по одному признаку.

ГРАНИЦА. Swift чиню вместе с Flutter не из широты, а потому что это ОДНА находка одного обхода: оставить swift значило бы сознательно отгрузить ту же дыру, зная о ней. Остальные девять НЕ ТРОГАЮ — они покрыты, и правка была бы шумом.

ГЛАВНОЕ — НЕ ДВА ФАЙЛА, А ГЕЙТ НА КЛАСС. Разовое добавление двух stack.json не мешает стеку номер 27 приехать с той же дырой. Нужен механический гейт: стек, объявляющий расширения, обязан иметь хотя бы один достижимый для его файлов гейт — свой или родительский (конвенция #236).

## Acceptance Criteria

AC1. Дефект ВОСПРОИЗВЕДЁН до фикса: показано, что для набора файлов с .dart (и отдельно .swift) не применяется ни один стек-гейт. Воспроизведение через gate_applies_to/infer_stacks_from_files, а не рассуждением.
AC2. stacks/flutter/stack.json получает гейты, соответствующие реальной тулчейн-практике Flutter и уже описанные в stacks/flutter/guide.md: анализ (dart analyze), формат (dart format с ненулевым кодом при расхождении), тесты (flutter test). Форма — как у go/rust: enabled=false по умолчанию, severity/trigger/stacks/timeout заданы явно.
AC3. То же для stacks/swift/stack.json: сборка, линт, тесты. Swift правится в этой же задаче, потому что найден тем же обходом; оставить его значило бы отгрузить известную дыру.
AC4. ГЛАВНОЕ: механический гейт на КЛАСС — стек, объявляющий extensions, обязан иметь хотя бы один достижимый гейт для своих файлов, свой или унаследованный. Разовая правка двух файлов не мешает стеку №27 приехать с той же дырой.
AC5. Гейт класса УЧИТЫВАЕТ НАСЛЕДОВАНИЕ и не требует своих гейтов там, где работает родительский: django/fastapi/flask (pytest из python), react/next/nuxt/vue/svelte (eslint/js-test/tsc), laravel (php-гейты), blade (через отображение .blade.php в php). Гейт, требующий собственных гейтов у каждого стека, потребовал бы девять бессмысленных правок и был бы отключён.
AC6. НЕГАТИВНЫЙ: гейт класса ПРОВЕРЕН внесённой сиротой — стек с расширением и без единого достижимого гейта обязан ронять проверку. Гейт, никогда ничего не ловивший, — гейт-гипотеза.
AC7. НЕГАТИВНЫЙ: гейт класса не выродился в пустышку — есть страховка, что он читает непустой набор стеков и что отображение расширение→стек непусто. Иначе он сравнивал бы пустое с пустым и был бы вечно зелёным.
AC8. НЕГАТИВНЫЙ: команды новых гейтов НЕ выполняются в проверке. Тулчейна Flutter и Swift на машине сборки нет, и тест, зовущий flutter test, падал бы у всех — проверяется СТРУКТУРА объявления (severity, trigger, stacks, наличие команды), а не результат её запуска.
AC9. Объявления новых гейтов проходят валидацию схемы стека (stacks/_schema.json, tausik stack lint) — иначе они не загрузятся в реестр и окажутся мёртвым текстом.
AC10. ruff чист, полный pytest зелёный в обоих режимах, CHANGELOG EN+RU.

## Plan

## Rollback

git revert <commit>. Правка аддитивна: два stack.json получают ключ gates (все enabled=false, поведение по умолчанию не меняется) плюс новый тестовый файл. Откат возвращает flutter и swift в состояние сирот — при откате ОБЯЗАТЕЛЬНО переоткрыть задачу, иначе зелёный вердикт снова перестанет что-либо значить.

## Journal

- 2026-07-20T14:52:16Z [implementation] — AC1 ВОСПРОИЗВЕДЁН замером, а не рассуждением: обойдены все стеки с extensions, для каждого построен пробный набор файлов и через infer_stacks_from_files + DEFAULT_GATES посчитаны достижимые стек-гейты. Сирот ровно ДВЕ: flutter (.dart -> {flutter} -> 0 гейтов) и swift (.swift -> {swift} -> 0 гейтов). Разведка карточки подтверждена независимо. РАСХОЖДЕНИЕ: карточка говорит «26 каталогов stacks/», фактически их 25 (26-м, видимо, посчитан _schema.json). На вывод это не влияет — сироты те же две, — но число в карточке неверно и переносить его дальше нельзя.
- 2026-07-20T14:57:39Z [implementation] — Реализовано: flutter получил dart-analyze/dart-format/flutter-test, swift — swift-build/swiftlint/swift-test, все enabled=false (тулчейна на машине сборки нет). Реестр 27 -> 33 гейта, сирот 0. ГЛАВНОЕ — tests/test_stack_gate_coverage.py: гейт на КЛАСС, достижимость считается ПРОДОВЫМ gate_applies_to, а не второй копией правила (конвенция #249). Гейт проверен внесённой сиротой end-to-end: снял gates у flutter — упал именно test_every_stack_with_extensions_has_a_reachable_gate[flutter], имя стека в параметре. Этот же прогон вскрыл изъян в моём тесте: при исчезнувшем гейте он падал KeyError вместо внятного сообщения — исправлено. ПОБОЧНАЯ НАХОДКА: tausik stack lint смотрит ТОЛЬКО .tausik/stacks/, встроенные объявления против stacks/_schema.json не валидировались нигде — на чистой машине команда печатает 'nothing to lint'. Добавлена страховка на весь набор встроенных деклараций.
- 2026-07-20T15:21:44Z [implementation] — ПОБОЧНАЯ НАХОДКА ВНЕ ОБЛАСТИ ЭТОЙ ЗАДАЧИ, заведена отдельно: mcp-gate-toggle-mutates-real-project-config. Падение test_mcp_integration.py:324 (WinError 32 на .tausik/config.json.tmp) в utf8-прогоне оказалось не флейком, а признаком: _handle_gate_toggle игнорирует переданный svc и пишет в конфиг РЕАЛЬНОГО проекта. Воспроизведено трижды детерминированно — один тест дописывает mypy:enabled в живой config.json. В область текущей задачи не вношу (дисциплина области), конфиг восстановлен в наблюдавшееся состояние. Изолированно tests/test_mcp_integration.py: 16 passed.
- 2026-07-20T15:42:09Z [implementation] — AC-1: ✓ Воспроизведено ЗАМЕРОМ через infer_stacks_from_files + DEFAULT_GATES: для .dart кандидатный стек {flutter}, для .swift {swift}, достижимых стек-гейтов 0 в обоих случаях — tests/test_stack_gate_coverage.py::TestTheCoverageGateActuallyCatchesAnOrphan::test_the_measured_orphans_are_the_two_that_were_fixed AC-2: ✓ stacks/flutter/stack.json получил dart-analyze (block/verify), dart-format (warn/commit, --set-exit-if-changed), flutter-test (block/verify); форма как у go — enabled=false, severity/trigger/stacks/timeout заданы явно — tests/test_stack_gate_coverage.py::TestTheNewGatesAreDeclaredNotExecuted::test_gate_is_registered_with_the_declared_shape AC-3: ✓ stacks/swift/stack.json получил swift-build, swiftlint, swift-test той же формы — tests/test_stack_gate_coverage.py::TestTheNewGatesAreDeclaredNotExecuted::test_gate_is_registered_with_the_declared_shape AC-4: ✓ Гейт на КЛАСС: каждый стек с extensions параметризованно проверяется на наличие достижимого гейта; достижимость считает ПРОДОВЫЙ gate_applies_to, а не вторая копия правила — tests/test_stack_gate_coverage.py::test_every_stack_with_extensions_has_a_reachable_gate AC-5: ✓ Наследование учтено: девять дочерних стеков проверены на покрытие родителем (django/fastapi/flask -> pytest, react/next/nuxt/vue/svelte -> eslint, laravel -> phpstan), blade отдельно через двойное расширение — tests/test_stack_gate_coverage.py::TestInheritanceIsRespected AC-6: ✓ Проверен внесённой сиротой ДВАЖДЫ: синтетически (.nosuchlang) и END-TO-END — снял gates у flutter, упал именно test_every_stack_with_extensions_has_a_reachable_gate[flutter] — tests/test_stack_gate_coverage.py::TestTheCoverageGateActuallyCatchesAnOrphan::test_an_orphan_stack_is_detected AC-7: ✓ Не пустышка: список стеков >=20, отображение расширение→стек непусто и проверено поимённо, стек-гейтов в реестре >=15; плюс обратный тест «гейт, назвавший стек, делает его достижимым» — иначе проверка проходила бы на функции, всегда возвращающей пустоту — tests/test_stack_gate_coverage.py::TestTheCoverageGateIsNotHollow AC-8: ✓ Команды НЕ выполняются: проверяется структура объявления (stacks/severity/trigger/фрагмент команды/enabled=False); отдельно закреплено, что тяжёлые гейты висят на verify, а не на task-done (Verify-First) — tests/test_stack_gate_coverage.py::TestTheNewGatesAreDeclaredNotExecuted::test_heavy_gates_run_on_verify_not_task_done AC-9: ✓ Оба объявления проходят stack_schema.validate_decl; сверх задачи добавлена валидация ВСЕХ встроенных деклараций — tausik stack lint смотрит только .tausik/stacks/ и на чистой машине печатает «nothing to lint», то есть встроенные не проверялись нигде — tests/test_stack_gate_coverage.py::test_every_builtin_stack_decl_passes_schema_validation AC-10: ✓ ruff check + ruff format --check чисты; полный прогон обеих линий в обоих режимах: 5243 passed, 23 skipped, 0 failed (обычный 1216s, -X utf8 1141s), секции warnings нет; CHANGELOG.md и CHANGELOG.ru.md дополнены — CHANGELOG.md Negative: 6 негативных проверок. Внесённая сирота синтетическая и end-to-end; обратный тест на достижимость (иначе проверка зелёная на всегда-пустой функции); три страховки от вырождения (список стеков, отображение расширений, число стек-гейтов); запрет task-done для тяжёлых гейтов. Domain: Диспетчеризация гейтов по стекам. Предмет — зелёный вердикт, не означающий ничего: пропущенный гейт помечается skipped, а необъявленный не оставляет в выводе следа вовсе. Правило держится гейтом на класс, а не двумя правками: стек №26 приедет с той же дырой. Checklist: Замер, а не впечатление — обойдены все 25 стеков, число названо. Расхождение с карточкой (26 против 25) зафиксировано в журнале, а не перенесено молча. Гейт проверен падением, а не утверждением. Изъян собственного теста (KeyError вместо сообщения при исчезнувшем гейте) найден тем же прогоном и исправлен. Побочный дефект (тесты MCP меняют живой config.json) НЕ втащен в эту задачу — заведён отдельно как mcp-gate-toggle-mutates-real-project-config с воспроизведением. Дрейф bootstrap отсутствует, doctor чист.
