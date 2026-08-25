---
slug: token-metrics-append-name-lies
title: "append_token_rows заменяет, а не дописывает — имя лжёт, тест красный в main"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: l26-token-metrics-rotation
scope: "scripts/hooks/session_metrics.py, tests/test_token_metrics.py, вызывающие функцию модули"
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/token_rows.py"
  - "scripts/hooks/token_metrics.py"
  - "tests/test_token_metrics.py"
  - "tests/test_token_metrics_rotation.py"
scope_paths:
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/token_rows.py"
  - "scripts/hooks/token_metrics.py"
  - "tests/test_token_metrics.py"
  - "tests/test_token_metrics_rotation.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-18T15:14:21Z"
---

## Goal

Коммит 32df941 (l26-token-metrics-rotation) сменил семантику: функция теперь ЗАМЕНЯЕТ строки текущей сессии, а не дописывает — по построению идемпотентно, потому что extract_token_rows всегда отдаёт полный набор сессии. Но функция осталась называться append_token_rows, а tests/test_token_metrics.py::TestAppendTokenRows::test_appends_rows_idempotent_across_calls кодирует СТАРЫЙ контракт: зовёт функцию дважды непересекающимися частичными наборами и ждёт 2 строки, получает 1. Проверено git stash в сессии #112 — тест падает на чистом main, то есть коммит уехал с красным тестом (defect escape). Задача: (1) переименовать функцию и класс тестов так, чтобы имя отражало replace-семантику — вводящее в заблуждение имя это ровно тот путь, которым баг вернут обратно; (2) переписать тест на реальный контракт: повторный вызов с ТЕМ ЖЕ полным набором сессии не должен множить строки, а вызов с расширенным набором должен заменить строки сессии на новый набор; (3) не подгонять ожидание под текущее поведение вслепую — сначала зафиксировать намерение в докстринге. Важность: красный тест в main маскирует последующие регрессы и обесценивает обе линии как гейт.

## Acceptance Criteria

1. Функция переименована из `append_token_rows` в имя, отражающее replace-семантику (`replace_session_token_rows`); все вызывающие и тесты обновлены; старого имени в дереве не остаётся.
2. Тест кодирует реальный контракт: повторный вызов с ТЕМ ЖЕ полным набором строк сессии не должен множить строки (идемпотентность), а вызов с расширенным набором заменяет строки этой сессии на новый набор целиком.
3. Строки ДРУГИХ сессий не должны затираться при замене — покрыто отдельным тестом.
4. Негативные сценарии сохранены и зелёные: пустой список строк → no-op (None), отсутствующий каталог `.tausik` → None без создания файла, ошибка записи не должна оставлять .tmp-файл.
5. `python -m pytest tests/test_token_metrics.py -q` зелёный; полная быстрая линия `pytest tests/` зелёная (0 failed).
6. `ruff check scripts/ tests/` чист; бейджи и `docs/_generated/constants.json` пересчитаны при изменении числа тестов.

## Plan

## Rollback

git revert коммита; переименование чисто механическое, поведение не меняется.

## Journal

