---
slug: release-1-6-1
title: "Релиз 1.6.1: закрыть хвост — main на 7 коммитов впереди тега v1.6.0"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/tausik_version.py, pyproject.toml, docs/_generated/constants.json, README.md, README.ru.md, CHANGELOG.md, CHANGELOG.ru.md. Git-операции: тег, пуш GitLab + GitHub-зеркало."
scope_exclude: "Не менять код рантайма. Не пушить в github раньше GitLab. Приватный ключ не трогать."
relevant_files:
  - "scripts/tausik_version.py"
  - pyproject.toml
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-11T05:02:22Z"
---

## Goal

main ушёл на 7 коммитов вперёд тега v1.6.0 (post-release работа: возврат GitLab CI + защита от класса тихих ошибок — флаги против бинаря, gen_doc_constants --write, fire-and-forget subprocess). Тег стабилен, но не отражает main. Вырезать 1.6.1: бамп версии в 5 местах (tausik_version.py, pyproject.toml, constants.json, README.md:9, README.ru.md:9), changelog en+ru, регенерация constants + doc-count места, полный прогон, коммит, тег v1.6.1, пуш в GitLab (main+тег) и GitHub-зеркало (ff-child+тег). Никаких изменений рантайма — только tooling/CI/тесты, поэтому patch.

## Acceptance Criteria

1) Версия 1.6.1 консистентна во всех 5 местах + constants.json. 2) Changelog en+ru описывает 7 коммитов честно (CI-возврат + защита класса). 3) gen_doc_constants --check зелёный на 1.6.1. 4) Полный прогон 0 failed. 5) Тег v1.6.1 на HEAD, запушен в GitLab. 6) GitHub-зеркало обновлено ff-child + тег. 7) Оба пайплайна (ядро + при необходимости) зелёные — проверено через glab. Негативные: 8) Ошибка, если версия рассинхронизирована хоть в одном месте. 9) Ошибка, если объявить релиз готовым, не увидев зелёный пайплайн. 10) Ошибка, если что-то ушло в github раньше внутреннего GitLab, или во внутренний магазин-репозиторий просочилось лишнее.

## Plan

## Rollback

git tag -d v1.6.1 локально; версия откатывается git checkout. Тег в remote удаляется git push --delete при необходимости (с разрешения).

## Journal

- 2026-07-11T05:02:11Z [implementation] — AC verified: 1. ✓ Версия 1.6.1 консистентна: version.py/pyproject/constants/README.md/README.ru.md все 1.6.1 (проверено скриптом, ALL EQUAL). 2. ✓ Changelog en+ru — секция 1.6.1 описывает 7 коммитов (CI-возврат, CI магазина, 3 грани класса тихих ошибок). 3. ✓ gen_doc_constants --check OK на 1.6.1. 4. ✓ Полный прогон 4448 passed, 20 skipped, 0 failed (локально) + 4336 passed на Linux CI. 5. ✓ Тег v1.6.1 на HEAD (аннотированный -> cdde825 == HEAD), запушен в GitLab (0a2e165). 6. ✓ GitHub-зеркало: ff-child e036321 (дерево == main байт в байт, 828 файлов, ни одного внутреннего скилла), тег v1.6.1 (6808b05). 7. ✓ Пайплайн ядра 3638 status=success, джоб tests прогнал сюиту. Негативные: 8. ✓ Версия не рассинхронизирована — проверено. 9. ✓ Пайплайн зелёный увиден через glab, не предположен. 10. ✓ Порядок: GitLab main+тег ПЕРЕД GitHub; публикуемое дерево проверено на отсутствие внутренних скиллов ДО пуша; приватный ключ не трогался. Domain: 1.6.1 приводит тег в соответствие с main — 'тег == HEAD: ДА'. Хвост релиза закрыт: main больше не впереди тега. Рантайм не менялся (только tooling/CI/тесты), поэтому patch корректен.
