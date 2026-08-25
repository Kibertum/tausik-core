---
slug: state-git-roundtrip-gate
title: "Разгитигнорить tausik/ и добавить гейт round-trip: файлы и БД обязаны сходиться"
status: done
epic: team-state-in-git
story: state-in-branch-mvp
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: ".gitignore, scripts/gate_state_roundtrip.py (new), scripts/gate_registry.py, tests/test_gate_registry.py, tests/test_state_roundtrip_gate.py (new), .tausik/config.json (auto_export для этого репо)"
scope_exclude: "state_export.py/state_serialize.py/state_import.py (уже готовы в state-git-export — не трогать), глобальный дефолт state.auto_export, привязка гейта к task-done триггеру, коммит/пуш 1953 файлов (только материализация в рабочее дерево)"
relevant_files:
  - ".gitignore"
  - "scripts/gate_state_roundtrip.py"
  - "scripts/gate_registry.py"
  - "tests/test_state_roundtrip_gate.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T20:37:54Z"
---

## Goal

Финальный кусок MVP: сделать git-native стейт видимым в репозитории и защитить его от дрейфа механически — ровно в духе проекта (проверка, а не обещание).

Объём: (1) Разгитигнорить каталог стейта (tausik/ или подпуть) — убрать соответствующую строку/добавить исключение в .gitignore, оставив приватное (venv, кэши, ключи, receipts, логи) по-прежнему игнорируемым. Только durable-проекция едет в git. (2) Гейт round-trip: экспорт из текущей БД обязан давать РОВНО те файлы, что лежат в git (нет расхождения БД↔файлы). Если разошлись — гейт красный с указанием, что запустить (state export / sync). Это ловит: забыл закоммитить экспорт; правил файл руками мимо БД; недетерминированный сериализатор. (3) Гейт быстрый (входит в verify/ task-done путь без заметной цены). (4) Догфуд: этот самый репозиторий проходит гейт после первого полного экспорта.

Негативные сценарии: расхождение хотя бы в одном поле одной сущности → гейт красный; лишний/недостающий файл → красный; приватные пути (venv/keys) НЕ попадают под гейт и остаются игнорируемыми.

Зависит от state-git-export.

## Acceptance Criteria

1. .gitignore: строка `tausik/` (line 80) убрана — durable-проекция трекается; приватное ОСТАЁТСЯ ignored (.tausik/ runtime, *.pem/*.key, .rag/, IDE-dirs, *.log, receipts). Проверка: git check-ignore подтверждает tausik/tasks/x.md НЕ ignored, а .tausik/tausik.db ignored.
2. Новый gate_state_roundtrip.py (impl run_state_roundtrip_gate_for(gate,files)->(bool,str)), зарегистрирован в gate_registry _SCOPED, trigger=[commit] (НЕ task-done — иначе auto-close родителя даёт ложный drift; commit — где 'забыл закоммитить экспорт' реально важно), severity block. Запускает build_tree(svc) + check_tree(tausik/) на свежем read-соединении; красный при любом расхождении файлы↔БД (лишний/недостающий файл, отличие поля) с remediation `tausik state export`. Read-only, fail-open на ошибке (гейт не роняет commit). Gracefully SKIP когда tausik/ не материализован (opt-in, не ломает чужие проекты/fresh clone).
3. state.auto_export включён для ЭТОГО репо (.tausik/config.json), чтобы триггеры держали tausik/ в синке; глобальный дефолт (OFF) для чужих проектов НЕ меняется.
4. Догфуд: `tausik state export` материализует полный tree (~1953 файла), гейт зелёный (check совпадает).
НЕГАТИВ: расхождение в одном поле сущности → красный; лишний/недостающий файл → красный; приватные пути (.tausik/, *.key) НЕ под гейтом и остаются ignored (тесты); tausik/ отсутствует → SKIP (не ложный красный на fresh clone).
5. Полная суита зелёная; test_gate_registry обновлён под новый гейт; scoped verify PASS. НЕ коммитить (решение пользователя — 1953 файла остаются untracked для ревью).

## Plan

[{"step": "Verify ignore separation: tausik/ (durable) trackable, .tausik/ (runtime) ignored \u2014 make explicit via .gitignore comment", "done": true}, {"step": "Write gate_state_roundtrip.py (build_tree+check_tree, commit-trigger, opt-in skip, fail-open)", "done": true}, {"step": "Register state_roundtrip in gate_registry _SCOPED", "done": true}, {"step": "Enable state.auto_export in this repo config", "done": true}, {"step": "Materialize full export (tausik state export) + confirm gate green (dogfood)", "done": true}, {"step": "Tests: green/drift/extra/missing/skip/private-paths/registration", "done": true}, {"step": "Full suite + mypy + bootstrap sync + CHANGELOG", "done": true}, {"step": "verify + close (no commit \u2014 user decision)", "done": true}]

## Rollback

git revert коммита (когда будет) — новый gate-модуль + строка регистрации + строка .gitignore + config; откат возвращает tausik/ в ignore и убирает гейт. Материализованные 1953 файла untracked — удаляются `rm -rf tausik/`. Без миграций БД.

## Journal

- 2026-07-26T20:27:13Z [implementation] — Реализовано. Открытие: tausik/ (durable) УЖЕ трекабельно (не-dotted), .tausik/ (runtime) игнорируется line 20 — разделение структурное по имени; AC1 удовлетворён, добавил явный комментарий в .gitignore (защита от случайного bare tausik/). gate_state_roundtrip.py: build_tree(свежий read-backend)+check_tree, trigger=[commit] block, SKIP при отсутствии tausik/tausik.db (opt-in), ExportError→red, прочие→fail-open. Зарегистрирован в gate_registry _SCOPED (10-й scoped гейт). state.auto_export=true в .tausik/config.json (глобальный дефолт OFF не тронут). Догфуд: tausik state export → 2000 файлов, гейт ЗЕЛЁНЫЙ ('matches DB export 2000 files'). Тесты test_state_roundtrip_gate.py (8): skip/green/hand-edit-red/extra-red/missing-red/private-paths-not-gated/fail-open-no-db/registration-commit-not-taskdone. Все зелёные. ruff+mypy чисты (mypy Success 2 files), bootstrap --ide all синхронизирован, drift зелёный. CHANGELOG EN+RU. Полная суита запущена. НЕ коммичу (решение пользователя — 2000 файлов untracked для ревью).
- 2026-07-26T20:37:51Z [implementation] — AC verified: 1. ✓ tausik/ (durable, не-dotted) трекабельно, .tausik/ (runtime) ignored line 20; git check-ignore: tausik/tasks/foo.md НЕ ignored, .tausik/tausik.db ignored. .gitignore комментарий защищает от bare tausik/. test_private_paths_are_not_under_the_gate 2. ✓ gate_state_roundtrip.py build_tree+check_tree, зарегистрирован _SCOPED trigger=[commit] block. test_state_roundtrip_gate.py::TestGateRegistration (commit не task-done), test_green/test_red_on_single_field_hand_edit/extra/missing, test_skips_when_no_tree/fails_open_on_missing_db. mypy Success 3. ✓ state.auto_export=true в .tausik/config.json; _auto_export_enabled()==True. Глобальный дефолт OFF не тронут (isolated trigger-тесты зелёные) 4. ✓ Domain: tausik state export → 2000 файлов материализованы, run_state_roundtrip_gate()==(True,'matches DB export 2000 files') на ЖИВОМ репо. Полная суита 6056 passed/0 failed (constants regen после +8 тестов). verify scoped PASS. bootstrap drift зелёный
