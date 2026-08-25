---
slug: tausik-tree-gitattributes-lf
title: "Дерево tausik/ не закреплено на LF в .gitattributes: на свежем клоне под Windows round-trip гейт релиза 1.8 краснеет"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: renar-tree-gitattributes-lf
scope: ".gitattributes (добавление правила для дерева tausik/), tests/ (новый тест закрепления, выводящий набор из state_serialize.ENTITY_DIRS), CHANGELOG.md и CHANGELOG.ru.md."
scope_exclude: "НЕ трогать newline-обработку в state_serialize.write_tree — LF там верен, чинится сторона git, а не генератора. НЕ добавлять глобальное правило `* eol=lf`: оно переформатирует несвязанные отслеживаемые файлы (тот же запрет стоял в scope_exclude задачи renar-tree-gitattributes-lf). НЕ трогать правило renar/**. Не переписывать существующие тесты экспорта."
relevant_files:
  - ".gitattributes"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "tausik/stories/kb-git-sync.md"
  - "tausik/tasks/kb-brain-deprecate.md"
  - "tausik/tasks/kb-export-tasks.md"
  - "tausik/tasks/revise-kb-export-tasks-superseded.md"
  - "tausik/decisions/reviziya-obema-1-8-sokratila-byudzhet-s-2087-do-1927-no-ne.md"
  - "tausik/decisions/revyu-pyati-zakrytyh-zadach-nashlo-chto-state-export.md"
  - "tausik/memory/audit-kachestva-sessii-153-revyu-partii-152-nashlo-devyat.md"
  - "tausik/memory/novoe-proizvodnoe-derevo-obyazano-byt-vneseno-v-kazhdyy.md"
  - "tausik/memory/zadacha-obyavivshaya-svoyu-zhe-proektsiyu-v-relevant-files.md"
  - "tausik/tasks/brain-db-binding-ignores-path-case.md"
  - "tausik/tasks/cascade-mutations-never-project-to-tree.md"
  - "tausik/tasks/complexity-proxy-counts-state-projection.md"
  - "tausik/tasks/docs-drift-after-s152-batch.md"
  - "tausik/tasks/ghost-projection-on-fk-cascade-delete.md"
  - "tausik/tasks/projection-property-test-cannot-reach-cascades.md"
  - "tausik/tasks/publish-risk-gate-docstring-lies-after-205.md"
  - "tausik/tasks/risk-l3-still-blocks-after-demotion.md"
  - "tausik/tasks/service-knowledge-one-line-from-filesize-gate.md"
  - "tausik/tasks/task-update-partial-write-then-raise.md"
  - "tausik/tasks/tausik-tree-gitattributes-lf.md"
  - "tausik/tasks/tool-call-syntax-leaks-into-entity-text.md"
  - "tests/test_state_tree_eol_pin.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T20:27:24Z"
---

## Goal

Найдено в сессии #153 при экспорте состояния в ревизии revise-kb-export-tasks-superseded. git выдал «warning: in the working copy of tausik/stories/kb-git-sync.md, LF will be replaced by CRLF the next time Git touches it».

ДЕФЕКТ. .gitattributes закрепляет `renar/** text eol=lf` и в комментарии называет причину дословно: дерево пишется с LF, а при core.autocrlf=true на Windows чекаут делает CRLF, и `renar export --check` видит ложный дрейф. Дерево tausik/ имеет РОВНО ТО ЖЕ СВОЙСТВО и НЕ закреплено. state_serialize пишет LF-only с одним завершающим переводом строки, а check_tree намеренно читает файлы с ВЫКЛЮЧЕННОЙ universal-newline трансляцией, чтобы CRLF-пересохранение не прошло как чистое (tests/test_state_export.py::test_check_tree_detects_crlf_corruption). Значит на свежем клоне под Windows все 2095 файлов дерева станут CRLF и `tausik state export --check` вместе с gate_state_roundtrip покраснеют — не иногда, а гарантированно.

ДОКАЗАТЕЛЬСТВО, а не рассуждение. В этом репозитории core.autocrlf=true, .gitattributes для tausik/ пуст. `git ls-files --eol` на файлах, полученных ЧЕКАУТОМ и с тех пор не переписанных инструментом: CHANGELOG.md — i/lf w/crlf, README.md — i/lf w/crlf. На закреплённом дереве: renar/README.md — i/lf w/lf, attr «text eol=lf». Файлы tausik/ сейчас показывают w/lf только потому, что их только что записал экспортёр, а не git.

ПОЧЕМУ ЭТО БЛОКЕР 1.8. Git-native состояние — заглавная фича релиза. Первое, что делает новый пользователь под Windows, — клонирует репозиторий; второе — получает красный гейт на нетронутом дереве. Задача renar-tree-gitattributes-lf (закрыта 2026-06-14) чинила этот же класс для renar/ и в своём scope_exclude сознательно сузила правило до renar/. Дерево tausik/ появилось позже и правила не получило.

