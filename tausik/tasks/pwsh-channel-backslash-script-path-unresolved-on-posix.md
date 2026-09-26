---
slug: pwsh-channel-backslash-script-path-unresolved-on-posix
title: "Канал PowerShell не разрешает путь скрипта с обратной косой на posix: python .\\helper.py проходит гейт записи с кодом 0 в CI на Linux"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: pwsh-write-gate-does-not-read-script-files-either
scope: null
scope_exclude: "Канал Bash и python_source_writes не меняются — обратная косая в Bash есть экранирование, а не разделитель; резолвер общий и нейтрален к диалекту; формы Start-Process не расширяются"
relevant_files:
  - "scripts/hooks/pwsh_write_parse.py"
  - "tests/test_pwsh_channel_reads_script_files.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/hooks/pwsh_write_parse.py"
  - "tests/test_pwsh_channel_reads_script_files.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T20:39:15Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАВЕДЕНО ПО ПЕРВОМУ ПАЙПЛАЙНУ 1.9 НА GITLAB (#6658, job tests 34449, Linux). Падение: tests/test_pwsh_channel_reads_script_files.py::TestTheLiveGateOnThePowerShellChannel::test_a_script_writing_outside_the_acl_is_refused[python .\helper.py] — _gate вернул 0, ожидалось 2; остальные четыре написания (helper.py, & python helper.py, ./helper.py, Start-Process) на Linux зелёные. МЕХАНИЗМ (по коду, не догадка): pwsh_write_parse._script_argv отдаёт токен «.\helper.py» как есть (докстринг: «python .\x.py needs nothing done to it» — верно ТОЛЬКО на Windows), python_source_writes.writes_in_script_file делает os.path.join(root, script): на posix обратная косая — символ имени, файла «.\helper.py» нет, fail-soft отдаёт пусто, гейт пропускает запись вне ACL. PowerShell на любом хосте (pwsh на Linux тоже) принимает обратную косую как разделитель, значит нормализация принадлежит ДИАЛЕКТУ, а не резолверу. Тест 9 ячеек из #201 замерялся на Windows; лента WSL #205 этот файл уже содержала? — проверить по журналу #205 (8066 тестов); в CI это первый прогон файла на Linux. Долг качества pwsh-write-gate-does-not-read-script-files-either, найден CI.

## Acceptance Criteria

AC1 НОРМАЛИЗАЦИЯ В ДИАЛЕКТЕ: _script_argv (или его вызов) переводит обратные косые в токене скрипта в os.sep на любом хосте, потому что PowerShell на любом хосте принимает их как разделитель; на Windows поведение побайтово прежнее; докстринг «needs nothing done to it» исправлен на измеренное.
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ: параметризованный тест python .\helper.py зелёный на Linux (прогон в WSL, числа в журнале) и на Windows; мутации: нормализация снята — тест краснеет в WSL (на Windows остаётся зелёным — и это записано как граница мутации); нормализация применена и к каналу Bash — контрольный тест Bash с обратной косой как экранированием краснеет либо, если такого теста нет, он добавляется (ошибка «экранирование прочитано как разделитель» должна быть видна).
AC3 CHANGELOG.md и CHANGELOG.ru.md синхронно; scoped verify зелёный; ruff/mypy чисто; bootstrap --ide all перед done (правится scripts/hooks), verify после него; память ДО done.

## Plan

## Rollback

git revert коммита: канал возвращается к передаче пути как есть; на Windows поведение не меняется

## Journal

