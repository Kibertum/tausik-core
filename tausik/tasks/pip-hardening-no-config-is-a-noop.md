---
slug: pip-hardening-no-config-is-a-noop
title: "--no-config не существует ни в одной версии pip; hardening v1.3.4 — фикция, тест зелёный на моке"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: review-skill-supplychain-findings
scope: "scripts/skill_manager.py (install_skill_deps), tests/test_skill_manager.py. Зеркала — через bootstrap."
scope_exclude: "Не трогать логику подписей и CRLF (отдельные задачи). Не пушить без разрешения."
relevant_files:
  - "scripts/skill_manager.py"
  - "scripts/skill_deps.py"
  - "tests/test_skill_manager.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/tausik_version.py"
  - pyproject.toml
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T12:33:07Z"
---

## Goal

Убрать несуществующий флаг --no-config, заменить hardening на реально работающий (явный --index-url на командной строке бьёт любой pip.conf), исправить ложное сообщение 'pip is too old' и перестать запускать pip дважды. Проверено: pip 22.3.1 и pip 26.0.1 обе отвечают 'no such option: --no-config' (rc=2), флага нет в --help. PIP_CONFIG_FILE=os.devnull подавляет только ENV+USER конфиги: 'pip config debug' показывает, что GLOBAL (C:\ProgramData\pip\pip.ini) и SITE (venv/pip.ini) читаются всё равно. tests/test_skill_manager.py:748 мокает subprocess и потому утверждает наличие флага, который не принимает ни один pip.

## Acceptance Criteria

1) --no-config удалён; двойной запуск pip и ложное сообщение «pip is too old» убраны. 2) Защита от подмены индекса реально работает: явный --index-url в аргументах (CLI бьёт defaults парсера) плюс --isolated (существует в pip 22.3.1 и 26.0.1). 3) Тест на строке ~748 больше не закрепляет несуществующий флаг. 4) Появился тест, который проверяет флаги против НАСТОЯЩЕГО pip, а не мока. 5) Зеркала синхронны после bootstrap. Негативные сценарии: 6) Ошибка, если хоть один передаваемый флаг не принимается реальным pip (rc=2, 'no such option'). 7) Ошибка, если тест проверяет флаги только моком — именно мок скрыл баг с v1.3.4. 8) Ошибка, если стрипанье PIP_* из env потеряно: hardening не должен ослабнуть. 9) Ошибка, если полный прогон даёт новое падение против базы 4319 passed / 12 skipped.

## Plan

## Rollback

git checkout -- scripts/skill_manager.py tests/test_skill_manager.py, затем bootstrap для зеркал. Правка локальна в install_skill_deps.

## Journal

- 2026-07-10T12:25:57Z [implementation] — AC verified: 1. ✓ --no-config удалён, двойной запуск и ложная строка убраны — TestInstallDepsEnvHardening::test_pip_install_runs_exactly_once (ровно 1 вызов) и ::test_no_false_claim_about_old_pip (в stdout нет 'too old' и '--no-config'). 2. ✓ Защита реальна — ::test_pip_install_pins_the_index_on_the_command_line: '--isolated' в cmd, cmd[index('--index-url')+1] == DEFAULT_PIP_INDEX_URL. Основание вычитано в pip/_internal/configuration.py: iter_config_files отдаёт GLOBAL и SITE безусловно, isolated снимает только USER+env, а cli/parser.py::_update_defaults кладёт конфиг в defaults, которые перебивает явный аргумент. 3. ✓ Тест на несуществующем флаге заменён; 'assert "--no-config" in cmd' больше нет. 4. ✓ Проверка против НАСТОЯЩЕГО pip — TestPipFlagsAreRealFlags::test_every_flag_we_pass_is_accepted_by_real_pip (rc=0) плюс сторож пробы ::test_probe_rejects_a_nonexistent_flag (--no-config -> rc=2). Офлайн, через 'pip install <флаг> --help'. 5. ✓ Зеркала: cmp skill_manager.py против .claude/.cursor/.kilo/.qwen после bootstrap --ide all — identical x4. 6. ✓ (негативный) Ни один передаваемый флаг не отвергается реальным pip: проверено на 22.3.1 (venv) и 26.0.1 (система), обе дают rc=0 на '--isolated --index-url ... --quiet' и rc=2 на '--no-config'. 7. ✓ (негативный) Флаги больше не проверяются одним моком: добавлен прогон против настоящего pip. 8. ✓ (негативный) Стрипанье PIP_* не потеряно — ::test_pip_install_strips_pip_index_url_from_env проходит. 9. ✓ (негативный) Полный прогон 4323 passed, 12 skipped, 0 failed; 4323+12+120 deselected = 4455 = constants.json. Domain: сквозная проверка вне тестов — одноразовый venv с pip 22.3.1 (ensurepip, ровно сломанный случай): 'import six' до установки rc=1, install_skill_deps(requires=['six']) вернул True, 'import six' после rc=0, version=1.17.0. То есть requires действительно ставится, а не просто собирается правильная строка аргументов.
- 2026-07-10T12:33:02Z [implementation] — Root cause (integration-mismatch): контракт внешнего бинаря был предположен, а не проверен. v1.3.4 добавила pip-флаг --no-config, которого не существует ни в одной версии pip (22.3.1 и 26.0.1 обе дают 'no such option', rc=2); pip падал на каждой установке зависимостей скилла. Ошибка прожила два минорных релиза, потому что единственный тест мокал subprocess.run и утверждал наличие флага в собранной строке аргументов — мок не может отвергнуть флаг, который отвергает настоящий pip. Тот же корень породил и ложное сообщение 'pip is too old' в правке c3e7ed9: автор объяснил отказ старым pip, снова не спросив pip. Prevention: любой флаг/аргумент внешнего исполняемого файла закрепляется хотя бы одним тестом против реального бинаря, а не против мока; для pip это офлайн-проба 'pip install <флаг> --help' (rc=0 существует, rc=2 нет), и сама проба стережётся тестом, который проверяет, что она умеет говорить «нет» (TestPipFlagsAreRealFlags::test_probe_rejects_a_nonexistent_flag). Мок остаётся только там, где проверяется наша логика (стрипанье PIP_*, однократность запуска), а не чужой контракт.
