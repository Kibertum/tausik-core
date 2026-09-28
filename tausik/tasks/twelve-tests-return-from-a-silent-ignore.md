---
slug: twelve-tests-return-from-a-silent-ignore
title: "Двенадцать тестов возвращаются из --ignore, приехавшего молча в сборном релизном коммите"
status: done
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - ".github/workflows/tests.yml"
  - ".gitlab-ci.yml"
  - "tests/test_ci_lanes_are_honest.py"
scope_paths:
  - ".github/workflows/tests.yml"
  - ".gitlab-ci.yml"
  - "tests/test_ci_lanes_are_honest.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - full-lane-runs-serial-on-a-twenty-core-machine
completed_at: "2026-09-08T08:51:50Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕРЕНО #189, И ЗАМЕР СНИМАЕТ ЕДИНСТВЕННОЕ ВОЗРАЖЕНИЕ. Оба файла — tests/test_bootstrap_skills_coverage.py (8 тестов) и tests/test_bootstrap_real.py (4) — исключены `--ignore` в .github/workflows/tests.yml (и в быстрой матрице, и в джобе test-full) и в .gitlab-ci.yml. В быстрой ленте они пропущены как slow, в полной локальной убиты сторожем. Итого ДВЕНАДЦАТЬ тестов не выполняются НИГДЕ, и их молчание неотличимо от зелени.
ПРОИСХОЖДЕНИЕ УСТАНОВЛЕНО ГИТОМ, а не догадкой: оба --ignore внесены коммитом 3189f67 (26.04, сборный релиз v1.3), где о них не сказано ни слова ни в сообщении, ни рядом в диффе; в первой версии файла (a158380) их не было; затем скопированы в GitLab (fd803f3) и в локальные замеры. Никто не решал их исключить по существу.
ВОЗРАЖЕНИЕ «А ВДРУГ ОНИ КРАСНЫЕ» СНЯТО: прогон с -o faulthandler_timeout=600 последовательно дал 22 passed за 824.32 s, exit 0. Они здоровы, они просто длинные (52.47-65.35 s).
ДЕЛАЕТСЯ ПОСЛЕ решения по сторожу зависаний и включения xdist, иначе возврат приведёт к тем же смертям. НЕГАТИВНОЕ: тест обязан краснеть, если --ignore вернётся, — иначе исключение приедет молча во второй раз.

## Acceptance Criteria

AC1. НИ ОДНА ЛЕНТА CI НЕ ИСКЛЮЧАЕТ ТЕСТОВЫЙ ФАЙЛ ПО ПУТИ. Ни в .github/workflows/tests.yml, ни в .gitlab-ci.yml нет действующего --ignore на tests/.

AC2. ДВЕНАДЦАТЬ ТЕСТОВ ДОСТИЖИМЫ И ЗЕЛЕНЫ. Прогон обоих модулей с -m '' завершается успехом, и это ЗАМЕР, а не рассуждение.

AC3. ЕСТЬ ЛЕНТА, КОТОРАЯ ИХ ДЕЙСТВИТЕЛЬНО ЗАПУСКАЕТ. Существует джоб, зовущий полную ленту (-m ''), — иначе снятие --ignore ничего не меняет: slow-маркер продолжает их отсекать.

AC4 (НЕГАТИВНЫЙ). ВОЗВРАТ --ignore КРАСНЕЕТ. Тест обязан отказать, если исключение по пути вернётся в любой из двух конфигов, — иначе оно приедет молча во второй раз, ровно как в первый.

AC5. ГРАНИЦА. Отсутствие полной ленты в GitLab здесь НЕ чинится: это отдельный открытый дефект gitlab-has-no-full-lane-at-all, и комментарий в самом конфиге об этом говорит.

## Plan

## Rollback

Правка двух строк в двух файлах CI. Откат — git revert; продуктовый код не трогается.

## Journal

- 2026-09-08T08:51:20Z [implementation] — Верификационный чек-лист (SENAR Rule 5): AC-1: ✓ tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file AC-2: ✓ замер сегодня: pytest tests/test_bootstrap_skills_coverage.py tests/test_bootstrap_real.py -m '' — 12 passed за 63.24 s, exit 0 AC-3: ✓ tests/test_ci_lanes_are_honest.py::test_a_job_runs_the_full_slow_lane AC-4: ✓ tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file (тот же тест краснеет на возврате) AC-5: ✓ граница соблюдена: .gitlab-ci.yml не менялся, открытый дефект назван в журнале и в комментарии конфига
- 2026-09-08T08:51:20Z [implementation] — ЗАКРЫВАЕТСЯ ПО ФАКТУ, А НЕ ПОВТОРНОЙ ПРАВКОЙ. Работа приехала внутри задач-предшественниц, ровно как предсказывала сама формулировка («ДЕЛАЕТСЯ ПОСЛЕ решения по сторожу зависаний и включения xdist»). Установлено гитом, а не памятью: — коммит 2bfd3d1 («сторож зависаний перестал убивать здоровые тесты») УБРАЛ оба --ignore из .github/workflows/tests.yml и .gitlab-ci.yml; — коммит 25fe8ef починил триггер ветки в GitLab; — джоб test-full в GitHub зовёт `pytest tests/ -m ''` без исключений, то есть двенадцать тестов там ИСПОЛНЯЮТСЯ. ЗАМЕР СЕГОДНЯ (смена #232): прогон обоих модулей с -m '' — 12 passed за 63.24 s, exit 0. Замер #189 давал 824.32 s последовательно; разница — xdist, включённый задачей про полную ленту. То есть возражение «они длинные» снято не обещанием, а числом: минута. СТОРОЖ НА МЕСТЕ: tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file отказывает при возврате --ignore на tests/ в любом из двух конфигов и называет решение #275. ОСТАЁТСЯ ОТКРЫТЫМ И НЕ ЗАКРЫВАЕТСЯ ЗДЕСЬ: в GitLab полной ленты нет вовсе, поэтому на линии разработки эти двенадцать по-прежнему не гоняются. Это отдельный дефект gitlab-has-no-full-lane-at-all, и комментарий в .gitlab-ci.yml прямо это говорит.
- 2026-09-08T09:42:21Z [done] — ПОПРАВКА К ЦИТАТАМ ЭТОГО ЗАКРЫТИЯ — НАЙДЕНА РЕВЬЮ, ДЕФЕКТ МОЙ. В чек-листе и в журнале трижды назван узел tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file. Класса TestNoLaneExcludesByPath НЕ СУЩЕСТВУЕТ. Настоящий адрес: tests/test_ci_lanes_are_honest.py::TestNoCiLaneExcludesTestFiles::test_no_ci_command_ignores_a_test_file Тест существует, зелен и делает ровно то, что о нём сказано, — неверно было ИМЯ КЛАССА, написанное по памяти вместо чтения файла. Это класс «выдуманной цитаты»: ссылка была неверна уже в момент написания, и по ней доказательство закрытия не разрешается. ПРИЧИНА: имя метода я скопировал из вывода grep, а имя класса дописал по смыслу. Правило на будущее: узел цитируется ЦЕЛИКОМ из одного источника — вывода pytest или разбора файла, — а не собирается из двух. AC-1 и AC-4 закрытия сохраняют силу: тест тот же, адрес исправлен.
- 2026-09-26T18:44:28Z [done] — EVIDENCE-UNPROVEN: tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath::test_no_ci_command_ignores_a_test_file — git never carried this path or member under any directory