- 2026-09-03T20:28:34Z [implementation] — СТАРТ (параллельно с snapshot-test-races-the-clock-on-linux, ждущей цикла в WSL; scope_write_gate берёт ВСЕ активные задачи). Инвентарь по вызову: _script_argv (pwsh_write_parse.py:103) -> writes_in_script_file (python_source_writes.py:211, os.path.join общий для диалектов). Несущее место одно — _script_argv; потребитель один — _parse:216; тесты — test_pwsh_channel_reads_script_files.py. Сложность simple подтверждена. Починка: нормализация обратной косой в os.sep в самом диалекте, только для токенов-путей (не после -c/-m, без пробелов и кавычек, не опции); на Windows тождество.
- 2026-09-03T20:32:21Z [implementation] — ПОЧИНКА: _paths_for_host в pwsh_write_parse — обратная косая -> os.sep только в токенах-путях (не опция, не после -c/-m, без пробелов и кавычек); _script_argv применяет её к обеим ветвям. Тесты: класс TestABackslashIsAPathInPowerShellAndAnEscapeInBash — две ячейки с ПРОТИВОПОЛОЖНЫМИ вердиктами файлов .helper.py и helper.py, код выхода говорит, какой файл прочёл каждый диалект (Bash 2/0, PowerShell 0/2); плюс юнит-тест: payload -c сохраняет обратные косые. Windows: 15 passed, ruff/mypy чисто, файл 313 строк. LINUX (WSL-клон): 15 passed; параметр python .\helper.py зелёный. МУТАЦИИ: Linux — нормализация снята (HEAD-версия диалекта) -> 3 failed, в т.ч. ячейка CI и контрольная; Windows — та же мутация ОСТАЁТСЯ ЗЕЛЁНОЙ (os.sep есть обратная косая; граница мутации, записана). ВЫЖИЛО ДВОЕ и оба честно: (1) «утечка нормализации в общий резолвер» не наблюдаема ни на одной ОС — канал Bash съедает обратную косую ещё в shlex (.\helper.py -> .helper.py), до резолвера она не доходит; мутация недостижима, заменяю на достижимую (нормализация ДО лексера Bash); (2) «снято условие -c/-m» выжило, потому что payload юнит-теста содержит кавычки и его прикрывает правило о кавычках — payload заменяю на бескавычный с обратной косой.
- 2026-09-03T20:37:40Z [implementation] — МУТАЦИИ ИТОГО (базовый rc=0, убито только rc=1). Юнит-тест пиннит os.sep на «/» — иначе на Windows любая мутация замены невидима (тождество). Убиты на Windows: (a) нормализация снята в обычной ветке _script_argv; (a2) снята в ветке Start-Process; (c) снято правило -c/-m — payload a\nb превращался в a/nb; (d) нормализация утекла в диалект Bash ДО лексера — контрольная ячейка красная (Bash прочёл helper.py вместо .helper.py); (f) снято правило о кавычках — токен print('a\nb') нормализован. Убито на Linux (WSL-клон): диалект прежней версии -> 3 failed (ячейка CI python .\helper.py, контрольная plain-writes-outside, юнит-тест). Правило «не опции» УДАЛЕНО как непроверяемое (мутация выживала, потому что опции не резолвятся вовсе); правило «без пробелов» заменено на «без кавычек и перевода строки» — путь с пробелом приходит одним токеном и есть путь. Выжившая и объяснённая: «утечка в общий резолвер» ненаблюдаема на обеих ОС — Bash съедает обратную косую в shlex до резолвера; заменена достижимой (d).
- 2026-09-03T20:39:12Z [implementation] — AC-1: ✓ tests/test_pwsh_channel_reads_script_files.py::TestABackslashIsAPathInPowerShellAndAnEscapeInBash::test_a_dash_c_payload_keeps_its_backslashes (_paths_for_host в диалекте, обе ветви _script_argv, os.sep; на Windows тождество; докстринг исправлен). AC-2: ✓ tests/test_pwsh_channel_reads_script_files.py::TestTheLiveGateOnThePowerShellChannel::test_a_script_writing_outside_the_acl_is_refused зелёный на Linux (WSL-клон, 15 passed) и Windows; tests/test_pwsh_channel_reads_script_files.py::TestABackslashIsAPathInPowerShellAndAnEscapeInBash::test_each_dialect_reads_its_own_file — контроль Bash в двух ячейках; мутации в журнале: снята нормализация -> Linux 3 failed, Windows зелёный (граница записана); утечка в диалект Bash до лексера -> контроль красный; -c/-m и кавычки -> юнит-тест красный. AC-3: ✓ CHANGELOG.md + CHANGELOG.ru.md синхронно; ruff/mypy чисто; bootstrap --ide all выполнен, verify после него; память #545 до done. Root cause (missing-validation): диалект PowerShell отдавал путь с обратной косой общему резолверу как есть; на POSIX это символ имени, fail-soft скрыл «не найден». Prevention: значение символа знает диалект — он и переписывает путь для хоста; тест канала гоняется на posix, а не только на Windows (память #545). Domain: python .\helper.py на Linux отказан с кодом 2, Bash по-прежнему читает .helper.py.
- 2026-09-03T20:39:36Z [done] — Negative: python .\helper.py со скриптом, пишущим вне ACL, — гейт отказывает кодом 2 на Linux (WSL-клон, 15 passed) и Windows; диалект прежней версии на Linux — 3 failed; нормализация, утёкшая в лексер Bash, — контрольная ячейка красная; payload -c и токен с кавычкой сохраняют обратные косые (юнит-тест с os.sep=/). Все ячейки в журнале выше.
