---
slug: pip-ne-imeet-flaga-no-config-ni-v-odnoy-versii-mok-v-teste
title: "pip не имеет флага --no-config ни в одной версии; мок в тесте это скрыл"
type: gotcha
tags:
  - mocks
  - pip
  - skills
  - supply-chain
  - testing
task: review-skill-supplychain-findings
edges: []
---

Проверено на pip 22.3.1 (ensurepip в venv, Python 3.11) и pip 26.0.1: оба отвечают 'no such option: --no-config' с rc=2, флага нет в 'pip install --help'. Настоящий флаг — --isolated (есть в обеих). Отсюда: hardening из v1.3.4 (med-batch-1-hooks #2) ронял install_skill_deps ВСЕГДА, а не только на старом pip.

Что именно что отключает (прочитано в pip/_internal/configuration.py, а не по памяти): iter_config_files всегда отдаёт kinds.GLOBAL и kinds.SITE. isolated=True пропускает только USER-конфиг и PIP_*-переменные. PIP_CONFIG_FILE=os.devnull подавляет ENV+USER, но GLOBAL (C:\ProgramData\pip\pip.ini, /etc/pip.conf) и SITE (venv/pip.ini) читаются всё равно — подтверждено 'pip config debug'. Значит ни один из двух механизмов не отключает конфиг целиком.

Реальная защита от подмены индекса — явный --index-url в командной строке: pip кладёт конфиг в defaults парсера (cli/parser.py:_update_defaults), а явный аргумент CLI перебивает defaults.

Урок про тест: tests/test_skill_manager.py:748 утверждал `'--no-config' in captured['cmd']`, мокая subprocess. Тест был зелёный ровно потому, что никогда не звал настоящий pip. Флаг для внешнего бинаря нельзя закреплять моком — нужен хотя бы один прогон против реального исполняемого файла.
