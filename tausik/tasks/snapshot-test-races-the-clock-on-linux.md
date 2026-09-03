---
slug: snapshot-test-races-the-clock-on-linux
title: "Тест снимка дерева гонится с часами: на Linux в CI перезапись за тот же тик оставляет mtime прежним, и предусловие теста краснит зелёный гейт"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: bootstrap-drift-gate-off-source-edits-never-reach-the-cli
scope: null
scope_exclude: "scripts/running_source_drift.py не меняется — дефект в предусловии теста, а не в снимке; остальные тесты модуля не трогаются"
relevant_files:
  - "tests/test_running_source_drift.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_running_source_drift.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T20:38:40Z"
---

## Goal

ЗАВЕДЕНО ПО ПЕРВОМУ ПАЙПЛАЙНУ 1.9 НА GITLAB (#6658, job tests 34449, 2 failed / 8506 passed / 156 skipped, Linux, gitlab-runner). Падение: tests/test_running_source_drift.py::TestSnapshot::test_identical_rewrite_is_not_a_change — assert st_mtime_ns != before, оба значения 1788466239540459716. МЕХАНИЗМ (замер по trace, не догадка): тест создаёт a.py, снимает before, сдвигает mtime на +5 с через os.utime, затем write_text той же строкой и ТРЕБУЕТ, чтобы mtime после записи отличался от before. Запись ставит mtime = «сейчас» ядра, а «сейчас» на ext4/overlay в CI квантуется тиком (jiffies, 1–4 мс): создание и перезапись уложились в один тик, mtime после записи РАВЕН before, предусловие ложно. Гейт (Snapshot по sha1) здесь ни при чём — падает проверка предпосылки, а не утверждение о гейте. На Windows NTFS отдаёт 100-нс метки и гонка не проявлялась; ЛЕНТА WSL #205 ЭТОГО ТЕСТА ЕЩЁ НЕ СОДЕРЖАЛА (файл из #207). Долг качества работы #207 (задача bootstrap-drift-gate-off-source-edits-never-reach-the-cli), найденный CI, а не ревью.

## Acceptance Criteria

AC1 ПРЕДУСЛОВИЕ НЕ ЗАВИСИТ ОТ ЧАСОВ: после перезаписи теми же байтами тест САМ выставляет mtime через os.utime на значение, заведомо отличное от before, и утверждает отличие; затем snapshot.changed() == [] — утверждение о гейте (содержимое, не mtime) сохраняется дословно.
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ (мутации): Snapshot, ключуемый на mtime вместо sha1, — тест краснеет (мутация scripts/running_source_drift.py в памяти, файл восстановлен); предусловие, выставляющее mtime равным before, — тест краснеет на предусловии, то есть ошибка предпосылки по-прежнему видна; тест прогнан в цикле 30 раз подряд под xdist на Windows и 30 раз в WSL — 0 падений (числа в журнале).
AC3 CHANGELOG.md и CHANGELOG.ru.md синхронно (запись о первом пайплайне 1.9 и двух Linux-падениях); память — если урок не сводится к #529/#542 — ДО done.

## Plan

## Rollback

git revert коммита: тест возвращается к предусловию по часам; гейт не меняется

## Journal

- 2026-09-03T20:21:09Z [implementation] — СТАРТ. Инвентарь: одно несущее место — tests/test_running_source_drift.py::TestSnapshot::test_identical_rewrite_is_not_a_change; scripts/running_source_drift.py по вызову не участвует (падает предусловие, а не утверждение о снимке). Сложность simple подтверждена. Починка: запись теми же байтами, ЗАТЕМ os.utime на before+5с, предусловие детерминировано.
- 2026-09-03T20:25:36Z [implementation] — ПОЧИНКА: запись теми же байтами, затем os.utime(before+5с), предусловие «mtime != before» детерминировано; докстринг называет гонку и пайплайн #6658. Модуль 19 passed; ruff чист. ЦИКЛ 30 ПРОГОНОВ НА WINDOWS под xdist: 0 падений. МУТАЦИИ 2/2 УБИТЫ (базовый rc=0, убито только rc=1): (a) Snapshot ключуется на mtime вместо sha1 -> assert [a.py] == [] красный — утверждение о гейте живое; (b) предусловие выставляет mtime = before -> красный на предусловии с равными числами, то есть ошибка предпосылки видна, как в CI. Осталось: цикл 30 в WSL (в клоне нет pytest — восстановить venv по рецепту #205) и CHANGELOG.
- 2026-09-03T20:32:21Z [implementation] — ЗАМЕР НА LINUX: свежий клон в WSL (~/tausik-ci-linux3, python 3.12.3, шаги job tests из .gitlab-ci.yml: venv, pytest pytest-xdist PyYAML ruff mypy, requirements.txt, job-локальный git config, autocrlf false, bootstrap --no-detect --ide all, БД удалена), правленый тест скопирован: ЦИКЛ 30 ПРОГОНОВ — 0 падений; модуль 19 passed. На Windows цикл 30 — 0 падений. AC2 закрыт числами на обеих платформах.
- 2026-09-03T20:32:30Z [implementation] — AC-1: ✓ tests/test_running_source_drift.py::TestSnapshot::test_identical_rewrite_is_not_a_change (utime на before+5с ПОСЛЕ перезаписи; snap.changed() == [] дословно). AC-2: ✓ мутации 2/2 в журнале (снимок по mtime -> красный на утверждении о гейте; предусловие mtime=before -> красный на предусловии); цикл 30 под xdist на Windows — 0 падений; цикл 30 в свежем WSL-клоне по шагам job tests — 0 падений; модуль 19 passed на обеих. AC-3: ✓ CHANGELOG.md + CHANGELOG.ru.md синхронно; память #544 до done. Root cause (missing-validation): предпосылка о времени файла ожидалась от часов ФС, квант меток на Linux-раннере — тик ядра, создание и перезапись легли в один тик. Prevention: предпосылку о mtime выставлять явно os.utime после записи; первый прогон нового теста на Linux — часть закрытия (память #544). Domain: тест больше не зависит от разрешения меток времени ФС.
- 2026-09-03T20:38:37Z [implementation] — AC-1: ✓ tests/test_running_source_drift.py::TestSnapshot::test_identical_rewrite_is_not_a_change (utime на before+5с ПОСЛЕ перезаписи; snap.changed() == [] дословно). AC-2: ✓ мутации 2/2 в журнале (снимок по mtime -> красный на утверждении о гейте; предусловие mtime=before -> красный на предусловии); цикл 30 под xdist на Windows — 0 падений; цикл 30 в свежем WSL-клоне по шагам job tests — 0 падений; модуль 19 passed на обеих. AC-3: ✓ CHANGELOG.md + CHANGELOG.ru.md синхронно; память #544 до done. Root cause (missing-validation): предпосылка о времени файла ожидалась от часов ФС, квант меток на Linux-раннере — тик ядра, создание и перезапись легли в один тик. Prevention: предпосылку о mtime выставлять явно os.utime после записи; первый прогон нового теста на Linux — часть закрытия (память #544). Domain: тест больше не зависит от разрешения меток времени ФС.
