---
slug: write-gate-reads-open-literals-out-of-strings-and-comments
title: "Гейт записи считает целью литерал open() из строки и даже из КОММЕНТАРИЯ: ложный блок на собственных тестах"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: write-gate-parses-command-text-not-writes
scope: null
scope_exclude: "scripts/hooks/pwsh_write_parse.py и pwsh_cmd_parse.py: канал PowerShell читает только субстрат ФАЙЛА через python_source_writes и не имеет встроенного плеча python -c вовсе — это отдельный дефект другого класса (пропуск, не фантом), проверяется пробником в #207 и заводится отдельной задачей, а не чинится здесь"
relevant_files:
  - "scripts/hooks/python_source_writes.py"
  - "scripts/hooks/python_invocation.py"
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/test_bash_write_gate_hook.py"
  - "tests/test_write_gate_reads_code_not_text.py"
  - "docs/ru/enforcement-coverage.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/hooks/python_source_writes.py"
  - "scripts/hooks/python_invocation.py"
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/test_bash_write_gate_hook.py"
  - "tests/test_write_gate_reads_code_not_text.py"
  - "docs/ru/enforcement-coverage.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T15:36:55Z"
---

## Goal

НАЙДЕНО ЗАМЕРОМ В #203, В ХОДЕ write-gate-bypassed-by-trailing-flag-and-versioned-interpreter, И ОТДЕЛЕНО ПО РЕШЕНИЮ #296: класс дефекта другой. Та задача чинила РАЗБОР АРГУМЕНТОВ команды (какой файл считается запускаемым скриптом). Этот дефект — в ТОЧНОСТИ ДЕТЕКТОРА содержимого: прочитав правильный файл, детектор не отличает исполняемый код от текста.

ЗАМЕР 1, СЛУЧАЙНЫЙ И ОТ ТОГО УБЕДИТЕЛЬНЫЙ. Гейт заблокировал запуск САМОГО измерительного стенда задачи: python <scratchpad>/measure_write_gate.py -> exit 2, названы три пути (harness/x.py, scripts/x.py, harness/y.py). Стенд не пишет НИ ОДНОГО из них: это строковые литералы, которые он записывает во временный каталог по вычисленному пути. Обход стоил одной строки — собрать литерал из кусков, — но обходить пришлось СВОЙ ЖЕ гейт, чтобы измерить его.

ЗАМЕР 2, ВОСПРОИЗВОДИМЫЙ И ЕЩЁ ХУЖЕ. python tests/test_x.py, где файл содержит ТОЛЬКО определение функции и КОММЕНТАРИЙ вида # fixture literal: open("harness/y.py", "w") -> exit 2, цель harness/y.py взята ИЗ КОММЕНТАРИЯ. Комментарий не исполняется никогда и ни при каких условиях.

ПОЧЕМУ ЭТО ВАЖНО, А НЕ КОСМЕТИКА. Ложный блок здесь дороже пропуска, и это записано в докстринге самого модуля как осознанная асимметрия: «a false block on an everyday command stops the work, and a gate that stops the work is one an agent learns to switch off». Наш собственный каталог tests/ полон литералов open(..., "w") — они там ПРЕДМЕТ проверки. Значит любой запуск тестового файла напрямую (а также любого скрипта, который эти литералы цитирует, документирует или генерирует) блокируется гейтом, называющим пути, которых команда не пишет. Агент, получивший такой отказ, учится не доверять отказу.

КОРНЕВАЯ ПРИЧИНА. _OPEN_RE есть регулярное выражение по ТЕКСТУ файла. Оно не знает ни строковых литералов, ни комментариев, ни закомментированного кода, ни docstring'ов.

НАПРАВЛЕНИЕ, НЕ ПРЕДПИСАНИЕ. Наиболее вероятный ход — разбирать прочитанный скрипт через ast и брать только настоящие узлы Call с именем open и константными аргументами; тогда комментарии и вложенные литералы отпадают по построению. Ограничители, которые придётся назвать ЯВНО и измерить: (1) файл с синтаксической ошибкой — мягкая деградация, как сейчас у нечитаемого; (2) стоимость ast.parse на каждой команде Bash при пределе 256 КБ; (3) не потерять то, что ловится сегодня — литеральный open внутри реально исполняемого кода обязан ловиться по-прежнему; (4) ВСТРОЕННЫЙ payload (python -c "...") разбирается тем же _OPEN_RE и по тексту команды, а не по файлу: решить, распространяется ли ход на него, и объявить.

НАЧИНАТЬ С ЗАМЕРА. Прогнать по РЕАЛЬНОМУ каталогу tests/ этого репозитория и предъявить ЦИФРОЙ, сколько файлов сейчас дают фантомную цель. Без этой цифры непонятно, ложный блок здесь редкость или норма.

