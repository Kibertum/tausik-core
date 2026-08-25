---
slug: v156-p4-single-ide-source
title: "P4: закрепить единый источник IDE-списка (если не закрыт P0-deep)"
status: done
epic: v156
story: v156-kilo-zai-finetune
complexity: simple
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "tests/ (guard-тест single-source IDE)"
scope_exclude: "bootstrap/ (уже сведено в P0 — только верификация)"
relevant_files:
  - "tests/test_ide_single_source.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T19:30:20Z"
---

## Goal

Гарантировать, что список поддерживаемых IDE задаётся в ОДНОМ месте (_IDE_DIRS) и оттуда расходится в --ide all, wrapper-цикл и любые другие потребители. Если P0-deep уже свёл всё к _IDE_DIRS — задача закрывается верификацией отсутствия дублей (grep).

## Acceptance Criteria

1. Аудит: в bootstrap/ нет хардкод-списков IDE вне канонических констант (grep пуст). 2. Все потребители (get_ide_target, --ide all, argparse choices, wrapper-инжект) выводятся из IDE_DIRS/SCAFFOLD_IDES. 3. Guard-тест фиксирует инвариант: SCAFFOLD_IDES ⊆ IDE_DIRS; argparse --ide choices == [*SCAFFOLD_IDES,'all']; windsurf/codex ∈ IDE_DIRS, ∉ SCAFFOLD_IDES. 4. НЕГАТИВНЫЙ: если в SCAFFOLD_IDES появится IDE, отсутствующий в IDE_DIRS — тест падает (инвариант нарушен).

## Plan

[{"step": "\u0410\u0443\u0434\u0438\u0442 bootstrap/: \u043d\u0435\u0442 \u0445\u0430\u0440\u0434\u043a\u043e\u0434-\u0441\u043f\u0438\u0441\u043a\u043e\u0432 IDE \u0432\u043d\u0435 IDE_DIRS/SCAFFOLD_IDES (grep \u043f\u0443\u0441\u0442)", "done": true}, {"step": "Guard-\u0442\u0435\u0441\u0442 test_ide_single_source.py: 6 \u0438\u043d\u0432\u0430\u0440\u0438\u0430\u043d\u0442\u043e\u0432 (subset, split, kilo, choices, --ide all, no-literal)", "done": true}, {"step": "\u0420\u0435\u043a\u043e\u043d\u0441\u0430\u0439\u043b doc-constants + README (4420\u21924426)", "done": true}, {"step": "\u041d\u0430\u0445\u043e\u0434\u043a\u0430: ide_utils.IDE_REGISTRY \u0431\u0435\u0437 qwen/kilo \u2014 \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430 P5 (\u0440\u0443\u043d\u0442\u0430\u0439\u043c-\u0434\u0435\u0442\u0435\u043a\u0442 \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u0436\u0438\u0432\u043e\u0433\u043e Kilo)", "done": true}]

## Rollback

git revert — добавляется только тест, без изменения поведения.

## Journal

- 2026-06-19T19:30:19Z [implementation] — AC verified: AC-1: ✓ grep по bootstrap/*.py — нет хардкод-списков IDE вне канонических констант (test_no_hardcoded_ide_list_literal_in_bootstrap PASSED). AC-2: ✓ все потребители выводятся из IDE_DIRS/SCAFFOLD_IDES: get_ide_target (_IDE_DIRS alias), --ide all (list(SCAFFOLD_IDES)), argparse choices ([*SCAFFOLD_IDES,'all']), wrapper-инжект (" ".join(IDE_DIRS)) — подтверждено grep'ом потребителей. AC-3: ✓ guard-тест test_ide_single_source.py 6/6 PASSED: subset (SCAFFOLD_IDES⊆IDE_DIRS), split (windsurf/codex∈IDE_DIRS,∉SCAFFOLD_IDES), kilo scaffold-capable, choices derive, --ide all derive, no-literal. AC-4: ✓ НЕГАТИВНЫЙ: test_scaffold_ides_subset_of_ide_dirs падёт, если в SCAFFOLD_IDES добавить IDE без записи в IDE_DIRS. Domain: P0-deep структурно закрыл три рассинхронизированных списка → две именованные константы. Находка: ide_utils.IDE_REGISTRY (рантайм-детект IDE для skill-системы) не содержит qwen/kilo — отдельная подсистема, вынесено в P5 (требует живого Kilo для auto-detect env-сигнатуры, overlap с P3). doc-constants+README реконсайл 4420→4426.
