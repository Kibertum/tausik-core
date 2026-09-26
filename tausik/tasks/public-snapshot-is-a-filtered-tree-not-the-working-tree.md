---
slug: public-snapshot-is-a-filtered-tree-not-the-working-tree
title: "Публичный снимок 1.9 — отфильтрованное дерево без бухгалтерии tausik/ и внутренних файлов, собранное кодом и проверенное собственным прогоном"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/publication_tree.py (новый), scripts/project_cli_*.py и project_parser*.py (команда publish), tests/test_publication_lines.py, tests/test_publication_tree.py (новый), tests/ (тесты, читающие живую проекцию), docs/ru/publishing.md, docs/en/publishing.md, docs/ru/cli.md, docs/en/cli.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: ".gitignore не меняется (tausik/ остаётся отслеживаемым на GitLab); git push, tag, release — запрещены; .agents/ не трогать."
relevant_files:
  - "scripts/publication_snapshot.py"
  - "scripts/project_cli_publish.py"
  - "scripts/project_parser_publish.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "tests/test_publication_snapshot.py"
  - "tests/test_publish_cli.py"
  - "tests/test_publication_lines.py"
  - "tests/conftest.py"
  - "tests/test_ci_runs_where_development_happens.py"
  - "tests/test_ci_lanes_are_honest.py"
  - "tests/test_plan_19_names_the_composition_in_force.py"
  - "tests/test_renar_measurer_caveats.py"
  - "tests/test_senar_version_claim.py"
  - "tests/test_renar_manifest_chain.py"
  - "docs/ru/publishing.md"
  - "docs/en/publishing.md"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T14:17:30Z"
resolution: null
resolution_reason: null
---

## Goal

Решение #368, п.2-3. ЗАМЕР, смена #251: в дереве 4379 отслеживаемых файлов, из них 3075 — проекция бухгалтерии tausik/{tasks,stories,epics,decisions,memory,graph-snapshots}; github/main несёт 2438 файлов tausik/ из 3576. Публикация сегодня (docs/ru/publishing.md) выносит ВСЁ дерево и говорит это прямо; классы утечки (39 файлов с путём среды разработки, 5 с внутренним хостом) живут в основном в этой бухгалтерии. Задача: (1) scripts/publication_tree.py — сборка публичного снимка из тега/коммита линии разработки: git read-tree с исключением объявленного перечня (проекция tausik/, TODO.md, TAUSIK-plan-1.9.md, .gitlab-ci.yml; храповики tausik/*.json остаются), commit-tree поверх заданного родителя (публичной головы), без force; перечень исключений — ОДНА объявленная константа, а не память; команда `tausik publish snapshot --from <ref> --parent <sha> [--dry-run]` печатает, что вошло и что исключено, с числами; (2) проверка равенства: `tausik publish verify --snapshot <sha> --from <ref>` сверяет отфильтрованное дерево с деревом снимка байт в байт (git diff-tree) — это и есть «GitLab идентичен GitHub»; (3) снимок обязан проходить свой полный прогон: сборка снимка во временный каталог + bootstrap --no-detect --ide all + pytest -m '' — и здесь всплывут тесты, читающие живую бухгалтерию tausik/tasks (closure-evidence remainder и т.п.); каждый такой тест делается честным на дереве без проекции (skip с причиной или чтение того, что есть); (4) tests/test_publication_lines.py расширяется: перечень исключений неизменен без правки теста, снимок не содержит ни одного файла проекции, классы утечки на СНИМКЕ равны нулю (не «объявленный остаток», а ноль — бухгалтерия ушла); (5) docs/{ru,en}/publishing.md переписаны под #368: две линии, что публикуется, команды выкладки, тег как часть выкладки.

## Acceptance Criteria

AC-1: `tausik publish snapshot --from HEAD --parent <sha> --dry-run` печатает перечень исключений и числа (вошло N файлов / исключено M), и M ≥ 3075 на сегодняшнем дереве. AC-2: собранный снимок не содержит ни одного пути из tausik/{tasks,stories,epics,decisions,memory,graph-snapshots}, TODO.md, TAUSIK-plan-1.9.md, .gitlab-ci.yml, и содержит tausik/gates.json, policy.json, published_tags.json, spec_coverage.json — тест на временном репозитории. AC-3: `tausik publish verify` даёт ноль расхождений между отфильтрованным деревом источника и снимком; НЕГАТИВ: снимок с одним изменённым байтом или с одним лишним файлом — отказ с именем файла. AC-4: НЕГАТИВ: сборка поверх родителя, который не является публичной головой (не fast-forward), — отказ; force не предусмотрен флагом вовсе. AC-5: полный прогон на собранном снимке во временном каталоге (bootstrap --no-detect --ide all; pytest -m '') зелёный на этой машине; число passed/skipped записано в журнал; тесты, зависевшие от живой проекции tausik/, названы и починены. AC-6: классы утечки на снимке (tests/test_publication_lines.py) — ноль вхождений пути среды разработки и внутреннего хоста; мутация — вернуть один файл проекции в перечень включений — краснит. AC-7: docs/{ru,en}/publishing.md описывают модель #368 и команды; CHANGELOG EN/RU. AC-8: signed verify. Push/тег/релиз НЕ выполняются — только сборка и проверка локально.

## Plan

## Rollback

git revert; публикация вернётся к ручной процедуре commit-tree над полным деревом.

## Journal

