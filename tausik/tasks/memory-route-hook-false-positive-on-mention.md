---
slug: memory-route-hook-false-positive-on-mention
title: "memory_route-хук блокирует УПОМИНАНИЕ пути-стока в Bash-команде — over-detection парсера у блокирующего хука с другим профилем цены"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: memory-route-gate-ide-agnostic-enforcement-block-a
scope: "scripts/hooks/bash_write_parse.py, scripts/hooks/memory_pretool_block.py, tests/test_memory_sinks.py, docs/ru/agent-contract.md (при подтверждении п.5), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/hooks/bash_write_gate.py — поведение QG-0 не меняется (AC3). scripts/memory_sinks.py и deny-list — не при чём, дефект в определении ЦЕЛЕЙ, а не в списке стоков. gate_memory_route.py — гейт читает git, а не Bash-команды."
relevant_files:
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/memory_pretool_block.py"
  - "tests/test_memory_sinks.py"
  - "docs/ru/agent-contract.md"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T23:58:56Z"
---

## Goal

Дефект memory-route-gate-ide-agnostic-enforcement-block-a, обнаружен собственным dogfooding в той же сессии. Хук memory_pretool_block переиспользует bash_write_parse.write_targets — правильное решение против дублирования правила, но у парсера есть СОЗНАТЕЛЬНАЯ over-detection: при непарсящейся команде он падает в _redir_targets_regex, который «переобнаруживает, а не недообнаруживает» (документировано в bash_write_parse). Для QG-0 это дёшево: худший случай — попросят задачу, которая и так нужна. Для memory_route цена другая: команда, лишь УПОМИНАЮЩАЯ путь-сток в кавычках (`python -c "print('> .cursor/rules/a.mdc')"`, `grep -n '> .clinerules' README.md`), БЛОКИРУЕТСЯ страшным сообщением про утечку знаний, а выходов только два — маркер `confirm: cross-project` (ложь: это не кросс-проектная преференция) или правка config allow (постоянное ослабление ради разовой команды). Воспроизведено вживую: хук заблокировал диагностический python -c, распарсив мусорный «путь» `.cursor/rules/a.mdc/"',`. Ложное срабатывание блокирующего хука без корректирующего слоя ниже — это тренировка обхода. Нужно: memory_route НЕ должен использовать over-detecting fallback (недообнаружение здесь покрыто гейтом и pre-commit, у over-detection корректора нет), плюс тесты на упоминание-не-запись. Попутно проверить обратное: прячет ли `bash -c 'cmd > file'` цель от парсера — если да, документированная граница «нужно активно обфусцировать» завышена, потому что bash -c не обфускация.

## Acceptance Criteria

1. Воспроизведение ДО фикса: тест показывает, что хук блокирует команду, которая лишь упоминает путь-сток в кавычках и ничего не пишет (`python -c "print('> .cursor/rules/a.mdc')"`, `grep -n '> .clinerules' README.md`).
2. Хук memory_pretool_block перестаёт судить по результату over-detecting fallback: цели, полученные из непарсящейся команды регулярным выражением, для этого хука не основание для блока. Механизм — явный, объявленный в парсере признак «цель получена fallback'ом», а не второй парсер и не эвристика на стороне хука (иначе это вторая копия правила, conv #266).
3. bash_write_gate (QG-0) сохраняет прежнее поведение бит-в-бит: у него другая цена ошибки, over-detection там намеренная. Тест на неизменность.
4. NEGATIVE: настоящая Bash-запись в сток по-прежнему блокируется — `printf x > .clinerules`, `cat >> ~/.claude/.../memory/x.md <<EOF`, `tee .cursor/rules/a.mdc`.
5. Проверено и зафиксировано, прячет ли `bash -c 'cmd > file'` цель от парсера. Если да — граница в docs/ru/agent-contract.md и в докстроке bash_write_gate переформулирована честно (`bash -c` — не обфускация), либо парсер рекурсивно разбирает payload интерпретатора. Молчание недопустимо в любом случае.
6. Тесты на все перечисленные случаи; полный прогон pytest зелёный; все гейты зелёные.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита. Изменение локализовано в признаке fallback'а у bash_write_parse и в одной ветке memory_pretool_block; bash_write_gate не трогается, поэтому откат не затрагивает QG-0. Хук целиком отключается TAUSIK_SKIP_MEMORY_HOOK=1 (пишет bypass-событие).

