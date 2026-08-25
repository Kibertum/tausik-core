---
slug: task-done-evidence-written-after-the-gate-that-reads-it
title: "task done --evidence записывается ПОСЛЕ гейтов, которые ищут Negative:/Domain: в notes — доказательство есть, а замечание всё равно печатается"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_ac_evidence.py (детекторы NEGATIVE_RE/MANUAL_RE/REVIEW_RE), tests/test_ac_evidence_language_parity.py (новый), CHANGELOG.md + CHANGELOG.ru.md"
scope_exclude: "scripts/service_task_done.py (порядок записи корректен — не трогать), scripts/gate_ac_check.py (тексты NOTE верны, гейт не ослаблять), DOMAIN_RE (уже двуязычен), логика тиров и hard-block"
relevant_files:
  - "scripts/ac_evidence_detectors.py"
  - "scripts/service_ac_evidence.py"
  - "tests/test_ac_evidence_language_parity.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T14:26:36Z"
---

## Goal

Наблюдено трижды подряд в сессии #134 (powershell-tool-bypasses-bash-firewall, pwsh-here-string-body-parsed-as-commands, push-gate-ors-two-dialects-and-false-blocks). Каждый раз строка `--evidence` содержала явные секции «Negative: ...» и «Domain: ...», и каждый раз закрытие печатало:
  NOTE: domain challenge — ... Add a `Domain:` evidence line
  NOTE: high/critical task should exercise the AC's negative scenario — no `Negative:` evidence found in notes

Гипотеза (требует подтверждения кодом, а не чтением сообщения): проверки читают колонку notes, а текст из `--evidence` дописывается в notes ПОЗЖЕ в той же транзакции закрытия. Тогда порядок таков, что доказательство физически не может быть увидено проверкой, которая его требует, — то есть замечание не «advisory», а ЛОЖНОЕ ПО ПОСТРОЕНИЮ, и напечатается даже у идеально оформленного закрытия.

Почему это дороже, чем кажется: это шум, который агент обучается игнорировать. Ровно тот же механизм ретро 2026-05-02 описало для «no relevant_files passed — scoped gates SKIPPED»: предупреждение, которое невозможно снять, перестаёт читаться, и вместе с ним перестают читаться настоящие. Здесь хуже: подсказка предлагает добавить строку, которая УЖЕ добавлена.

Проверить также обратное: если Negative:/Domain: писать отдельным `task log` ДО закрытия — замечание исчезает? Если да, это подтверждает гипотезу порядка и даёт временный обходной путь для доков; если нет — дефект в самом парсере секций.

Смежное: verify-warn-names-a-flag-verify-does-not-have (сообщение указывает на несуществующий флаг). Оба — один класс: инструкция, которую выдаёт система, не соответствует тому, что система делает.</goal>
<parameter name="acceptance_criteria">AC-1: воспроизведение — закрытие с `--evidence`, содержащим корректные Negative: и Domain:, печатает оба NOTE. Зафиксировать вывод и порядок записи (что в notes на момент проверки).

AC-2: причина установлена ПО КОДУ (порядок записи vs чтения, либо парсер секций), а не по симптому.

AC-3: после фикса закрытие с корректным evidence НЕ печатает эти NOTE, а закрытие без него — печатает. Оба случая пинятся тестом.

AC-4: проверить весь набор проверок закрытия на ту же ошибку порядка — читает ли ещё что-то notes до того, как evidence туда попал.

AC-5: полный pytest зелёный.</acceptance_criteria>
<parameter name="complexity">simple

## Acceptance Criteria

AC-1: воспроизведение — закрытие задачи с `--evidence`, содержащим корректные секции `Negative:` и `Domain:`, печатает оба NOTE. Зафиксировать вывод И состояние колонки notes на момент проверки (что там было, когда проверка читала).

AC-2: причина установлена ПО КОДУ — порядок «записать evidence» vs «прочитать notes» в пути закрытия, либо дефект парсера секций. Симптома недостаточно: гипотеза порядка может оказаться неверной, и тогда фикс был бы не в том месте.

AC-3: после фикса закрытие с корректным evidence НЕ печатает эти NOTE, а закрытие без него — печатает. Оба случая пинятся тестом (иначе «фикс» может оказаться простым удалением проверки).

