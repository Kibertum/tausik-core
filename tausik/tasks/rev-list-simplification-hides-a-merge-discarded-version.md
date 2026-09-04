---
slug: rev-list-simplification-hides-a-merge-discarded-version
title: "rev-list --all без --full-history прячет версию манифеста, отброшенную слиянием, и пол счётчика снова ниже истории"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: next-version-reads-the-journal-tip-not-its-history
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_renar.py"
  - "tests/test_renar_manifest_chain.py"
  - "tests/test_git_exec.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-04T21:51:32Z"
---

## Goal

НАЙДЕНО ВНЕШНИМ L3 #38 (claude-opus-5) на закрытую next-version-reads-the-journal-tip-not-its-history, ВОСПРОИЗВЕДЕНО МОИМ ПРОГОНОМ. `git rev-list --all -- FILE` применяет history simplification по умолчанию: слияние, разрешённое в пользу одной стороны (`merge -s ours`), TREESAME своему родителю, и коммиты отброшенной стороны выпадают из перечня, оставаясь ДОСТИЖИМЫМИ. Синтетика: main v1, v2; ветка wave v3 от v1; merge -s ours; ветка удалена. rev-list --all даёт 2 коммита, rev-list --all --full-history — 4; journal_high_water = 2, next_version = 3 — переиздание v3 поверх другого содержимого, ровно §13.4.1. Докстринг journal_high_water и CHANGELOG утверждали «every commit reachable from ANY ref» — это было неверно.

ТУДА ЖЕ по тому же ревью: (MEDIUM) заявленная стоимость «55 мс при любом n» считала только два процесса git; замер сквозной — 125–151 мс на 10 коммитах, потому что каждый блоб разбирается PyYAML (~6.5 мс/КБ), то есть стоимость ЛИНЕЙНА по числу коммитов манифеста при плоском числе процессов. Заявление поправить, цифру записать. (LOW) живая охрана test_the_committed_history_never_reuses_a_version_number использует тот же rev-list без --full-history и форму n+1 (два процесса на коммит) — привести к --full-history и одному cat-file --batch через существующий парсер. (LOW) нет живого теста, что явный stdin вместе с input даёт громкий ValueError от subprocess.run. (LOW) AC-7 закрытой задачи называет класс TestProjectRootBelowTheWorktreeTop вместо TestHistoryBelowTheWorktreeTop — тик журнала верен, текст AC нет.

Root cause (design-gap): выбрана команда git по названию флага (--all), а её семантика упрощения истории не была прочитана; синтетика #213 проверила ветку без слияния и не проверила слияние с отбрасыванием стороны. Prevention: тест на merge -s ours в TestFloorIsTheWholeHistory; правило в память — у rev-list/log по пути ВСЕГДА спрашивать себя про simplification.

## Acceptance Criteria

AC-1: journal_high_water перечисляет историю с --full-history; на синтетике «main v1,v2; wave v3 от v1; merge -s ours; ветка удалена» high water = 3 и next_version = 4 (тест в TestFloorIsTheWholeHistory). Negative: без флага тот же репозиторий даёт 2 и 3 — мутация «флаг снят» убивается этим тестом.
AC-2: закреплённый argv на --write и на чтение истории обновлён (два теста), число процессов не изменилось — четыре на --write, два на историю.
AC-3: докстринг journal_high_water и next_version и обе записи CHANGELOG больше не утверждают «каждый достижимый коммит» без оговорки об упрощении истории и не утверждают «55 мс при любом n»: записана сквозная цифра (125–151 мс на 10 коммитах) и названа линейность по числу коммитов из-за разбора YAML при плоском числе процессов.
AC-4: живая охрана test_the_committed_history_never_reuses_a_version_number читает историю с --full-history и одним cat-file --batch через _batch_blobs (два процесса, не n+1) и по-прежнему зелёная на живом репозитории.
AC-5 (negative, живой subprocess): git_exec.run_git с явным stdin и input одновременно поднимает ValueError от subprocess.run — громкая несовместимость закреплена тестом.
AC-6: чеклист закрытия next-version… исправлен записью журнала (класс TestHistoryBelowTheWorktreeTop); память с правилом «у rev-list/log по пути спрашивай про simplification» записана; мутации объявлены и убиты по ветви.

