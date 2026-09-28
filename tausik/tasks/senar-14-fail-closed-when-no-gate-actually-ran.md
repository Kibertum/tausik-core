---
slug: senar-14-fail-closed-when-no-gate-actually-ran
title: "Ноль выполненных гейтов даёт положительный вердикт — это не fail-closed"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: complex
role: backend
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: "НЕ трогаем: реализацию самих гейтов (gate_filesize, gate_changelog и прочие) — предмет задачи вердикт О ПРОГОНЕ, а не проверки; тип GateOutcome и его четыре состояния (уже введены задачей check-result-conflates-could-not-run-with-passed, здесь только ЧИТАЮТСЯ); схему таблицы gate_runs; путь кэша verify (cache HIT отдаёт прежний вердикт прежнего прогона); MCP-инструменты сверх параметра task_done; счётчики числа инструментов — новых инструментов не появляется."
relevant_files:
  - "scripts/verify_zero_gate.py"
  - "scripts/verify_handle_check.py"
  - "scripts/verify_handle.py"
  - "scripts/verify_cache.py"
  - "scripts/verify_recent_lookup.py"
  - "scripts/verify_no_test_mapped.py"
  - "scripts/project_cli_verify.py"
  - "scripts/gate_verify_first.py"
  - "scripts/gate_post_scope.py"
  - "scripts/service_gates.py"
  - "scripts/service_task_done.py"
  - "scripts/service_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "tests/test_zero_gate_verdict.py"
  - "tests/test_cli_verify_guards.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-04T11:21:30Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Отсутствие отрицательной находки перестаёт быть положительным вердиктом. Это §8.6(e) SENAR 1.4 — SHALL на всех конфигурациях, и стандарт особо оговаривает, что это свойство НЕ ослабляется ни на одной из них.

## Acceptance Criteria

AC1. ВОСПРОИЗВЕДЕНИЕ ЖИВОЕ, из сессии #177: verify --task <slug> --no-tests-expected напечатал 'no gate actually executed' и при этом записал прогон с exit=0 и выдал handle, которым задача была закрыта. Ни один гейт не выполнялся. Это буквально то, что §8.6(e) запрещает: отсутствие отрицательной находки принято за положительный вердикт.
AC2. ЧЕСТНОСТЬ ПОМЕТКИ НЕ ЯВЛЯЕТСЯ ИСПОЛНЕНИЕМ ТРЕБОВАНИЯ. Мы записываем no_tests_declared=1 и печатаем, что закрытие опирается на заявление, а не на проверку. Это лучше молчания, но §8.6(e) — свойство ВЕРДИКТА, а не сопроводительного текста. Задача обязана решить именно вердикт.
AC3. РЕШЕНИЕ НЕ ИМЕЕТ ПРАВА СВЕСТИСЬ К ЗАПРЕТУ. Есть законные случаи, когда гейтам нечего проверять: задача-исследование, задача-документ, задача без правок в коде. Нужен путь, при котором такой случай закрывается ЯВНО объявленным исключением с записью, а не молчаливым положительным вердиктом.
AC4. Разобрать заодно --no-file-changes: там гейт filesize пропускается по конструкции (skip_on_fileless_close). Проверить, не даёт ли этот путь такой же пустой положительный вердикт.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест обязан ПОКРАСНЕТЬ на текущем поведении до правки — прогон с нулём выполненных гейтов не должен давать пригодный к закрытию handle.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ: гейт, который был ПРОПУЩЕН по своей области (hadolint без Dockerfile), и гейт, который УПАЛ, не должны схлопываться в одно состояние. Пропуск по неприменимости — законен, ноль выполненных при наличии применимых — нет.

## Plan

## Rollback

git revert: закрытие с нулём гейтов снова даёт положительный вердикт

## Journal

