---
slug: hook-stderr-encoding-locale-dependent
title: "Хуки пишут не-ASCII в stderr в кодировке локали, и тесты читают их в кодировке родителя"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/_common.py"
  - "scripts/hooks/task_cost_budget_check.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/hooks/session_start.py"
  - "tests/test_hook_encoding.py"
  - "tests/test_cost_budget_task.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/hooks/*.py"
  - "tests/test_cost_budget_task.py"
  - "tests/test_hook_encoding.py"
  - ".claude/settings.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-07-19T20:27:58Z"
---

## Goal

Найдено в сессии #119 побочно: пять тестов в tests/test_cost_budget_task.py падают под `python -X utf8 -m pytest` и проходят под `python -m pytest`. Это НЕ регрессия задачи, в которой нашлось, — латентная хрупкость, которую флаг просто вскрыл.

МЕХАНИЗМ, проверен на сырых байтах. Хук cost-budget пишет в stderr строку «2× hard cap reached — stop and re-plan». Символы × (U+00D7) и — (U+2014) уходят в кодировке локали Windows: b'2\xd7 hard cap reached \x97'. Тест зовёт subprocess.run(..., text=True) БЕЗ encoding=, поэтому родитель декодирует дефолтом СВОЕЙ среды. Обычно совпадает, и всё зелено. Под -X utf8 родитель декодирует как UTF-8, дочерний процесс (запущенный без -X utf8) пишет cp1251 — UnicodeDecodeError в потоке-читателе, stdout/stderr становятся None, и падение выглядит как «TypeError: argument of type NoneType is not iterable», то есть никак не намекает на кодировку.

ПОЧЕМУ ЭТО ДЕФЕКТ ПРОДА, А НЕ ТОЛЬКО ТЕСТА. Тест — лишь свидетель. Хук пишет диагностику в кодировке локали машины: на хосте с другой локалью сообщение о превышении бюджета придёт агенту мохнатым мусором. Сообщение хука — часть контракта надзора, оно обязано быть читаемым везде одинаково. Чинить надо ОБА конца: хук форсирует UTF-8 на своём stderr, тест передаёт encoding="utf-8" явно.

