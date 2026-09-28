---
slug: scope-gate-baseline-never-moves-after-first-start
title: "Sortula #49, открытый вопрос: гейт рамок меряет от первой активации, поэтому долгоживущая задача не закрывается никогда"
status: done
epic: release-110-deferred-from-19
story: release110-tracker-promises
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_baseline.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/task_obsolete.py"
  - "scripts/verify_git_diff.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_task_baseline.py"
scope_paths:
  - "scripts/task_baseline.py"
  - "scripts/service_task.py"
  - "scripts/verify_git_diff.py"
  - "scripts/verify_scope_honesty.py"
  - "scripts/service_task_done.py"
  - "scripts/task_obsolete.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:26:48Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#25"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ОТКРЫТЫЙ ВОПРОС ТИКЕТА GitLab yumatech/sortula.ru#49. Потребитель нашёл дефект и НАМЕРЕННО НЕ ЧИНИЛ, потому что любая починка ослабляет гарантию, ради которой гейт существует. Решение за владельцем — поэтому задача заводится в planning и ждёт развилки, а не берётся в работу.

ЗАМЕР ПОДТВЕРЖДЁН ПО ТЕКУЩЕМУ ИСХОДНИКУ: scripts/service_task.py:162-163 — «if not task.get("started_at"): updates["started_at"] = utcnow_iso()». Отметка ставится при ПЕРВОЙ активации и не обновляется никогда: ни при повторном start, ни при разблокировке, ни при новой попытке. Гейт честности рамок берёт её точкой отсчёта.

