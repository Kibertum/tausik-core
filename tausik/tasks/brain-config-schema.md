---
slug: brain-config-schema
title: "Секция brain в .tausik/config.json"
status: done
epic: shared-brain
story: brain-onboarding-docs
complexity: simple
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py (добавить секцию brain, не трогать gates-логику), tests/test_brain_config.py (новый)"
scope_exclude: "scripts/brain_schema.py (не трогать — brain-local-schema закрыта), bootstrap/, .claude/, другие конфиг-файлы"
relevant_files:
  - "scripts/brain_config.py"
  - "tests/test_brain_config.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T00:02:34Z"
---

## Goal

Расширить project_config.py: новая секция brain = {enabled, project_names[], local_mirror_path, ttl_web_cache, ttl_decisions, private_url_patterns[]}. Валидация при старте. Defaults безопасные (enabled=false пока не пройден wizard).

## Acceptance Criteria

1) В scripts/project_config.py добавлена секция brain: DEFAULT_BRAIN dict с безопасными defaults (enabled=false, local_mirror_path='~/.tausik-brain/brain.db', notion_integration_token_env='NOTION_TAUSIK_TOKEN', database_ids={decisions:'',web_cache:'',patterns:'',gotchas:''}, project_names=[], ttl_web_cache_days=30, ttl_decisions_days=null, private_url_patterns=[]). 2) Публичные функции: load_brain(cfg)→merged dict с defaults; is_brain_enabled(cfg)→bool; validate_brain(cfg)→list[str] (ошибки валидации, пусто если ok); get_brain_mirror_path(cfg)→absolute expanded path; compute_project_hash(name)→16-hex SHA256. 3) Токен НЕ хранится в config — только имя env var; validate_brain предупреждает если enabled=true, но env var пуст. 4) validate_brain возвращает ошибки для: enabled=true + пустые database_ids; enabled=true + пустой token env; невалидный regex в private_url_patterns. 5) Expand ~ и env vars в local_mirror_path через os.path.expanduser + expandvars. 6) compute_project_hash канонизирует имя: strip().lower().replace(' ', '-') и возвращает SHA256(canonical)[:16]. 7) Tests в tests/test_brain_config.py: все 5 публичных функций покрыты (≥10 кейсов). 8) Gates: pytest зелёный + ruff clean на project_config.py/test_brain_config.py. 9) Evidence: файл+diff + pytest output + «AC verified: N. ... ✓».

## Plan

## Rollback

## Journal

- 2026-04-22T23:59:44Z [implementation] — AC verified: 1. scripts/brain_config.py создан с DEFAULT_BRAIN dict (safe defaults: enabled=False, mirror=~/.tausik-brain/brain.db, token_env=NOTION_TAUSIK_TOKEN, database_ids={4 категории:''}, project_names=[], ttl_web=30, ttl_decisions=None, private_url_patterns=[]) ✓ 2. Публичные функции: load_brain, is_brain_enabled, validate_brain, get_brain_mirror_path, compute_project_hash ✓ 3. Токен НЕ в config — только имя env var; validate_brain проверяет os.environ.get(token_env) ✓ 4. validate_brain: disabled=skip big checks; enabled+пустой db_id → ошибка на каждую категорию; enabled+пустой token env → ошибка; enabled+env var unset → ошибка; invalid regex / non-string в private_url_patterns → ошибка; ttl <=0 → ошибка ✓ 5. get_brain_mirror_path: expanduser + expandvars + abspath ✓ 6. compute_project_hash: canonical = strip().lower() + re.sub(r"\s+","-") → SHA256[:16]; детерминирован для "My Project" == "my-project" == " My Project " ✓ 7. tests/test_brain_config.py — 20 тестов, pytest 20/20 в 0.08s + регресс 103/103 (brain_config+brain_schema+gates) ✓ 8. Gates: ruff clean на project_config.py/brain_config.py/test_brain_config.py; filesize: project_config.py 357 строк, brain_config.py 126 (оба < 400 лимит после рефакторинга — сначала складывал в project_config.py, получил 471, вынес в отдельный модуль) ✓ 9. Evidence: 2 файла (brain_config.py + test_brain_config.py), project_config.py не изменён по итогу. Импорт в тесте — import brain_config (not project_config).