- 2026-09-04T11:19:26Z [implementation] — ИНВЕНТАРЬ ДО ОЦЕНКИ, ПО ВЫЗОВУ И ПО КЛАССУ. Носители: verify_zero_gate.py (новый, понятие), verify_handle_check.py (477 -> 496, у предела: пришлось ВЫНЕСТИ туда же родственное понятие noncacheable), verify_handle.py (колонка в загрузчике строки), verify_cache.py (вторая дверь), verify_recent_lookup.py (колонка в SELECT), verify_no_test_mapped.py (ветка AC6), project_cli_verify.py (текст вердикта), gate_verify_first.py, gate_post_scope.py (единая форма вызова), service_gates.py (три подписи), service_task_done.py, service_task.py, project_cli_task.py, project_parser_task.py (флаг), harness MCP tools.py + handlers_task.py, два файла тестов, docs x2, CHANGELOG x2. 19 несущих -> сложность ПЕРЕОЦЕНЕНА medium -> complex ДО старта. ЗАМЕР ПРЕМИСЫ, ГЛАВНАЯ НАХОДКА СВЕРХ ЗАДАНИЯ. Дверей было ДВЕ, а не одна. verify_cached_run документирует, что непригодный к повтору прогон метится префиксом noncacheable| и валидатор handle такую строку отвергает; в списке классов префикса ПЕРВЫМ назван «все гейты пропущены». Но ветка «все пропущены» возвращается РАНЬШЕ, чем метка ставится (verify_cached_run отдаёт управление в handle_no_test_mapped, который пишет command=cache_command без префикса), — то есть первый же класс, который префикс называет, был единственным, который он не покрывал. Поэтому такой прогон был пригоден к повтору поиском свежего зелёного (has_fresh_verify_run сверяет команду и хэш файлов) весь срок кэша. Починка только валидатора handle оказалась бы декоративной. Память #555. AC4 ЗАМЕРЕН, ДЕФЕКТА НЕТ. skip_on_fileless_close несёт РОВНО ОДИН гейт — changelog, и он поставляется выключенным (default_config enabled=False). Verify-First на пустом закрытии НЕ пропускается: у него своя третья ветвь, требующая от git доказательства, что в объявленной области нет незакоммиченных изменений. Это вердикт со свидетельством, причём git-овым, а не словом агента. Закреплено тестом по реестру, а не утверждением в прозе.
- 2026-09-04T11:19:54Z [implementation] — МУТАЦИИ. Базовый rc=0, 51 passed. Убитой считается ТОЛЬКО rc=1 (память #542). Объявлено 11, применено 11, УБИТО 11; восстановленный прогон rc=0 / 51 passed. Мутанты: старая запись без outcome читается как выполнение; COULD_NOT_RUN схлопывается в NOT_APPLICABLE; пустой список результатов признаётся «нечему применяться»; пропуск засчитан выполнением; булева колонка читается как False; handle перестал отказывать; признание игнорируется (выход закрыт); вторая дверь оставлена открытой; отказ перестал называть отвергнутую строку; заявление отмывает сломанный гейт; загрузчик строки перестал читать колонку. ПЕРВЫЙ ПРОГОН ДАЛ «7/7 УБИТО» ПРИ ОДИННАДЦАТИ ОБЪЯВЛЕННЫХ. Четыре мутанта напечатали SKIP «anchor appears 0 times»: якоря писались с переводом строки \n, а рабочая копия хранит CRLF — однострочные совпадали, многострочные нет, и пропуск бил ровно по самым содержательным. Строка «7/7» читается как полный успех. Знаменатель обязан печатать число ОБЪЯВЛЕННЫХ, а не применённых. Память #554; родственно #542 — там ложное убийство, здесь ложная полнота. Negative: негативный сценарий AC5 предъявлен НЕ синтетикой, а падением СУЩЕСТВУЮЩЕГО теста: tests/test_cli_verify_guards.py::TestNoTestsExpectedEscape::test_declared_run_is_reusable_by_task_done утверждал ровно старое поведение («ok is True» для прогона без единого выполненного гейта) и покраснел на первой же правке. Он переписан на новую форму пригодности — отказ БЕЗ признания и приём С признанием, обе стороны в одном тесте, — а не ослаблен. Вторая половина негативного: тест test_an_ordinary_run_is_unaffected_by_the_acknowledgement_default закрепляет, что честный прогон флага не требует, иначе починка была бы запретом на закрытие вообще. AC-1: ✓ tests/test_zero_gate_verdict.py::test_a_handle_for_a_run_with_no_executed_gate_is_refused AC-2: ✓ tests/test_zero_gate_verdict.py::test_the_verify_note_is_not_a_verdict AC-3: ✓ tests/test_zero_gate_verdict.py::test_the_same_handle_is_accepted_once_the_closer_acknowledges AC-4: ✓ tests/test_zero_gate_verdict.py::test_only_the_changelog_gate_skips_on_a_fileless_close AC-5: ✓ tests/test_cli_verify_guards.py::TestNoTestsExpectedEscape::test_declared_run_is_reusable_by_task_done AC-6: ✓ tests/test_zero_gate_verdict.py::test_a_gate_that_could_not_run_is_not_declared_away Domain: результат осмыслен вне тестов. Реальный вход — закрытие задачи агентом: до правки последовательность «verify --no-tests-expected -> task done --verify-handle» закрывала задачу, при которой не проверялось НИЧЕГО, и след в БД был единственным, что отличало её от проверенной. Теперь та же последовательность отказывает и называет флаг, а закрытие требует второго явного акта, который записывается. Физическая осмысленность различения двух видов невыполнения: гейт, которому нечего смотреть, и гейт, который сломался, дают ОДИНАКОВОЕ отсутствие находки, но разную причину; признать можно только первое, потому что второе означает утрату свидетельства, а не его отсутствие.
