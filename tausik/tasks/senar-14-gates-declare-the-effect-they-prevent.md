---
slug: senar-14-gates-declare-the-effect-they-prevent
title: "Гейты не объявляют эффект, который предотвращают, — только чем они его ловят"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: "формулировки эффектов для гейтов НЕ выдумываю там, где предмет принадлежит владельцу: беру из уже написанных комментариев реестра и из red_proofs.violation, где они есть; смысловую осмысленность формулировки проверяет РЕВЬЮ, тест закрепляет только присутствие, непустоту и отсутствие заглушек"
relevant_files:
  - "scripts/gate_spec.py"
  - "scripts/gate_registry.py"
  - "scripts/gate_registry_scoped.py"
  - "scripts/gate_run_record.py"
  - "scripts/backend_schema_gate_runs.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "tests/test_gate_prevented_effect.py"
  - "tests/test_gate_runs_persist.py"
  - "tests/test_migrations_v50_adapt_statuses.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_spec.py"
  - "scripts/gate_registry.py"
  - "scripts/gate_registry_scoped.py"
  - "scripts/gate_run_record.py"
  - "scripts/backend_schema_gate_runs.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "tests/test_gate_prevented_effect.py"
  - "tests/test_gate_runs_persist.py"
  - "tests/test_migrations_v50_adapt_statuses.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T15:13:01Z"
---

## Goal

У каждого гейта TAUSIK объявлено, КАКОЕ ИЗМЕНЕНИЕ не происходит, пока вердикт отрицателен. Это условие §8.6(a) SENAR 1.4, SHALL на всех конфигурациях включая Core, и без него заявление о соответствии разделу 8 недействительно по §13.4.

## Acceptance Criteria

AC1. РАЗРЫВ ПОКАЗАН НА НАШЕМ РЕЕСТРЕ. В scripts/gate_registry.py у гейта есть description вида 'Lint with ruff before commit'. Это описание МЕХАНИЗМА, а не предотвращаемого эффекта. Стандарт отдельно оговаривает: 'обеспечивает качество' объявленным эффектом не является, потому что ни одно предлагаемое действие нельзя проверить на соответствие такой формулировке.
AC2. Эффект объявлен ДЛЯ КАЖДОГО гейта в реестре, а не для образцовых. Формулировка отвечает на один вопрос: какое конкретное изменение НЕ произойдёт, пока вердикт отрицателен.
AC3. ПРОВЕРКА ПРИМЕНИМОСТИ МЕХАНИЧЕСКАЯ ТАМ, ГДЕ ЭТО ВОЗМОЖНО, И ЧЕЛОВЕЧЕСКАЯ ТАМ, ГДЕ НЕТ. §13.7 честно говорит, что (a) — это проверка присутствия плюс тест применимости, которому нужен читатель. Значит тест закрепляет присутствие и непустоту, а осмысленность формулировки проверяет ревью. Выдавать первое за второе нельзя.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест обязан ПОКРАСНЕТЬ на новом гейте, заведённом без объявленного эффекта. Иначе следующий гейт приедет без него, и поле станет украшением.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: формулировки-заглушки ('обеспечивает качество', 'проверяет корректность', пустая строка, копия названия гейта) обязаны отвергаться списком запрещённых образцов. Это ровно тот случай, который стандарт называет поимённо.
AC6. Объявленный эффект попадает В ЗАПИСЬ О ПРОГОНЕ, а не только в реестр. §8.6(g) требует, чтобы запись опознавала состояние, для которого вынесен вердикт; без эффекта запись не говорит, что именно было предотвращено.

## Plan

## Rollback

git revert <commit> для кода. Миграция v51 добавляет НЕНУЛЛИРУЕМУЮ-опциональную колонку gate_runs.prevents (ALTER TABLE ADD COLUMN, значение NULL для старых строк) — откат схемы не требуется: колонка безвредна и читается как «записано до появления различения». Если откат нужен полностью, SCHEMA_VERSION возвращается на 50 и колонка остаётся в существующих БД без последствий.

## Journal

- 2026-09-06T15:12:50Z [implementation] — AC verified: AC1 (разрыв показан на нашем реестре): ✓ description гейтов описывал МЕХАНИЗМ («Lint with ruff before commit»); добавлено отдельное поле GateSpec.prevents, отвечающее на вопрос §8.6(a). Тест требует, чтобы prevents НЕ совпадал ни с именем гейта, ни с его description. ✓ tests/test_gate_prevented_effect.py::test_no_gate_hides_behind_a_stock_phrase AC2 (для КАЖДОГО гейта): ✓ заполнено для всех 17 записей реестра, тест параметризован по GATE_REGISTRY — новый гейт попадает под него автоматически, без правки списка. ✓ tests/test_gate_prevented_effect.py::test_every_gate_declares_the_effect_it_prevents AC3 (механическое там, где можно; человеческое там, где нельзя): ✓ тест закрепляет ПРИСУТСТВИЕ, непустоту, минимальную длину и отсутствие заглушек; осмысленность оставлена ревью, и это сказано в докстринге модуля прямо, а не подразумевается. Три совещательных гейта (mypy, bandit, tdd_order) объявляют, что не предотвращают НИЧЕГО, потому что выключены или warn — приукрашивание было бы ровно тем утверждением, ради проверяемости которого поле заводится. AC4 NEGATIVE (новый гейт без объявления краснеет): ✓ проверено на GateSpec, собранном в тесте, а не правкой живого реестра — правило, которое можно проверить только сломав реестр, никто проверять не станет. Мутация T1 (пустое объявление принимается) убита по ветви. ✓ tests/test_gate_prevented_effect.py::test_a_new_gate_without_a_declaration_is_caught AC5 NEGATIVE (заглушки отвергаются списком): ✓ список запрещённых образцов включает названные стандартом поимённо; мутация T2 (список обезврежен) убита. ✓ tests/test_gate_prevented_effect.py::test_a_stock_phrase_is_caught AC6 (эффект попадает В ЗАПИСЬ): ✓ схема v51 добавила gate_runs.prevents, ALTER TABLE зарегистрирован, свежая и мигрированная схемы совпадают. Строка хранит формулировку, действовавшую на момент записи (мутация T5 убита), незнакомый гейт пишет NULL, а не выдуманный эффект (T4 убита), и запись без объявления невозможна (T3 убита). ✓ tests/test_gate_prevented_effect.py::TestTheEffectReachesTheRecord Мутаций 5, все KILLED по ветви; мутатор удалён сразу. Полный прогон 9157 passed / 27 skipped, mypy Success 358 файлов, ruff чист, bootstrap --check без дрейфа. CHANGELOG в обоих файлах. Domain: читатель строки gate_runs теперь видит не только «какой гейт и с каким исходом», но и «что именно этот вердикт удержал» — без чего запись не отвечает на вопрос §8.6(g).
