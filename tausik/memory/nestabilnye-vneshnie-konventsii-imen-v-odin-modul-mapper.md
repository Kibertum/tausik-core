---
slug: nestabilnye-vneshnie-konventsii-imen-v-odin-modul-mapper
title: "Нестабильные внешние конвенции имён — в один модуль-маппер + лит-линт"
type: convention
tags:
  - conventions
  - lint
  - otel
  - pattern
  - telemetry
task: l26-otel-export
edges: []
---

Когда интегрируешь внешнюю схему/конвенцию имён с НЕСТАБИЛЬНЫМ статусом (напр. OTel GenAI semconv: open-telemetry/semantic-conventions-genai, 0 релизов, статус Development на 2026-07-18) — держи ВСЕ имена в ОДНОМ модуле-маппере, а остальной код обращается к ним через константы. Добавь тест-линт, падающий на литерал имени (напр. r"[\"']gen_ai\.") где угодно вне маппера. Тогда churn конвенции = правка одного файла, а не расползание по кодовой базе. Маппер должен САМ декларировать нестабильность (docstring + CONVENTIONS_STATUS/SOURCE как данные), чтобы будущий churn читался как ожидаемое, а не как баг. Реализовано в scripts/otel_semconv.py (l26-otel-export). Тот же приём применим к любому внешнему API/протоколу в статусе Development.
