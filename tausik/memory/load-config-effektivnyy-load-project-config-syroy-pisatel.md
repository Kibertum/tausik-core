---
slug: load-config-effektivnyy-load-project-config-syroy-pisatel
title: "load_config() эффективный, load_project_config() сырой — писатель обязан брать сырой"
type: gotcha
tags: []
task: l26-config-trust-tiers
edges: []
---

После введения трастовых тиров у конфига ДВА загрузчика, и путать их опасно:

- load_config() — ЭФФЕКТИВНЫЙ конфиг: project + user (~/.tausik/config.json) + managed ($TAUSIK_MANAGED_CONFIG), плюс применённая политика «project может только ужесточать». Для ЧИТАТЕЛЕЙ (их ~47).
- load_config_with_rejections() — то же плюс список отклонений. Для doctor и интроспекции.
- load_project_config() — СЫРОЙ project-слой. Для ПИСАТЕЛЕЙ.

Почему это не косметика: save_config() сохраняет то, что ему дали. Писатель, сделавший load_config() → мутация → save_config(), скопирует настройки пользователя и оператора в файл репозитория, который едет в git. Round-trip писателей три: ProjectService.gate_enable/gate_disable, MCP _handle_gate_toggle, brain _ConfigOps. Все переведены на сырой слой; на утечку есть тест (test_config_trust.py::TestReaderWriterSplit::test_gate_toggle_does_not_leak_user_tier_into_the_repo_file).

Побочный эффект для ТЕСТОВ: патчить надо тот загрузчик, который зовёт код под тестом. tests/test_doctor_auto_verify_hint.py патчил project_config.load_config, а doctor перешёл на load_config_with_rejections — патч тихо промахнулся, и doctor начал читать реальный конфиг машины. Симптом был не «ошибка патча», а исчезнувшее предупреждение.

Изоляция сьюты: tests/conftest.py::_isolated_config_trust_tiers (autouse) уводит TAUSIK_USER_CONFIG во временный путь и снимает TAUSIK_MANAGED_CONFIG — иначе сьюта измеряет машину разработчика.</content>
<parameter name="tags">["config", "trust-tiers", "tests", "mocking"]
