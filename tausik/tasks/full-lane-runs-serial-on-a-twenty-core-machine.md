---
slug: full-lane-runs-serial-on-a-twenty-core-machine
title: "Полная лента идёт в один поток на двадцатиядерной машине: 32 минуты вместо четырёх"
status: done
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "pyproject.toml (addopts + комментарий с числами), .github/workflows/tests.yml, .github/workflows/test-coverage.yml, .gitlab-ci.yml, CONTRIBUTING.md, tests/test_ci_lanes_are_honest.py (храповик), scripts/gate_command_runner.py (инъекция полной ленты), tests/test_gates.py (утверждения об инъекции), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files:
  - pyproject.toml
  - ".github/workflows/tests.yml"
  - ".github/workflows/test-coverage.yml"
  - ".gitlab-ci.yml"
  - CONTRIBUTING.md
  - "tests/test_ci_lanes_are_honest.py"
  - "scripts/gate_command_runner.py"
  - "tests/test_gates.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on:
  - hang-guard-promises-eleven-times-headroom-and-has-one
completed_at: "2026-08-30T18:33:40Z"
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

ЗАМЕРЕНО В СЕССИИ #186, НЕ ПРЕДПОЛОЖЕНО. Полная лента (`pytest -m ''`) на дереве 3c3c87a: последовательно — 7395 passed за 32m24s; под `-n auto` на 20 ядрах — 7397 passed, 24 skipped, 2 failed за 228.59s (3m48s). УСКОРЕНИЕ 8.5x.

