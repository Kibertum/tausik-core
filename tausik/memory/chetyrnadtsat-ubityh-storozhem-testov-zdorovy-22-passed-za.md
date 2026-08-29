---
slug: chetyrnadtsat-ubityh-storozhem-testov-zdorovy-22-passed-za
title: "Четырнадцать убитых сторожем тестов ЗДОРОВЫ: 22 passed за 824 s при пороге 600"
type: context
tags:
  - ci
  - hang-guard
  - measurement
  - tests
task: null
edges: []
---

Замер #189: pytest по трём файлам (bootstrap_skills_coverage, bootstrap_real, stress) с -m '' -o faulthandler_timeout=600, последовательно, Windows — 22 passed за 824.32 s (13m44s), exit 0. Все четырнадцать тестов, которые сторож зависаний убивал и в один поток, и под xdist, ПРОХОДЯТ: они медленные, а не сломанные. Их настоящее время измерено впервые (убитый тест не попадает в --durations): двенадцать лежат плотной группой 52.47-65.35 s, из них семь превышают 60 s даже в изоляции без нагрузки; test_100_sessions 43.43 s последовательно против 77.09 s под нагрузкой xdist. Порог 60 рассекает группу посередине, запас не 11x и не 1.09x, а 0.92x. Состав четырнадцати: skills_coverage 8 (весь файл) + bootstrap_real 4 (весь файл) + stress 2; прежняя запись «9+4+2» арифметически неверна. Оба файла целиком исключены --ignore и в GitHub CI (обе джобы), и в GitLab CI, поэтому двенадцать из четырнадцати не выполняются нигде.
