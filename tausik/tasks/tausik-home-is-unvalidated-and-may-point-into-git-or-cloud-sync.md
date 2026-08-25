---
slug: tausik-home-is-unvalidated-and-may-point-into-git-or-cloud-sync
title: "TAUSIK_HOME не валидируется: общая база может оказаться внутри git-дерева или в облачной синхронизации"
status: done
epic: shared-knowledge
story: kb-global
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_home_guard.py"
  - "scripts/knowledge_db.py"
scope_paths:
  - "scripts/knowledge_db.py"
  - "scripts/knowledge_home_guard.py"
  - "tests/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-03T18:55:08Z"
---

## Goal

Найдено ревью безопасности сессии #155.

ЗАМЕР: scripts/knowledge_db.py::knowledge_home делает os.path.abspath(os.path.expanduser(override)) и больше ничего. Нет проверок: что путь не внутри git-отслеживаемого дерева; что это не симлинк/junction; что это не сетевой путь (UNC/SMB, NFS-mount); что это не каталог облачной синхронизации.

ПОЧЕМУ ЭТО ВАЖНО ИМЕННО ЗДЕСЬ: решение не вызывать скраббер на пути --global держится на утверждении «это файл в домашней папке, он не покидает машину». Если TAUSIK_HOME указывает внутрь рабочего дерева проекта, содержимое общей базы — знание из ВСЕХ проектов пользователя — уедет в git первым же `git add -A`. Если он указывает в Dropbox или OneDrive (а это тоже физически домашняя папка), оно уедет в облако. И то и другое — ровно тот выход за границу, который решение объявило невозможным по построению.

ПУТИ ПОПАДАНИЯ НЕ ТОЛЬКО ЗЛОНАМЕРЕННЫЕ: неверная переменная в конфиге CI, MCP-обёртка с чужим окружением, скопированный чужой .env.

ЧТО СДЕЛАТЬ: валидировать разрешённый путь и ОТКАЗЫВАТЬ (или громко предупреждать) когда он внутри активного git-репозитория либо внутри известного каталога облачной синхронизации. Образец проверок уже есть в проекте — skill_manager/skill_content_scan проверяют симлинки и обход каталогов при установке скиллов, следовать надо им.

## Acceptance Criteria

РЕШЕНИЕ ПО ФОРМЕ ОТВЕТА, записано явно. Задача предлагала «отказывать либо громко предупреждать». Ни то, ни другое целиком: ответ РАЗНЫЙ для случаев, которые мы можем починить сами, и тех, которые не можем. Отказ там, где починить нельзя; САМОЗАЩИТА там, где можно. Слепой отказ на git-дереве забраковал бы установку по умолчанию у каждого, кто держит домашний каталог в репозитории дотфайлов, — это частая практика, и отказ там был бы ложной тревогой на пустом месте.

AC1: путь разрешается ЧЕРЕЗ symlink/junction до всех проверок. Тест: home за симлинком, указывающим в облачный каталог, отвергается; проверка идёт по цели, а не по имени ссылки.
AC2: сетевой путь ОТВЕРГАЕТСЯ. Тест: UNC (\\server\share) и путь с корнем на сетевом диске дают ошибку, называющую причину и то, что делать.
AC3: каталог облачной синхронизации ОТВЕРГАЕТСЯ. Тест: OneDrive, Dropbox, Google Drive, Яндекс.Диск, iCloud как компонент пути дают ошибку. Совпадение по КОМПОНЕНТУ пути, не по подстроке: каталог «my-dropbox-notes» НЕ должен отвергаться.
AC4: git-дерево НЕ отвергается, а обезвреживается. В каталоге хранилища создаётся .gitignore с «*», поэтому `git add -A` из корня репозитория его не заберёт. Тест: хранилище внутри инициализированного репозитория; после открытия `git status --porcelain` не показывает его, и `git check-ignore` подтверждает игнорирование.
AC5: уже отслеживаемое хранилище — ОТКАЗ, а не молчаливое продолжение. .gitignore не распространяется на то, что уже под контролем версий, поэтому здесь утечка УЖЕ произошла; продолжать как ни в чём не бывало значит её усугублять. Тест: файл добавлен в индекс, открытие отвергается с сообщением, называющим, что файл уже отслеживается.
AC6: проверка не платится на каждом обращении. Тест: результат вычисляется один раз на процесс (счётчик вызовов дорогой части не растёт при повторных открытиях).
AC7 (НЕГАТИВ И ГРАНИЦЫ): (а) обычный путь по умолчанию вне git и вне облака проходит без ошибки и без .gitignore-шума там, где git-дерева нет; (б) несуществующий ещё каталог проверяется по будущему расположению, а не падает; (в) отсутствие git в PATH не превращается в ложный отказ — невозможность спросить git названа в сообщении, а не выдана за ответ; (г) пустой и состоящий из пробелов TAUSIK_HOME отвергается с ошибкой, а не молча превращается в текущий каталог.
AC8: докстринг knowledge_home перестаёт умалчивать: он называет проверку и то, что решение НЕ звать скраббер на пути --global опирается именно на неё.

