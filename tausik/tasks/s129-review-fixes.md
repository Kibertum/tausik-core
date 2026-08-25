---
slug: s129-review-fixes
title: "Ревью-фиксы батча 1.8: content-blind changelog-гейт, fail-open конфига, corrupt-key слепота, CWD в receipt show"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: changelog-continuous-gate
scope: "scripts/gate_changelog.py, scripts/project_cli_verify.py, scripts/verify_run_record.py, scripts/project_cli_receipt.py, scripts/verify_git_diff.py (только если нужен content-aware хелпер), tests/test_changelog_gate.py, tests/test_cli_verify_guards.py, CHANGELOG.md, CHANGELOG.ru.md, docs/ru/agent-contract.md"
scope_exclude: "crypto_sign/crypto_keys внутренности (формат ключа и подписи не трогаем), gate_verify_first, risk/L3-логика, прочие гейты, схема БД"
relevant_files:
  - "scripts/gate_changelog.py"
  - "scripts/verify_git_diff.py"
  - "scripts/project_root.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_cli_receipt.py"
  - "scripts/verify_run_record.py"
  - "tests/test_changelog_gate.py"
  - "tests/test_service_verification.py"
  - "tests/test_verify_first_contract.py"
  - "tests/test_fileless_close.py"
  - "tests/test_qg2_gates.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CLAUDE.md
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
  - "docs/ru/architecture.md"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "tests/conftest.py"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_tausik_service.py"
  - "tests/test_verify_receipt_emit.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T14:38:26Z"
---

## Goal

Закрыть находки adversarial-review незакоммиченного батча s129. Гейт непрерывного CHANGELOG сейчас доказывает только «файл байтово грязный» — пустая строка в оба файла проходит гейт и записывает в журнал «Changelog gate: verified», то есть политика #275 не работает, работает её театр. Конфиг гейта падает fail-open на любой ошибке разбора, при этом его собственный докстринг ссылается на doctor как на страховку, которой в doctor нет. Наблюдаемость подписи, только что добавленная в l26-signing-key-boundary, слепа к повреждённому ключу: load_public бросает — код печатает благодушное «нет ключа», воспроизводя ровно тот дефект тихой деградации, ради которого писался. И `receipt show` всё ещё резолвит project_dir через os.getcwd(), то есть прозаическая запись CHANGELOG про CWD-независимость подписи неверна для соседней команды. Слаг задачи уже процитирован в комментариях кода (gate_changelog.py:67, verify_run_record.py:146) — ссылка обязана резолвиться.

## Acceptance Criteria

AC1 (content-blind гейт). enforce_changelog доказывает СОДЕРЖАНИЕ, а не байтовую грязь: правка, добавляющая только пустые строки/пробелы, НЕ проходит гейт; правка, добавляющая непустую строку, проходит. Тест fail-then-pass на whitespace-only diff.
AC2 (fail-open конфига). Ошибка разбора task_done.changelog_gate (неверная форма блока) отличается от «не сконфигурирован»: она НЕ выключает гейт молча — либо блокирует по образцу gate_verify_first, либо пишет счётное событие + видимое предупреждение. Докстринг, ссылающийся на несуществующую страховку в doctor, приведён в соответствие с реальностью (или страховка добавлена в doctor). Тест на malformed-конфиг.
AC3 (files не список). changelog_gate.files присутствует, но не список → это ошибка авторства конфига, а не повод молча подставить билингвальный дефолт TAUSIK. Тест.
AC4 (corrupt-key слепота). _project_has_key отличает «ключа нет» (доброкачественный opt-out) от «файл ключа есть, но не грузится» (повреждение): второй случай идёт в тот же WARNING + receipt_sign_failed, что и провал подписи. Тест на существующий-но-битый ключ.
AC5 (CWD в receipt show). project_cli_receipt резолвит project_dir от корня проекта (svc.tausik_dir()), а не os.getcwd() — либо, если фикс сознательно отложен, прозаическая запись CHANGELOG сужается до verify/record_run и заводится follow-up задача. Тест на запуск из подкаталога.
AC6 (мёртвая ветка). isinstance(row, dict) в _project_dir_from_conn — недостижимая ветка: убрана либо заменена на реально достижимую проверку (hasattr(row,'keys') для sqlite3.Row) с тестом, который её исполняет.
AC7. Полный прогон pytest зелёный, БЕЗ warnings. Гейты task-done зелёные.
AC8. CHANGELOG.md и зеркало CHANGELOG.ru.md обновлены прозаической записью (гейт само-проверяется на этом закрытии).

