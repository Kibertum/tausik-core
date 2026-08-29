---
slug: twelve-tests-return-from-a-silent-ignore
title: "Двенадцать тестов возвращаются из --ignore, приехавшего молча в сборном релизном коммите"
status: planning
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - full-lane-runs-serial-on-a-twenty-core-machine
completed_at: null
---

## Goal

ЗАМЕРЕНО #189, И ЗАМЕР СНИМАЕТ ЕДИНСТВЕННОЕ ВОЗРАЖЕНИЕ. Оба файла — tests/test_bootstrap_skills_coverage.py (8 тестов) и tests/test_bootstrap_real.py (4) — исключены `--ignore` в .github/workflows/tests.yml (и в быстрой матрице, и в джобе test-full) и в .gitlab-ci.yml. В быстрой ленте они пропущены как slow, в полной локальной убиты сторожем. Итого ДВЕНАДЦАТЬ тестов не выполняются НИГДЕ, и их молчание неотличимо от зелени.
ПРОИСХОЖДЕНИЕ УСТАНОВЛЕНО ГИТОМ, а не догадкой: оба --ignore внесены коммитом 3189f67 (26.04, сборный релиз v1.3), где о них не сказано ни слова ни в сообщении, ни рядом в диффе; в первой версии файла (a158380) их не было; затем скопированы в GitLab (fd803f3) и в локальные замеры. Никто не решал их исключить по существу.
ВОЗРАЖЕНИЕ «А ВДРУГ ОНИ КРАСНЫЕ» СНЯТО: прогон с -o faulthandler_timeout=600 последовательно дал 22 passed за 824.32 s, exit 0. Они здоровы, они просто длинные (52.47-65.35 s).
ДЕЛАЕТСЯ ПОСЛЕ решения по сторожу зависаний и включения xdist, иначе возврат приведёт к тем же смертям. НЕГАТИВНОЕ: тест обязан краснеть, если --ignore вернётся, — иначе исключение приедет молча во второй раз.

## Acceptance Criteria

## Plan

## Rollback

Правка двух строк в двух файлах CI. Откат — git revert; продуктовый код не трогается.

## Journal
