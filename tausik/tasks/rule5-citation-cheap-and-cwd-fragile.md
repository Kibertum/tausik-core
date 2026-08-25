---
slug: rule5-citation-cheap-and-cwd-fragile
title: "Гейт Rule 5: ссылка на тест не проверяется по существу, а корень берётся из cwd — обещание строгости не выполняется"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: rule5-checklist-keyword-theater
scope: "scripts/gate_ac_check.py, tests/test_checklist_hardgate.py, CHANGELOG.md, CHANGELOG.ru.md, docs/ru/agent-contract.md"
scope_exclude: "scripts/service_ac_evidence.py (парсер не трогаем — его расширение это ac-evidence-parser-format-strict), scripts/hooks/**"
relevant_files:
  - "scripts/gate_ac_check.py"
  - "scripts/gate_test_citation.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "tests/test_checklist_hardgate.py"
  - "tests/test_agent_units_recording.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T10:15:29Z"
---

## Goal

Находки adversarial-ревью сессии #133 НА ФИКС rule5-checklist-keyword-theater, воспроизведены исполнением кода.

(1) CWD-ХРУПКОСТЬ. _test_ref_exists резолвит путь от os.getcwd(), тогда как весь остальной фреймворк намеренно cwd-независим (project_config.find_tausik_dir поднимается до 10 каталогов вверх, hooks/_common.project_root существует ровно для этого). Замер: одна и та же задача, cwd=. → ref_exists=True, hard_block=False; cwd=docs или cwd=scripts → ref_exists=False, hard_block=True. Агент, работающий из подкаталога, получает блок с сообщением «a path that does not resolve is treated as no evidence at all» при полностью настоящем доказательстве, и НЕТ строки в журнале, которая это чинит. Единственный выход — config task_done.checklist_hard=false, у которого, в отличие от TAUSIK_SKIP_HOOKS, нет даже supervision-события. То есть новый гейт создаёт ровно ту петлю «ложный блок → выключение надзора», которую docstring соседнего детектора объявляет недопустимой.

(2) ССЫЛКА ДЕШЕВЛЕ, ЧЕМ ЗАЯВЛЕНО. Docstring утверждает, что цитата — «the only claim it cannot make cheaply». Проверено: hard_block=False для «1. ✓ tests/test_hooks.py::test_totally_made_up_9876» (имя теста после :: отбрасывается и НИКОГДА не проверяется), для «AC-1: ✓ test_hooks.py::test_x» (fallback по basename достаёт любой из ~300 файлов в tests/), и для «AC-1: ✓ tests/../scripts/gate_ac_check.py::test_x» — обход через .. засчитывает ИСХОДНИК САМОГО ГЕЙТА как «тест, который существует». На NTFS сравнение ещё и регистронезависимо. Заявление о дороговизне подделки не выполняется; честный вывод ревью: гейт не строже прежнего, а иначе обходим.

(3) ЛОЖНОЕ УТВЕРЖДЕНИЕ В КОММЕНТАРИИ. Написано «Nothing reads a keyword list any more; if one reappears, it is deciding something it cannot know». Но checklist_missing засчитывает e.is_manual/e.is_review, а это регулярки MANUAL_RE=\\bmanual(?:ly)?\\b и REVIEW_RE=/review|review record|adversarial из service_ac_evidence. Проверено: notes «1. adversarial» → checklist_missing=False. Словарь сократился с ~28 слов до 4; механизм не изменился. Утверждение надо либо исполнить, либо снять — сейчас оно вводит в заблуждение ровно в том файле, который чинил введение в заблуждение.

## Acceptance Criteria

1. Корень резолвится от ПРОЕКТА, а не от cwd: используется существующий резолвер (project_config.find_tausik_dir / CLAUDE_PROJECT_DIR), а не os.getcwd(). Проверено тестом, который запускает предикат из подкаталога (monkeypatch.chdir) и получает ТОТ ЖЕ вердикт, что из корня. Тест обязан падать на текущем коде.
2. Обход через .. закрыт: путь цитаты нормализуется и обязан лежать ВНУТРИ каталога тестов проекта. Негатив-тест на «tests/../scripts/gate_ac_check.py» обязателен и обязан падать на текущем коде.
3. Имя теста после `::`, если оно указано, ПРОВЕРЯЕТСЯ в файле (наличие определения). Несуществующее имя не засчитывается. Негатив-тест на «tests/test_hooks.py::test_totally_made_up_9876».
4. Fallback по голому basename либо убирается, либо сужается так, что не даёт засчитать произвольный файл из tests/; решение обосновано в коде.
5. Ложное утверждение в комментарии про «nothing reads a keyword list» устранено ПО СУЩЕСТВУ: либо is_manual/is_review перестают влиять на вердикт, либо комментарий говорит правду о том, что advisory-уровень принимает четыре слова, и это названо явно. Молчаливое сохранение неверного текста недопустимо.
6. Docstring перестаёт утверждать «the only claim it cannot make cheaply». Вместо этого перечисляется, что именно проверяется и что НЕ проверяется (что тест реально исполнялся, что он относится к задаче) — как названный остаток.
7. Регресс не допущен: закрытия сессии #133 по-прежнему не получают предупреждения; сравнение до/после на реальной БД показывает, что число блокируемых закрытий не УМЕНЬШИЛОСЬ по сравнению с текущим состоянием.
8. pytest зелёный (полный прогон), verify с исполненным pytest, bootstrap --ide all, CHANGELOG×2 с признанием того, что предыдущая запись переоценивала строгость гейта.

## Plan

## Rollback

