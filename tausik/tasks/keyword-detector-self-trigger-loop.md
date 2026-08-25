---
slug: keyword-detector-self-trigger-loop
title: "Stop-хук rag-first глушит ход: нудж срабатывает на собственном тексте, выход недостижим"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/hooks/keyword_detector.py, scripts/hooks/user_prompt_submit.py, tests/ (новые тесты), .claude/settings.json если нужна перерегистрация. Зеркала — через bootstrap, не руками."
scope_exclude: "Не трогать fix/skill-requires-venv и findings 3.1-3.6. Не коммитить и не пушить без разрешения. Не редактировать .claude/scripts/* напрямую."
relevant_files:
  - "scripts/hooks/keyword_detector.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "tests/test_keyword_detector_hook.py"
  - "tests/test_user_prompt_submit_hook.py"
  - "docs/en/hooks.md"
  - "docs/ru/hooks.md"
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T12:11:21Z"
---

## Goal

Убрать блокирующий rag-first нудж со Stop и перенести его в UserPromptSubmit как additionalContext. Две первопричины, обе воспроизведены на живом транскрипте: (1) SEARCH_RECOMMENDATION содержит 'where is X', 'how does Z work' и 'где определ' — Claude Code отдаёт reason блокировки как user-сообщение, детектор матчится на самого себя (v14b чинил только tool_result, не фидбек хука); (2) escape-hatch '"search_code" not in last_assistant' недостижим: записи транскрипта поблочные, _read_last_message отдаёт первую запись роли assistant, часто tool_use, _extract_text даёт '' — то есть ВЫЗОВ search_code не засчитывается, засчитывается только слово в прозе. Итог: Stop блокируется почти каждый ход, харнесс показывает 'Stop hook blocking error' и ход умирает без вывода. Побочно: тело скилла /start само содержит 'where is X used', то есть /start глушит себя даже без фидбека.

## Acceptance Criteria

1) Stop-хук больше не возвращает decision=block по search-intent; на Stop остаётся только drift-guard. 2) Нудж переехал в UserPromptSubmit и отдаётся как additionalContext, не тратя ход. 3) Тест: текст SEARCH_RECOMMENDATION, поданный как пользовательский промпт, НЕ вызывает нудж (анти-саморазгон). 4) Тест: развёрнутое тело слэш-команды (содержит '<command-name>' и 'where is X used') НЕ вызывает нудж. 5) _read_last_message при поиске прозы ассистента пропускает записи с пустым текстом (thinking/tool_use), а не возвращает ''. 6) Зеркала .claude/.cursor/.kilo/.qwen синхронны после bootstrap. Негативные сценарии: 7) Ошибка, если после правки обычный вопрос 'where is parse_manifest defined' перестал давать нудж — защита от саморазгона не должна глушить настоящий триггер. 8) Ошибка, если drift-guard перестал блокировать Stop при 'сейчас напишу' без активной задачи. 9) Ошибка, если полный прогон тестов даёт хоть одно новое падение против зафиксированной базы 4316 passed / 12 skipped.

## Plan

## Rollback

git checkout -- scripts/hooks/keyword_detector.py scripts/hooks/user_prompt_submit.py tests/, затем bootstrap для восстановления зеркал. Правка изолирована в двух хуках; откат не трогает БД и ветку fix/skill-requires-venv.

## Journal