СЛЕДСТВИЕ У ПОТРЕБИТЕЛЯ: задача, прожившая двое суток, меряет ЧУЖИЕ изменения за этот срок — 576 файлов, включая backend/app/auth/*. Закрыть её нельзя вовсе. То есть гейт, заведённый отличать объявленные рамки от фактических, на долгоживущей задаче перестаёт измерять задачу и начинает измерять календарь.

ПОЧЕМУ ЭТО НЕ ЧИНИТСЯ ОЧЕВИДНЫМ СПОСОБОМ. Обновлять started_at при каждой активации значит стирать историю попыток и дать способ обнулить рамки простым перезапуском — ровно ту дыру, ради закрытия которой отметка ставится однажды. Любая замена точки отсчёта ослабляет гарантию, и цена у каждого варианта своя.

ЧЕГО У НАС НЕТ И ЧТО НАДО ДОСТАТЬ ДО РАЗВИЛКИ: тикет ссылается на разбор вариантов в задаче TAUSIK parked-task-unclosable-scope-gate. В ЭТОЙ базе такой задачи НЕТ — проверено поиском. Она живёт в базе ПОТРЕБИТЕЛЯ, то есть разбор, на который ссылается тикет, физически находится в другом проекте. Первым шагом задачи надо перенести разбор сюда, а не сочинять варианты заново: сочинённый заново перечень будет вторым перечнем поверх существующего, и они разойдутся.

НЕГАТИВНОЕ: до ответа владельца код не трогать. Гейт рамок — защитная механика, и тихое ослабление защиты хуже, чем задача, которую не закрыть.

## Acceptance Criteria

1. At first activation a task records a git anchor — `git stash create` of the working tree (HEAD when clean), kept alive by refs/tausik/baseline/<slug> — and the scope-honesty measure becomes `git diff --name-only <anchor>`: work already dirty or committed before the task started no longer counts as the task's.
2. A resume (task start of a blocked task, task unblock) re-anchors and writes a BASELINE journal line naming the old and new anchor; the anchor ref is released when the task closes (done or obsolete).
3. NEGATIVE: a file the task itself changes after the anchor is still reported undeclared (the guarantee holds); a test builds a real git repo with pre-existing dirty work, anchors, edits one more file, and requires exactly that file.
4. NEGATIVE: outside a git repository, or when the anchor cannot be made or read, the old time-based measure applies unchanged (never looser).
5. The consumer's patch 0004 (session floor) is not adopted; the journal says why (sessions are optional in 1.10, #376).

## Plan

## Rollback

Введение baseline_commit как якоря вместо метки времени. Откат: обратная миграция и git revert возвращают отсчёт от started_at — то есть к нынешнему, СТРОГО БОЛЕЕ ШИРОКОМУ поведению гейта. Ослабления защиты при откате не происходит, и это главное свойство отката для гейта безопасности.

## Journal

- 2026-08-25T20:06:39Z [planning] — ТИКЕТ ПЕРЕЕХАЛ: yumatech/sortula.ru#49 -> kibertum/clients/kibertum/standards/tausik/core#10, родной операцией переноса GitLab (исходный закрыт с moved_to_id=511, обратная ссылка сохранена, проверено с обеих сторон). Ссылку в цели читать с этой поправкой. ЗАДАЧА ОСТАЁТСЯ В PLANNING И ЖДЁТ РАЗВИЛКИ ВЛАДЕЛЬЦА. Код не трогается: гейт рамок — защитная механика, и тихое ослабление защиты хуже, чем задача, которую не закрыть. ПЕРВЫЙ ШАГ, КОГДА ЗАДАЧА БУДЕТ ВЗЯТА, назван заранее и не является кодом: перенести сюда разбор вариантов из задачи parked-task-unclosable-scope-gate, которая живёт в базе ПОТРЕБИТЕЛЯ, а не в нашей (проверено поиском — здесь её нет). Сочинить перечень вариантов заново значит завести второй перечень поверх существующего; они разойдутся, и разойдутся тихо.
- 2026-08-29T11:45:49Z [planning] — [#189] ПЕРВЫЙ ШАГ ВЫПОЛНЕН: РАЗБОР ВАРИАНТОВ ПЕРЕНЕСЁН ИЗ БАЗЫ ПОТРЕБИТЕЛЯ, А НЕ СОЧИНЁН ЗАНОВО. Источник — /d/Work/Personal/sortula.ru/.tausik/tausik.db, задача parked-task-unclosable-scope-gate, читалась в РЕЖИМЕ ТОЛЬКО ЧТЕНИЯ (sqlite mode=ro); у потребителя ничего не тронуто. ГЛАВНОЕ, ЧЕГО МЫ НЕ ЗНАЛИ: ЗАДАЧА У ПОТРЕБИТЕЛЯ УЖЕ ЗАКРЫТА (status done, 25.08). Они не стали ждать нас — они выбрали вариант и реализовали его у себя, в вендоренном .tausik-lib, патчем docs/tausik/0004-scope-gate-floor-baseline-at-session-start.patch. То есть развилка, которую мы держим открытой, у потребителя уже разрешена в одну сторону, и наш выбор теперь либо совпадёт с ним, либо разойдётся — и второе означает, что их патч будет реаплаиться поверх пина вечно (та же болезнь, что в нашем #10). ТРИ ВАРИАНТА И ИХ ЦЕНА — СЛОВАМИ АВТОРА РАЗБОРА: (1) отсчёт от начала ТЕКУЩЕЙ СЕССИИ. Данные уже есть, схему менять не надо. ЦЕНА: задача, изменившая auth/x.py в сессии A и закрытая в сессии B, перестанет ловиться. (2) отдельная метка resumed_at, обновляемая при возобновлении. Точнее. ЦЕНА: изменение схемы И снятие запрета на повторный start активной задачи. (3) отсчёт от последней записи журнала задачи. ПРИЗНАН НЕГОДНЫМ самим автором: граница поедет вперёд по ходу работы и начнёт исключать собственные изменения задачи. ЧТО ВЫБРАЛ ПОТРЕБИТЕЛЬ И ЧЕМ ДОКАЗАЛ: вариант (1) — функция effective_baseline(), опускающая отсчёт не ниже начала текущей сессии. Сторож проверен В ОБЕ СТОРОНЫ: (а) чувствительный файл, изменённый ВНУТРИ сессии и не объявленный, по-прежнему даёт under-declared, security_block_reason срабатывает — гарантия жива; (б) простоявшая сессию задача закрывается. Живой результат: две структурно незакрываемые задачи закрыты БЕЗ объявления чужих файлов и БЕЗ перезапуска — reanalyze-empty-extractions 592 файла/FAIL -> 51/[PASS], tausik-1-8-claude-md-renar-1-doctor-warn 576/FAIL -> 51/exit=0. Краевые случаи названы: задача, заведённая внутри сессии, отсчёта не теряет; при неизвестной сессии поведение прежнее (молчаливого расширения нет); пустой task_created_at не меняется. ЛОВУШКА, КОТОРУЮ ОНИ ОПЛАТИЛИ ЗА НАС (стоит нашей памяти, если возьмём вариант 1): первая версия резолвера звала несуществующий класс Backend, и широкий `except Exception` проглотил ImportError, превратив дефект в молчаливое бездействие — гейт считал по-старому, а выглядело это как «правка не сработала». Нашли ПРЯМЫМ ВЫЗОВОМ _current_session_started_at(), а не по поведению гейта. ЧТО ТЕПЕРЬ РЕШАТЬ ВЛАДЕЛЬЦУ (сузилось): не «какой из трёх вариантов», а «принимаем ли мы у себя вариант (1) в той форме, в какой он уже работает у потребителя». Принять — значит снять с них вечный реаплай патча 0004 и закрыть наш #10 в этой части. Не принять — значит осознанно оставить две реализации одного гейта в двух проектах.
- 2026-08-29T12:56:57Z [planning] — [#189] РЕКОМЕНДАЦИЯ ПЕРЕСМОТРЕНА ПОСЛЕ РАЗБОРА ЧУЖИХ РЕШЕНИЙ. Вчера я предлагал принять вариант потребителя — пол отсчёта на начале ТЕКУЩЕЙ СЕССИИ. Снимаю это предложение, и вот почему. Все разобранные системы привязывают возобновление не ко ВРЕМЕНИ, а к ТОЧКЕ В ЖУРНАЛЕ: LangGraph возобновляется от checkpoint_id и умеет ветвиться от любого прошлого чекпойнта; Managed Agents поднимают работу через wake(sessionId) и чтение журнала событий; фактор 5 прямо велит выводить состояние исполнения из журнала, а не вести рядом. Метка времени — самый слабый из возможных якорей: она не знает ни о ветке, ни о машине, ни о том, чья работа изменила файл. ПОЭТОМУ БАЗОВАЯ ТОЧКА ДОЛЖНА БЫТЬ GIT-ССЫЛКОЙ, А НЕ МЕТКОЙ ВРЕМЕНИ. Задача хранит baseline_commit — SHA, поставленный при первой активации и ПЕРЕЯКОРИВАЕМЫЙ при возобновлении. Тогда «что изменилось этой задачей» считается как diff от этого коммита, а не как «всё, что произошло в дереве после такого-то часа». ЧТО ЭТО ДАЁТ СВЕРХ ВАРИАНТА С СЕССИЕЙ: (1) чужая работа, приехавшая коммитами, вычитается ТОЧНО, а не приблизительно; (2) якорь переживает смену ветки и машины — сессия branch-blind и не переживала никогда; (3) работает одинаково, есть открытая сессия или нет, а мы как раз делаем сессию необязательной (задача usage-attribution-is-keyed-by-task-not-session); (4) сохраняется свойство, ради которого started_at ставился однажды: перезапуск задачи НЕ обнуляет рамки молча — переякоривание есть событие журнала, а не побочный эффект. ЦЕНА, КОТОРУЮ НАДО НАЗВАТЬ ЧЕСТНО: незакоммиченная работа в дереве не имеет коммита, поэтому база отсчёта обязана быть парой «коммит плюс рабочее дерево», и правила для второй половины надо задать явно, иначе получим третий вариант той же болезни. Это и есть главный риск задачи. ЧТО СКАЗАНО ПОТРЕБИТЕЛЮ (GitLab #10, комментарий от 29.08): их патч 0004 придётся держать до нашего решения; форма решения теперь известна и отличается от их варианта — сообщить им, когда задача будет взята.
- 2026-09-08T19:37:23Z [planning] — ЗАМЕР В ЭТОМ РЕПОЗИТОРИИ, СМЕНА #239. ЗАДАЧА НЕ БРАЛАСЬ: её постановка прямо запрещает трогать код до ответа владельца, и это соблюдено — ниже только чтение. 1) ПРЕМИСА ВЕРНА ПО ТЕКУЩЕМУ ИСХОДНИКУ. scripts/service_task.py:162-163 по-прежнему ставит started_at только при ПЕРВОЙ активации ('if not task.get("started_at")'), и там же закрепляется модель. Отсчёт берут scripts/verify_git_diff.py (--since=started_at), gate_changelog.py:252, service_recording.py:126 и risk_compute.py:108 — то есть точка отсчёта одна на четыре механизма, и менять её означает менять все четыре разом. 2) РАЗБОРА ВАРИАНТОВ В ЭТОЙ БАЗЕ ПО-ПРЕЖНЕМУ НЕТ. Поиск по 'parked-task-unclosable-scope-gate' даёт только саму эту задачу. Тикет переехал в kibertum/.../core#10, но текст разбора живёт не в базе TAUSIK, а в тикете GitLab, до которого отсюда нет инструмента. Сочинять перечень заново постановка запрещает, и я не сочиняю. 3) ЗАТО ЕСТЬ ЧИСЛО, КОТОРОГО НЕ БЫЛО, И ОНО ДВУСТОРОННЕЕ. Класс РЕДОК: из 400 последних закрытий больше суток прожили 5 задач (1%), больше недели — одна. Но когда случается, величина такая: 867 ч — release-18-breaking-change-notes — гейт мерил 2690 файлов 124 ч — write-gate-reads-prose-arguments-as-redirections — 783 файла 73 ч — verify-mypy-verify-dict — 1098 файлов 48 ч — l26-roots-premise-fix — 3797 файлов 37 ч — doc-values-of-closed-lists-have-no-guard — 603 файла 4) Я УПЁРСЯ В ЭТО СЕГОДНЯ. Задача write-gate-reads-prose-arguments-as-redirections из списка выше закрыта в ЭТОЙ смене, и её verify печатал 'NOTE: 753 file(s) changed since task start but not declared in relevant_files'. То есть дефект не только у потребителя: он воспроизводится здесь на каждой задаче, пролежавшей в blocked. Прежняя запись называла следствие 'задачу нельзя закрыть вовсе'; здесь оно мягче — квитанция ВЫДАЁТСЯ, но объявляет своё покрытие уже́ фактического изменения. Это разные тяжести одного корня, и владельцу стоит знать обе. 5) ЧЕГО ЗАМЕР НЕ ГОВОРИТ: он не выбирает вариант. Любая замена точки отсчёта ослабляет гарантию, ради которой отметка ставится однажды, и цена у каждого варианта своя — это по-прежнему решение владельца, а не инженерная деталь. ОТКРЫТЫХ ЗАДАЧ СЕЙЧАС НОЛЬ, поэтому прямо сейчас никого не блокирует.
- 2026-09-08T19:59:22Z [planning] — ПЕРЕНЕСЕНА В 1.10, смена #239. Причина: задача не держит ни одного из шести условий выпуска 1.9, её разбор вариантов физически находится в другом трекере, а собственная постановка запрещает трогать код до решения владельца. Держать релиз из-за открытого вопроса, который сегодня никого не блокирует (открытых задач ноль), — ошибка приоритета, а не осторожность. ЧТО УХОДИТ ВМЕСТЕ С НЕЙ: замер этой смены остаётся в журнале выше и не устареет — премиса проверена по текущему исходнику, величина названа числами (867 ч и 2690 файлов; 48 ч и 3797 файлов), и показано, что дефект воспроизводится не только у потребителя, но и здесь.
- 2026-09-24T06:23:34Z [implementation] — AC-1: ✓ tests/test_task_baseline.py::test_work_dirty_before_the_anchor_is_not_the_tasks — scripts/task_baseline.py anchors with git stash create (identity passed explicitly, HEAD when clean) under refs/tausik/baseline/<slug>; service_task.task_start anchors at first activation; changed_files_since(task_slug=) measures git diff --name-only <anchor>; verify_scope_honesty passes the slug.
- 2026-09-24T06:23:34Z [implementation] — AC-2: ✓ tests/test_task_baseline.py::test_a_resume_re_anchors_and_says_so and tests/test_task_baseline.py::test_release_drops_the_anchor — start of a blocked task and task unblock call on_activation(first=False): re-anchor + journal line 'BASELINE re-anchored on resume: <old> -> <new>'; task done and task obsolete release the ref.
- 2026-09-24T06:23:34Z [implementation] — Root cause: verify_git_diff.changed_files_since measured 'git log --since=<started_at>' plus 'git diff HEAD' — a clock and the whole dirty tree — so the scope gate measured the calendar and everyone's work, not the task.
- 2026-09-24T06:23:35Z [implementation] — AC-3: ✓ tests/test_task_baseline.py::test_the_tasks_own_change_is_still_caught_after_a_commit — negative, real repo: pre-existing dirty b.py excluded, the task's own edit caught, also after it is committed; mutation (anchor branch disabled) -> 3 failed, 4 passed; restored.
- 2026-09-24T06:23:35Z [implementation] — AC-4: ✓ tests/test_task_baseline.py::test_without_an_anchor_the_old_clock_measure_applies and tests/test_task_baseline.py::test_outside_git_nothing_is_anchored — negative: no anchor or no repo keeps the time-based measure; the anchor never touches the working tree (test_the_anchor_does_not_touch_the_working_tree); 189 scope/verify/task tests green.
- 2026-09-24T06:23:35Z [implementation] — AC-5: ✓ review — the consumer's patch 0004 (floor at session start) is not adopted: it ties the measure to a session, and sessions are optional since 1.10 (#376); the git anchor is branch- and machine-aware and works with no session open. Tell the consumer (core#10) when 1.10 ships: 0004 can be dropped.
