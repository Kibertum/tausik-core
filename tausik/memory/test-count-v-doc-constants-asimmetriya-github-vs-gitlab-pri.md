---
slug: test-count-v-doc-constants-asimmetriya-github-vs-gitlab-pri
title: "test_count в doc-constants: асимметрия GitHub vs GitLab при добавлении тестов"
type: gotcha
tags: []
task: null
edges: []
---

test_count в docs/_generated/constants.json зависит от окружения: 3.11=4742/4744, 3.13=4706 (модули с importorskip выпадают без опц.пакетов). Поэтому: GitHub Actions doc-check = --skip-test-count (матрица 3.11-3.13, счётчик разный) — test_count advisory. GitLab doc-check = строгий --check (один детерминированный раннер 3.12+PyYAML) — test_count гейтится. Мейнтейнер генерит constants.json на Windows-3.11+PyYAML → 3.11==3.12 счётчик, поэтому GitLab строгий проходит. При ДОБАВЛЕНИИ/УДАЛЕНИИ тестов: (1) python scripts/gen_doc_constants.py (реген test_count); (2) обновить бейджи И прозу '<N> tests'/'<N> тестов' в README.md И README.ru.md (кросс-файловый скан их гейтит); (3) проверять локально с установленным PyYAML, иначе счётчик занижен. Юнит test_constants_json_file_matches_live сам исключает test_count. Связано с [[event-window-boundary-flake]].
