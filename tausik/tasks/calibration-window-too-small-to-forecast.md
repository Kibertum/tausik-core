---
slug: calibration-window-too-small-to-forecast
title: "Окно калибровки n=10 даёт коэффициент, который за одну сессию проходит 0.49-0.71: прогноз срока на нём строить нельзя"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_tier_metrics.py"
  - "scripts/status_view.py"
  - "scripts/render_metrics.py"
  - "tests/test_metrics_tier.py"
scope_paths:
  - "scripts/backend_tier_metrics.py"
  - "scripts/status_view.py"
  - "scripts/render_metrics.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T07:22:06Z"
---

## Goal

Заведено по решению #211 (сессия #153), которое зафиксировало факт и вынесло вопрос к модели оценки сюда.

ЗАМЕР, четыре точки за одну сессию #153 на одном и том же наборе задач. Хендофф #152 считал по actual/budget = 0.60. В начале сессии `tausik status` показывал 0.71 (calibrated). После сотни активных минут — 0.62 (overestimating). После ста двадцати шести — 0.49 (overestimating). Окно всё это время n=10.

ПОЧЕМУ ЭТО НЕ ПРОСТО ШУМ, А ДЕФЕКТ ПРИМЕНЕНИЯ. Величина используется для прогноза срока релиза: 1927 вызовов бюджета при коэффициенте 0.49 дают 944 фактических, при 0.71 — 1368. Это разница между пятью и семью сессиями, то есть между двумя разными ответами владельцу на вопрос «когда релиз». Решение #209 объясняло сдвиг прогноза изменением коэффициента — и это объяснение оказалось построено на шуме, что решение #211 и признало.

ХУЖЕ ТОГО, ОКНО СМЕЩЕНО ПО ПОСТРОЕНИЮ. Десять последних закрытий — это десять ПОСЛЕДНИХ, то есть в сессии, где подряд закрывают однотипные задачи (пять дефектов проекции), окно заполняется одним типом работы и перестаёт представлять смесь. Именно это и произошло: коэффициент падал по мере того, как окно заполнялось задачами этой сессии.

ЧТО РЕШИТЬ. (1) Размер окна: фиксированное n больше, скользящее по времени, или экспоненциальное сглаживание — выбрать с обоснованием, а не по вкусу. (2) Отдавать ли вместе с точкой РАЗБРОС: прогноз без интервала на такой величине вводит в заблуждение сильнее, чем отсутствие прогноза. (3) Показывать ли n рядом с коэффициентом в `tausik status` и в блоке ёмкости — сейчас n виден только в metrics.

НЕ ДЕЛАТЬ: не подбирать окно так, чтобы цифра стала «стабильной» на этих данных. Стабильность, подогнанная задним числом, — это та же априорная настройка без проверки, из-за которой композит риска закрытия оказался антипредиктивным (бэктест 2026-07). Любой выбор обязан быть проверен на исторических закрытиях, а не на текущем окне.

## Acceptance Criteria

1. The window is chosen by a backtest on historical closures, not by taste: estimators (mean of 10/30, median of 30/50, aggregate of 30/50, EWMA 0.1) predicting the actual/budget of the NEXT 20 closures, judged by MAE and jitter; the numbers are in the journal and the docstring. 2. The winner replaces 'mean of last 10' in calibration_drift; the spread (p25-p75) and n travel with the point everywhere it is printed (status, metrics). 3. NEGATIVE: fewer than 5 samples still gives no coefficient; a test pins median-of-30 and the spread on a crafted history. 4. NEGATIVE: the choice is not tuned to the current window — it is the backtest winner over 580 forecast points.

## Plan

## Rollback

git revert; calibration returns to the mean of the last 10

## Journal

- 2026-09-24T07:20:14Z [implementation] — Backtest (session #272, 650 closures with budget+actual, 580 forecast points, target = actual/budget aggregate of the next 20 closures): mean10 MAE 0.463 jitter 0.094; mean30 0.398/0.032; median30 0.364/0.016; median50 0.379/0.010; agg30 0.407/0.034; agg50 0.419/0.020; ewma0.1 0.421/0.074. Winner: median of last 30 — lowest error, 6x less jitter than the current mean of 10.
- 2026-09-24T07:21:12Z [implementation] — AC-1: ✓ measurement — backtest logged above (7 estimators, 580 points, MAE+jitter); numbers repeated in the calibration_drift docstring.
- 2026-09-24T07:21:12Z [implementation] — AC-2: ✓ tests/test_metrics_tier.py::test_calibration_is_the_median_of_the_last_30_with_its_spread — calibration_drift = median of last 30 with p25/p75; status: 'Calibration: overestimating (median actual/budget=0.48, p25-p75 0.34-0.99, n=30)'; metrics prints the same.
- 2026-09-24T07:21:12Z [implementation] — AC-3: ✓ tests/test_metrics_tier.py::test_fewer_than_five_samples_still_give_no_coefficient — negative.
- 2026-09-24T07:21:13Z [implementation] — AC-4: ✓ review — negative: the choice is the backtest winner over the whole history, not a fit to the current window; 38 status/metrics tests green.