ОБЪЁМ. Строка в .gitattributes плюс тест, который проверяет закрепление СВОЙСТВОМ, а не перечнем каталогов (конвенция #354): всякий каталог, который экспортёр объявляет своим, обязан быть закреплён на LF. Источник перечня — state_serialize.ENTITY_DIRS и корень дерева, а не список в тесте, иначе шестая сущность добавится и правило снова отстанет.

## Acceptance Criteria

1. .gitattributes закрепляет дерево tausik/ на LF: `git check-attr eol -- tausik/tasks/<любой>.md` возвращает lf, а `git ls-files --eol tausik/` показывает attr «text eol=lf» для каждого файла дерева.
2. Закрепление проверяется СВОЙСТВОМ, а не перечнем каталогов (конвенция #354). Тест выводит проверяемый набор из ИСТОЧНИКА — корня дерева и state_serialize.ENTITY_DIRS — и требует, чтобы каждый выведенный путь был покрыт правилом .gitattributes. Добавление шестого вида сущности без правила валит тест, а не проходит молча.
3. Кросс-платформенно, на живом git, а не на строковой проверке атрибута: во временном репозитории с core.autocrlf=true файл дерева после свежего чекаута остаётся LF. В том же тесте держится и ПРЕМИСА — файл ВНЕ правила при тех же настройках становится CRLF. Без второй ветви тест зеленел бы и на сломанном правиле.
4. НЕГАТИВ И ГРАНИЦА. Правило не расползлось на репозиторий: `git check-attr eol` на CHANGELOG.md НЕ возвращает lf, то есть существующие файлы не переформатируются. Существующий контракт не ослаблен: подмена LF на CRLF внутри файла дерева по-прежнему видна как дрейф — tests/test_state_export.py::test_check_tree_detects_crlf_corruption остаётся зелёным.
5. `tausik state export --check` зелёный после правки; полный pytest зелёный; ruff и mypy чистые.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert / убрать строку правила из .gitattributes и удалить добавленный тест. Изменений в коде нет, схема и миграции не затрагиваются. Худший исход отката — возврат к текущему состоянию, то есть к ложному дрейфу на свежем клоне под Windows; потери данных откат вызвать не может.

## Journal

- 2026-07-28T20:08:20Z [implementation] — Реализация. .gitattributes: добавлено правило `tausik/** text eol=lf` с комментарием, который называет причину и отсылает к тесту, а не пересказывает список каталогов. Новый файл tests/test_state_tree_eol_pin.py, 4 теста в двух классах. ПРОВЕРКА ФАЛЬСИФИЦИРУЕМОСТИ ВЫПОЛНЕНА ДО ЗАЯВЛЕНИЯ О ЗЕЛЁНОМ (конвенция #351). Правило временно закомментировано, прогон повторён: 2 failed, 2 passed. Упали ровно содержательные — test_every_projected_directory_resolves_to_lf и test_tree_stays_lf_while_an_unpinned_file_converts, причём второй показал фактические байты `b'---\r\nslug: probe\r\n---\r\n\r\nbody\r\n'`, то есть чекаут действительно сконвертировал файл дерева. Правило восстановлено, повторный прогон 4 passed. Значит тест меряет правило, а не своё окружение. Замер на живом репозитории: `git check-attr eol` даёт lf для tausik/tasks/kb-export-tasks.md и renar/README.md, «unspecified» для CHANGELOG.md — правило действует и за пределы дерева не вышло. `tausik state export --check` — OK, 2107 файлов. Ренормализации индекса не потребовалось: файлы уже лежали i/lf w/lf, поэтому ни один файл дерева не появился в git status из-за атрибута (19 изменённых в tausik/ — это записи БД этой сессии, а не смена переводов строк). О ДВУХ ОСТАВЛЕННЫХ ТЕСТАХ, чтобы их не сочли лишними. test_registry_is_non_empty охраняет саму проверку: при пустом ENTITY_DIRS список путей выродился бы в один элемент, и покрывающий тест стал бы вакуумным, продолжая зеленеть. test_pin_does_not_reach_outside_the_tree держит границу, от которой отказались ещё в renar-tree-gitattributes-lf: сплошное `* eol=lf` починило бы дерево и переформатировало чужие файлы. CHANGELOG EN+RU обновлены парно.
- 2026-07-28T20:27:08Z [implementation] — AC-1: ✓ tests/test_state_tree_eol_pin.py::TestTreeIsPinned::test_every_projected_directory_resolves_to_lf — плюс замер на живом репозитории: `git check-attr eol -- tausik/tasks/kb-export-tasks.md` даёт lf, `git ls-files --eol` показывает i/lf w/lf. AC-2: ✓ tests/test_state_tree_eol_pin.py::TestTreeIsPinned::test_every_projected_directory_resolves_to_lf и ::test_registry_is_non_empty — проверяемый набор выводится из state_serialize.ENTITY_DIRS и из project_cli_state._resolve_out_dir (того же резолвера, которым пользуется CLI), а не из списка в тесте. Второй тест охраняет первый: при пустом реестре сверка выродилась бы в один путь и продолжала зеленеть, ничего не проверяя. AC-3: ✓ tests/test_state_tree_eol_pin.py::TestPinSurvivesACheckout::test_tree_stays_lf_while_an_unpinned_file_converts — временный репозиторий, клон с core.autocrlf=true, реальное правило скопировано из shipped .gitattributes байт в байт. Премиса держится в том же тесте: контрольный файл ВНЕ дерева обязан вернуться в CRLF, иначе зелёный означал бы лишь песочницу, где конвертация не сработала. AC-4: ✓ tests/test_state_tree_eol_pin.py::TestTreeIsPinned::test_pin_does_not_reach_outside_the_tree — CHANGELOG.md, README.md и scripts/state_serialize.py не получают eol=lf; на живом репозитории `git check-attr eol -- CHANGELOG.md` печатает «unspecified». Существующий контракт не ослаблен: tests/test_state_export.py::test_check_tree_detects_crlf_corruption зелёный в полном прогоне. AC-5: ✓ Полный pytest 6494 passed, 24 skipped, 0 failed за 813.24s. ruff check — All checks passed. mypy — Success, 314 файлов. `tausik state export --check` — OK, 2107 файлов. AC-6 (CHANGELOG): ✓ Парные записи добавлены в CHANGELOG.md и CHANGELOG.ru.md в шапку [Unreleased]. ФАЛЬСИФИЦИРУЕМОСТЬ ПРОВЕРЕНА ПРОГОНОМ ДО ЗАЯВЛЕНИЯ О ЗЕЛЁНОМ (конвенция #351): правило временно закомментировано, прогон дал 2 failed / 2 passed. Упали именно содержательные, и тест чекаута показал фактические байты b'---\r\nslug: probe\r\n---\r\n\r\nbody\r\n' — то есть конвертация реально произошла, а не была предположена. После восстановления правила 4 passed. Domain: осмысленность вне тестов. Дефект найден не рассуждением, а предупреждением живого git при обычном `tausik state export` в этой же сессии. Проверка «что делает git на самом деле» проведена на файлах, полученных чекаутом, а не записанных инструментом: CHANGELOG.md и README.md показывали w/crlf, renar/README.md (закреплённый) — w/lf. То есть механизм подтверждён на трёх реальных файлах репозитория до того, как был написан тест. Ренормализации индекса правило не потребовало — файлы дерева уже лежали i/lf w/lf, и ни один не появился в git status из-за атрибута. Negative: негативные сценарии прогнаны как проверки ОТСУТСТВИЯ эффекта. (1) Отсутствие расползания правила — три файла вне дерева не получают lf. (2) Отсутствие ослабления существующего контракта — детектор CRLF-порчи внутри файла остаётся зелёным. (3) Отсутствие вакуумной проверки — тест на непустой реестр. (4) Отсутствие ложного зелёного в песочнице — контрольный файл обязан сконвертироваться.
- 2026-07-28T20:27:43Z [done] — Root cause (integration-mismatch): дерево tausik/ введено эпиком team-state-in-git как ВТОРОЕ производное дерево проекта, но не внесено в .gitattributes, где первое (renar/**) уже закреплено на eol=lf ровно по этой причине. Генератор пишет LF, чекаут git при core.autocrlf=true переписывает в CRLF, а check_tree читает с выключенной universal-newline трансляцией и видит порчу — то есть два корректных по отдельности механизма дают красный гейт на стыке. Prevention: правило теперь проверяется тестом, который выводит покрываемые каталоги из реестра экспортёра (state_serialize.ENTITY_DIRS) и из резолвера корня дерева, а не из списка в тесте, поэтому шестой вид сущности упадёт громко. Общий вывод шире одной задачи и записан памятью #356: новое производное дерево обязано быть внесено в КАЖДЫЙ реестр, знающий про предыдущее, а проверить это надо grep-ом по имени предыдущего дерева ДО закрытия вводящей задачи. О ПРЕДУПРЕЖДЕНИИ «COMPLEXITY UNDERSTATED: declared simple but touched 23 behaviour-bearing files of 26». Предупреждение ЛОЖНОЕ и уже заведено дефектом complexity-proxy-counts-state-projection. Фактическая работа задачи — одна строка правила в .gitattributes, один новый тестовый файл и парные записи в двух CHANGELOG, то есть четыре файла. Остальные 22 из 26 — сгенерированная проекция БД (tausik/tasks/*.md, tausik/decisions/*.md, tausik/memory/*.md), попавшая в объявленную область потому, что gate верификации требует объявлять ВСЁ изменённое в дереве, а автотриггер перегенерирует проекцию при каждой записи в журнал. Сложность НЕ занижена; complexity остаётся simple сознательно.
