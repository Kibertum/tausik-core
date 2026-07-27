---
slug: format-evidence-pri-zakrytii-zadachi-chto-parsit-task-done
title: "Формат evidence при закрытии задачи (что парсит task done)"
type: convention
tags: []
task: null
edges: []
---

Парсер доказательств в task done ждёт КОНКРЕТНЫЕ маркеры, иначе выдаёт NOTE даже при полном фактическом покрытии. Проверено эмпирически 2026-07-18 на трёх закрытиях. (1) Пофакторное покрытие: строки вида AC-1: ✓ ... AC-2: ✓ — формат 1. ✓ парсер НЕ засчитывает (даёт 0/N criteria). (2) Негативный сценарий: нужен литеральный префикс Negative: — фразы негатив или НЕГАТИВНЫЙ СЦЕНАРИЙ не распознаются. (3) Для tier=high нужна ссылка на тест в виде пути tests/test_file.py::TestClass::test_name — просто описание теста словами не засчитывается. (4) Domain: и Checklist: — отдельные строки, тоже по префиксу. Практический шаблон строки журнала: AC-1: ✓ <что> — tests/test_x.py::test_y | Negative: <кейс> — tests/test_x.py::test_z | Domain: <смысл вне тестов> | Checklist: scope/тесты/security/rollback.
