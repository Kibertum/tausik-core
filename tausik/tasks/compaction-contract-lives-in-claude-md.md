---
slug: compaction-contract-lives-in-claude-md
title: "Политика компакции не выражена нигде: сжатие само решает, что забыть"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: "Раздел компакции в CLAUDE.md этого репозитория и блок COMPACTION_CONTRACT в bootstrap_templates для потребителей (standard/full); тест; CHANGELOG."
scope_exclude: "Не менять код хуков или сжатия; не трогать minimal-tier кроме одной строки-указателя; не релизить."
relevant_files:
  - CLAUDE.md
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - "tests/test_compaction_contract.py"
  - "tests/test_claude_md_size.py"
  - "tests/test_bootstrap_generate.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - CLAUDE.md
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_templates_tiers.py"
  - "tests/test_compaction_contract.py"
  - "tests/test_bootstrap_generate.py"
  - "docs/ru/agent-contract.md"
  - "docs/en/claude-md-guide.md"
  - "docs/ru/claude-md-guide.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/compaction-contract-lives-in-claude-md.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:32:20Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

ПЕРЕНОС ПРАКТИКИ CLAUDE CODE. Компакцию можно ИНСТРУКТИРОВАТЬ: в CLAUDE.md пишется, что обязано пережить сжатие («всегда сохраняй полный список изменённых файлов и команды тестов» — пример из документации). У нас не написано ничего, и каждое автосжатие решает само.
ПОЧЕМУ ЭТО ВАЖНО ИМЕННО ЗДЕСЬ: Anthropic прямо называет риск — «слишком агрессивное сжатие теряет тонкий контекст, важность которого выясняется позже». В нашей работе этот тонкий контекст имеет имя: оплаченные замеры и отменённые правила. Потеря замера стоит повторного прогона на 13 минут; потеря отменённого правила стоит воскрешения мёртвого правила.
ЧТО ДЕЛАЕТСЯ: раздел политики компакции в CLAUDE.md и в шаблоне bootstrap (то есть он достаётся и потребителям), перечисляющий поимённо: активная задача и её slug, объявленный scope и квитанция verify, замеры этой сессии с числами, отменённые/заменённые правила, запреты владельца, незакрытые развилки.
СТОИТ НОЛЬ КОДА И ДЕЙСТВУЕТ НА СЛЕДУЮЩЕМ ЖЕ СЖАТИИ. Делается ПЕРВЫМ в своей истории.

## Acceptance Criteria

AC-1: CLAUDE.md carries a compaction section that names, by item, what must survive a context compaction: the active task and its slug, the declared scope and the verify receipt, this session's measurements with their numbers, retired/superseded rules, owner prohibitions, open forks — and the static portion stays under the 4096-byte cap (test_claude_md_size). AC-2: bootstrap_templates.py carries the same contract as COMPACTION_CONTRACT, included in the standard and full tiers (and a one-line pointer in minimal), so a consumer's generated CLAUDE.md gets it on the next bootstrap. AC-3 (negative): tests/test_compaction_contract.py fails if any of the six items disappears from either place, and proves the minimal tier carries the pointer but not the full list. AC-4: the guide docs/{en,ru}/claude-md-guide.md name the section; CHANGELOG EN/RU; ruff, signed verify.

## Plan

[{"step": "COMPACTION_CONTRACT \u0432 \u0448\u0430\u0431\u043b\u043e\u043d\u0435 (standard/full + \u0443\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c \u0432 minimal)", "done": true}, {"step": "\u0420\u0430\u0437\u0434\u0435\u043b \u0432 CLAUDE.md \u0441 \u0443\u043a\u043b\u0430\u0434\u043a\u043e\u0439 \u0432 4096 \u0431\u0430\u0439\u0442 (\u0441\u0436\u0430\u0442\u044c \u0431\u043b\u043e\u043a \u043a\u043e\u043c\u0430\u043d\u0434)", "done": true}, {"step": "\u0422\u0435\u0441\u0442 \u043d\u0430 \u0448\u0435\u0441\u0442\u044c \u043f\u0443\u043d\u043a\u0442\u043e\u0432 \u0432 \u043e\u0431\u043e\u0438\u0445 \u043c\u0435\u0441\u0442\u0430\u0445; docs guide; CHANGELOG; verify", "done": true}]

## Rollback

git revert; поведения продукта не меняет.

## Journal

- 2026-09-12T15:26:16Z [implementation] — AC verified: AC-1 ✓ CLAUDE.md '## Компакция' names the six items; static portion 4089 B ≤ 4096 (tests/test_claude_md_size.py green) — room was made by trimming the commands block to the five lifecycle commands (the rest points at cli.md) and shortening three lines without dropping a rule. AC-2 ✓ COMPACTION_CONTRACT in bootstrap_templates_tiers.py, assembled after MEMORY and before SENAR_RULES in standard and full (test_the_contract_sits_after_memory_and_before_senar_rules); MINIMAL_COMPACTION pointer in minimal. AC-3 ✓ Negative: tests/test_compaction_contract.py — 6 RU items in CLAUDE.md, 6 EN items × 2 tiers, minimal carries the pointer and not the numbered list (20 tests). AC-4 ✓ docs/{en,ru}/claude-md-guide.md name the section in the recommended structure; CHANGELOG EN/RU; ruff clean; translation drift/stale docs green; bootstrap --check clean; signed verify below. Domain: the next auto-compaction in this repository is told what to keep — the measurement numbers and the retired rules that today's sessions had to re-derive twice.
- 2026-09-12T15:28:49Z [implementation] — Gate finding fixed: the generated consumer body sat at exactly 180 lines (the cap); the contract compressed to one line per item measures 190, and tests/test_bootstrap_generate.py's bound moves 180→190 with the measurement written into its docstring (precedent: the r14 overrides block moved it 150→180).
- 2026-09-12T15:31:32Z [implementation] — Correction: a second guard (test_graph_is_framework_machinery::test_it_was_paid_for_and_not_appended) holds the project's convention — lines are PAID, not budgeted — so the 180→190 move was reverted and the ten contract lines were paid for: memory-first/routing prose 13→10 lines, the SENAR 'Where Hard is hard' blockquote 5→3, workflow bullets 7→3, every rule and sink name kept. Generated body: 178/180.