git revert. Откат возвращает гейт, который блокирует честную работу из подкаталога и принимает поддельные цитаты; поэтому откат допустим только вместе с откатом родительской задачи rule5-checklist-keyword-theater, либо с одновременным выставлением config task_done.checklist_hard=false, чтобы не осталась худшая комбинация «строгий на вид, дырявый по сути».

## Journal

- 2026-07-24T10:03:25Z [implementation] — AC-1: ✓ tested via tests/test_checklist_hardgate.py::TestChecklistHardBlock::test_verdict_does_not_depend_on_the_directory_the_command_ran_from — корень резолвится через CLAUDE_PROJECT_DIR/find_tausik_dir. Дифференциальный прогон прежней и новой реализации на одном наборе: честная цитата из корня True→True, честная цитата из подкаталога False→True. AC-2: ✓ tested via ::test_traversal_out_of_the_test_tree_does_not_clear_the_gate; дифференциально tests/../scripts/prod.py: True→False. AC-3: ✓ tested via ::test_invented_test_name_on_a_real_file_does_not_clear_the_gate; дифференциально выдуманное имя теста: True→False, при этом честное имя на том же файле остаётся False-block. AC-4: ✓ fallback по basename сужен — резолвится ТОЛЬКО внутри tests/, свободный файл из дерева больше не засчитывается; обоснование в докстринге. AC-5: ✓ ложное «nothing reads a keyword list any more» заменено на правду ПО СУЩЕСТВУ: advisory-уровень действительно принимает manual/manually//review/adversarial, это названо явно и объяснено, почему хард-гейт их не принимает. AC-6: ✓ снято «the only claim it cannot make cheaply»; вместо него перечислено, что НЕ устанавливается (что тест исполнялся, что прошёл, что относится к задаче) — как названный остаток. AC-7: ✓ регресса нет: на реальной БД число блокируемых закрытий выросло 27→33, ослабление ровно одно и то же (release-1-3-docs-sweep, проверено адресно ранее); все четыре закрытия сессии #133 по-прежнему без предупреждения. AC-8: ✓ полный pytest 5653 passed (после двух исправлений ниже), verify #1261 pytest исполнен, bootstrap --ide all, CHANGELOG×2 + docs/ru/agent-contract.md с признанием переоценки строгости. Negative: подделка именем, обходом .. и голым basename закреплены как блокирующие. Domain: осмысленно вне тестов — противник предиката это агент с правом записи в собственные notes, и после правки цена подделки перестала быть нулевой, но НЕ стала бесконечной (написать tests/test_x.py с def test_a(): pass по-прежнему проходит) — это записано в коде честно, а не выдано за доказательство.
- 2026-07-24T10:03:25Z [implementation] — Root cause (missing-validation): предикат доказательства проверял СУЩЕСТВОВАНИЕ ФАЙЛА и на этом останавливался, а докстринг описывал его как проверку ТЕСТА — три уровня разрыва между заявленным и реализованным (имя после :: не проверялось вовсе, нормализация пути не делалась, поэтому .. выводил за дерево тестов, а корень брался из cwd вместо проекта). Ошибка проектирования, а не кодирования: я вывел свойство «подделка дорога» из одного факта (файл резолвится), не перечислив, ЧТО ИМЕННО подделывается — имя, путь и каталог запуска были тремя независимыми степенями свободы у противника, и ни одна не была закрыта. Prevention: для любого предиката, который что-то УДОРОЖАЕТ для противника, обязателен явный список «что именно проверяется» против «что подделывается», и каждая строка второго списка либо закрыта, либо названа остатком в докстринге. Формулировки вида «единственное, что нельзя сделать дёшево» без такого перечисления в код не пишутся: они закрепляют непроверенную посылку в месте, где следующий читатель примет её за факт.
- 2026-07-24T10:03:25Z [implementation] — Две поправки, найденные СОБСТВЕННЫМ замером во время задачи, а не ревью: (1) первая версия проверки имени сравнивала весь хвост после :: с 'def <имя>' и потому ОТВЕРГАЛА штатный pytest node id 'file::Class::method' — поймано на реальных задачах БД (real_test_AC упал 1→0 у firewall-git-clean-alternation-unanchored). Теперь проверяется каждый сегмент как def ИЛИ class, и отдельно отрезается параметризация '[case]'; tested via ::test_pytest_class_qualified_node_id_is_accepted. (2) Фикстура tests/test_agent_units_recording.py цитировала '::test_records_actual' — имя, которого в файле НЕТ: я сам его выдумал в предыдущей задаче, когда проверки имени ещё не было. Ужесточённый гейт немедленно это поймал на полном прогоне; цитата заменена на реальный ::TestTaskDoneRecordsActual::test_writes_call_actual_from_events. Это лучшее из доступных доказательств, что проверка работает: она первой поймала фальшивую цитату, написанную мной.
- 2026-07-24T10:15:12Z [implementation] — Filesize-гейт отказался закрывать задачу (gate_ac_check.py 419/400) — шов найден настоящий, а не косметический: проверка цитаты вынесена в scripts/gate_test_citation.py (116 строк), gate_ac_check остался на 321. Разделены два разных вопроса: «есть ли у критерия доказательство» и «настоящая ли эта цитата» — и ВСЕ дефекты, найденные ревью, жили во втором. Попутно убраны ставшие ненужными импорты os и re. Плюс устранён DeprecationWarning (invalid escape sequence '\;' в докстринге rm_wipe_detect — префикс r). Полный pytest после выноса: 5655 passed, 23 skipped, 0 warnings по этому файлу.
