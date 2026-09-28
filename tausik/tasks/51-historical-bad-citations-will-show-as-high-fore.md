---
slug: "51-historical-bad-citations-will-show-as-high-fore"
title: "51 historical bad citations will show as HIGH forever and teach readers to ignore HIGH"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/repo_coherence.py"
  - "scripts/repo_coherence_shape.py"
  - "scripts/repo_coherence_collectors.py"
  - "tausik/gates.json"
  - "tests/test_closure_evidence_remainder.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "scripts/repo_coherence.py"
  - "scripts/repo_coherence_collectors.py"
  - "scripts/repo_coherence_shape.py"
  - "tausik/gates.json"
  - "tests/test_repo_coherence.py"
  - "tests/test_closure_evidence_remainder.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T21:46:16Z"
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

ПОСЛЕДНЕЕ, ЧТО ОСТАЛОСЬ В ЛИНЗЕ ПОСЛЕ ЧИСТКИ. tausik coherence сообщает два HIGH: 31 цитата закрытия называет тест, исчезнувший ПОСЛЕ закрытия, и 20 называют тест, которого git НИКОГДА не имел. Обе — история: журналы закрытых задач append-only, переписать их нельзя, а переписать значило бы подделать доказательство.

ЧЕМ ЭТО ПЛОХО ИМЕННО СЕЙЧАС. Механизм ловли НОВЫХ выдуманных цитат заведён в этой же смене и работает при закрытии. Значит множество исторических находок ЗАМКНУТО и расти не должно. Но линза будет показывать их как HIGH на каждом прогоне вечно, и первое, чему это научит читателя, — пролистывать HIGH. Находка, которую нельзя устранить и которая повторяется каждый раз, обесценивает свою же категорию.

ЧТО ДЕЛАЕТСЯ: то же, что уже сделано для дубликатов тестов и поверхности классов, — ХРАПОВИК. Историческое число закрепляется, показывается как объявленный остаток, а HIGH остаётся только за РОСТОМ.

ЧЕГО НЕ ДЕЛАЕТСЯ: не править журналы, не прятать находки, не понижать severity для новых. Остаток обязан быть НАЗВАН и виден, а не заглушен.

## Acceptance Criteria

AC-1. Историческое число ЗАМЕРЕНО и закреплено в tausik/gates.json как объявленный остаток: сколько цитат сгнило и сколько выдумано на дату закрепления.
AC-2. Линза перестаёт сообщать закреплённый остаток как HIGH и сообщает его как объявленный остаток с числом. РОСТ по-прежнему HIGH.
AC-3. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест подсовывает число ВЫШЕ закреплённого и требует HIGH. Храповик, который не может покраснеть, — украшение.
AC-4. Храповику разрешено только УМЕНЬШАТЬСЯ, и это проверяется: закреплённое число выше измеренного есть ложь в обратную сторону, и оно тоже краснеет.
AC-5. Остаток НАЗВАН, а не спрятан: вывод линзы говорит, сколько исторических находок закреплено и что механизм ловли новых работает при закрытии.

## Plan

## Rollback

## Journal

- 2026-09-08T21:46:13Z [implementation] — AC verified: AC-1: ✓ tests/test_closure_evidence_remainder.py::TestЖивойОстатокЗакреплёнЧислом::test_база_объявлена_и_названа_числом — в tausik/gates.json закреплено rotted=31, never_existed=20 на 2026-09-08. AC-2: ✓ tests/test_closure_evidence_remainder.py::TestОстатокНеПрячется::test_совпадение_с_остатком_сообщается_как_остаток — совпадение с остатком даёт low и слова «declared remainder». Проверено ПРОГОНОМ линзы: HIGH-находок на дереве больше нет ни одной. AC-3: ✓ tests/test_closure_evidence_remainder.py::TestРостОстаётсяHIGH::test_превышение_остатка_даёт_high — 35 против базы 31 даёт high и count=4, то есть показан РОСТ, а не полное число. Второй тест: проект БЕЗ базы читается строго, каждая находка есть рост. AC-4: ✓ tests/test_closure_evidence_remainder.py::TestОстаткуРазрешеноТолькоУменьшАться::test_остаток_выше_измеренного_просит_подтянуть — база выше правды тоже сообщается: это ложь в обратную сторону. AC-5: ✓ вывод линзы называет число и говорит, что новые ловятся при закрытии с этого релиза. Причина закрепления записана рядом с числом в gates.json (append-only, may only shrink), проверяется tests/test_closure_evidence_remainder.py::TestЖивойОстатокЗакреплёнЧислом::test_причина_записана_рядом_с_числом — число без объяснения через полгода читается как «кто-то смирился». РАЗРЕЗ МОДУЛЯ ПОТРЕБОВАЛСЯ ПО ХОДУ И СДЕЛАН ПО НАЗВАННОМУ ШВУ. repo_coherence перешёл предел в 500 строк (567). Разрезан натрое: repo_coherence_shape (форма находки, безопасный запуск, потолок объёма, порядок строгости, граница непроверяемого — 91 строка), repo_coherence_collectors (десять коллекторов — 391), repo_coherence (сборка и отрисовка — 148). Отдельная задача на разрез, заведённая смену назад, удалена как выполненная здесь. ПЕРВЫЙ ВАРИАНТ РАЗРЕЗА СЛОМАЛ ПУБЛИЧНУЮ ПОВЕРХНОСТЬ, И ЭТО ПОЙМАЛИ СУЩЕСТВУЮЩИЕ ТЕСТЫ. Пять тестов упали с AttributeError: они подменяют коллекторы через repo_coherence._orphans и подобные. Поверхность восстановлена ре-экспортом; тест на её сохранность добавлен. Разрез, меняющий публичные имена, — не уборка, а правка поведения под видом уборки. Domain: проверено вне тестов прогоном линзы до и после. До: два HIGH (31 и 20). После: ноль HIGH, оба числа сообщены как объявленный остаток, десять коллекторов запущено, ноль пропущено.
