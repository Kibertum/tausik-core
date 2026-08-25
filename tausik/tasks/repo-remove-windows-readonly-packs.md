---
slug: repo-remove-windows-readonly-packs
title: "3.3: skill repo remove падает на Windows — rmtree без обработчика read-only git-паков"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/skill_repos.py (repo_remove), scripts/skill_git.py (rmtree_force), scripts/project_cli_skill.py (обработка ошибки), tests/test_skill_repo_trust.py"
scope_exclude: "Не менять формат config.json. Не трогать bootstrap_vendor.py."
relevant_files:
  - "scripts/skill_repos.py"
  - "scripts/skill_git.py"
  - "scripts/project_cli_skill.py"
  - "tests/test_skill_repo_trust.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T13:16:52Z"
---

## Goal

Первопричина: repo_remove (scripts/skill_repos.py:181) зовёт shutil.rmtree(repo_dir) без onexc/onerror. Git помечает .git/objects/pack/*.pack и *.idx read-only, на Windows это PermissionError. Репро воспроизведён: rmtree над read-only файлом падает, каталог остаётся; с обработчиком chmod(S_IWRITE)+retry удаляется. Хуже того, rmtree падает ДО update_config_repo_remove, поэтому конфиг остаётся с репозиторием, а вендор-кэш продолжает отдавать старую версию скилла — отсюда UNSIGNED уже после пуша подписи. Правка: onexc-обработчик (Python 3.12+) / onerror (3.11) со снятием read-only; сначала удалить каталог, затем править конфиг, и на неудаче — отказ с ненулевым кодом, а не тихий откат.

## Acceptance Criteria

1) repo_remove удаляет вендор-клон с read-only git-паками на Windows. 2) Каталог удаляется ДО правки конфига; при неудаче конфиг не трогается и команда падает с ненулевым кодом, а не печатает ложный успех. 3) CLI ловит SkillManagerError и выходит с 2, без трейсбека. Негативные сценарии: 4) Ошибка, если после неудачного удаления репозиторий исчез из конфига, а кэш остался — это исходный баг. 5) Ошибка, если premise неверна: тест проверяет, что настоящий git действительно кладёт read-only паки. 6) Ошибка при полном прогоне с новым падением.

## Plan

## Rollback

git checkout -- scripts/skill_repos.py scripts/project_cli_skill.py tests/; bootstrap для зеркал.

## Journal

- 2026-07-10T13:16:44Z [implementation] — AC verified: 1. ✓ repo_remove сносит клон с read-only паками — test_remove_survives_readonly_packs; живой прогон: каталог был, после repo_remove его нет, конфиг пуст. Сравнение со старым путём в том же прогоне: голый shutil.rmtree даёт PermissionError и каталог остаётся. 2. ✓ Удаление идёт ДО update_config_repo_remove; при неудаче поднимается SkillManagerError и конфиг не трогается — test_removal_failure_leaves_config_untouched (репозиторий остался в конфиге). 3. ✓ CLI ловит SkillManagerError, печатает в stderr и выходит с 2 — правка в project_cli_skill.py::_cmd_skill_repo. 4. ✓ (негативный) Исходный баг — кэш жив, а конфиг очищен — исключён порядком операций и закреплён тестом. 5. ✓ (негативный) Премиса проверена, а не принята: TestRealGitPacksAreReadOnly::test_git_writes_readonly_packs клонирует настоящий репозиторий и убеждается, что хотя бы один pack не доступен на запись (иначе skip). 6. — полный прогон в конце релиза. Root cause (logic-error): shutil.rmtree без onerror/onexc падает на read-only файлах Windows, а вызов стоял ПЕРЕД правкой конфига, поэтому исключение оставляло систему в противоречивом состоянии: вендор-кэш жив и отдаёт старую версию скилла, отсюда UNSIGNED уже после того, как подпись была запушена. Prevention: удаление каталога и правка состояния — одна операция; сначала необратимое действие, потом запись состояния, и никакого молчаливого проглатывания OSError. Обработчик снятия read-only вынесен в skill_git.rmtree_force и переиспользуется clone_repo при пересоздании устаревшего клона.
