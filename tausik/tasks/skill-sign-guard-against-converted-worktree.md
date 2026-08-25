---
slug: skill-sign-guard-against-converted-worktree
title: "skill sign обязан отказывать, если подписывает сконвертированное рабочее дерево"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/supply_sign.py (или отдельный модуль-помощник), tests/. Плюс .gitattributes в шаблон скилла и упоминание в docs/ru/skill-spec.md + docs/en."
scope_exclude: "Не менять способ хеширования: сырые байты, без нормализации (решение #129)."
relevant_files:
  - "scripts/supply_eol.py"
  - "scripts/supply_sign.py"
  - "scripts/project_cli_skill.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_supply_eol.py"
  - "docs/ru/skill-spec.md"
  - "docs/en/skill-spec.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T13:12:01Z"
---

## Goal

Не дать издателю выпустить подпись, которую никто не проверит. Если подписываемый каталог лежит в git-репозитории, сверить байты рабочего дерева с байтами индекса: 'git ls-files --eol -- <dir>' (проверено, работает) даёт 'i/lf w/crlf' там, где конверсия сработала. При расхождении — отказ с указанием файлов и подсказкой про .gitattributes '* -text'. Вне git — тихо пропустить проверку. Дополнить docs/ru/skill-spec.md и шаблон нового скилла файлом .gitattributes. Подпись остаётся подписью сырых байт: нормализация отвергнута (см. решение в задаче-родителе).

## Acceptance Criteria

1) Если подписываемый каталог в git-репозитории и рабочее дерево расходится с индексом по окончаниям строк, sign_artifact отказывает с перечислением файлов и подсказкой про .gitattributes '* -text'. 2) Проверка через 'git ls-files --eol': расхождение i/ и w/. 3) Вне git-репозитория проверка тихо пропускается — подписывать распакованный тарбол законно. 4) Есть аварийный выход для осознанного случая. Негативные сценарии: 5) Ошибка, если LF-дерево в LF-репозитории вдруг отвергается (ложное срабатывание). 6) Ошибка, если git отсутствует или команда падает — тогда не блокировать подпись, а предупредить. 7) Ошибка, если полный прогон даёт новое падение.

## Plan

## Rollback

git checkout -- scripts/ tests/ docs/; bootstrap для зеркал.

## Journal

- 2026-07-10T13:07:15Z [implementation] — AC verified: 1. ✓ sign_artifact отказывает и называет файлы — TestRaising::test_assert_names_the_files, TestSignArtifactIntegration::test_sign_refuses_converted_worktree. 2. ✓ Проверка сделана НЕ по 'git ls-files --eol', а сравнением байтов рабочего дерева с 'git cat-file blob :<path>'. Основание: проба показала, что в сконвертированном дереве --eol даёт w/crlf, но 'git status --porcelain' пуст (git нормализует перед сравнением), а blob-vs-disk точен и ловит любой smudge-фильтр, не только EOL. 3. ✓ Вне git тихо пропускается — test_outside_a_git_repo_is_skipped, is_git_worktree=False. 4. ✓ Аварийный выход --allow-eol-drift: есть в CLI ('.tausik/tausik skill sign --help' показывает), доходит до sign_artifact (test_allow_eol_drift_reaches_the_signer). 5. ✓ (негативный) Чистое LF-дерево не отвергается — test_clean_worktree_passes; бинарный logo.png не даёт ложного срабатывания — test_binary_file_is_not_a_false_positive. 6. ✓ (негативный) Отказ git не проглатывается — test_tracked_blob_failure_is_not_swallowed. 7. — полный прогон впереди. Найденный по дороге баг в собственной первой версии: repo_root() через 'rev-parse --show-toplevel' отдавал длинный путь (C:/Users/[вычеркнуто: local-path]/...), а artifact_dir был в 8.3-форме ([вычеркнуто: local-path]); os.path.relpath между ними давал мусор, cat-file падал с rc=128, и мой 'continue' объявлял файл нетронутым. Гвард молча не срабатывал — ровно тот класс тихой ошибки, который чиню. Исправлено: путь спрашивается у git ('rev-parse --show-prefix' + 'ls-files --full-name'), арифметики путей нет; отказ cat-file по отслеживаемому файлу теперь поднимает WorktreeDriftError, а не проглатывается. Закреплено тестом. Domain: живой прогон scratchpad/sign_guard_live.py на настоящем ключе проекта — сконвертированное дерево отвергнуто, чистое подписано (fp 103a83a2), --allow-eol-drift подписал, распакованный тарбол подписан без проверки. Приватный ключ не читался и не печатался. Документация: docs/{ru,en}/skill-spec.md получили раздел про подпись и окончания строк с требованием .gitattributes '* -text'. Шаблона нового скилла в репозитории нет — выдумывать не стал.
