---
slug: git-show-worktree
title: "Пути git show резолвятся от корня worktree: журнал читается только когда проект лежит В КОРНЕ репозитория"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: conformance-replaces-default-derived-from-a-date
scope: null
scope_exclude: "НЕ ТРОГАТЬ: RENAR-CONFORMANCE.yaml (не регенерируется); scripts/renar_conformance.py (параметр replaces уже верен, дефект не в нём); scripts/git_exec.py (единая точка запуска git корректна, чинится ВЫЗОВ, а не примитив); развёрнутые профили — генерируются bootstrap."
relevant_files:
  - "scripts/project_cli_renar.py"
  - "tests/test_renar_manifest_chain.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/project_cli_renar.py"
  - "tests/test_renar_manifest_chain.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-04T19:32:50Z"
---

## Goal

ЗАМЕР ПОДТВЕРЖДЁН на живом репозитории, git печатает подсказку сам. Из каталога scripts: git show HEAD:CHANGELOG.md отдаёт файл ИЗ КОРНЯ (rc=0), а git show HEAD:project.py падает с fatal: path scripts/project.py exists, but not project.py и подсказкой Did you mean HEAD:./project.py. То есть пут после двоеточия резолвится ОТ ВЕРХНЕГО УРОВНЯ WORKTREE, а не от cwd.

СЛЕДСТВИЕ ДЛЯ journal_manifest в scripts/project_cli_renar.py. root там это os.path.dirname(find_tausik_dir()), а find_tausik_dir идёт ВВЕРХ в поисках .tausik и совпадением с верхним уровнем git НИЧЕМ не обязан. Если проект лежит подкаталогом репозитория (монорепозиторий, пакет внутри большего дерева), git show HEAD:RENAR-CONFORMANCE.yaml вернёт ненулевой код при ЖИВОМ и закоммиченном манифесте, а ветвь show.returncode != 0 объявит это фактом ЖУРНАЛ ПУСТ. Ошибка становится фактом, ссылка не выдаётся НИКОГДА, и §13.4.2 рвётся молча ровно тем способом, против которого писалась охрана. Это тот же класс, что чинила родительская задача, и я внёс его в починку сам.

В НАШЕМ репозитории корень проекта совпадает с верхним уровнем worktree, поэтому живой артефакт НЕ затронут. Дефект бьёт по чужим проектам, куда фреймворк ставится.

