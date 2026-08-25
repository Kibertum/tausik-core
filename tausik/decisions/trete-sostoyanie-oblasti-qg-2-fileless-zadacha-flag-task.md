---
slug: trete-sostoyanie-oblasti-qg-2-fileless-zadacha-flag-task
task: qg2-cannot-close-fileless-task
date: "2026-07-20"
edges: []
---

## Decision

Третье состояние области QG-2 (fileless-задача) = флаг task done --no-file-changes, проверяемый git status --porcelain по объявленной области (relevant_files как pathspec; всё дерево при пустом списке). Fail-closed: git недоступен ИЛИ область грязна → блок. Доказательство ФАКТОМ git, не словом. Счётность — отдельная колонка tasks.no_file_changes_declared (симметрично no_tests_declared). Гейты области НЕ гонятся (нечего гонять).

## Rationale

changed_files_since ОТВЕРГНУТ: его git log --since ловит ЧУЖИЕ коммиты, сделанные ПОСЛЕ старта задачи (накопление к релизу), из-за чего глобальный change-set fileless-задачи никогда не пуст → закрытие невозможно навсегда. working-tree porcelain судит только НЕЗАКОММИЧЕННОЕ = область ответственности здесь-и-сейчас, обходя ловушку --since. Область как pathspec делает proof accumulation-friendly: правки в чужих каталогах не считаются. Не-вакуумность обеспечена тем, что грязная область блокирует (доказано тестом), поэтому необязательное объявление не становится «закрыть что угодно».