- 2026-07-18T15:12:11Z [implementation] — AC-1: ✓ Функция переименована append_token_rows -> replace_session_token_rows в scripts/hooks/session_metrics.py; обновлены докстринг-ссылка в scripts/hooks/token_metrics.py и оба тест-файла. Grep по всему дереву (scripts/ tests/ docs/) возвращает 0 вхождений старого имени. Все пять IDE-зеркал пересобраны bootstrap --ide all и содержат новое имя. AC-2: ✓ Тест переписан на реальный контракт: tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_rerun_with_the_same_set_does_not_duplicate (повтор с тем же полным набором -> 2 строки, не 4) и tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_grown_set_replaces_the_session_wholesale (расширенный набор заменяет строки сессии целиком). AC-3: ✓ tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_other_sessions_are_not_erased — после записи сессий 1 и 2 в файле присутствуют обе. AC-4: ✓ Negative: пустой список строк -> None (tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_no_rows_returns_none); отсутствующий каталог .tausik -> None и файл не создан (tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_no_tausik_dir_returns_none); ротация и отсутствие .tmp-хвоста покрыты существующим tests/test_token_metrics_rotation.py (не тронут, проходит). AC-5: ✓ tests/test_token_metrics.py + tests/test_token_metrics_rotation.py = 36 passed. Полная быстрая линия на тихом дереве: 4705 passed, 21 skipped, 0 failed. Медленная линия: 138 passed, 0 failed. AC-6: ✓ ruff check scripts/ tests/ — All checks passed. docs/_generated/constants.json перегенерирован (test_count 4792 -> 4843), бейджи в README.md и README.ru.md обновлены тем же прогоном gen_doc_constants.py --write. Root cause: коммит 32df941 сменил семантику функции с append на replace-by-session и добавил новый файл тестов, но не тронул старый тест, кодировавший прежний контракт — красный тест уехал в main (проверено git stash на чистом дереве). Усугублялось тем, что имя функции осталось append_*, расходясь с поведением. Знание зафиксировано: память #219.
- 2026-07-18T15:14:20Z [implementation] — AC-1: ✓ Функция переименована append_token_rows -> replace_session_token_rows в scripts/hooks/session_metrics.py (ныне scripts/hooks/token_rows.py); обновлены докстринг в scripts/hooks/token_metrics.py и оба тест-файла. Grep по scripts/ tests/ docs/ возвращает 0 вхождений старого имени. Все пять IDE-зеркал пересобраны bootstrap --ide all. AC-2: ✓ tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_rerun_with_the_same_set_does_not_duplicate (повтор тем же полным набором -> 2 строки, не 4); tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_grown_set_replaces_the_session_wholesale (расширенный набор заменяет строки сессии целиком). AC-3: ✓ tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_other_sessions_are_not_erased — после записи сессий 1 и 2 в файле присутствуют обе. AC-4: ✓ Negative: пустой список строк -> None, tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_no_rows_returns_none; отсутствующий каталог .tausik -> None и файл не создан, tests/test_token_metrics.py::TestReplaceSessionTokenRows::test_no_tausik_dir_returns_none; ротация по размеру и сохранение чужих сессий покрыты нетронутым tests/test_token_metrics_rotation.py (10 тестов, проходят). AC-5: ✓ tests/test_token_metrics.py + tests/test_token_metrics_rotation.py = 36 passed. Полная быстрая линия на тихом дереве: 4705 passed, 21 skipped, 0 failed. Медленная линия: 138 passed, 0 failed. AC-6: ✓ ruff check scripts/ tests/ — All checks passed. docs/_generated/constants.json перегенерирован, бейджи README.md и README.ru.md обновлены тем же прогоном gen_doc_constants.py --write. Сверх AC: filesize-гейт заблокировал закрытие — scripts/hooks/session_metrics.py 467 строк. Долг доставшийся (467 и в HEAD до правок), но обходить его через gates.filesize.exempt_files я не стал: это ровно тот класс обхода, который закрывается соседней задачей l26-config-trust-tiers. Модуль разделён по естественному шву: извлечение per-tool строк и писатель token_metrics.jsonl вынесены в scripts/hooks/token_rows.py (171 строка), session_metrics.py остался с разбором транскрипта и session-level rollup (327 строк). Имена ре-экспортированы, вызывающие и тесты не тронуты. Root cause: коммит 32df941 сменил семантику функции с append на replace-by-session и добавил новый файл тестов, но не тронул старый тест, кодировавший прежний контракт — красный тест уехал в main (подтверждено git stash на чистом дереве). Усугублялось расхождением имени функции с поведением. Знание зафиксировано: память #219.
- 2026-07-18T15:14:40Z [done] — Root cause (regression): коммит 32df941 сменил семантику append_token_rows с «дописать строки» на «заменить строки сессии» и добавил НОВЫЙ файл тестов test_token_metrics_rotation.py, но не тронул СТАРЫЙ тест test_token_metrics.py::TestAppendTokenRows::test_appends_rows_idempotent_across_calls, кодировавший прежний контракт — красный тест уехал в main и остался незамеченным. Prevention: при смене семантики функции обязателен grep её имени по ВСЕМУ дереву тестов, а не только написание нового тест-файла; новый файл не отменяет старый. Плюс переименовывать функцию вместе со сменой семантики — имя append_* при поведении replace_* и есть тот путь, которым баг возвращают. Отличать свой регресс от доставшегося дешевле всего через git stash -u + прогон подозрительного файла (30 секунд), а не рассуждением. Domain: результат осмыслен вне тестов. Проверено на реальных данных прошлой сессии — файл .tausik/token_metrics.jsonl содержал 1 034 407 строк при 45 934 уникальных (95.6% дублей, 190.5 МБ), потому что каждый повторный прогон SessionEnd-хука дописывал полный набор сессии заново. После смены семантики на replace-by-session файл 8.5 МБ, и повторный прогон хука его не растит. Строки других сессий при замене сохраняются, то есть историческая атрибуция токенов по сессиям не теряется — а это и есть назначение файла. Калибровка: call_actual=110 против бюджета 25. Бюджет ставился под «переименовать и поправить тест». Не учтено: (1) синхронизация пяти IDE-зеркал, (2) регенерация constants.json и бейджей, (3) filesize-гейт заблокировал закрытие из-за доставшегося долга 467 строк и потребовал разделения модуля. Для задач, трогающих scripts/hooks/, реалистичный минимум — 60: зеркала и doc-constants входят в цену почти всегда.
