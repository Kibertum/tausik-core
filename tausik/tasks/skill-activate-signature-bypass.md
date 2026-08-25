---
slug: skill-activate-signature-bypass
title: "skill activate обходит проверку подписи и фильтр копирования, которые есть у skill install"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/service_skills.py, scripts/skill_manager.py, tests/test_skill_activate_supply_chain.py, tests/test_vendor.py, docs/_generated/constants.json"
scope_exclude: "scripts/supply_verify_install.py (верификатор корректен, менять его контракт не требуется), scripts/skill_repos.py, bootstrap/, harness/ и .claude/ (генерируемые зеркала — правится только корень)"
relevant_files:
  - "scripts/service_skills.py"
  - "scripts/skill_manager.py"
  - "tests/test_skill_activate_supply_chain.py"
  - "tests/test_vendor.py"
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-18T20:33:32Z"
---

## Goal

ДЕФЕКТ БЕЗОПАСНОСТИ в поставленном коде, найден аудитом цепочки поставки (сессия #117), подтверждён чтением кода лично.

СУТЬ: check_skill_signature имеет РОВНО ОДНУ точку вызова — skill_manager.py:301, путь install. Путь activate (service_skills.py:119-133) подпись не проверяет вообще и делает shutil.copytree БЕЗ ignore-фильтра, который в copy_skill (skill_manager.py:254-266) вырезает hooks/, .claude-plugin/, CLAUDE.md и .git*.

ЭКСПЛУАТАЦИЯ: скилл, заблокированный или помеченный UNVERIFIED при install, ставится одной командой `tausik skill activate <name>` со всеми проверками в обход. Причём скилл не обязан быть в манифесте tausik-skills.json: _find_vendor_skill (service_skills.py:88-98) находит его по одному наличию SKILL.md в любом склонированном vendor-репо. Через MCP activate доступен агенту напрямую и не требует force.

СМЕЖНЫЙ ДЕФЕКТ (чинится здесь же, тот же метод): _find_vendor_skill итерирует os.listdir без сортировки и берёт первое совпадение. Два репозитория с одноимённым скиллом дают недетерминированный выбор — атакующий, чей репо уже добавлен, перехватывает активацию популярного имени. Для сравнения find_skill_source (skill_manager.py:211) использует sorted(), то есть предсказуем, но всё ещё first-wins.

ПРИНЦИП ИСПРАВЛЕНИЯ: activate не имеет права быть более слабым путём, чем install. Верификация и фильтр — общий код, а не продублированный, иначе они снова разойдутся. Первопричина расхождения именно в дублировании: фильтр написан как локальная функция внутри copy_skill и потому недоступен второму потребителю.

ГРАНИЦА: скиллы фреймворка (_find_official_skill) — first-party, подписи не имеют и не требуют. Проверка применяется к vendor-источнику.

## Acceptance Criteria

1. skill_activate вызывает check_skill_signature для vendor-источника ДО того, как первый файл попадает в дерево скиллов. LEVEL_BLOCK — отказ с сообщением верификатора; LEVEL_WARN — установка с предупреждением (тот же adoption-path, что у install, не строже и не слабее).
2. skill_activate применяет ТОТ ЖЕ фильтр копирования, что copy_skill: hooks/, .claude-plugin/, .git*, CLAUDE.md, __pycache__, .mypy_cache не попадают в активированное дерево. Фильтр вынесен в ОДНУ общую функцию и вызывается обоими путями — продублированного списка исключений в репозитории не остаётся (проверяется grep-ом: литерал ".claude-plugin" встречается ровно один раз в scripts/).
3. _find_vendor_skill возвращает имя vendor-репозитория вместе с путём (оно нужно для поиска запиненного ключа) и итерирует sorted(os.listdir(...)) — выбор детерминирован.
4. Коллизия имён: если одноимённый скилл найден в ДВУХ и более vendor-репозиториях, поднимается ServiceError с перечислением кандидатов, а не берётся первый. Тихая перезапись одноимённым устранена.
5. config_path=None (ключ запинить негде) даёт LEVEL_WARN, а не пропуск проверки: неизвестность сообщается, а не выдаётся за успех (конвенция #226).
6. Тесты, каждый падает на текущем коде и проходит после фикса:
   а) активация неподписанного vendor-скилла — предупреждение, установка проходит;
   б) активация скилла с битым запиненным ключом — ServiceError, каталог назначения НЕ создан;
   в) активированное дерево не содержит hooks/, .claude-plugin/, CLAUDE.md, .git*;
   г) одноимённый скилл в двух репо — ServiceError со списком кандидатов;
   д) официальный (first-party) скилл активируется без требования подписи.
7. Регрессия отсутствует: полный прогон pytest зелёный, существующие тесты test_supply_verify_install.py и тесты скиллов не тронуты по смыслу.
8. Оба файла остаются под гейтом 400 строк.

## Plan

## Rollback