НАЙДЕНО АДВЕРСАРИАЛЬНЫМ РЕВЬЮ на саму починку (память #536). Ни один новый тест этого не ловит СТРУКТУРНО: все синтетические фикстуры кладут манифест ровно в корень git init, то есть root равен верхнему уровню в КАЖДОМ тесте.

ВТОРАЯ НАХОДКА ТОГО ЖЕ РЕВЬЮ, чинить вместе: next_version и previous_link читают журнал КАЖДЫЙ САМ, то есть четыре запуска git на один --write, и версия со ссылкой могут быть посчитаны по РАЗНЫМ состояниям HEAD. Чинить порознь нельзя: правка пути ниже иначе делается в двух местах.

## Acceptance Criteria

1. journal_manifest резолвит путь ОТ CWD (форма HEAD:./ИМЯ). Тест на синтетическом репозитории, где корень проекта есть ПОДКАТАЛОГ верхнего уровня worktree: манифест закоммичен, previous_link обязан его назвать. Сегодня этот тест красный.
2. Различие сохранено и в вложенной раскладке: при ОТСУТСТВИИ закоммиченного манифеста ответ (0, None), а при недоступном git None. НЕГАТИВНЫЙ СЦЕНАРИЙ: ошибка чтения не маскируется под пустой журнал, и пустой журнал не маскируется под ошибку.
3. Журнал читается ОДИН раз на один --write: next_version и previous_link получают уже прочитанное состояние. Число запусков git на один --write закреплено ТЕСТОМ и равно двум, а не четырём.
4. НЕГАТИВНЫЙ СЦЕНАРИЙ ОШИБКИ: все пять прежних отказных путей родительской задачи остаются зелёными, публичные сигнатуры previous_link и next_version продолжают работать без предварительно прочитанного журнала.
5. Мутации объявлены ДО прогона, каждая новая ветвь убита, выжившие разобраны до конца.

## Plan

## Rollback

git revert коммита задачи. Артефакт RENAR-CONFORMANCE.yaml не регенерируется, схема и данные не затрагиваются.

## Journal

- 2026-09-04T19:25:23Z [implementation] — Root cause (logic-error): cwd у git-подпроцесса задаёт, КАКОЙ репозиторий будет найден, но путь после двоеточия в HEAD:ИМЯ резолвится от ВЕРХНЕГО УРОВНЯ worktree. Я прочитал cwd=root как «вопрос ограничен этим каталогом» и не проверил это замером, хотя git печатает подсказку про HEAD:./ИМЯ сам. Вторая половина того же корня: git_exec.run по замыслу НЕ бросает на ненулевом коде, поэтому ветвь «show.returncode != 0» собрала ВСЕ отказы git, а не только отсутствие пути, и объявила их фактом «журнал пуст» — той самой стороной, которая отказывается откатываться. Prevention: (1) Утверждение о том, ОТКУДА команда считает путь, проверяй запуском, а не чтением сигнатуры — здесь хватило двух вызовов на живом репозитории. (2) Ветвь «ошибка против отсутствия» не выводи из кода выхода команды, которая на всё отвечает одинаково: спрашивай отсутствие ОТДЕЛЬНЫМ вопросом с однозначным ответом (ls-tree даёт rc=0 и пустой вывод). (3) Фикстура, которая кладёт корень проекта ровно туда, где лежит .git, СТРУКТУРНО не может увидеть этот класс — в родительской задаче таких фикстур было шесть, все зелёные; пиши хотя бы одну с корнем в ПОДКАТАЛОГЕ. Записано памятью #576. ЗАМЕРЫ, НА КОТОРЫХ ДЕРЖИТСЯ ПОЧИНКА. Из scripts: git show HEAD:CHANGELOG.md rc=0 (файл из КОРНЯ), git show HEAD:project.py fatal с подсказкой HEAD:./project.py, git show HEAD:./project.py rc=0. ls-tree: наличие rc=0 со строкой, отсутствие rc=0 с пустым выводом, не-репозиторий rc=128, битая ссылка rc=128. МУТАЦИИ: объявлено 8, убито 8. N2 СНАЧАЛА ВЫЖИЛ и был разобран до конца — оказалось, я объявил ему неверный убийца: проба ls-tree обрывает путь до чтения blob, когда своего манифеста нет, поэтому потеря ./ в том сценарии не наблюдаема. Дыра настоящая и была не покрыта: свой манифест закоммичен И наверху лежит чужой — тогда проба проходит, чтение идёт и без ./ возвращает ЧУЖОЙ манифест. Написан test_our_own_entry_is_read_not_the_one_at_the_top, после чего N2 убит. Negative: пять отказных путей плюс два новых — blob числится в HEAD, но нечитаем (ошибка, а не отсутствие) и корень проекта в подкаталоге без своего манифеста (отсутствие, а не ошибка). Ни один не даёт ни падения, ни выдуманной ссылки. ЧТО НЕ ЗАКРЫТО И ПОЧЕМУ. Находка критика C2: next_version читает верхушку журнала, а не историю, поэтому с main сегодня переиздаётся v1. Заведена отдельной задачей next-version-reads-the-journal-tip-not-its-history — форма починки есть выбор из трёх вариантов с разной стоимостью, а не деталь. Здесь сделано ровно одно: докстринг перестал обещать «one past the highest ever issued» и называет остаток риска прямо. Переобещание убрано в ту же смену, в какую найдено.
- 2026-09-04T19:28:35Z [implementation] — Verification checklist. AC-1: ✓ tests/test_renar_manifest_chain.py::TestProjectRootBelowTheWorktreeTop::test_a_committed_manifest_below_the_top_is_still_found AC-1: ✓ tests/test_renar_manifest_chain.py::TestProjectRootBelowTheWorktreeTop::test_our_own_entry_is_read_not_the_one_at_the_top AC-2: ✓ tests/test_renar_manifest_chain.py::TestProjectRootBelowTheWorktreeTop::test_a_nested_root_still_tells_an_empty_journal_from_an_unreadable_one AC-2: ✓ tests/test_renar_manifest_chain.py::TestProjectRootBelowTheWorktreeTop::test_a_sibling_directorys_manifest_is_not_mistaken_for_ours AC-2: ✓ tests/test_renar_manifest_chain.py::test_a_blob_listed_but_unreadable_is_an_error_not_an_absence AC-3: ✓ tests/test_renar_manifest_chain.py::TestWriteChainEndToEnd::test_one_write_reads_the_journal_exactly_once AC-4: ✓ tests/test_renar_manifest_chain.py::TestJournalOutranksWorkingCopy (пять прежних отказных путей, все зелёные) AC-4: ✓ tests/test_renar_manifest_chain.py::test_a_git_failure_is_not_a_fabricated_link AC-4: ✓ tests/test_renar_manifest_chain.py::test_the_link_names_the_predecessor_not_today (публичные сигнатуры previous_link и next_version работают без предварительно прочитанного журнала) AC-5: ✓ verification_run #2071 (exit=0, receipt signed) плюс мутации N1-N8, убито 8 из 8, выживший N2 разобран до конца и породил недостающий тест Domain: результат осмыслен вне тестов и опирается на замер живого git, а не на чтение сигнатуры. Из каталога scripts настоящего репозитория: git show HEAD:CHANGELOG.md отдаёт файл из КОРНЯ, git show HEAD:project.py падает с подсказкой самого git про HEAD:./project.py, git show HEAD:./project.py отдаёт верный файл. Реальный вход, на котором это важно: TAUSIK ставится в чужие проекты, и .tausik ниже верхнего уровня репозитория — штатная раскладка монорепозитория, а не экзотика. Без ./ такой проект либо не находил свой манифест, либо публиковал ссылку на ЧУЖОЙ журнал аудита; вторая форма опаснее, потому что резолвится. Domain: вторая половина проверена так же — коды выхода git измерены, а не предположены: ls-tree даёт rc=0 с пустым выводом при отсутствии, rc=0 со строкой при наличии, rc=128 при отсутствии репозитория и при битой ссылке. Именно поэтому отсутствие спрашивается ls-tree, а не выводится из rc у show, который на все свои отказы отвечает 128 одинаково. Полная лента 8900 passed / 25 skipped / 0 failed за 113.3 с; ruff, ruff format --check, mypy чисто; bootstrap --ide all и --check без дрейфа; размеры 338 и 532 (тест — исключение из лимита).
- 2026-09-04T19:30:00Z [implementation] — ВТОРОЙ ВЫЖИВШИЙ МУТАНТ, НАЙДЕН РЕВЬЮ, РАЗОБРАН ДО КОНЦА. Тестирующий рецензент прогнал мутацию, которой я НЕ ОБЪЯВЛЯЛ: ослабил охрану link = f"{mid}@v{version}" if version and mid else None до простого if mid. Мутант ВЫЖИЛ на всех 27 тестах. ПОЧЕМУ. Все производители пары (версия, id) — _parse_manifest, _existing_manifest, journal_manifest — дают либо (0, None), либо (n больше нуля, "id"). Промежуточной формы (0, "id") лента не порождала НИГДЕ, поэтому половина version and была для неё НЕОТЛИЧИМА от отсутствия. Но форма достижима: манифест с manifest-id и БЕЗ manifest-version разбирается ровно в (0, "id"), потому что _parse_manifest берёт int(data.get("manifest-version", 0)). Под ослабленной охраной публикуется id@v0 — версия, которой законно не бывает, то есть ровно тот класс §13.4.2, против которого писался весь этот модуль. Симметрия, которую я упустил: тест на «id нет, версия есть» у меня БЫЛ (test_a_manifest_without_an_id_yields_no_link), обратного не было. Охрана из двух условий требует двух отказных случаев, по одному на каждое. Написан test_a_journal_entry_without_a_version_yields_no_link (запись коммитится в журнал, чтобы шла ветвь журнала, а не отката). Мутация повторена после — УБИТА. Итог по задаче: мутаций девять, убито девять, выживших ноль; двое выживали сначала, и оба указали на настоящую дыру. Negative: покрыты обе половины охраны — id без версии и версия без id.
