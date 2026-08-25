---
slug: bolshoe-revyu-sessii-129-chetyre-audita-reliza-1-8-diff
title: "Большое ревью сессии #129: четыре аудита релиза 1.8 (diff, архитектура, доки, продукт)"
type: context
tags:
  - audit
  - release-1.8
  - review
  - session-129
task: s129-review-fixes
edges: []
---

Четыре параллельных аудита ветки release/1.8-batch-s126. Что найдено и куда заведено.

ДИФФ (adversarial): changelog-гейт доказывал байтовую грязь, а не содержание — пустая строка проходила и писала в журнал «verified»; конфиг гейта падал fail-open с оправданием на несуществующую проверку в doctor; _project_has_key читал повреждённый ключ как «ключа нет»; receipt show/export резолвили ключ от cwd. Всё закрыто в s129-review-fixes.

ПРОДУКТ: 24 записи [Unreleased] — все про гейты, НИ ОДНОЙ пользовательской фичи; decision #161 добавил ~23 задачи в релиз, который #145 запрещает тегировать до полного завершения → релиз, который не может выйти. Рекомендация: расцепить тег (landscape-2026-h2 → 1.8.0, shared-knowledge → 1.9.0). Гейт changelog БЛОКИРОВАЛ канонический /ship (commit на шаге 7, close на шаге 8) — исправлено. .tausik/ в gitignore ⇒ 30МБ знаний в одном файле без бэкапа и без второго человека: тасок-БД не разделяется между разработчиками, чек некому показать (kb-export-* / kb-global-* — правильный фикс, не начаты). Нет способа переоткрыть задачу.

АРХИТЕКТУРА: filesize-гейт деформирует архитектуру — 100 из 278 модулей scripts/ САМИ пишут в докстринге, что это split ради гейта; 6 файлов ровно по 400 строк; при этом реальные god-объекты гейту не видны (ProjectService 117 публичных методов через 9 миксинов, SQLiteBackend 129), а единственный настоящий god-модуль (handlers.py, 1289 строк) явно ИСКЛЮЧЁН. Движок физически продублирован 5× (301 .py × 5 = 273940 строк) — из-за этого существует bootstrap_drift-гейт и 59 sys.path.insert. Цены моделей: opus-4-8 отсутствует в таблице ⇒ вся стоимость сессий = $0.

ДОКИ: матрица соответствия SENAR зовёт Warning'ами гейты, которые реально блокируют (QG-0 scope, Rule 2, Rule 5); hooks.md не знает двух флагманских хуков 1.8; ru/senar.md прямо противоречит en/senar.md по правилам 4-6; дрейф-сканер счётчиков СЛЕП из-за regex (\s+hooks не матчит «21 real-time hooks») ⇒ gen_doc_constants --check зелёный при устаревших числах. constants.json при этом честен.

Заведено: cost-pricing-missing-opus-48, doctor-hardcodes-claude-dir, gate-registry-single-source, block-messages-phantom-go-and-platform, docs-enforcement-drift-matrix, hooks-bypass-config-trust-tiers, status-cli-mcp-divergence, git-exec-single-wrapper, project-config-god-module-split.