- 2026-07-10T12:00:15Z [implementation] — Первопричины подтверждены на живом транскрипте, не по чтению: (1) _has_search_intent(SEARCH_RECOMMENDATION)=True — текст нуджа цитировал 'where is X', 'how does Z work', 'где определ', а Claude Code возвращает reason блокировки как user-сообщение; проигрыш детектора на транскрипте дал last_user='Stop hook feedback:\n[TAUSIK rag-first nudge]...' и 'Stop would BLOCK: True'. (2) last_asst chars=0 — записи транскрипта поблочные, _read_last_message отдавал первую запись роли assistant (часто tool_use), _extract_text -> '' ; escape-hatch '"search_code" not in last_assistant' был недостижим, вызов инструмента не засчитывался. (3) тело /start SKILL.md содержит 'where is X used' — слэш-команда глушила себя. Правка: Stop = только drift-guard; rag-нудж переехал в user_prompt_submit.py как additionalContext. _read_last_message теперь пропускает записи с пустым текстом (drift-guard раньше слепо получал '' на ходе, кончавшемся tool_use). Добавлен _is_machine_prompt: '/'-префикс, '<command-name>', '<command-message>', '[TAUSIK '. Из текста нуджа убраны цитаты триггеров. Таблица истинности проверена: 'where is parse_manifest defined' -> нудж; 'где определена функция clone_repo' -> нудж; сам SEARCH_RECOMMENDATION -> нет; фидбек Stop-хука -> нет; '/start' -> нет; тело скилла -> нет. Тесты: test_keyword_detector_hook 19 passed (TestSearchIntentNudge и TestToolResultFalsePositiveGuard заменены на TestSearchIntentIsNotAStopConcern + TestLastAssistantProseLookup), test_user_prompt_submit_hook 22 passed (новый TestRagFirstNudge, включая анти-саморазгон). Зеркала синхронизированы через bootstrap --ide all.
- 2026-07-10T12:06:26Z [implementation] — Полный прогон после правки: 2 failed, 4317 passed, 12 skipped. Оба падения — счётчик тестов: правка добавила +3 теста (4448 -> 4451), docs/_generated/constants.json и README-бейджи замерли на 4448. gen_doc_constants.py обновляет только constants.json; четыре doc-count сайта (README.md:11 бейдж, README.md:113 bold, README.md:190 prose, README.ru.md:11 бейдж) правятся вручную — гейт check_docs их лишь ловит. Это подтверждает convention #146 (bump doc-count sites руками). После правки: gen_doc_constants --check OK, test_check_docs_hook + test_gen_doc_constants 44 passed. Запущен финальный полный прогон для подтверждения нуля падений.
- 2026-07-10T12:11:04Z [implementation] — AC1 pass — Stop больше не блокирует по search-intent: TestSearchIntentIsNotAStopConcern::test_search_intent_no_longer_blocks_stop; на живом транскрипте (том самом, что глушил ходы) хук даёт rc=0 и пустой stdout. AC2 pass — нудж в UserPromptSubmit как additionalContext: TestRagFirstNudge::test_english_where_is_triggers. AC3 pass — анти-саморазгон: test_own_recommendation_text_does_not_rearm проверяет _has_search_intent(SEARCH_RECOMMENDATION) == False; до правки этот же вызов давал True. AC4 pass — test_slash_command_body_does_not_trigger ('/start' и тело с <command-name>). AC5 pass — _read_last_message пропускает записи с пустым текстом: TestLastAssistantProseLookup::test_drift_found_behind_trailing_tool_use_entry (drift-проза за хвостовым tool_use теперь видна; раньше last_asst=''). AC6 pass — cmp обоих хуков против .claude/.cursor/.kilo/.qwen после bootstrap --ide all: identical x8. AC7 (негативный) pass — настоящий триггер жив: test_english_where_is_triggers + test_russian_triggers; таблица истинности: 'where is parse_manifest defined' -> нудж, 'где определена функция clone_repo' -> нудж. AC8 (негативный) pass — drift-guard не задет: TestSearchIntentIsNotAStopConcern::test_drift_guard_survives + 8 passed по -k 'Drift or Prose'. AC9 (негативный) pass — полный прогон 4319 passed, 12 skipped, 0 failed против базы 4316/12/0; прирост +3 = новые тесты. Два промежуточных падения (test_check_docs_hook, test_gen_doc_constants) были дрейфом счётчика 4448 -> 4451, закрыты gen_doc_constants.py + ручным бампом четырёх doc-count сайтов; gen_doc_constants --check OK.
- 2026-07-10T12:11:16Z [implementation] — AC verified: 1. ✓ Stop не блокирует по search-intent — TestSearchIntentIsNotAStopConcern::test_search_intent_no_longer_blocks_stop; на живом транскрипте, глушившем ходы, rc=0 и пустой stdout. 2. ✓ Нудж в UserPromptSubmit как additionalContext — TestRagFirstNudge::test_english_where_is_triggers. 3. ✓ Анти-саморазгон — test_own_recommendation_text_does_not_rearm: _has_search_intent(SEARCH_RECOMMENDATION)==False; до правки тот же вызов давал True. 4. ✓ Тело слэш-команды не триггерит — test_slash_command_body_does_not_trigger ('/start' и текст с <command-name>). 5. ✓ _read_last_message пропускает пустые записи — TestLastAssistantProseLookup::test_drift_found_behind_trailing_tool_use_entry; раньше last_asst=''. 6. ✓ Зеркала синхронны — cmp обоих хуков против .claude/.cursor/.kilo/.qwen после bootstrap --ide all: identical x8. 7. ✓ (негативный) Настоящий триггер жив — test_english_where_is_triggers, test_russian_triggers; 'where is parse_manifest defined' -> нудж, 'где определена функция clone_repo' -> нудж. 8. ✓ (негативный) Drift-guard не задет — test_drift_guard_survives; -k 'Drift or Prose' 8 passed. 9. ✓ (негативный) Полный прогон 4319 passed, 12 skipped, 0 failed против базы 4316/12/0; +3 = мои новые тесты. Промежуточные падения test_check_docs_hook и test_gen_doc_constants были дрейфом счётчика 4448->4451; закрыты gen_doc_constants.py плюс ручным бампом четырёх doc-count сайтов; gen_doc_constants --check OK.