- 2026-09-13T14:13:39Z [implementation] — Сделано: scripts/publication_snapshot.py (EXCLUDED_FROM_PUBLIC_SNAPSHOT — одна константа; snapshot_tree через временный индекс read-tree/rm --cached -r по правилам/write-tree — рабочее дерево, индекс и ref не тронуты; build_snapshot_commit поверх публичной головы; snapshot_matches — равенство деревьев с именованием путей A/D/M; leaks_in_snapshot — один git grep на класс, 23 с → 0.27 с). CLI tausik publish snapshot|verify (project_cli_publish + project_parser_publish; ops-парсеры собраны в add_ops, чтобы project_parser остался < 500). ЗАМЕР на дереве 1.9: 1308 файлов уходит, 3090 остаётся, tausik/*.json едут. Классы утечки: 43 примера путей D:\Work в тестах/докстрингах и один хост в фикстуре нейтрализованы (C:\Projects, gitlab.example.internal); пины на всём дереве опущены 5→4 и 39→22; на снимке — 0/0 (CHANGELOG*.md в allowlist как описание класса). Тесты, чей предмет исключён (#368), объявлены dormant на снимке через conftest.IS_PUBLIC_SNAPSHOT / DORMANT_ON_PUBLIC_SNAPSHOT (ci_runs_where_development_happens, ci_lanes_are_honest, plan_19, measurer_caveats, version_claim tausik/**, publication_lines pins, manifest_chain на сплющенной истории). Ревью: 4 high (traceback на опечатке → REFUSED; нет CLI-тестов → tests/test_publish_cli.py; per-file git show → git grep; заявление о «stale parent» шире механизма → переформулировано: ловит fast-forward push владельца), 2 medium (parent-check до скана; легенда с M), 2 low — все закрыты. ПОЛНЫЙ ПРОГОН НА СОБРАННОМ СНИМКЕ (worktree снимка рабочего дерева + bootstrap --no-detect --ide all + pytest -m ''): 10522 passed, 21 skipped, 0 failed за 8:19. Push/tag не выполнялись.
- 2026-09-13T14:17:27Z [implementation] — AC-1 ✓ `tausik publish snapshot --from HEAD --parent github/main --dry-run` (живой CLI после bootstrap): published 1308 / excluded 3090 под 9 правилами, по правилу: tasks 1646, stories 284, epics 109, decisions 369, memory 678, graph-snapshots 1, TODO.md 1, TAUSIK-plan-1.9.md 1, .gitlab-ci.yml 1 — M = 3090 ≥ 3075; tests/test_publish_cli.py::TestTheHappyPathReportsAndWritesNoRef::test_dry_run_reports_and_writes_no_commit. AC-2 ✓ tests/test_publication_snapshot.py::TestTheExclusionListIsOneDeclaration::test_the_projection_and_the_internal_files_stay_behind (временный репозиторий: проекция и три файла отсутствуют, gates.json/policy.json есть); ::TestTheLiveTree::test_the_ratchet_files_are_kept_and_the_projection_is_not (живое дерево: tausik/*.json в kept). AC-3 ✓ ::TestIdenticalIsATreeComparison::test_a_faithful_snapshot_matches; (НЕГАТИВ) ::test_a_snapshot_that_lost_a_file_is_refused_by_name — строка «D<TAB>docs/en/x.md» в отказе; ::test_a_snapshot_that_carries_the_projection_is_refused_by_name — tausik/tasks/some-task.md и TODO.md названы. AC-4 ✓ (НЕГАТИВ) ::TestRefusalsAreLoud::test_a_parent_that_is_not_a_commit_raises и tests/test_publish_cli.py::TestRefusalsAreCleanLines::test_a_parent_that_is_not_a_commit_is_refused_before_any_scan; ::test_a_typo_in_from_is_a_refusal_not_a_traceback; флага force нет в парсере (project_parser_publish.py). Заявление о «stale parent» сужено честно: команда не знает вершины remote — её ловит fast-forward-only push владельца (docs/publishing.md EN/RU). AC-5 ✓ полный прогон на СОБРАННОМ снимке (worktree снимка рабочего дерева, bootstrap --no-detect --ide all, pytest -m ''): 10522 passed, 21 skipped, 0 failed за 8:19; тесты, чей предмет исключён (#368), объявлены dormant через conftest.IS_PUBLIC_SNAPSHOT/DORMANT_ON_PUBLIC_SNAPSHOT (7 файлов), а три настоящих дефекта, всплывших на снимке, починены (stdin=DEVNULL в subprocess, entrypoint-guard, encoding в тесте). AC-6 ✓ tests/test_publication_snapshot.py::TestTheLiveTree::test_no_leak_class_survives_on_the_snapshot — 0/0 по рабочему дереву в наборе снимка; `publish snapshot --dry-run` по HEAD после коммита даст 0/0 (leaks_in_snapshot читает blob'ы ревизии); 43 примера путей и 1 хост фикстуры нейтрализованы; пины всего дерева 5→4, 39→22 (tests/test_publication_lines.py); (НЕГАТИВ) мутация — вернуть один файл проекции в kept — ловится ::test_the_projection_and_the_internal_files_stay_behind и ::test_the_rules_are_the_ones_decision_368_named. AC-7 ✓ docs/{ru,en}/publishing.md — порядок выкладки по #368 с командами; docs/{ru,en}/cli.md; CHANGELOG EN/RU. AC-8 ✓ verify #2605 подписан. Push/tag/release не выполнялись. Domain: то, что уедет на GitHub тегом 1.9, собрано командой, проверено на равенство фильтру, свободно от классов утечки и проходит собственный полный прогон — а не «всё дерево, как получится».