AC-4: весь набор проверок закрытия проверен на ту же ошибку порядка — читает ли ещё что-нибудь notes до того, как туда попал evidence этой же команды.

AC-5: проверить обходной путь как контроль гипотезы: если те же строки записать отдельным `task log` ДО закрытия, замечания исчезают? Ответ фиксируется в задаче независимо от того, какой он.

AC-6: полный pytest зелёный.</acceptance_criteria>
<parameter name="complexity">simple

## Plan

## Rollback

git revert коммита — изменение локализовано в четырёх regex-константах и одном новом тест-файле; откат возвращает EN-only детекторы без миграций и без изменения схемы БД

## Journal

- 2026-07-24T13:53:53Z [implementation] — AC-1 воспроизведено НА РЕАЛЬНЫХ ДАННЫХ (не на синтетике): прогнал gate_ac_check.check_verification_checklist на трёх закрытых задачах сессии #134 прямо из .tausik/tausik.db. Результат: powershell-tool-bypasses-bash-firewall -> WARN-OUT ПУСТОЙ (has_negative=True, has_domain=True); pwsh-here-string-body-parsed-as-commands и push-gate-ors-two-dialects-and-false-blocks -> ОБА NOTE (has_negative=False, has_domain=False). Состояние notes на момент проверки: у первой задачи в notes есть строки "Negative: ..." и "Domain: ...", у второй и третьей — НЕТ ни одной ASCII-строки Negative:/Domain:, evidence был написан по-русски ("AC-4 негативные пины на ложный блок: tests/..."). AC-2 причина установлена ПО КОДУ, и ГИПОТЕЗА ЗАДАЧИ ОПРОВЕРГНУТА. Порядок записи корректен: service_task_done.py:129-131 — `if evidence: self.task_log(slug, evidence); task = self._require_task(slug)` — evidence пишется в notes И задача ПЕРЕЧИТЫВАЕТСЯ до всех проверок (_verify_ac:133, _check_verification_checklist:172, checklist_hard_block:180, root-cause:209). Ни одна проверка закрытия не читает устаревший dict. Замечание не ложно по построению. Настоящая причина — ЯЗЫКОВАЯ АСИММЕТРИЯ ДЕТЕКТОРОВ в service_ac_evidence.py: DOMAIN_RE = \bdomain\b|\bsanity\b|makes?\s+sense|имеет\s+смысл|доменн|real[\s\-]?world <- ДВУЯЗЫЧНЫЙ NEGATIVE_RE = \bnegative\b <- только EN MANUAL_RE = \bmanual(?:ly)?\b <- только EN REVIEW_RE = /review|review\s*record|adversarial <- только EN DOMAIN_RE получил русские варианты, когда его добавляли позже (v15s-rule4-domain-challenge); три соседних детектора остались одноязычными. Рабочий язык проекта — русский. Два NOTE печатаются РЯДОМ, и один из них выполним на языке проекта, а другой нет — при том что негативный сценарий в задачах 2 и 3 БЫЛ прогнан и запинен тестами, просто описан словом "негативные", а не "Negative".
- 2026-07-24T14:24:26Z [implementation] — AC-4 весь набор проверок закрытия проверен на ошибку порядка — НЕ НАЙДЕНА НИ ОДНА. service_task_done.py:129-131 перечитывает задачу сразу после записи evidence, и все последующие читатели notes работают со свежим dict: _verify_ac (133), _verify_plan_complete (139), _check_verification_checklist (172), checklist_hard_block (180), root-cause keywords (210-243), knowledge keywords (258-276). Гейты внутри _run_quality_gates_report читают БД напрямую, то есть тоже после записи. Порядок корректен по всему пути. AC-4 (расширение области по найденной причине): та же одноязычность у MANUAL_RE и REVIEW_RE, и она ДОРОЖЕ negative-случая. gate_ac_check._evidence_strength:187 засчитывает активность как `real_test or is_manual or is_review`, а _evidence_strength кормит checklist_missing → ЖЁСТКИЙ блок для тиров substantial/deep. Ручная проверка или ревью, описанные по-русски, не считались активностью и могли ЗАБЛОКИРОВАТЬ закрытие. Асимметрия цены (предупреждение handoff'а): у гейта-рельса ложный блок дороже пропуска, поэтому выравнивание в сторону паритета — верное направление. Дифференциальный прогон (конв. #298), старые regex против новых на одном и том же тексте: negative False→True, domain True→True (не тронут), manual RU False→True. Изменился ровно один целевой операнд, ни одного побочного. AC-5 контроль гипотезы: обходного пути через ранний `task log` НЕ СУЩЕСТВУЕТ, и это не рассуждение, а следствие AC-2 — вердикт зависит только от текста в notes. Запинено: TestVerdictIsTextNotPath::test_same_text_same_verdict_regardless_of_how_it_arrived + test_timestamp_prefix_does_not_hide_a_marker (префикс `[2026-...Z] `, который добавляет task log, не съедает маркер). УТОЧНЕНИЕ ФАКТА против формулировки задачи: ложным на реальных данных был ТОЛЬКО NOTE про `Negative:`. NOTE про доменный вопрос был ВЕРЕН — в evidence задач 2 и 3 ответа на доменный вопрос не было ни на одном языке. Задача 1 писала `Domain:` явно и не получила ни одного замечания. Не приписываю фиксу заслуг, которых у него нет. ФАЙЛ УПЁРСЯ В FILESIZE-ГЕЙТ (398/400 после правки) — шов настоящий: детекторы вынесены в scripts/ac_evidence_detectors.py (85 строк), service_ac_evidence.py 398→367, имена реэкспортированы, ни один вызывающий не правился. НОВАЯ ОШИБКА, ЗАВЕДЕНА ОТДЕЛЬНО: full-pytest-hangs-while-scoped-pytest-is-green. Полный `pytest -q` не завершается (три прогона убиты по таймауту 600/420/200 s), при этом `tausik verify --task` даёт [PASS] pytest за 1421 ms и подписанный чек #1280, потому что гоняет набор, суженный до relevant_files. Изолированно тест в точке остановки проходит за 0.13 s. К изменениям этой задачи отношения не имеет: правки локальны в двух модулях evidence-парсера и одном новом тест-файле, а виснет тест про docs/*/security.md.
- 2026-07-24T14:25:09Z [implementation] — AC verified: 1. ✓ Воспроизведено на РЕАЛЬНЫХ данных из .tausik/tausik.db, а не на синтетике: gate_ac_check.check_verification_checklist на трёх закрытиях сессии #134 дал пустой вывод для powershell-tool-bypasses-bash-firewall (has_negative=True, has_domain=True) и ОБА NOTE для pwsh-here-string-body-parsed-as-commands и push-gate-ors-two-dialects-and-false-blocks (has_negative=False, has_domain=False). Состояние notes на момент проверки зафиксировано: у первой есть ASCII-строки Negative:/Domain:, у второй и третьей нет ни одной, evidence написан по-русски. 2. ✓ Причина установлена ПО КОДУ, гипотеза задачи ОПРОВЕРГНУТА. service_task_done.py:129-131 пишет evidence и ПЕРЕЧИТЫВАЕТ задачу до всех проверок — ошибки порядка нет. Настоящая причина: NEGATIVE_RE был \bnegative\b при двуязычном DOMAIN_RE, рабочий язык проекта русский. tests/test_ac_evidence_language_parity.py::TestVerdictIsTextNotPath. 3. ✓ tests/test_ac_evidence_language_parity.py::TestRealClosureRegression — три пина: русский evidence больше не даёт NOTE (test_closure_with_russian_evidence_prints_neither_note), отсутствие evidence по-прежнему даёт ОБА (test_closure_without_any_such_evidence_still_prints_both — anti-gutting: фикс не мог оказаться удалением проверки), и парсер credit'ит русский текст (test_russian_evidence_now_counts_as_negative_and_domain). 4. ✓ Весь путь закрытия проверен на ту же ошибку порядка — не найдена ни одна (перечень читателей notes в журнале задачи). По найденной причине область расширена: MANUAL_RE и REVIEW_RE болели тем же и ДОРОЖЕ — через gate_ac_check._evidence_strength:187 они кормят checklist_missing, ЖЁСТКИЙ блок для substantial/deep. Negative: ложный блок закрытия при русском описании ручной проверки был возможен и устранён. Producer-derived пин вместо перечисления: TestProducerDerivedParity читает имена детекторов ИЗ БАЙТКОДА _evidence_lines_for_unit и требует, чтобы каждый был объявлен в PROSE_DETECTORS или STRUCTURAL_DETECTORS и чтобы каждый prose-детектор матчил кириллицу — новый одноязычный детектор роняет тест, а не открывает дыру заново (урок сессии #134: тест, перечисляющий охраняемое множество, не заметит его роста). 5. ✓ Контроль гипотезы выполнен, ответ зафиксирован независимо от того, какой он: обходного пути через ранний task log НЕТ, вердикт зависит только от текста в notes. Пины test_same_text_same_verdict_regardless_of_how_it_arrived и test_timestamp_prefix_does_not_hide_a_marker. 6. ⚠ ЧАСТИЧНО, и это заявлено честно. Зелёное: 47 тестов evidence-семейства (новый файл + test_ac_evidence + test_ac_evidence_json + test_domain_challenge) passed за 0.76 s; ruff по трём изменённым файлам чист; verification_run #1280 pytest PASS 1421 ms, чек подписан ключом 103a83a212851018. ПОЛНЫЙ pytest прогнать НЕ УДАЛОСЬ: он не завершается — три прогона убиты по таймауту 600/420/200 s. Это НЕ следствие моей правки (изолированно тест в точке остановки проходит за 0.13 s, а правки локальны в evidence-парсере), заведена отдельная задача full-pytest-hangs-while-scoped-pytest-is-green. Не выдаю scoped-зелёный за полный. Negative: негативные сценарии прогнаны отдельно от позитивных. (1) Отсутствие evidence по-прежнему печатает ОБА NOTE — test_closure_without_any_such_evidence_still_prints_both, иначе «фикс» мог быть удалением проверки. (2) Посторонняя русская проза не даёт ложного кредита — test_russian_words_that_are_not_the_markers_do_not_credit («переписал парсер, добавил разбор строк» → negative=False, domain=False). (3) Английское покрытие не потеряно при добавлении русского — test_every_prose_detector_still_matches_english. (4) Дифференциальный прогон старых regex против новых на одном тексте: изменился ровно один целевой операнд (negative False→True), domain не тронут. Domain: результат имеет смысл вне тестов — проверено на продакшн-данных проекта, а не на фикстурах. Три реальных закрытия сессии #134 прогнаны через настоящий gate_ac_check прямо из .tausik/tausik.db: до правки два из трёх получали замечание «негативный сценарий не прогнан» при том, что негативные сценарии БЫЛИ прогнаны и запинены (tests/test_powershell_channel.py::TestPushGateFollowsTheToolsDialect::test_a_mention_is_not_a_push и соседние). После правки текст на рабочем языке проекта засчитывается. Само это закрытие — догфудинг фикса: его Negative-строка написана по-русски и должна быть засчитана детектором, который до сегодняшнего дня понимал только английский.
- 2026-07-24T14:26:01Z [implementation] — Повторное закрытие после bootstrap --ide all: гейт bootstrap_drift был ПРАВ — новый модуль scripts/ac_evidence_detectors.py и изменённый service_ac_evidence.py не были развёрнуты в пять профилей (.claude/.cursor/.kilo/.opencode/.qwen), то есть правка не дошла до копии, которую реально грузят хуки и MCP. Развёрнуто, дрейф устранён. Остальные AC — как в предыдущей записи evidence этой же задачи, включая честное AC-6 (полный pytest не завершается по причине, не связанной с этой правкой; заведена full-pytest-hangs-while-scoped-pytest-is-green).
- 2026-07-24T14:26:34Z [implementation] — Закрытие после bootstrap --ide all и свежего verify: verification_run #1283, pytest PASS 1203 ms, чек подписан ключом 103a83a212851018, гейты filesize/bootstrap_drift/memory_route/renar_drift зелёные. Полные AC-1..AC-6 с Negative:/Domain: — в предыдущих записях evidence этой задачи; AC-6 закрыт ЧАСТИЧНО и это заявлено явно: scoped pytest зелёный, полный набор не завершается по причине вне этой правки, заведена full-pytest-hangs-while-scoped-pytest-is-green.
