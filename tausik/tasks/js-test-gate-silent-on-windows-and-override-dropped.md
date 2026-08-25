---
slug: js-test-gate-silent-on-windows-and-override-dropped
title: "GitLab #9: гейт js-test не запускается на Windows, а переопределение команды молча отбрасывается"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - check-result-conflates-could-not-run-with-passed
completed_at: null
---

## Goal

Тикет GitLab #9, заведён шесть дней назад, задачи под ним НЕ БЫЛО — обнаружено разбором трекеров в сессии #178. Две половины, обе тихие. Первая: на Windows npm вызывается без расширения, поэтому гейт js-test не запускается вовсе. Вторая: переопределение команды гейта молча отбрасывается — это уже записано общей памятью как gotcha «отвергнутая команда гейта не краснеет, а молча откатывается к дефолту», то есть дефект известен и подтверждён на другом проекте.

ПОЧЕМУ ЭТО ЗАДАЧА ИСТОРИИ ПРИМИТИВОВ, А НЕ ОТДЕЛЬНЫЙ ДЕФЕКТ: обе половины суть один класс — результат проверки не различает «не смогло выполниться» и «прошло». Гейт, который не нашёл npm, и гейт, чью команду отвергли, обязаны давать третий исход с причиной, а не молчать. Закрывается вместе с check-result-conflates-could-not-run-with-passed и служит его приёмочным примером: пока эти две половины не краснеют, задача примитивов не выполнена.

НЕГАТИВНОЕ: расширение .cmd для npm нельзя чинить точечной правкой в одном месте — надо проверить, сколько ещё гейтов зовут внешние инструменты по голому имени, и лечить классом. Иначе следующий тикет придёт про yarn или pnpm.

## Acceptance Criteria

## Plan

## Rollback

## Journal