## Journal

- 2026-07-23T23:58:34Z [implementation] — Root cause (edge-case): один парсер целей записи у двух потребителей с ПРОТИВОПОЛОЖНОЙ ценой ошибки. bash_write_parse при непарсящейся команде намеренно ПЕРЕобнаруживает — это верно для QG-0 (худший случай: попросят задачу, которая и так нужна), но я переиспользовал его в memory_pretool_block, не сверив цену ошибки. У memory_route блок обвиняет агента в утечке знаний, а выходов два: маркер, который был бы неправдой, и постоянное исключение в конфиге ради разовой команды. Ложное срабатывание там дороже пропуска, потому что тренирует обход. Переиспользование парсера было правильным (одно правило, не две копии), ошибка — в допущении, что и ИНТЕРПРЕТАЦИЯ его ответа общая. Prevention: переиспользуя общий детектор в новом потребителе, сверять не только правило, но и ЦЕНУ ОШИБКИ в каждую сторону; если она различается — детектор обязан объявлять уверенность (здесь: write_targets_with_confidence → parsed/regex_fallback), а не каждый потребитель угадывать её заново. Признак, что цена различается: у одного потребителя ниже по потоку есть корректирующий слой, у другого нет.
- 2026-07-23T23:58:54Z [implementation] — AC1 ✓ Воспроизведение: test_a_quoted_mention_is_not_a_write — python -c с закавыченным путём, grep '> .clinerules', echo с упоминанием, плюс две реально непарсящиеся команды (awk/sed с несбалансированной кавычкой). На коде до фикса непарсящиеся блокировались. AC2 ✓ Признак объявлен В ПАРСЕРЕ: write_targets_with_confidence возвращает (targets, CONFIDENCE_PARSED|CONFIDENCE_REGEX_FALLBACK). Хук не заводит второй парсер и не угадывает эвристикой — он читает объявленную уверенность (conv #266). AC3 ✓ write_targets не изменён (делегирует и отбрасывает уверенность); test_qg0_parser_contract_is_unchanged проверяет бит-в-бит равенство ответа для parsed и regex_fallback случаев. tests/test_bash_write_gate_hook.py зелёный без правок. AC4 NEGATIVE ✓ test_real_bash_writes_are_still_blocked: printf > .clinerules, tee .cursor/rules/a.mdc, echo >> .github/copilot-instructions.md — все返 exit 2. Плюс прежний тест на heredoc в ~/.claude/**/memory/. AC5 ✓ ПОДТВЕРЖДЕНО: bash -c 'printf x > .clinerules' → [], sh -c "echo x > .cursor/rules/a.mdc" → []. Это обходит и QG-0. Граница переформулирована в docs/ru/agent-contract.md ЧЕСТНО: убрано «нужно намеренно обфусцировать», названо, что bash -c обфускацией не является, добавлен раздел про непарсящуюся команду и разную цену ошибки у двух потребителей. Дыра заведена задачей bash-c-wrapper-bypasses-qg0-write-gate. test_interpreter_wrapper_hides_the_target закрепляет нынешнее поведение, чтобы будущее изменение было видимым. AC6 ✓ Полный прогон 5558 passed / 23 skipped / 0 failed; ruff All checks passed; verify #1232 подписан. CHANGELOG ✓ два раздела в [Unreleased] EN + RU-зеркало (сам фикс и честная переформулировка границы). Domain: пропуск не молчаливый и не безграничный — пишется fail_open_unparseable_bash (считаемое supervision-событие), а in-tree половину deny-list пересудят гейт memory_route и pre-commit до коммита. Непокрытым остаётся только home-сток при непарсящейся Bash-команде — названо явно, не подразумевается.
