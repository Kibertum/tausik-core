---
slug: v155-readme-kilo-zai
title: "v1.5.5 README EN+RU: добавить Kilo Code + z.ai/GLM (заголовочные фичи отсутствуют)"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: null
tier: moderate
call_budget: 50
defect_of: null
scope: "README.md, README.ru.md (только секции Supported IDEs / install / features intro). Возможно docs/en|ru если там тот же пробел."
scope_exclude: "Не менять исходный код/логику; CHANGELOG[1.5.5] уже корректен."
relevant_files:
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T11:02:19Z"
---

## Goal

README.md и README.ru.md не отражают заголовочные фичи 1.5.5: в таблице Supported IDEs нет Kilo Code, нет упоминания z.ai/GLM model routing, install-секция без --ide kilo. Добавить, синхронизировать EN/RU, прогнать doc-checks, переопубликовать релиз.

## Acceptance Criteria

1. README.md таблица Supported IDEs содержит строку Kilo Code (статус first-class). 2. z.ai/GLM model routing упомянут (ссылка на docs/en/kilo-zai.md). 3. install/quickstart показывает --ide kilo. 4. README.ru.md синхронизирован с EN. 5. gen_doc_constants --check + doc_drift_scanners + pytest зелёные. 6. Релиз v1.5.5 переопубликован (gitlab main + github orphan + gh release notes согласованы). 7. Ошибка/abort (негативный сценарий): при ошибке doc-drift, расхождении счётчиков (124 MCP / 13 skills / 4401 tests) с реальностью, ИЛИ отклонении внешнего push — НЕ публиковать, остановиться и доложить; частичная выкладка недопустима.

## Plan

## Rollback

git revert README-коммита; тег v1.5.5 вернуть на 266ba6c; github orphan вернуть на предыдущий снапшот через reflog.

## Journal

- 2026-06-19T11:02:05Z [implementation] — AC verified: 1. ✓ README.md таблица Supported IDEs содержит Kilo Code (First-class via MCP, гейты на task start/done). 2. ✓ z.ai/GLM callout + ссылка docs/en/kilo-zai.md + family-aware routing в features. 3. ✓ install: --ide claude|cursor|qwen|kilo. 4. ✓ README.ru.md синхронизирован (RU-зеркало). 5. ✓ gen_doc_constants --check exit 0, doc_drift_scanners exit 0, pytest green (verify cache). 6. ✓ переиздано: gitlab main→c61bbb1 + тег; github orphan 8084cc9 + тег v1.5.5; gh release резолвится (isDraft=false, README Kilo row в снапшоте 3×). 7. ✓ negative: счётчики (124/13/4401) не трогал, drift=0, push не отклонён — abort не понадобился. Knowledge: [[181]] orphan-релиз паттерн уже покрывает flow.
- 2026-06-19T11:02:19Z [implementation] — AC verified: 1.✓ Kilo Code в таблице IDE. 2.✓ z.ai/GLM callout+ссылка+routing. 3.✓ install --ide kilo. 4.✓ RU синхронизирован. 5.✓ doc-checks+pytest green. 6.✓ переиздано gitlab+github+gh release (README Kilo row в снапшоте). 7.✓ abort не понадобился. verify cache green.
