---
slug: verify-external-flags-against-real-binaries
title: "Флаги внешних бинарей проверять против настоящих бинарей, а не мока"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "tests/ (новый файл проверки флагов). Возможно scripts/ — если найдётся собранный руками флаг, которого нет в бинаре (тогда чинить как --no-config)."
scope_exclude: "Не менять gate_runner без необходимости. Не добавлять сетевых вызовов в тесты."
relevant_files:
  - "tests/test_external_flags_are_real.py"
  - "stacks/rust/stack.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T21:37:10Z"
---

## Goal

Релиз 1.6.0 вырос из --no-config: флаг, которого нет ни в одной версии pip, прожил два минора, потому что единственный тест мокал subprocess. Образец правильной проверки уже есть — TestPipFlagsAreRealFlags: 'pip install <флаг> --help' даёт rc=0 на существующем флаге и rc=2 на выдуманном, офлайн. Обобщить на остальные бинари, которым мы передаём собранные руками флаги: git (clone -c core.autocrlf=false -c core.eol=lf, config --local --get, ls-files -z --full-name, cat-file blob, pull --ff-only, rev-parse --show-prefix/--is-inside-work-tree), и per-stack verify-команды (ruff/mypy/tsc/hadolint и т.д., если они собираются из констант). Для каждого distinct набора флагов — тест, который спрашивает настоящий бинарь, принимает ли он их. Где бинаря нет на машине — skip, не ложный успех. Мок остаётся только там, где проверяется НАША логика (стрипанье env, порядок вызовов), а не чужой контракт.

## Acceptance Criteria

1) Тест проверяет каждый distinct набор флагов git, которые мы передаём, против настоящего git — офлайн, без сети. 2) Если per-stack verify-команды собираются из констант (ruff/mypy/tsc/hadolint), их флаги тоже проверяются против бинаря, когда он доступен. 3) Проба сама стережётся тестом: подтверждает, что умеет отвергнуть выдуманный флаг (иначе она бесполезна, как мок). 4) Отсутствие бинаря — skip с причиной, не зелёный по пустоте. Негативные сценарии: 5) Ошибка, если тест зелёный на выдуманном флаге — значит проба не работает. 6) Ошибка, если тест мокает subprocess вместо реального бинаря — это ровно то, что скрыло --no-config. 7) Ошибка, если полный прогон даёт новое падение. 8) Ошибка, если офлайн-проба git реально ходит в сеть (clone внешнего URL) — использовать --help/локальные операции.

## Plan

## Rollback

git checkout -- tests/ scripts/

## Journal

- 2026-07-10T21:37:01Z [implementation] — AC verified: 1. ✓ Флаги git проверяются против настоящего git офлайн — TestGitFlagsAreRealFlags: валидирующие подкоманды (ls-files -z/--full-name, cat-file --batch-check, pull --ff-only, config --local/--get, branch --show-current, diff --numstat/--name-only, log --name-only, rev-parse --short) через rc=129-пробу; rev-parse-флаги (--is-inside-work-tree, --show-prefix, --show-toplevel) поведением; EOL-пины проверены локальным clone (без сети, url через as_uri()). 2. ✓ per-stack команды (stacks/*/stack.json) + UNIVERSAL_GATES + auto_format.FORMATTERS: флаг-токен ищется в '<tool> [subcmd] --help', есть бинарь -> проверяем (ruff/pytest/gofmt локально прошли), нет -> skip. 3. ✓ Проба стережётся: test_probe_rejects_a_bogus_flag (git ls-files --bogus -> rc=129), test_surface_is_non_empty. 4. ✓ Отсутствие бинаря -> skip с причиной (7 skip: mvn, npx, npm, phpstan, bandit). Негативные: 5. ✓ Доказано, что тест ловит выдуманный флаг: вернул '—' в rust stack.json -> test_no_gate_command_has_a_smart_dash УПАЛ; вернул '--' -> зелёный. 6. ✓ Тест НЕ мокает subprocess — зовёт реальные бинари; мок остался только в TestInstallDepsEnvHardening для НАШЕЙ логики (стрипанье env). 7. ✓ Полный прогон 4443 passed, 19 skipped, 0 failed. 8. ✓ git-проба офлайн: clone только по file://-url локального репо, никаких внешних URL. Улов класса (defect того же рода, что --no-config): stacks/rust/stack.json содержал 'cargo clippy — -D warnings' с длинным тире U+2014 вместо '--'. shlex даёт ['cargo','clippy','—','-D','warnings'] — '-D warnings' не доходит до драйвера rustc. Никто не ловил: cargo нет ни на dev, ни на CI. Исправлено на '--'. Проверено, что других non-ASCII в командах stack.json нет. test_no_gate_command_has_a_smart_dash ловит это статически, без всякого бинаря. Root cause (integration-mismatch): контракт чужого бинаря собирается руками и закрепляется моком. Prevention: любой флаг наружу проверяется против настоящего бинаря (rc-проба или help-grep), проба стережётся known-bogus кейсом, отсутствие бинаря — skip; плюс дешёвый статический тест на unicode-тире и чистую shlex-токенизацию всех gate-команд. Память #200.
