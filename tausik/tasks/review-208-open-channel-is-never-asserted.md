---
slug: review-208-open-channel-is-never-asserted
title: "Ревью #208: страж таблицы мутаций не утверждает, что канал open сработал — снятие спая open оставляет тест зелёным"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: review-207-open-spy-blind-and-doctor-at-cap
scope: null
scope_exclude: "Реализации гейтов, билдеры COVERED/EXCUSED и их литералы не меняются; новых каналов перехвата, кроме уже трёх, не добавляется; doctor и pyc_hygiene не трогаются"
relevant_files:
  - "tests/test_gates_catch_their_violation.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/architecture.md"
scope_paths:
  - "tests/test_gates_catch_their_violation.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/architecture.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-03T20:04:17Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАВЕДЕНО РЕВЬЮ L3 #208 (запись БД #16, opus, полный прогон) на починку 3c0d6c0; долг по качеству работы смены #207, найденный ревью на починку (память #536). ИНВЕНТАРЬ ДО ОЦЕНКИ: несущий файл один — tests/test_gates_catch_their_violation.py, функция test_the_table_leaves_the_repository_untouched; плюс CHANGELOG x2 и одна фраза в docs/en. (1) HIGH, ДОКАЗАНО МУТАЦИЕЙ РЕВЬЮЕРА: комментарий и коммит обещают «каждый канал обязан сработать», но собственные утверждения есть только у sqlite и subprocess; удаление двух строк monkeypatch на builtins.open/io.open оставляет тест ЗЕЛЁНЫМ, а 24 реальных события записи перестают наблюдаться — тот же класс дефекта, что закрывала review-207, на один канал уже. (2) MEDIUM: два утверждения о каналах узнают канал по ФОРМЕ пути (.db, proj, proj/.git) — молчаливая связка с литералами билдеров _state_project и _memory_route_project: переименование каталога краснит тест ложным «subprocess channel saw nothing», а билдер, открывший *.db через open, удовлетворит утверждение sqlite при мёртвом спае sqlite. (3) LOW x5: список written хранит и чтения (connect без режима, cwd любого процесса), сообщение говорит про write; дисклеймер называет os.open, а замер показывает: os.open 13 раз и всё DEVNULL, тогда как os.mkdir/makedirs 83 раза и не смотрится никем; spy_process берёт argv только позиционно — subprocess.run(args=[...]) даст TypeError под спаем; проверка вхождения — голый startswith без normcase и разделителя; CHANGELOG.md:93 не перенесена по ширине; EN-абзац потерял оборот «три канала, которыми пользуются билдеры». Замер каналов ревьюером по двенадцати билдерам: open 24, mkdir/makedirs 83, os.open 13 (DEVNULL), sqlite 4, subprocess 26; shutil/os.replace/tempfile — ноль.

## Acceptance Criteria

