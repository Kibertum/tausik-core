---
slug: l26-skill-supply-chain-threat
title: "Threat-model магазина скиллов (горящий рынок атак 2026)"
status: done
epic: landscape-2026-h2
story: l26-ecosystem
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Не переписывать существующий supply_verify_install.py (ed25519 подпись at-install уже есть — только credit в threat-model); не трогать config_trust.py / trust-tier механизм; не менять brain_scrubbing.py (его _ZERO_WIDTH_RE для brain-контента, дополняем, не дублируем); не реализовывать OMS/Sigstore (отклонён владельцем); не строить post-install re-verify (Orca-вектор — задокументировать как accepted/deferred, не кодить)."
relevant_files:
  - "scripts/skill_content_scan.py"
  - "scripts/skill_manager.py"
scope_paths:
  - "scripts/skill_content_scan.py"
  - "scripts/skill_manager.py"
  - "tests/test_skill_content_scan.py"
  - "docs/en/skill-supply-chain-threat-model.md"
  - "docs/ru/skill-supply-chain-threat-model.md"
  - "docs/en/security.md"
  - "docs/ru/security.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T17:14:36Z"
---

## Goal

СТРАТЕГИЧЕСКАЯ ВОЗМОЖНОСТЬ И ОДНОВРЕМЕННО РИСК. Главный вектор атак 2026 — не MCP-серверы, а markdown-скиллы: полезная нагрузка это ПРОЗА, поэтому сигнатурное сканирование не работает. Данные: Snyk ToxicSkills (2026-02-05) на выборке 3984 скиллов — 36.8 процента с проблемами, 13.4 процента с критичными, 76 подтверждённых вредоносов, 8 ещё живых на публикации, 91 процент вредоносных использовали prompt injection, 10.9 процента содержали захардкоженные секреты. Кампания ClawHavoc (февраль 2026) — 341 вредоносный скилл из 2857, инфостилер AMOS; реестр вычистил 2419 скиллов. Unit 42 (июнь 2026): обход сканеров раздуванием README до 22 МБ, подмена рекомендаций агента в рантайме. Orca (май 2026): сканирование только при создании, поэтому подмена после проверки работает. Формулировка Unit 42 бьёт в корень — экосистеме не хватает изоляции между логикой скилла и полномочиями агента. Задача: threat-model собственного магазина по этим известным примитивам (подмена после проверки, тихая перезапись одноимённым, невидимые Unicode-инструкции в блоке тегов U+E0000, раздутые файлы против сканера, накрутка счётчика установок), затем меры. ПРЯМАЯ АНАЛОГИЯ ДЛЯ TAUSIK: CVE-2025-59536 (CVSS 8.7) — хуки из repo-supplied .claude/settings.json исполнялись ДО диалога согласия; у TAUSIK механизм хуков ровно той же формы. Решение по OMS/Sigstore ОТКЛОНЕНО владельцем — остаёмся на своём ed25519.

## Acceptance Criteria

AC1. Threat-model собственного магазина скиллов задокументирована по известным примитивам 2026: подмена после проверки (Orca), тихая перезапись одноимённым, невидимые Unicode-инструкции (U+E0000 tag block), раздутые файлы против сканера (Unit 42, README до 22 МБ), накрутка счётчика установок. Каждый вектор — с оценкой применимости к TAUSIK.
AC2. Разобрана прямая аналогия CVE-2025-59536 (хуки из repo-supplied .claude/settings.json исполнялись до диалога согласия): зафиксировано, применим ли вектор к механизму хуков TAUSIK той же формы, и выбрана мера (согласие/подпись/блок до доверия).
AC3. По каждому вектору назван статус — митигировано / принято / отложено с обоснованием; пустых строк threat-model нет. Отклонение OMS/Sigstore учтено (остаёмся на ed25519).
AC4. Хотя бы одна выбранная к реализации мера покрыта тестом или гейтом (например, детектор невидимых Unicode-инструкций фейлит на образце скилла с U+E0000).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; установка скиллов возвращается к прежнему поведению

## Journal

- 2026-07-27T17:00:12Z [implementation] — Drafted invisible-Unicode detector (scan_invisible_unicode): U+E0000-E007F tag block (primary), zero-width (200B/C/D/2060/FEFF), bidi overrides (202A-E/2066-9, Trojan Source CVE-2021-42574), soft-hyphen. Awaiting surface-map (Explore agent) to finalize module placement + install-hook wiring + CVE-2025-59536 trust-tier verdict.
- 2026-07-27T17:14:26Z [implementation] — AC verified: AC1 ✓ threat-model 5 векторов задокументирована (docs/{en,ru}/skill-supply-chain-threat-model.md) с оценкой применимости к TAUSIK по каждому; AC2 ✓ CVE-2025-59536 разобран — вердикт «не применим по дизайну» (.claude/ gitignored+генерится bootstrap, project-config untrusted), 2 остаточных пути диспозиционированы; AC3 ✓ статус по каждому вектору (митигировано/принято/неприменимо/отложено), пустых строк нет, OMS/Sigstore-отклонение учтено; AC4 ✓ scripts/skill_content_scan.py + вшит в copy_skill, tests/test_skill_content_scan.py 10 тестов PASS включая U+E0000-образец и copy_skill-блок отравленного SKILL.md. ruff+mypy clean. verify run #1522 exit=0 (pytest over test_skill_content_scan + test_skill_manager). CHANGELOG EN+RU обновлены. Closing via CLI (stale-MCP gate_registry).
