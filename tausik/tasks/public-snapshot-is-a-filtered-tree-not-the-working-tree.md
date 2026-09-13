---
slug: public-snapshot-is-a-filtered-tree-not-the-working-tree
title: "Публичный снимок 1.9 — отфильтрованное дерево без бухгалтерии tausik/ и внутренних файлов, собранное кодом и проверенное собственным прогоном"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Решение #368, п.2-3. ЗАМЕР, смена #251: в дереве 4379 отслеживаемых файлов, из них 3075 — проекция бухгалтерии tausik/{tasks,stories,epics,decisions,memory,graph-snapshots}; github/main несёт 2438 файлов tausik/ из 3576. Публикация сегодня (docs/ru/publishing.md) выносит ВСЁ дерево и говорит это прямо; классы утечки (39 файлов с путём среды разработки, 5 с внутренним хостом) живут в основном в этой бухгалтерии. Задача: (1) scripts/publication_tree.py — сборка публичного снимка из тега/коммита линии разработки: git read-tree с исключением объявленного перечня (проекция tausik/, TODO.md, TAUSIK-plan-1.9.md, .gitlab-ci.yml; храповики tausik/*.json остаются), commit-tree поверх заданного родителя (публичной головы), без force; перечень исключений — ОДНА объявленная константа, а не память; команда `tausik publish snapshot --from <ref> --parent <sha> [--dry-run]` печатает, что вошло и что исключено, с числами; (2) проверка равенства: `tausik publish verify --snapshot <sha> --from <ref>` сверяет отфильтрованное дерево с деревом снимка байт в байт (git diff-tree) — это и есть «GitLab идентичен GitHub»; (3) снимок обязан проходить свой полный прогон: сборка снимка во временный каталог + bootstrap --no-detect --ide all + pytest -m '' — и здесь всплывут тесты, читающие живую бухгалтерию tausik/tasks (closure-evidence remainder и т.п.); каждый такой тест делается честным на дереве без проекции (skip с причиной или чтение того, что есть); (4) tests/test_publication_lines.py расширяется: перечень исключений неизменен без правки теста, снимок не содержит ни одного файла проекции, классы утечки на СНИМКЕ равны нулю (не «объявленный остаток», а ноль — бухгалтерия ушла); (5) docs/{ru,en}/publishing.md переписаны под #368: две линии, что публикуется, команды выкладки, тег как часть выкладки.

## Acceptance Criteria

AC-1: `tausik publish snapshot --from HEAD --parent <sha> --dry-run` печатает перечень исключений и числа (вошло N файлов / исключено M), и M ≥ 3075 на сегодняшнем дереве. AC-2: собранный снимок не содержит ни одного пути из tausik/{tasks,stories,epics,decisions,memory,graph-snapshots}, TODO.md, TAUSIK-plan-1.9.md, .gitlab-ci.yml, и содержит tausik/gates.json, policy.json, published_tags.json, spec_coverage.json — тест на временном репозитории. AC-3: `tausik publish verify` даёт ноль расхождений между отфильтрованным деревом источника и снимком; НЕГАТИВ: снимок с одним изменённым байтом или с одним лишним файлом — отказ с именем файла. AC-4: НЕГАТИВ: сборка поверх родителя, который не является публичной головой (не fast-forward), — отказ; force не предусмотрен флагом вовсе. AC-5: полный прогон на собранном снимке во временном каталоге (bootstrap --no-detect --ide all; pytest -m '') зелёный на этой машине; число passed/skipped записано в журнал; тесты, зависевшие от живой проекции tausik/, названы и починены. AC-6: классы утечки на снимке (tests/test_publication_lines.py) — ноль вхождений пути среды разработки и внутреннего хоста; мутация — вернуть один файл проекции в перечень включений — краснит. AC-7: docs/{ru,en}/publishing.md описывают модель #368 и команды; CHANGELOG EN/RU. AC-8: signed verify. Push/тег/релиз НЕ выполняются — только сборка и проверка локально.

## Plan

## Rollback

git revert; публикация вернётся к ручной процедуре commit-tree над полным деревом.

## Journal