ПРОВЕРИТЬ ШИРЕ ОДНОГО ХУКА: та же формула subprocess.run(text=True) без encoding и та же запись не-ASCII в stderr почти наверняка есть и в других хуках и тестах. Разовая правка одного файла тут неуместна — нужен обход всех scripts/hooks/*.py и всех вызовов subprocess в tests/.

## Acceptance Criteria

AC1. Регрессия воспроизведена ДО фикса: пять тестов tests/test_cost_budget_task.py падают под `python -X utf8 -m pytest` и проходят без флага. После фикса ОБА режима зелёные. Зафиксирован сырой байтовый след (b"2\xd7 ... \x97"), а не только факт падения.
AC2. Корректность вывода хука не зависит от того, КАК его позвали. Хук форсирует UTF-8 на своих stdout/stderr в КОДЕ, а не полагается на флаг -X utf8 в строке вызова. Проверено тестом на СЫРЫХ БАЙТАХ (encoding не передаётся, читается bytes), запуская хук БЕЗ -X utf8 — иначе тест доказал бы сам себя.
AC3. Тестовый конец починен: вызовы subprocess, читающие вывод хуков, передают encoding явно. Молчаливое наследование кодировки родителя недопустимо.
AC4. Обход ШИРЕ одного хука: проверены ВСЕ scripts/hooks/*.py (26 шт.) и все вызовы subprocess в tests/. Охват зафиксирован списком, а не утверждением «проверил». Найденное исправлено.
AC5. Механический гейт (конвенция #236): новый хук, пишущий не-ASCII без форсирования UTF-8, ловится автоматически. Гейт перечисляет нарушителей поимённо, а не падает с булевым «что-то не так». Разовая правка 26 файлов без гейта не принимается — регрессия вернётся с 27-м хуком.
AC6. Вторая линия обороны сохранена и тоже механизирована: каждый вызов хука в settings.json обязан нести -X utf8. Новый хук, добавленный в конфиг без флага, ловится тем же прогоном. Belt and braces: код и конфиг проверяются независимо.
AC7. НЕГАТИВНЫЙ: гейт не срабатывает ложно. Хук из чистого ASCII и subprocess в бинарном режиме (без text=True) не считаются нарушением. Покрыто тестом, иначе гейт начнут отключать.
AC8. Форсирование UTF-8 не может уронить хук: символ, не представимый в целевой кодировке, не приводит к исключению внутри надзорного механизма (errors-политика выбрана осознанно и обоснована).
AC9. Полный pytest зелёный в ОБОИХ режимах (с -X utf8 и без), ruff чист, CHANGELOG EN+RU обновлены.

## Plan

## Rollback

git revert <commit>. Правка аддитивная и не трогает ни схему БД, ни формат данных: добавляется вызов force_utf8_io() в точки входа хуков, явный encoding в вызовы subprocess тестов и новый тест-гейт. Откат одним revert возвращает прежнее поведение (кодировка локали) без миграций и без потери данных. Промежуточный вариант отката: снять только тест-гейт (tests/test_hook_encoding.py), оставив исправления — гейт независим от фикса и удаляется отдельно.

## Journal

- 2026-07-19T20:27:25Z [implementation] — AC-1: ✓ регрессия воспроизведена сырыми байтами до фикса — b'2\xd7 hard cap \x97 stop\r\n', не декодируется как UTF-8; после фикса оба режима зелёные (5234 passed под -X utf8 и без) — tests/test_hook_encoding.py::TestHookOutputIsUtf8OnRawBytes::test_unguarded_output_is_not_utf8_this_is_the_defect AC-2: ✓ корректность вывода не зависит от способа запуска: хук зовёт force_utf8_io() в коде, тест запускает БЕЗ -X utf8 и читает сырые байты — tests/test_hook_encoding.py::TestHookOutputIsUtf8OnRawBytes::test_guarded_output_is_utf8_regardless_of_invocation AC-3: ✓ 59 вызовов subprocess в 36 тест-файлах получили явный encoding — tests/test_hook_encoding.py::TestNoSilentEncodingInheritance::test_no_test_reads_a_subprocess_in_the_parents_encoding AC-4: ✓ обход шире одного хука: просканированы все 26 scripts/hooks/*.py и весь каталог tests/; охват зафиксирован не утверждением, а самим сканированием, плюс антипустышки — tests/test_hook_encoding.py::TestEveryHookForcesUtf8::test_the_scan_actually_sees_the_hooks AC-5: ✓ механический гейт перечисляет нарушителей поимённо (нашёл 11 хуков и 59 вызовов до фикса) — tests/test_hook_encoding.py::TestEveryHookForcesUtf8::test_hooks_emitting_non_ascii_call_the_guard AC-6: ✓ вторая линия обороны механизирована и в артефакте, и в источнике: оба профиля хоста (.claude, .qwen) плюс функции bootstrap/, строящие команду — tests/test_hook_encoding.py::TestSettingsKeepTheFlag::test_the_generator_itself_emits_the_flag AC-7: ✓ ложных срабатываний нет — tests/test_hook_encoding.py::TestGateDoesNotFireFalsely (5 тестов) AC-8: ✓ защита не роняет хук: errors='replace', идемпотентна, no-op на потоках без reconfigure — tests/test_hook_encoding.py::TestGuardNeverRaises::test_unencodable_character_degrades_instead_of_raising AC-9: ✓ 5234 passed / 0 failed В ОБОИХ режимах, ruff чист по scripts/ tests/ bootstrap/, CHANGELOG EN+RU Negative: не-ASCII только в докстринге не считается нарушением (в поток не попадает никогда) — tests/test_hook_encoding.py::TestGateDoesNotFireFalsely::test_non_ascii_only_in_a_docstring_is_not_flagged Negative: не-ASCII только в комментарии не считается нарушением (AST их отбрасывает) — tests/test_hook_encoding.py::TestGateDoesNotFireFalsely::test_non_ascii_only_in_a_comment_is_not_flagged Negative: subprocess в бинарном режиме не нарушение — декодирования нет, наследовать нечего — tests/test_hook_encoding.py::TestNoSilentEncodingInheritance::test_binary_mode_is_not_an_offender Negative: модуль, который ничего не печатает, не нарушение даже с русскими строками — tests/test_hook_encoding.py::TestGateDoesNotFireFalsely::test_a_module_that_never_writes_is_not_flagged Domain: смысл вне тестов — сообщение хука это КАНАЛ НАДЗОРА, а не логи. Через него агент узнаёт о превышении бюджета, о блокировке политикой, о запрете записи вне области. Нечитаемое сообщение надзора эквивалентно отсутствующему: агент не обязан догадываться, что «2\xd7 hard cap» значит «стоп». Хуже того, отказ проявляется как TypeError про NoneType, то есть выглядит как баг вызывающего, а не как проблема кодировки — и уводит диагностику в сторону. Проверено на сырых байтах реального запуска, а не выведено из рассуждения. Checklist: scope — правка в 11 хуках строго аддитивная (сверено: число def совпадает с HEAD по каждому файлу), в 36 тестах строго внутристрочная (сверено: число тестов И число строк совпадает с HEAD, память #225 про съеденный регуляркой код); тесты — 19 новых в гейте, из них 5 негативных и 3 антитавтологических; security — не затронуто, канал надзора стал читаемее, а не слабее; rollback — git revert, схема и данные не тронуты, гейт снимается отдельно от фикса. ПОПРАВКА К КАРТОЧКЕ (найдено при исполнении): карточка утверждала «дефект прода» без оговорки. Фактически прод был закрыт: все вызовы в обоих сгенерированных конфигах несут -X utf8. Настоящий дефект тоньше и хуже — корректность хука зависела от ЗАПУСКАЮЩЕГО, то есть от одной строки на профиль хоста в bootstrap/. Это и починено. Оценка complexity поднята simple -> medium: 26 хуков, 48 тест-файлов, два профиля хоста и два генератора — не разовая правка.
- 2026-07-19T20:27:57Z [implementation] — AC verified 9/9 — детальные строки с маркерами AC-N, Negative, Domain и Checklist записаны в журнал задачи. Прогон verification_run #1072 (pytest PASS, 12750 ms). Сводка: 11 хуков получили force_utf8_io() (AST-направленная вставка, число def сверено с HEAD по каждому файлу); 59 вызовов subprocess в 36 тест-файлах получили явный encoding (число тестов И число строк сверено с HEAD — правка строго внутристрочная); новый механический гейт tests/test_hook_encoding.py, 19 тестов, из них 5 негативных и 3 антитавтологических. Полный набор 5234 passed / 0 failed В ОБОИХ режимах (python -m pytest и python -X utf8 -m pytest) — до работы под вторым падало 5. ruff чист по scripts/ tests/ bootstrap/. CHANGELOG EN+RU обновлены. Зеркало .claude синхронизировано bootstrap и проверено. Поправка к карточке: она называла это «дефектом прода» без оговорки. Прод фактически был закрыт — оба сгенерированных конфига хоста несут -X utf8 на всех вызовах. Настоящий дефект тоньше: корректность хука зависела от запускающего, то есть от одной строки на профиль в bootstrap/. Гейт поэтому проверяет и артефакт, и источник.