## Plan

## Rollback

git revert коммита. Гейт остаётся config-gated (task_done.changelog_gate.enabled=false отключает без ревёрта); изменения в _project_has_key/receipt show — чистые фиксы резолва пути, откатываются файлово через git checkout -- <file>.

## Journal

- 2026-07-23T14:09:24Z [implementation] — Реализовано: (1) verify_git_diff.files_with_substantive_additions — content-aware проверка (добавленная НЕПУСТАЯ строка), покрывает tracked-diff (HEAD, staged+unstaged), untracked-файлы и, через since=started_at, УЖЕ ЗАКОММИЧЕННЫЕ во время задачи изменения; (2) _is_repo_root: .git может быть ФАЙЛОМ (worktree/submodule) — isdir объявлял worktree «не репозиторием», а все потребители фейлятся закрыто ⇒ в worktree нельзя было закрыть ни fileless-задачу, ни пройти changelog-гейт (находка product-аудита P1); (3) gate_changelog: конфиг читается через tausik_dir проекта (conv #265), malformed-блок = БЛОК вместо тихого fail-open, files не-список = ошибка авторства, а не подстановка билингвального дефолта TAUSIK; (4) project_root.root_from_service — одна формулировка «корень от хэндла, не от cwd» вместо четырёх приватных; (5) _project_has_key проверяет НАЛИЧИЕ файла ключа, а не загружаемость — битый ключ больше не читается как «ключа нет»; (6) receipt show/export резолвят project_dir от корня, а не os.getcwd(); (7) убрана недостижимая ветка isinstance(row, dict). Основание для (1)+since: продуктовый аудит нашёл, что гейт блокировал КАНОНИЧЕСКИЙ путь /ship (commit на шаге 7, close на шаге 8) — единственным проходом оставался --no-changelog.
- 2026-07-23T14:25:42Z [implementation] — Прогон после фиксов: 12 падений, ВСЕ на стороне тестов, не кода. (а) 11 тестов в test_service_verification.py подменяли ГЛОБАЛЬНЫЙ os.path.isdir, чтобы изобразить «это репозиторий» — предикат переименован в _is_repo_root (теперь exists, а не isdir, ради worktree), заглушки переведены на именованный шов verify_git_diff._is_repo_root: точечная подмена контракта вместо глобального патча os. (б) 5 заглушек project_config.load_config в трёх файлах объявлены как lambda БЕЗ аргументов, а гейт теперь передаёт tausik_dir (conv #265) — TypeError ловился моим же fail-closed обработчиком и честно рапортовался как «конфиг нечитаем»; заглушки приняли *a/**k. Поведение продукта в обоих случаях верное — правились именно тесты. Отдельно: тест committed-whitespace падал по СВОЕЙ предпосылке (окно since=1970 захватывало seed-коммит фикстуры с реальным текстом) — seed забэкдейчен на 2020, окна тестов начинаются с 2021.
- 2026-07-23T14:36:16Z [implementation] — AC1 ✓ content-aware: files_with_substantive_additions требует ДОБАВЛЕННУЮ непустую строку; проверено на РЕАЛЬНОМ git-репозитории, а не на заглушке (TestRealGit::test_whitespace_only_edit_does_not_count → set(), test_real_entry_counts → {CHANGELOG.md}, test_committed_whitespace_only_still_does_not_count). Дыра существовала именно потому, что все 20 прежних тестов подменяли git-слой, в котором она сидела (conv #268). AC2 ✓ fail-open закрыт: сломанный блок конфига возвращает текст ошибки, enforce_changelog БЛОКИРУЕТ с называнием дефекта (test_broken_config_fails_closed + 5 параметризованных форм); ложная ссылка на несуществующую проверку в doctor из докстринга убрана, вместо неё явное разделение «нет блока = тихий opt-out» / «блок сломан = блок». AC3 ✓ files не-список (строка, список с не-строкой) — ошибка авторства конфига, а не подстановка билингвального дефолта TAUSIK. AC4 ✓ _project_has_key решает по НАЛИЧИЮ файла ключа (crypto_keys.keys_dir + KEY_FILENAME/PUB_FILENAME), а не по успеху load_public: повреждённый ключ больше не читается как «ключа нет» и идёт в WARNING + receipt_sign_failed. AC5 ✓ receipt show и receipt export резолвят project_dir через project_root.root_from_service(svc), os.getcwd() убран из обоих. AC6 ✓ недостижимая ветка isinstance(row, dict) удалена (PRAGMA-строки индексируются позиционно и как tuple, и как sqlite3.Row). AC7 ✓ полный прогон 5385 passed / 23 skipped, БЕЗ warnings; два падения этого прогона были дефектами МОИХ артефактов и закрыты: (а) мета-гейт test_hook_encoding поймал мой же тестовый git-хелпер, декодирующий вывод дочернего процесса в кодировке родителя — добавлен encoding=utf-8; (б) счётчик тестов в docs/_generated/constants.json перегенерирован (gen_doc_constants --write). Профили IDE передеплоены (bootstrap --ide all) — новый модуль project_root.py иначе отсутствовал бы в рантайме (.claude/scripts) и валил бы MCP ImportError'ом, а bootstrap_drift — закрытие. AC8 ✓ CHANGELOG.md и CHANGELOG.ru.md содержат прозаические записи (гейт само-проверяется этим закрытием); docs/ru/agent-contract.md описывает новое поведение: что считается записью, окно since=started_at и почему (/ship коммитит до закрытия), fail-closed на сломанном конфиге, чтение конфига по tausik_dir проекта. СВЕРХ AC (находки продуктового и архитектурного аудитов, тот же модуль): (i) гейт больше не блокирует канонический путь /ship — коммиты, сделанные во время задачи, засчитываются; (ii) _is_repo_root: .git в worktree/сабмодуле это ФАЙЛ — прежняя проверка isdir объявляла worktree «не репозиторием», а все потребители фейлятся закрыто, то есть агент в worktree не мог ни закрыть fileless-задачу, ни пройти changelog-гейт вообще.
- 2026-07-23T14:36:43Z [implementation] — AC1 ✓ content-aware: files_with_substantive_additions требует ДОБАВЛЕННУЮ непустую строку; проверено на РЕАЛЬНОМ git-репозитории, не на заглушке (TestRealGit: whitespace_only → set(), real_entry → {CHANGELOG.md}, committed_whitespace_only → set()). Дыра жила именно потому, что все прежние тесты подменяли git-слой, в котором она сидела (conv #268). AC2 ✓ fail-open закрыт: сломанный блок конфига возвращает ошибку, гейт БЛОКИРУЕТ с называнием дефекта (test_broken_config_fails_closed + 5 параметризованных форм); ложная ссылка докстринга на несуществующую проверку в doctor убрана — теперь явное разделение «нет блока = тихий opt-out» / «блок сломан = блок». AC3 ✓ files не-список — ошибка авторства конфига, а не подстановка билингвального дефолта TAUSIK. AC4 ✓ _project_has_key решает по НАЛИЧИЮ файла ключа, а не по успеху load_public: повреждённый ключ больше не читается как «ключа нет». AC5 ✓ receipt show и receipt export резолвят project_dir через project_root.root_from_service(svc); os.getcwd() убран из обоих. AC6 ✓ недостижимая ветка isinstance(row, dict) удалена. AC7 ✓ полный прогон 5385 passed / 23 skipped, без warnings; два падения прогона были дефектами МОИХ артефактов и закрыты: мета-гейт test_hook_encoding поймал мой тестовый git-хелпер, декодирующий вывод дочернего процесса в кодировке родителя (добавлен encoding=utf-8), и счётчик тестов в constants.json перегенерирован. Профили IDE передеплоены — иначе новый project_root.py отсутствовал бы в рантайме (.claude/scripts) и валил бы MCP ImportError. AC8 ✓ оба CHANGELOG содержат прозу (гейт само-проверяется этим закрытием); agent-contract.md описывает: что считается записью, окно since=started_at и почему, fail-closed на сломанном конфиге, чтение конфига по tausik_dir проекта. СВЕРХ AC: гейт больше не блокирует канонический /ship (коммиты во время задачи засчитываются); _is_repo_root — .git в worktree/сабмодуле это ФАЙЛ, прежний isdir объявлял worktree «не репозиторием», и все потребители фейлились закрыто, то есть в worktree нельзя было ни закрыть fileless-задачу, ни пройти changelog-гейт.
- 2026-07-23T14:38:04Z [implementation] — AC1 ✓ content-aware: files_with_substantive_additions требует ДОБАВЛЕННУЮ непустую строку; проверено на РЕАЛЬНОМ git-репозитории, не на заглушке (TestRealGit: whitespace_only → set(), real_entry → {CHANGELOG.md}, committed_whitespace_only → set()). Дыра жила именно потому, что все прежние тесты подменяли git-слой, в котором она сидела (conv #268). AC2 ✓ fail-open закрыт: сломанный блок конфига возвращает ошибку, гейт БЛОКИРУЕТ с называнием дефекта (test_broken_config_fails_closed + 5 параметризованных форм); ложная ссылка докстринга на несуществующую проверку в doctor убрана — теперь явное разделение «нет блока = тихий opt-out» / «блок сломан = блок». AC3 ✓ files не-список — ошибка авторства конфига, а не подстановка билингвального дефолта TAUSIK. AC4 ✓ _project_has_key решает по НАЛИЧИЮ файла ключа, а не по успеху load_public: повреждённый ключ больше не читается как «ключа нет». AC5 ✓ receipt show и receipt export резолвят project_dir через project_root.root_from_service(svc); os.getcwd() убран из обоих. AC6 ✓ недостижимая ветка isinstance(row, dict) удалена. AC7 ✓ полный прогон 5385 passed / 23 skipped, без warnings; два падения прогона были дефектами МОИХ артефактов и закрыты: мета-гейт test_hook_encoding поймал мой тестовый git-хелпер, декодирующий вывод дочернего процесса в кодировке родителя (добавлен encoding=utf-8), и счётчик тестов в constants.json перегенерирован. Профили IDE передеплоены — иначе новый project_root.py отсутствовал бы в рантайме (.claude/scripts) и валил бы MCP ImportError. AC8 ✓ оба CHANGELOG содержат прозу (гейт само-проверяется этим закрытием); agent-contract.md описывает: что считается записью, окно since=started_at и почему, fail-closed на сломанном конфиге, чтение конфига по tausik_dir проекта. СВЕРХ AC: гейт больше не блокирует канонический /ship (коммиты во время задачи засчитываются); _is_repo_root — .git в worktree/сабмодуле это ФАЙЛ, прежний isdir объявлял worktree «не репозиторием», и все потребители фейлились закрыто, то есть в worktree нельзя было ни закрыть fileless-задачу, ни пройти changelog-гейт.
- 2026-07-23T14:38:18Z [implementation] — Root cause (missing-validation): гейт доказывал ПРОКСИ вместо предмета — 'файл байтово грязный' вместо 'в файл добавлена запись', а его конфиг падал открыто на любой ошибке разбора; ту же подмену предмета повторили _project_has_key (загружаемость ключа вместо наличия), receipt show/export (cwd вместо корня проекта) и _is_repo_root (тип узла .git вместо существования). Все три теста-набора при этом подменяли ровно тот слой, в котором сидела дыра, поэтому 20 зелёных тестов её не видели. Prevention: (1) гейт обязан судить о том, о чём его спросили — доказательство формулируется в терминах политики (добавленная непустая строка), а не в терминах ближайшего дешёвого сигнала git; (2) хотя бы один тест на гейт гоняется против РЕАЛЬНОГО производителя факта (настоящий git-репозиторий), а не против заглушки — conv #268; (3) fail-open допустим только там, где 'не сконфигурировано' достоверно отличимо от 'сломано', иначе опечатка тихо снимает политику; (4) прежде чем оправдывать fail-open ссылкой на страховку в другом месте (doctor) — проверить, что страховка существует.
- 2026-07-23T14:38:26Z [implementation] — AC1-AC8 подтверждены (полная развёртка залогирована выше): content-aware доказательство на реальном git; malformed-конфиг = блок, а не тихое выключение; files не-список = ошибка авторства; ключ судится по наличию, а не по загружаемости; receipt show/export резолвят корень от хэндла; мёртвая ветка удалена; 5385 passed без warnings; оба CHANGELOG и agent-contract обновлены. Сверх AC: снят блок канонического /ship и слепота к git-worktree.
