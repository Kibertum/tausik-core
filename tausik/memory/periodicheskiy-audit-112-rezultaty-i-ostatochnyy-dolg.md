---
slug: periodicheskiy-audit-112-rezultaty-i-ostatochnyy-dolg
title: "Периодический аудит #112: результаты и остаточный долг"
type: context
tags: []
task: null
edges: []
---

Quality sweep SENAR Rule 9.5, сессия #112 (аудит был просрочен на 3 сессии).

ЧИСТО: ruff по scripts/ tests/ bootstrap/; gen_doc_constants --check; audit_orphan_files (нет сирот); audit_unused_python (нет неиспользуемых top-level символов); audit_translation_drift (структурного расхождения en/ru нет, 3 пары помечены skip-маркером намеренно).

ОСТАТОЧНЫЙ ДОЛГ по filesize (>400 строк, все доставшиеся, ни один не введён в этой сессии):
- harness/claude/mcp/project/handlers.py 1273
- harness/claude/mcp/project/tools.py 980
- harness/claude/mcp/codebase-rag/server.py 562
- scripts/doc_drift_scanners.py 524
- harness/claude/mcp/codebase-rag/rag_indexer.py 412
- scripts/service_knowledge.py 406
- scripts/project_cli_ops.py 403
Гейт filesize их не ловит, потому что бежит по relevant_files задачи, а не по всему дереву. Два скрипта (403 и 406) на грани — упадут при первом же касании. handlers.py — каноническое MCP-дерево по решению #134, там же 6 doc-count сайтов по конвенции #204, поэтому его деление дороже обычного.

НАЙДЕНО И ЗАВЕДЕНО: audit-stale-docs-scope-noise — audit_stale_docs ходит по файловой системе, а не по индексу git, поэтому печатает ИМЕНА файлов из gitignored docs/research/_internal/ (конфликт с конвенцией #176 о неразглашении внутренних исследований), и не исключает docs/research/*, хотя исключает локализованные docs/{en,ru}/research/*.

НЕ ЗАВЕДЕНО, требует проверки в следующий аудит: audit_pytest_dedupe выдаёт 11+ групп «похожих» тестов по сигнатуре. Похоже на ложные срабатывания сигнатурного сравнения на параметризованных тестах, но не проверено предметно. Если группы окажутся настоящими дублями — это лишнее время в обеих линиях.</content>
<parameter name="tags">["audit", "senar-9.5", "filesize-debt", "session-112"]