## Acceptance Criteria

AC1 ЗАМЕР ДО/ПОСЛЕ ЦИФРОЙ. По всем .py репозитория (tests/, scripts/, harness/, bootstrap/; замер #207: 878 файлов): ДО — 6 файлов с целью от регулярного выражения, все 6 фантомы (исполняемых литералов AST не нашёл ни одного); ПОСЛЕ — 0 фантомов, 0 потерянных реальных целей. Цифры — в журнале задачи.
AC2 ТАБЛИЦА ФОРМ, а не примеров (память #535). НЕ цель: комментарий; docstring; строковый литерал; закомментированный код; режим чтения r/rb; вычисленный путь (f-строка, имя, конкатенация); режим не-константа. ЦЕЛЬ: голый open; атрибутная форма X.open (io/codecs); режим позиционный и ключевой mode=; путь ключевой file=; raw-строка и неявная склейка литералов; внутри def/with/class/lambda; режимы w/a/x и '+'. Каждая форма — тест через writes_in_source И через реальный write_targets (субстрат файла и субстрат python -c).
AC3 ВСТРОЕННЫЙ PAYLOAD python -c разбирается тем же AST. Формы -c: отдельный токен, склеенный -cCODE, кластер -uc, после -X/-W с их значениями, после -m -> нет кода. Аргументы-ДАННЫЕ больше не дают цель: python -m pytest -k "open('x','w')", python script.py "open('x','w')". Текстовое регулярное плечо остаётся ТОЛЬКО для упоминания не-python интерпретатора — объявлено в докстринге и enforcement-coverage.md.
AC4 ДЕГРАДАЦИЯ ОБЪЯВЛЕНА: исходник, который ast не читает (SyntaxError, NUL, RecursionError) — прежнее регулярное выражение, а не тишина; файл больше MAX_SCRIPT_BYTES — пусто, как раньше. Стоимость ast.parse измерена на худшем файле репозитория и записана в журнал.
AC5 МУТАЦИИ: не менее трёх мутаций детектора (снять fallback на SyntaxError, снять ключевой mode=, снять '+', считать Constant в docstring вызовом) — каждая убита НАЗВАННЫМ тестом (память #536).
AC6 ДОКУМЕНТАЦИЯ: enforcement-coverage.md абзац о ложном блоке переписан как закрытый для читаемого Python; докстринги bash_write_gate.py и python_source_writes.py больше не обещают дефект; CHANGELOG.md и CHANGELOG.ru.md синхронно.
AC7 scoped verify зелёный, полная лента ОДИН раз в конце с прочитанной строкой passed/failed (память #529), mypy и ruff чисто, bootstrap --ide all перед done.

## Plan

## Rollback

git revert коммита задачи: детектор возвращается к регулярному выражению по тексту, поведение гейта — к состоянию #206; данных и миграций нет

## Journal

- 2026-09-03T15:25:53Z [implementation] — ЗАМЕР ДО (heredoc-пробник, до старта): 878 .py в tests/ scripts/ harness/ bootstrap/, 7.5 МБ. Регулярное выражение OPEN_RE называет цель в 6 файлах; AST по узлам Call open с константным путём и режимом w/a/x/+ — в 0 файлах. Значит все 6 находок ФАНТОМЫ (100% находок), реальных литеральных записей в репозитории нет ни одной. Файлы: test_bash_write_gate_hook.py, test_gate_shellless.py, test_memory_route_gate_resolves_against_shell_cwd.py, test_wrapper_flags_hide_the_wrapped_command.py, test_write_gate_resolves_against_shell_cwd.py и САМ python_source_writes.py (пример в докстринге). SyntaxError файлов 0. Стоимость: regex 70 мс на всё, AST 1670 мс на всё = 1.9 мс/файл, худший файл test_gates.py 60 КБ = 9.8 мс; при пределе 256 КБ оценка ~40 мс на команду.
- 2026-09-03T15:25:53Z [implementation] — ИНВЕНТАРЬ ПОТРЕБИТЕЛЕЙ по ВЫЗОВУ: (1) bash_write_parse._writers_in: _OPEN_RE.findall по тексту sub при _mentions_interpreter(sub) or is_python — субстрат ТЕКСТ КОМАНДЫ; (2) python_source_writes.writes_in_script_file -> writes_in_source — субстрат ФАЙЛ, вызывается из bash_write_parse (_script_file_writes) и из pwsh_write_parse._parse через _script_argv; (3) pwsh-канал встроенного плеча НЕ имеет. Heredoc-тела вырезаются до разбора (_strip_heredocs), значит python - <<EOF вообще не читается — остаток, не этой задачи. ДИЗАЙН: writes_in_source -> ast, fallback на прежнее regex при SyntaxError/ValueError/RecursionError; python_invocation.python_inline_code для -c (формы: отдельный токен, -cCODE, кластер -uc, после -X/-W значений; -m раньше -c -> нет кода); в _writers_in: is_python -> AST по -c и по файлу, БЕЗ текстового regex по аргументам-данным; иначе при упоминании интерпретатора — текстовое regex как прежде.
- 2026-09-03T15:33:13Z [implementation] — МУТАЦИИ 6/6 УБИТЫ, каждая названным тестом: (1) fallback на SyntaxError -> [] — 4 теста TestDegradationIsDeclaredNotSilent; (2) mode= игнорируется — 6 тестов [keyword mode]/[keyword file and mode] на трёх субстратах; (3) '+' не режим записи — 3 теста [update mode r+]; (4) встроенное плечо обратно на текст всей строки — 13 тестов inline_c [comment]/[docstring]/[commented-out code] и др.; (5) склеенный -cCODE снят — 2 теста; (6) атрибутная форма X.open снята — 6 тестов. Оговорка по памяти #536: мутации автора покрывают воображённое; матрица форм — граница того же воображения. Ревью на эту починку обязательно.
- 2026-09-03T15:33:13Z [implementation] — ПОСЛЕ починки, пробник через write_targets, 16 форм: python -c CODE (отдельный, склеенный -cCODE, кластер -uc, после -X utf8, после -W ignore, через timeout/env-префикс, внутри bash -c) — цель найдена во всех; аргументы-данные (python -m pytest -k "open(...)", python script.py "open(...)", python -c 'print(1)' "open(...)", комментарий внутри -c) — 0 целей, ДО было 4 фантома; mode='w' и raw-строка — теперь ловятся, ДО были пропуском; ruby -e и xargs python -c — по-прежнему текстовое чтение, цель найдена. Сверх: bash -c "python -c ..." даёт цель ДВАЖДЫ (текстовое плечо внешнего sub по упоминанию + спуск в payload) — было и до, гейт множеством нечувствителен, не чинил. НАХОДКА ВНЕ РАМОК (scope_exclude): канал PowerShell python -c "open('n.py','w')" -> [] — ПРОПУСК, встроенного плеча у pwsh_write_parse нет вовсе, Bash-контроль даёт ['n.py']. Не заведено — предъявить владельцу.
- 2026-09-03T15:36:54Z [implementation] — Root cause (logic-error): детектор литеральных записей читал ТЕКСТ исходника Python регулярным выражением, а не КОД — у текста нет различия между вызовом, строкой, докстрингом и комментарием, поэтому процитированный литерал становился целью, которой команда не пишет (6 из 6 находок по репозиторию — фантомы), а неявная склейка, raw-строка и mode= проходили мимо. Prevention: субстрат, у которого есть парсер, читать парсером (ast), таблицу форм держать в тесте, прогоняемом через РЕАЛЬНЫЙ вход парсера на обоих субстратах, и деградацию при нечитаемом входе объявлять как fallback к прежнему чтению, а не как тишину; каждая новая форма — мутацией, а не зелёным прогоном.
- 2026-09-03T15:37:24Z [done] — AC-1: ✓ замер до/после в журнале: 878 файлов, ДО 6 файлов с целью и все 6 фантомы, ПОСЛЕ 0 фантомов, 0 потерянных (AST-целей в дереве 0); закреплено тестом test_the_repository_itself_yields_no_phantom. AC-2: ✓ tested via tests/test_write_gate_reads_code_not_text.py — таблица FORMS 28 строк x 3 субстрата (детектор, файл через write_targets, python -c через write_targets). AC-3: ✓ tested via TestInlineCodeIsTheCodeAndOnlyTheCode — 8 написаний -c читаются, 5 форм аргументов-данных не дают цели, ruby -e/xargs остаются текстовым плечом; объявлено в докстринге _writers_in и enforcement-coverage.md. AC-4: ✓ tested via TestDegradationIsDeclaredNotSilent — SyntaxError/NUL/глубина -> текстовое чтение, >256K -> пусто; стоимость 1.9 мс/файл, 9.8 мс худший файл — в журнале. AC-5: ✓ мутации 6/6 убиты, перечень в журнале. AC-6: ✓ enforcement-coverage.md абзац переписан, докстринги bash_write_gate.py/python_source_writes.py, CHANGELOG.md + CHANGELOG.ru.md синхронно. AC-7: ✓ scoped verify #1987 PASS, полная лента 8565 passed / 25 skipped / 0 failed (строка прочитана), mypy 354 файла чисто, ruff чисто по файлам задачи, bootstrap --ide all выполнен. Domain: гейт больше не отказывает запуску реальных тестовых файлов репозитория с процитированными open(..., 'w') — шесть файлов, которые вчера давали фантомную цель, сегодня дают ноль, а python -c с реальной записью по-прежнему блокируется.