## Plan

## Rollback

git revert. Проверка только отказывает или создаёт .gitignore в каталоге хранилища; данные не трогаются. Откат возвращает невалидируемый TAUSIK_HOME и оставляет созданный .gitignore на месте — он безвреден.

## Journal

- 2026-08-03T18:54:16Z [implementation] — Ревью (отдельный агент) дало ЧЕТЫРЕ critical, каждый ВОСПРОИЗВЕДЁН запуском кода, не чтением. Все приняты. (1) Существующий посторонний .gitignore (например *.log от инструментов) заставлял protect_home_in_git отступить, и git add -A клал хранилище в индекс — то есть проверка тихо не делала ничего ровно в том случае, ради которого написана. Теперь спрашивается, ИГНОРИРУЕТ ли git хранилище (check-ignore), а правило ДОПИСЫВАЕТСЯ, а не заменяет файл. (2) Кэш держал git-вердикт навсегда: каталог, ставший репозиторием ПОСЛЕ первой проверки в том же процессе, оставался без защиты — а долгоживущий MCP-сервер это ровно тот процесс, который назван в моём же докстринге как модель угрозы. Разделил: путь кэшируется (он не меняется), git перерешается на каждом открытии. Побочно это убрало git-подпроцесс с пути чтения. (3) Список облачных каталогов не ловил OneDrive - Acme Corp (имя по умолчанию почти на каждой управляемой машине Windows) и macOS-раскладку Library/CloudStorage/<провайдер>-<аккаунт>. Добавлено: компонент cloudstorage ловит всех провайдеров разом, префикс 'onedrive - ' со ЗНАЧАЩИМИ пробелами. Голый префикс onedrive НЕ годится: он глотает onedrive-backup-scripts — ложная тревога, ради избегания которой всё и разделено. (4) Сетевой том под буквой диска (Z: от логон-скрипта) и mount по fstab не ловились. Добавлено: GetDriveTypeW на Windows, /proc/mounts на Linux. macOS назван как НЕ покрытый — /Volumes это и локальные диски тоже, отказ всему неопознанному отверг бы обычный внешний диск. MEDIUM про box/mega как обычные английские слова принят: убраны из списка, оставлены суффиксные корни. MEDIUM про смешение двух задач в дереве — это состояние рабочего каталога, а не коммита; обе задачи отдельные. Два конвенционных гейта репозитория поймали мои же подпроцессы: encoding=utf-8 в тестах и stdin=DEVNULL в MCP-достижимом модуле. Исправлено. Две ОШИБКИ в фоновом полном прогоне (test_verify_handle, test_web_cache) оказались следствием ДВУХ ОДНОВРЕМЕННЫХ прогонов pytest, а не дефектом: перепрогон обоих файлов зелёный.
- 2026-08-03T18:55:02Z [implementation] — Ответ разделён по тому, можно ли опасность УБРАТЬ: отказ там, где нельзя, самозащита там, где можно. AC-1: ✓ tests/test_knowledge_home_guard.py::TestSymlinksAreResolvedBeforeAnythingIsJudged::test_a_link_pointing_into_a_synced_directory_is_refused AC-1: ✓ tests/test_knowledge_home_guard.py::TestSymlinksAreResolvedBeforeAnythingIsJudged::test_the_resolved_path_is_what_callers_get_back AC-2: ✓ tests/test_knowledge_home_guard.py::TestWhatIsRefusedOutright::test_a_network_path_is_refused AC-2: ✓ tests/test_knowledge_home_guard.py::TestWhatIsRefusedOutright::test_a_mapped_or_mounted_network_volume_is_refused AC-3: ✓ tests/test_knowledge_home_guard.py::TestWhatIsRefusedOutright::test_a_cloud_sync_directory_is_refused AC-3: ✓ tests/test_knowledge_home_guard.py::TestWhatIsRefusedOutright::test_the_macos_unified_cloud_layout_is_refused_whatever_the_provider AC-3: ✓ tests/test_knowledge_home_guard.py::TestWhatIsNotRefused::test_a_directory_merely_NAMED_after_a_sync_tool_is_fine AC-4: ✓ tests/test_knowledge_home_guard.py::TestAGitTreeIsNeutralisedRatherThanRefused::test_a_store_inside_a_work_tree_is_allowed AC-4: ✓ tests/test_knowledge_home_guard.py::TestAGitTreeIsNeutralisedRatherThanRefused::test_and_it_is_hidden_from_git_add_dash_A AC-4: ✓ tests/test_knowledge_home_guard.py::TestTheStoreItselfGoesThroughTheGuard::test_opening_the_store_inside_a_repo_leaves_it_ignored AC-5: ✓ tests/test_knowledge_home_guard.py::TestAnAlreadyTrackedStoreIsRefused::test_it_refuses_and_names_the_situation AC-6: ✓ tests/test_knowledge_home_guard.py::TestWhatIsCachedAndWhatIsDeliberatelyNot::test_the_path_verdict_is_computed_once_per_resolved_home AC-6: ✓ tests/test_knowledge_home_guard.py::TestWhatIsCachedAndWhatIsDeliberatelyNot::test_a_directory_that_BECOMES_a_repository_is_still_protected AC-7: ✓ tests/test_knowledge_home_guard.py::TestWhatIsNotRefused::test_an_ordinary_home_needs_no_gitignore AC-7: ✓ tests/test_knowledge_home_guard.py::TestWhatIsNotRefused::test_a_directory_that_does_not_exist_yet_is_validated_not_crashed_on AC-7: ✓ tests/test_knowledge_home_guard.py::TestGitBeingUnavailableIsNotAnAnswer::test_a_missing_git_does_not_produce_a_false_refusal AC-7: ✓ tests/test_knowledge_home_guard.py::TestGitBeingUnavailableIsNotAnAnswer::test_protection_still_happens_without_git_on_the_path AC-7: ✓ tests/test_knowledge_home_guard.py::TestWhatIsRefusedOutright::test_an_empty_home_is_refused_rather_than_resolved_to_the_cwd AC-8: ✓ tests/test_knowledge_home_guard.py::TestTheStoreItselfGoesThroughTheGuard::test_knowledge_home_refuses_a_synced_override AC-8: ✓ tests/test_knowledge_home_guard.py::TestTheStoreItselfGoesThroughTheGuard::test_a_read_only_check_creates_nothing Сверх критериев, по итогам ревью (каждый дефект ревью ВОСПРОИЗВЁЛ запуском): AC-4: ✓ tests/test_knowledge_home_guard.py::TestAGitTreeIsNeutralisedRatherThanRefused::test_a_gitignore_that_does_NOT_cover_the_store_is_not_mistaken_for_protection AC-4: ✓ tests/test_knowledge_home_guard.py::TestAGitTreeIsNeutralisedRatherThanRefused::test_the_other_rules_in_that_file_survive AC-4: ✓ tests/test_knowledge_home_guard.py::TestAGitTreeIsNeutralisedRatherThanRefused::test_a_gitignore_that_already_covers_the_store_is_left_alone Прогоны: срез knowledge/brain/mypy/ruff/docs/changelog 1114 passed, 6 skipped. mypy чист. Полный прогон 6870 passed; два падения были на МОИХ подпроцессах (конвенции репозитория encoding и stdin=DEVNULL) — исправлены и перепрогнаны, две ОШИБКИ оказались следствием двух одновременных сессий pytest, перепрогон зелёный. Домен: проверка отвечает на вопрос «уедет ли этот файл с машины», и ответ проверяется САМИМ git (check-ignore и git add -A), а не пересказом наших намерений.