## Plan

## Rollback

git revert коммита задачи; без схемы и данных.

## Journal

- 2026-09-04T21:50:39Z [implementation] — ВОСПРОИЗВЕДЕНО ПРОГОНОМ (до правки): синтетика main v1,v2 / wave v3 от v1 / merge -s ours / branch -D: rev-list --all перечислил 2 коммита, rev-list --all --full-history — 4; journal_high_water=2, next_version=3. HIGH-2 того же ревью воспроизведён отдельно и заведён внеисторийной changelog-gate-switch-is-outside-config-trust-guards. Сквозная стоимость journal_high_water на живом репозитории: 151/127/125 мс (три прогона), не 55. ПОЧИНКА: флаг --full-history в argv rev-list; докстринг journal_high_water объясняет, почему флаг load-bearing, и называет линейную стоимость разбора YAML (~6.5 мс/КБ) при плоском числе процессов; next_version: «ветка, удалённая ПОСЛЕ слияния, — внутри журнала». Тест test_a_version_discarded_by_a_merge_is_still_in_the_floor (merge -s ours → high water 3, next 4); закреплённые argv обновлены; живая охрана переписана на --full-history + один cat-file --batch через _batch_blobs (два процесса вместо 2n); живой тест: run_git с явным stdin и input → ValueError «stdin and input» от subprocess.run. CHANGELOG обоих файлов поправлен в самой записи (флаг, цифра 125–151 мс, линейность). Лента: 59 зелёных в трёх файлах, ruff/format/mypy чисто, файл 486 строк. МУТАЦИИ 2/2: R1 флаг снят → убит merge-тестом (ветвь rev-list); R2 охрана тихо выбирает stdin=None при обоих аргументах → убит живым тестом ValueError. Мутатор удалён. Память #588. Живой репозиторий после правки: high water по-прежнему 17.
- 2026-09-04T21:51:28Z [implementation] — AC-1: ✓ tests/test_renar_manifest_chain.py::TestFloorIsTheWholeHistory::test_a_version_discarded_by_a_merge_is_still_in_the_floor (merge -s ours, ветка удалена → high water 3, next_version 4). Negative: мутация R1 «--full-history снят» убита этим тестом (даёт 2 и 3). AC-2: ✓ tests/test_renar_manifest_chain.py::TestWriteChainEndToEnd::test_one_write_reads_the_journal_exactly_once (argv с --full-history, четыре процесса); tests/test_renar_manifest_chain.py::TestFloorIsTheWholeHistory::test_the_history_read_is_two_processes_whatever_its_length (два процесса) AC-3: ✓ докстринги journal_high_water и next_version переписаны (флаг load-bearing; 125–151 мс сквозных, линейность по коммитам из-за YAML); CHANGELOG.md и CHANGELOG.ru.md поправлены в записи задачи next-version с отсылкой к ревью #38 AC-4: ✓ tests/test_renar_manifest_chain.py::test_the_committed_history_never_reuses_a_version_number (rev-list --all --full-history + один cat-file --batch через _batch_blobs; зелёный на живом репозитории) AC-5: ✓ tests/test_git_exec.py::TestInputKeepsTheGuard::test_both_given_is_subprocesss_loud_error_not_a_quiet_pick (живой subprocess.run, ValueError «stdin and input»); мутация R2 убита им AC-6: ✓ журнал next-version… дополнен записью с верным классом TestHistoryBelowTheWorktreeTop; память #588; мутации 2/2 убиты по ветви Root cause (design-gap): команда git выбрана по названию флага без чтения семантики упрощения истории; синтетика проверила ветку без слияния. Prevention: тест на merge -s ours в TestFloorIsTheWholeHistory, память #588 «у rev-list/log по пути спрашивай про simplification». Domain: RENAR §13.4.1 (неповторяемость версий манифеста), git history simplification.
- 2026-09-04T21:51:41Z [done] — Root cause (edge-case): path-limited rev-list applies history simplification by default, so a version on the side a merge discarded was reachable yet unlisted and got re-issued; the synthetic repositories of #213 covered a branch without a merge and never a merge that dropped a side. Prevention: --full-history on every journal walk, a merge -s ours case in TestFloorIsTheWholeHistory, memory #588 (read the simplification semantics of any git walk chosen by flag name).