pytest-xdist не установлен и не упомянут НИГДЕ: ни в pyproject.toml, ни в requirements.txt, ни в .gitlab-ci.yml, ни в .github/workflows/*.yml. Девятнадцать ядер из двадцати простаивают все 32 минуты.

ПОЧЕМУ ЭТО НЕ ЛЕЧИТСЯ ВЫЧЁРКИВАНИЕМ ТЕСТОВ. Стоимость ленты ПЛОСКАЯ — записано в самом pyproject.toml: «30 самых медленных это 10% от неё, остальное ~0.09 s x 5700». И масса корпуса тоже плоская: 409 файлов, 5859 функций, топ-20 файлов дают 18% массы, топ-60 — 37.5%. Толстого хвоста, вырезав который что-то изменится, НЕ СУЩЕСТВУЕТ. Вычеркнуть 1000 тестов (17% корпуса, недели судейства, риск снести настоящего стража) купило бы примерно 5 минут. Одна строка конфига покупает 28.

ДВА ПАДЕНИЯ ЗАМЕРА, И ОНИ РАЗНЫЕ:
1) tests/test_mypy_clean.py::test_declared_tree_is_mypy_clean — АРТЕФАКТ ЗАМЕРА, не находка: во временное окружение не был поставлен mypy, тест честно сказал «No module named mypy». К xdist отношения не имеет.
2) tests/test_stress.py::TestStressSessions::test_100_sessions — НАСТОЯЩИЙ кандидат в xdist-небезопасные. Воркер gw14 умер («node down: Not properly terminated»), трассировка ведёт в service_session.session_end -> subprocess.run. Стресс-тест, поднимающий 100 сессий, под двадцатью параллельными воркерами либо дерётся за общий ресурс (.tausik/, SQLite, cwd), либо выедает машину. РАЗОБРАТЬ, а не объявить: либо чинится, либо получает объявленную последовательную группу (xdist_group), и причина записывается словами.

ЧТО ДЕЛАЕТСЯ: pytest-xdist в requirements.txt, `-n auto` в [tool.pytest.ini_options], разбор test_100_sessions. Проверить взаимодействие с faulthandler_timeout = 60 и faulthandler_exit_on_timeout: в замере сторож зависаний ЛОЖНО НЕ СРАБОТАЛ ни разу под двадцатью воркерами, но это надо закрепить, а не запомнить. Проверить, что порядок тестов, ставший недетерминированным, не прячет тесты, зависящие друг от друга.

ФЕНС ВЛАДЕЛЬЦА: pyproject.toml правится только с его согласия и ОДНИМ ЗАХОДОМ вместе с hang-guard-promises-eleven-times-headroom-and-has-one и pytest-asyncio-default-loop-scope-unset-warns-on-every-run — все три правят один и тот же блок [tool.pytest.ini_options].

ОГОВОРКА К ЧИСЛАМ: замер гонялся с --ignore двух bootstrap-модулей (скопировано из CI), поэтому 7397 и 7395 — не строго одна выборка. Порядок ускорения это не меняет, но при закреплении базовой линии выборки обязаны совпасть.

## Acceptance Criteria

1. ПАРАЛЛЕЛЬ ВКЛЮЧЕНА КОНФИГОМ, А НЕ ПАМЯТЬЮ: -n auto стоит в addopts pyproject.toml, поэтому любой прогон в корне репозитория идёт параллельно без ручного флага. Квитанция: прогон БЕЗ флагов печатает в шапке gw0..gwN.
2. ПОЛНАЯ ЛЕНТА ЗЕЛЁНАЯ ПОД ПАРАЛЛЕЛЬЮ: pytest -m '' даёт exit 0, состав сверен с замером #190 (7434 passed, 24 skipped). Расхождение, если оно есть, объяснено числом, а не словом.
3. КАЖДЫЙ ПУТЬ УСТАНОВКИ СТАВИТ pytest-xdist. Их ПЯТЬ, а не два: .github/workflows/tests.yml (джобы test и test-full), .github/workflows/test-coverage.yml, .gitlab-ci.yml, CONTRIBUTING.md (английский и русский блоки).
4. НЕГАТИВНЫЙ СЦЕНАРИЙ, ДОКАЗАННЫЙ МУТАЦИЕЙ: если хоть одна строка установки ставит pytest БЕЗ pytest-xdist, пока addopts требует -n, храповик обязан упасть с ненулевым кодом и назвать файл-нарушитель. Проверяется удалением pytest-xdist из одного файла -> ошибка, exit 1; возврат копией со сверкой sha256, не git checkout. Ошибка самого прогона без плагина тоже названа: pytest: error: unrecognized arguments: -n.
5. ПОЛНАЯ ЛЕНТА ЧЕРЕЗ TAUSIK_VERIFY_FULL=1 НЕ ТЕРЯЕТ ПАРАЛЛЕЛЬ: инъекция снимает только фильтр маркеров, а не весь addopts. Квитанция: collect-only даёт тот же состав 7459, что и прежнее стирание addopts.
6. ЦЕНА НАЗВАНА ЧИСЛОМ И ЗАПИСАНА РЯДОМ С ФЛАГОМ: узкий scoped-прогон дорожает с 1.68 s до 6.80 s (tests/test_gate_outcome.py, 20 тестов) — это фиксированный старт воркеров, и он платится на КАЖДОМ верифае.

## Plan

## Rollback

Строка -n auto в pyproject плюс pytest-xdist в requirements. Откат: git revert возвращает последовательный прогон; результат тестов от способа запуска не зависит, поэтому откат не меняет вердиктов.

## Journal

- 2026-08-26T11:02:43Z [planning] — ЗАМЕР СЕССИИ #187 ОПРОВЕРГ ГЛАВНУЮ ПОСЫЛКУ ЭТОЙ ЗАДАЧИ: ПАДЕНИЯ ПОД XDIST — НЕ ОТ XDIST. Полная лента под `-n auto` на 20 ядрах, БЕЗ --ignore (в отличие от замера #186): 7414 passed, 24 skipped, 14 FAILED за 316.97 s. Не 2 падения, а 14. Разница с #186 объясняется целиком: тот замер гонялся с `--ignore` двух bootstrap-модулей, скопированным из CI, и потому этих падений не видел (оговорка о несовпадении выборок в цели задачи оказалась важнее, чем выглядела). СОСТАВ 14 ПАДЕНИЙ: tests/test_bootstrap_skills_coverage.py — 9, tests/test_bootstrap_real.py — 4, tests/test_stress.py — 2 (test_100_sessions, test_session_handoff_chain). Все — «worker crashed», ни одного обычного assert. ПРИЧИНА НАЙДЕНА, И ОНА ОДНА НА ВСЕ 14. Прогнал те же три файла ПОСЛЕДОВАТЕЛЬНО, без xdist: падают так же, и причина печатается прямым текстом — `Timeout (0:01:00)!` с дампом стеков всех потоков, то есть faulthandler_timeout=60 + faulthandler_exit_on_timeout=true. Сторож зависаний убивает процесс, и для xdist это выглядит как «node down: Not properly terminated». XDIST ЗДЕСЬ НИ ПРИ ЧЁМ: он лишь переводит смерть процесса в «воркер упал». СЛЕДСТВИЕ ДЛЯ ЭТОЙ ЗАДАЧИ. Пункт «разобрать test_100_sessions: чинить или объявить последовательную группу xdist_group» ОТПАДАЕТ в своей нынешней формулировке — тест не xdist-небезопасен, он просто дольше 60 секунд. Объявлять ему последовательную группу значило бы лечить симптом чужой болезни. Порядок работ переворачивается: сначала развилка сторожа зависаний (hang-guard-promises-eleven-times-headroom-and-has-one), потом xdist. ДЛИТЕЛЬНОСТИ ПОД XDIST (для калибровки порога, топ-6): test_bulk_status_transitions 59.13 s — В ОДНОЙ СЕКУНДЕ ОТ ПОРОГА; test_full_lane_strictly_larger_than_fast_lane 39.07; test_declared_tree_is_mypy_clean 32.67; test_status_under_load 30.58; test_creates_venv 27.94; test_metrics_under_load 27.54. Тесты, чьи воркеры убиты, в список длительностей не попадают вообще — их истинное время НЕ ИЗМЕРЕНО ни разу, потому что их всегда убивают раньше. ЧТО ЕЩЁ НЕ ЗАМЕРЕНО И ЖДЁТ СУББОТЫ: прогон тех же трёх файлов с поднятым порогом (-o faulthandler_timeout=600) — он даст НАСТОЯЩЕЕ время test_100_sessions и двух bootstrap-модулей и тем самым цифру для развилки владельца. Запуск был начат и прерван остановкой сессии. ОТДЕЛЬНАЯ НАХОДКА, ЗАВЕДЕНА ЗАДАЧЕЙ tracebacks-name-a-repository-path-that-does-not-exist: трассировка сторожа называет файл как D:\Work\Personal\claude\tests\... — путь, которого не существует; похоже на co_filename из .pyc, переживших переезд дерева. К падениям отношения не имеет, диагностику путает.
- 2026-08-29T11:47:47Z [planning] — [#189] ПОПРАВКА К СОСТАВУ ЧЕТЫРНАДЦАТИ ПАДЕНИЙ И ОТВЕТ О ИХ ЗДОРОВЬЕ. Замер (три файла, -m '', -o faulthandler_timeout=600, последовательно): 22 passed за 824.32 s, exit 0 — все четырнадцать ЗДОРОВЫ, они медленные, а не сломанные. Состав, проверенный подсчётом функций: skills_coverage 8 (весь файл), bootstrap_real 4 (весь файл), stress 2 — 8+4+2=14; прежняя запись «9+4+2» давала 15 и была неверна. Настоящее время: двенадцать в диапазоне 52.47-65.35 s, из них семь больше 60 s даже в изоляции; test_100_sessions 43.43 s последовательно против 77.09 s под нагрузкой xdist — то есть накладные xdist на этом тесте примерно 1.8x, и они реальны, но убивает его порог, а не гонка. Вывод для порядка работ подтверждён: xdist ставится ПОСЛЕ решения по сторожу, иначе те же четырнадцать умрут снова, просто быстрее.
- 2026-08-30T17:51:34Z [implementation] — [#191] ПРАВКА СДЕЛАНА, КВИТАНЦИИ СНЯТЫ ДО ПОЛНОГО ПРОГОНА. addopts = "-m 'not slow' -n auto". Прогон БЕЗ флагов печатает «created: 20/20 workers» — AC1 закрыт. Путей установки оказалось ПЯТЬ, а не два, названных в передаче смены: третий workflow .github/workflows/test-coverage.yml гоняет pytest со своим списком (pytest pytest-cov) и глушит падение через `|| true`, то есть без плагина отчитался бы «нет данных о покрытии» вместо смерти; и CONTRIBUTING.md (два блока) — первый же pytest нового участника упал бы на unrecognized arguments: -n. Храповик добавлен в tests/test_ci_lanes_are_honest.py, требование выводится из самого addopts (снимут -n — правило само уходит). МУТАЦИЯ: снял pytest-xdist из .gitlab-ci.yml и из английского блока CONTRIBUTING.md -> exit 1, оба файла названы поимённо; возврат копией, sha256 совпал побайтово (f660131d..., 337be5c7...). НАЙДЕНО ПОПУТНО И ПОЧИНЕНО ТУТ ЖЕ: TAUSIK_VERIFY_FULL=1 вставлял --override-ini=addopts=, то есть стирал addopts ЦЕЛИКОМ вместе с -n auto — единственный прогон, обязанный быть полной батареей, стал бы единственным последовательным. Заменено на -m '' (побеждает маркер из addopts, потому что разбирается позже). Замер: -m '' и --override-ini=addopts= дают ОДИНАКОВЫЙ состав 7459 против 7317 быстрой ленты; при этом -m '' сохраняет «created: 20/20 workers», а стирание addopts даёт последовательный прогон (20 passed in 0.94s против 4.43s). ЦЕНА ЗАМЕРЕНА: узкий scoped-прогон 1.68 s -> 6.80 s (tests/test_gate_outcome.py, 20 тестов) — фиксированный старт воркеров, платится на каждом верифае; записана рядом с флагом в pyproject. Предполётные: ruff чист, tests/test_gates.py + test_gate_outcome.py + test_gate_command_runner.py — 148 passed.
- 2026-08-30T18:33:38Z [implementation] — AC1 PASS — addopts = "-m 'not slow' -n auto" в pyproject.toml. Квитанция: `python -m pytest tests/test_gate_outcome.py` БЕЗ единого флага печатает «created: 20/20 workers» и «20 workers [20 items]». Параллель включена конфигом, а не памятью. AC2 PASS — полная лента под параллелью: 7438 passed, 24 skipped, exit 0, 783.94 s (wall 795.52). Состав сверен ЧИСЛОМ, а не словом: предыдущий прогон дал 7435 passed + 1 failed = 7436 исполненных, плюс два новых теста порядка бюджета (TestTheInnerBudgetIsOrderedUnderTheGuard) = 7438. Расхождение с замером #190 (7434/7435) объясняется тем же способом: +1 храповик установки, +2 теста порядка. AC3 PASS — pytest-xdist стоит во всех ПЯТИ путях: .github/workflows/tests.yml (джобы test и test-full, обе строки pip install), .github/workflows/test-coverage.yml (третий workflow, найден в этой сессии — он гоняет pytest со своим списком и глушит падение через `|| true`, то есть отчитался бы «нет данных о покрытии» вместо смерти), .gitlab-ci.yml (якорь .venv), CONTRIBUTING.md (английский и русский блоки). AC4 PASS — храповик test_every_install_of_pytest_also_installs_what_addopts_needs в tests/test_ci_lanes_are_honest.py выводит требование из самого addopts (снимут -n — правило уходит само) и требует минимум пять проверенных строк установки, чтобы переименование ленты не сделало его пустым. МУТАЦИЯ: снял pytest-xdist из .gitlab-ci.yml и из английского блока CONTRIBUTING.md -> exit 1 с поимённым списком обоих нарушителей; возврат копией, sha256 совпал побайтово (f660131d..., 337be5c7...), тест снова зелёный. AC5 PASS — TAUSIK_VERIFY_FULL=1 больше не теряет параллель. Инъекция заменена с --override-ini=addopts= на -m ''. Замеры: состав одинаков (`-m ''` -> 7459 collected, `--override-ini=addopts=` -> 7459 collected, быстрая лента 7317); параллель сохраняется только у нового варианта — `pytest tests/test_gate_outcome.py -m ''` даёт «created: 20/20 workers» и 4.43 s, а старое стирание addopts даёт последовательный прогон 0.94 s без воркеров. Утверждения переписаны в tests/test_gates.py и сравнивают argv как ПОСЛЕДОВАТЕЛЬНОСТЬ, потому что пустой аргумент в склейке строк исчезает. AC6 PASS — цена названа числом и лежит рядом с флагом в pyproject.toml: узкий scoped-прогон tests/test_gate_outcome.py (20 тестов) дорожает с 1.68 s до 6.80 s, это фиксированный старт воркеров, и он платится на каждом верифае. Там же записано, почему pytest-xdist НЕ кладётся в requirements.txt (это рантайм-venv MCP с обязательным верхним пределом, а не тестовый инструментарий).
- 2026-08-30T18:33:58Z [done] — [#191] МАРКЕРЫ ДОКАЗАТЕЛЬСТВ, которых недосчитался парсер при закрытии. AC-1: ✓ прогон без флагов печатает «created: 20/20 workers» (tests/test_gate_outcome.py). AC-2: ✓ полная лента pytest -m '' — 7438 passed, 24 skipped, exit 0, 783.94 s. AC-3: ✓ pytest-xdist во всех пяти путях установки, проверяется тестом tests/test_ci_lanes_are_honest.py::TestEveryLaneInstallsWhatTheAddoptsDemand::test_every_install_of_pytest_also_installs_what_addopts_needs — он требует минимум пять строк установки с pytest и падает, если хоть одна из них без плагина. AC-4: ✓ мутация, см. ниже. AC-5: ✓ tests/test_gates.py::TestGateRunner::test_pytest_gate_full_lane_env_var_injects_override + test_pytest_via_python_m_gets_override. AC-6: ✓ числа 1.68 s -> 6.80 s записаны в pyproject.toml рядом с флагом. Negative: снял pytest-xdist из .gitlab-ci.yml и из английского блока CONTRIBUTING.md -> храповик упал с exit 1 и назвал ОБА файла поимённо («.gitlab-ci.yml: pytest PyYAML ruff misses ['pytest-xdist']», «CONTRIBUTING.md: pytest ruff pyyaml misses ['pytest-xdist']»); возврат копией, sha256 совпал побайтово, тест снова зелёный. Второй негативный: без плагина pytest вообще не стартует — `unrecognized arguments: -n`, то есть отказ громкий, а не тихий. Domain: смысл вне тестов проверяется тем, что лента реально исполняется двадцатью процессами и даёт тот же вердикт, что последовательная: 7438 passed / 24 skipped / exit 0 против 7434-7435 passed у последовательно-эквивалентных прогонов #190, и вся разница — это два добавленных теста и один храповик, а не изменившиеся вердикты. Результат теста от способа запуска не зависит; меняется только время.
