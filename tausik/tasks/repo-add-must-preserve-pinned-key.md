---
slug: repo-add-must-preserve-pinned-key
title: "3.2: повторный skill repo add сбрасывает запиненный ключ (шире, чем --force)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "scripts/skill_repos.py, tests/test_skill_manager.py"
scope_exclude: "Не менять формат config.json."
relevant_files:
  - "scripts/skill_repos.py"
  - "tests/test_skill_repo_trust.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T13:15:56Z"
---

## Goal

Первопричина точнее, чем в отчёте: update_config_repo_add (scripts/skill_repos.py:66) делает repos[name] = {"url": url} — заменяет запись целиком и теряет соседний ключ 'pubkey'. Репро: пин 'AAAA_pinned_key' -> повторный add -> get_repo_pinned_pubkey вернул None. Это не свойство --force: любой повторный add по уже настроенному имени снимает доверие, включая builtin-URL, где --force не нужен. Правка: мержить поля, а не перезаписывать. Если URL меняется — снимать пин осознанно и громко предупреждать, что доверие потеряно.

## Acceptance Criteria

1) update_config_repo_add мержит поля записи, не заменяет её целиком: pubkey переживает повторный add того же URL. 2) Если URL меняется, пин снимается осознанно и печатается громкое предупреждение о потере доверия. 3) repo_add печатает состояние доверия после добавления. Негативные сценарии: 4) Ошибка, если повторный add по builtin-URL (без --force) снимает пин — баг шире, чем --force. 5) Ошибка, если смена URL молча сохраняет старый пин: это было бы доверие к чужому репозиторию. 6) Ошибка, если полный прогон даёт новое падение.

## Plan

## Rollback

git checkout -- scripts/skill_repos.py tests/; bootstrap.

## Journal

- 2026-07-10T13:15:44Z [implementation] — AC verified: 1. ✓ update_config_repo_add мержит запись — test_readd_same_url_keeps_pin (пин переживает повторный add), test_other_fields_survive (соседнее поле 'default' цело), test_legacy_bare_url_string_entry (старый формат со строкой вместо словаря). 2. ✓ Смена URL снимает пин и возвращает dropped=True — test_changed_url_drops_pin_and_says_so; repo_add печатает WARNING про потерю доверия и команду повторного пина. 3. ✓ repo_add печатает 'Supply-chain: publisher key still pinned', когда пин цел. 4. ✓ (негативный) Баг воспроизводился без --force: тест зовёт update_config_repo_add напрямую, тот же builtin-путь. 5. ✓ (негативный) test_changed_url_drops_pin_and_says_so падал бы, если бы старый ключ молча ручался за новый origin. 6. — полный прогон в конце релиза. Первопричина (integration-mismatch по форме, logic-error по сути): repos[name] = {"url": url} — присваивание вместо мержа. Соседний ключ 'pubkey' исчезал вместе со всей записью. Отчёт связывал это с --force, но --force лишь разрешает добавить сторонний URL; снятие пина происходило при ЛЮБОМ повторном add, включая builtin. Prevention: не пересобирать словарь конфига целиком там, где в нём живут поля из других подсистем; мержить и возвращать флаг о потере доверия, чтобы вызывающий мог сказать это вслух.