AC1 КАЖДАЯ ЗАПИСЬ НЕСЁТ ИМЯ КАНАЛА: спай пишет пары (канал, путь) с тегами open / sqlite3 / subprocess, и тест утверждает, что МНОЖЕСТВО сработавших каналов равно ровно этим трём — по тегу, не по форме пути; литералы .db, proj, proj/.git из утверждений исчезают.
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ (мутации, каждая убита названным тестом): удалены обе строки патча open/io.open — тест краснеет с текстом «open channel saw nothing»; удалён патч sqlite3.connect — краснеет по тегу sqlite3; удалены патчи subprocess — краснеет по тегу subprocess; билдер пишет через open вне tmp_path — краснеет с путём; переименование каталога proj в билдере — тест ОСТАЁТСЯ зелёным (связка по форме пути снята).
AC3 СЛОВА СОВПАДАЮТ С ДЕЛОМ: список переименован в touched, сообщение об ошибке при пустом списке говорит о касаниях, не о записях; дисклеймер докстринга называет os.mkdir/os.makedirs как несмотримый канал, который реально срабатывает (замер: 83 вызова), и говорит, почему это не важно (пустой каталог невидим для git, файл внутри поймает open); spy_process принимает argv и позиционно, и как args= — тест с формой subprocess.run(args=[...], cwd=...) зелёный; проверка вхождения через os.path.normcase и границу разделителя — путь-сосед tmp_path с общим префиксом считается снаружи (тест).
AC4 EN-абзац docs/en/architecture.md несёт оборот про три канала, которыми пользуются билдеры; CHANGELOG.md:93 перенесена по ширине абзаца; CHANGELOG.md и CHANGELOG.ru.md дополнены синхронно.
AC5 Ревью на починку (память #536) агентом L3 и запись review record; scoped verify зелёный; ruff/mypy чисто; полная лента один раз в конце.

## Plan

## Rollback

git revert коммита: спай возвращается к двум утверждениям по форме пути; поведение гейтов и билдеров не меняется

## Journal

- 2026-09-03T19:39:01Z [implementation] — СТАРТ. L3 #16 записано (opus, полный прогон, без 429): 0 critical, 1 high, 1 medium, 5 low. Инвентарь снят до оценки: несущий файл один (test_the_table_leaves_the_repository_untouched), потребителей у спая нет — он локален функции; CHANGELOG x2 и одна фраза docs/en. Сложность simple. План: теги каналов в записях спая, утверждение по множеству тегов, touched вместо written, argv позиционно и как args=, normcase+граница, дисклеймер про mkdir; затем мутации 5, scoped, ревью на починку L3.
- 2026-09-03T19:46:06Z [implementation] — ПОЧИНКА. Спай вынесен в _install_spies(monkeypatch) -> список пар (канал, путь); теги open/sqlite3/subprocess; утверждение fired == set(CHANNELS) и по каждому каналу с текстом «the <канал> channel saw nothing»; литералы .db/proj из утверждений сняты; written -> touched; spy_process берёт argv и позиционно, и как args=; _is_under с normcase и границей разделителя; дисклеймер называет os.mkdir/makedirs (83 вызова), а не os.open (13, все DEVNULL). Два новых теста: test_the_spies_note_every_channel_by_tag (форма args=, cwd и абсолютный argv записаны) и test_containment_has_a_boundary_and_folds_case (сосед rootx снаружи, родитель снаружи, регистр буквы диска на nt). Scoped 25 passed; ruff чист; mypy — 8 import-not-found, те же на HEAD (tests вне mypy-path). МУТАЦИИ 5/5 УБИТЫ: (1) сняты патчи open+io.open -> красный «the open channel saw nothing» (на HEAD оставался зелёным — high #16); (2) снят патч sqlite3.connect -> красный по тегу; (3) сняты патчи subprocess -> красный по тегу; (4) _write пишет leak-208.txt на три уровня выше root -> красный с путём; (5) каталог proj билдера переименован -> тест ОСТАЛСЯ зелёным, связка по форме пути снята. Файл после мутаций восстановлен побайтово (проверено git diff).
- 2026-09-03T19:47:55Z [implementation] — Root cause (missing-validation): утверждение «канал сработал» узнавало канал по форме пути (.db, proj/.git), а не по спаю, через который прошла запись, — поэтому снятие патча open не меняло исход, и обещание «каждый канал обязан сработать» держалось для двух каналов из трёх. Prevention: записи спая несут имя канала и утверждение идёт по множеству тегов; на каждый канал — мутация «патч снят» и обратная «литерал билдера переименован -> зелёный» (память выше); дисклеймер о несмотримых каналах — по замеру вызовов. Verify #2003 зелёный (scoped 11 файлов). Ревью на починку L3 запущено агентом (память #536).
- 2026-09-03T19:59:23Z [implementation] — РЕВЬЮ НА ПОЧИНКУ L3 #17 (opus): approved, 0/0/2/4, 16 мутаций ревьюера убиты. Починены все шесть находок: докстринг говорит ровно то, что закреплено (мёртвый спай ловится на каждом канале; уход билдера с канала — только для sqlite3/subprocess с одним пользователем каждый, для open — нет, замер ревьюера: _write через os.open/os.write остаётся зелёным); дисклеймер вернул общий оборот о прямых syscalls рядом с замером mkdir 83 / os.open 13 DEVNULL; fired == set(CHANNELS) оставлен как страж конструкции с комментарием; в тесте тегов — принадлежность вместо равенства списков; _is_under: rstrip разделителя для корня диска, плюс утверждение «у корня есть дети»; зеркала docs в профилях — bootstrap --ide all перед done. Scoped 25 passed, ruff чист, CRLF.
- 2026-09-03T20:03:47Z [implementation] — ДЕЛЬТА-СВЕРКА L3 #18 (opus): 5/6 закрыто, 13 мутаций перепрогнаны и убиты, зеркала docs в пяти профилях побайтово равны исходнику после bootstrap. Одна новая medium в моём тексте: «у subprocess один билдер-кормилец» — замер ревьюера по группировке записей спая: два (memory_route git init и gate_state_roundtrip.py:171 git status). Фраза исправлена: единственный канал с одним кормильцем — sqlite3; для open (шесть) и subprocess (два) уход билдера не ловится. Scoped 25 passed, ruff чист.
- 2026-09-03T20:04:14Z [implementation] — AC-1: ✓ tests/test_gates_catch_their_violation.py::test_the_table_leaves_the_repository_untouched (записи (канал, путь), утверждение по тегам, литералы .db/proj сняты). AC-2: ✓ мутации 5/5 в журнале + 16 и 13 у ревьюера (open снят -> красный по имени канала; sqlite3 снят; subprocess сняты; запись вне tmp_path -> красный с путём; proj переименован -> зелёный). AC-3: ✓ tests/test_gates_catch_their_violation.py::test_the_spies_note_every_channel_by_tag (форма args=, cwd и абсолютный argv) и tests/test_gates_catch_their_violation.py::test_containment_has_a_boundary_and_folds_case (сосед rootx, родитель, корень диска, регистр на nt); список touched, дисклеймер про mkdir 83 и прямые syscalls. AC-4: ✓ docs/en/architecture.md оборот про три канала; CHANGELOG.md:93 перенесена (все строки абзаца <= 78); CHANGELOG.md и CHANGELOG.ru.md синхронно. AC-5: ✓ review record L3 #17 approved 0/0/2/4 и дельта-сверка L3 #18 approved 0/0/1/0, последняя находка починена; verify_run зелёный (scoped 11 файлов); ruff чист; mypy — 8 import-not-found те же на HEAD; полная лента — один раз в конце смены. Domain: снятие любого из трёх спаев краснит ленту именем канала; переименование каталога билдера ленту не трогает.