git revert коммита. Изменение аддитивное: добавляется проверка на пути activate и общий фильтр. Отката данных не требуется — схема БД, конфиг и уже активированные скиллы не трогаются. Риск отката нулевой: возврат восстанавливает текущее (уязвимое) поведение, ничего не ломая. Если фикс окажется слишком строгим и заблокирует легитимную активацию, точечный откат — снять raise на LEVEL_BLOCK в skill_activate, оставив фильтр и детерминизм.

## Journal

- 2026-07-18T20:21:46Z [implementation] — ФИКС ГОТОВ, доказательство снято. Изменения: (1) skill_manager.py — фильтр вынесен из локальной _ignore внутри copy_skill в модульную skill_tree_ignore + _SKIP_DIRS/_SKIP_FILES на уровне модуля; copy_skill теперь её вызывает. (2) service_skills.py — _find_vendor_skill возвращает (skill_path, repo_name), итерирует sorted(), при >1 совпадении поднимает ServiceError со списком репозиториев; добавлен _verify_vendor_skill (зовёт check_skill_signature, BLOCK->ServiceError, WARN->текст в возврате, нечитаемый пин->ServiceError fail-closed по конвенции #221); skill_activate зовёт верификацию для vendor-источника и применяет skill_tree_ignore к ОБОИМ источникам. (3) tests/test_vendor.py — тест приведён к новому контракту кортежа. ПРОВЕРЕНО СТЭШЕМ, а не заявлено: на коде ДО фикса 7 из 9 новых тестов падают (unsigned-warn, tampered-refused, no-config-warn, copy-filter, collision x2, deterministic-lookup). Стэш восстановлен чисто, git status сверен. ЧЕСТНАЯ ОГОВОРКА к AC #6: формулировка «каждый тест падает на текущем коде» неточна. Два теста зелёные и до фикса по своей природе — test_signed_and_pinned_activates_without_warning и test_official_skill_activates_without_a_signature. Это не регрессионные тесты бага, а страховки от ПЕРЕСТРАХОВКИ: первый ловит ложный warning на валидной подписи, второй — что фикс не потребовал подписи у first-party скиллов. Оставляю их намеренно, AC считаю выполненным по существу (7 доказывают фикс, 2 охраняют границу), но не заявляю выполнение буквальной формулировки. Регрессия: 138 тестов в пяти смежных наборах зелёные (новый, supply_verify_install, skill_manager, vendor, copy_symlinks_disabled). Гейт 400 строк: service_skills 306, skill_manager 372. Дублирующегося списка исключений в scripts/ не осталось. ОТКРЫТО, не входит в scope: .claude/scripts/ — генерируемое зеркало, MCP-сервер грузится оттуда, поэтому фикс станет живым для текущего процесса только после bootstrap. Правка зеркала руками запрещена CLAUDE.md.
- 2026-07-18T20:33:31Z [implementation] — AC verified 1-8. 1. PASS — skill_activate зовёт _verify_vendor_skill ДО copytree (service_skills.py:175-183). LEVEL_BLOCK -> ServiceError, LEVEL_WARN -> текст в возврате. Доказательство: test_tampered_after_signing_is_refused (падает до фикса), test_unsigned_warns_but_activates (падает до фикса). 2. PASS — общая skill_tree_ignore (skill_manager.py:231), вызывается copy_skill'ом (:279) и skill_activate (:196). Grep ".claude-plugin" по scripts/ --include=*.py даёт РОВНО ОДНО вхождение — skill_manager.py:227. Доказательство: test_hooks_and_plugin_manifest_never_reach_the_tree (падает до фикса). 3. PASS — _find_vendor_skill возвращает (skill_path, repo_name), итерирует sorted(). Доказательство: test_lookup_is_deterministic (падает до фикса: ValueError too many values to unpack), test_find_vendor_skill в test_vendor.py приведён к новому контракту. 4. PASS — при >1 совпадении ServiceError с перечислением репозиториев. Доказательство: test_two_repos_publishing_one_name_is_an_error, test_collision_message_names_every_candidate (оба падают до фикса). 5. PASS — config_path=None даёт WARNING, а не пропуск. Доказательство: test_no_config_still_checks (падает до фикса). Нечитаемый пин обрабатывается строже — ServiceError, fail-closed по конвенции #221. 6. PASS ПО СУЩЕСТВУ, НО НЕ ПО БУКВЕ — заявляю расхождение явно. Формулировка критерия «каждый тест падает на текущем коде» неточна: из 9 новых тестов на коде ДО фикса падают 7, проверено git stash (стэш восстановлен, git status сверен). Два теста зелёные и до фикса ПО СВОЕЙ ПРИРОДЕ: test_signed_and_pinned_activates_without_warning и test_official_skill_activates_without_a_signature — это не регрессионные тесты бага, а страховки от перестраховки (валидная подпись не должна порождать warning; first-party скиллы не должны требовать подписи). Оставлены намеренно. Подпункты а-д критерия покрыты: а) test_unsigned_warns_but_activates; б) test_tampered_after_signing_is_refused, включая assert что каталог назначения НЕ создан; в) test_hooks_and_plugin_manifest_never_reach_the_tree; г) test_two_repos_publishing_one_name_is_an_error; д) test_official_skill_activates_without_a_signature. 7. PASS — полный прогон pytest: 4799 passed, 21 skipped, 0 failed. Единственная падавшая (test_check_docs_hook, дрейф doc-constants от +9 новых тестов и от изменения счётчика с прошлой сессии) устранена регенерацией gen_doc_constants.py --write; перепроверено — 6 passed. tausik verify --scope high по задаче: passed=True, гейты hadolint + pytest. 8. PASS — service_skills.py 306 строк, skill_manager.py 372, новый тест 177. Гейт 400 не нарушен. ЗАМЕЧАНИЕ О КАЧЕСТВЕ ДОКАЗАТЕЛЬСТВА: первый вызов tausik verify вернул passed=True при status=miss с НЕобъявленными relevant_files — живое воспроизведение открытого дефекта verify-cache-empty-scope-hit. Этот зелёный за доказательство не принимался; вместо него снят полный прогон pytest вручную, а relevant_files объявлены при закрытии. ОСТАЛОСЬ ВНЕ SCOPE: .claude/scripts/ — генерируемое зеркало, из которого грузится MCP-сервер; фикс станет живым для текущего процесса только после bootstrap. Правка зеркала руками запрещена CLAUDE.md.
- 2026-07-18T20:34:16Z [done] — EVIDENCE В ФОРМАТЕ КОНВЕНЦИИ #215 (первое закрытие ушло прозой «1. PASS», парсер засчитал 1/8 — переписываю маркерами). AC-1: ✓ подпись проверяется до записи файлов, BLOCK отказывает / WARN пропускает — tests/test_skill_activate_supply_chain.py::TestSignatureEnforced::test_tampered_after_signing_is_refused AC-2: ✓ общий фильтр копирования, дублирующего списка исключений не осталось — tests/test_skill_activate_supply_chain.py::TestCopyFilter::test_hooks_and_plugin_manifest_never_reach_the_tree AC-3: ✓ _find_vendor_skill возвращает (path, repo_name) и итерирует sorted() — tests/test_skill_activate_supply_chain.py::TestNameCollision::test_lookup_is_deterministic AC-4: ✓ коллизия имён в двух репо — ошибка со списком кандидатов, не первый попавшийся — tests/test_skill_activate_supply_chain.py::TestNameCollision::test_collision_message_names_every_candidate AC-5: ✓ config_path=None даёт WARNING, а не молчаливый пропуск — tests/test_skill_activate_supply_chain.py::TestSignatureEnforced::test_no_config_still_checks AC-6: ✓ пять подпунктов а-д покрыты; 7 из 9 тестов падают на коде до фикса (проверено git stash) — tests/test_skill_activate_supply_chain.py::TestSignatureEnforced::test_unsigned_warns_but_activates AC-7: ✓ регрессии нет, полный прогон 4799 passed / 21 skipped / 0 failed — tests/test_vendor.py::TestSkillCLI::test_find_vendor_skill AC-8: ✓ гейт 400 строк не нарушен (306 / 372 / 177) — tests/test_skill_activate_supply_chain.py::TestFirstPartySkills::test_official_skill_activates_without_a_signature Negative: подписанный скилл, изменённый ПОСЛЕ подписи, обязан быть отвергнут и не оставить ничего на диске — tests/test_skill_activate_supply_chain.py::TestSignatureEnforced::test_tampered_after_signing_is_refused Negative: одноимённый скилл из двух репозиториев не должен разрешаться молча в первый попавшийся — tests/test_skill_activate_supply_chain.py::TestNameCollision::test_two_repos_publishing_one_name_is_an_error Domain: вне тестов результат означает, что путь activate перестал быть более слабым входом, чем install. Реальный сценарий, который теперь закрыт: злоумышленник публикует TAUSIK-совместимый репозиторий, жертва добавляет его, install отказывает или предупреждает — и раньше та же поставка проходила одной командой activate, принося вдобавок hooks/ и .claude-plugin/, которые install вырезает. Через MCP activate вызывается агентом напрямую и force не требует, поэтому обход был доступен не только человеку. Побочно: утверждение README «a skill supply chain that verifies the same way on every platform» до этого фикса было ложным, теперь соответствует коду. Checklist: scope — объявлен и расширен ЯВНО перед записью в docs/_generated/constants.json, а не обойдён через Bash, где scope-гейт не действует; тесты — 9 новых, 7 доказаны падением до фикса через git stash с последующим восстановлением; security — устранён обход верификации подписи и недетерминированный выбор источника, применены конвенции #221 (нечитаемый пин блокирует) и #226 (неизвестность сообщается, а не выдаётся за успех); rollback — git revert, изменение аддитивное, данные и схема не тронуты.
