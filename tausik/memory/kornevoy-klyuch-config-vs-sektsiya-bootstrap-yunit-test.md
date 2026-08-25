---
slug: kornevoy-klyuch-config-vs-sektsiya-bootstrap-yunit-test
title: "Корневой ключ config vs секция bootstrap: юнит-тест генератора НЕ видит тихий no-op проводки"
type: gotcha
tags:
  - bootstrap
  - config
  - silent-no-op
  - testing
task: critical-output-mode-no-op-bootstrap-caveman
edges: []
---

.tausik/config.json имеет ДВА уровня, и их легко перепутать:
- КОРЕНЬ: context_tier, output_mode, brain, gates, rag — «настройки проекта».
- Секция `bootstrap`: core_skills, extension_skills, installed_skills, ide, stacks, _meta.

load_bootstrap_config() возвращает КОРТЕЖ `(config, full_cfg)`, где config = full_cfg['bootstrap'] (ВЛОЖЕННАЯ секция), а full_cfg = корень. bootstrap_ide получает параметром `config` — то есть СЕКЦИЮ. Прочитать из неё корневой ключ = молча получить дефолт.

ЧТО СЛУЧИЛОСЬ (v1.7.0, поймано ревью, не тестами): resolve_output_mode(config) вместо resolve_output_mode(full_cfg). Пользователь ставит задокументированный корневой output_mode=caveman → генераторы получают 'off' → bootstrap печатает «Done!», exit 0, режим не применён, предупреждения нет. ТИХИЙ NO-OP.

ПОЧЕМУ ТЕСТЫ ПРОСПАЛИ — главный урок: юнит-тесты вызывали build_full_body(output_mode='caveman') и генераторы НАПРЯМУЮ, передавая значение руками. Это доказывает, что генератор рендерит директиву, и НИЧЕГО не говорит о том, доставляет ли конфиг это значение. Тот же самообман, что «каждое зеркало проходило свои проверки в отдельности».

ПРАВИЛО: любой НОВЫЙ корневой ключ конфига обязан иметь INTEGRATION-тест, который пишет реальный .tausik/config.json и гоняет настоящий bootstrap_ide, а не юнит-тест генератора. Образец: tests/test_caveman_wiring_integration.py. И тест обязан быть проверен на красноту ДО фикса (вернуть баг → убедиться, что краснеет).

ПРОВЕРЕНО (класс, не экземпляр): остальные корневые читатели корректны — is_brain_enabled(full_cfg), resolve_context_tier(_cfg_for_tier). output_mode был единственным. Смежное: bootstrap.py грузит корень ДВАЖДЫ (full_cfg в load_bootstrap_config + _cfg_for_tier отдельно) — не дефект, но дублирование.
