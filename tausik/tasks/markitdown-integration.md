---
slug: markitdown-integration
title: "Интеграция Microsoft markitdown вместо ручных парсеров документов"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/doc_extract.py (new), scripts/project_parser_ops.py (new doc subcommand), scripts/project_cli_ops.py (new cmd_doc handler), scripts/project.py (dispatch), agents/skills/markitdown/SKILL.md (new), tests/test_doc_extract.py (new), references/markitdown-integration.md (new short doc)"
scope_exclude: "agents/skills/pdf/, agents/skills/excel/, scripts/brain_*.py, bootstrap/"
relevant_files:
  - "scripts/doc_extract.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "tests/test_doc_extract.py"
  - "agents/skills/markitdown/SKILL.md"
  - "references/markitdown-integration.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T11:09:50Z"
---

## Goal

Заменить наши ручные парсеры документов (pdf skill, excel skill, docx чтение) на Microsoft markitdown (https://github.com/microsoft/markitdown) — единый инструмент конвертации PDF/DOCX/PPTX/XLSX/HTML/EPUB/audio/image в markdown, оптимизированный под LLM-контекст. Это упрощает fallback-пути, уменьшает код в scripts/, и повышает точность извлечения текста (особенно таблиц из PDF/XLSX). Интегрируется как CLI-оркестратор (.tausik/tausik doc extract <file>) + обновление skill/pdf, skill/excel, опционально brain_webfetch classifier для HTML-страниц.

## Acceptance Criteria

1. Discovery (done implicitly): TAUSIK не имеет ручных парсеров — pdf/excel skills делегируют Claude Code Read и user venv. Markitdown добавляется как opt-in capability, не как замена.
2. Новый scripts/doc_extract.py: extract_to_markdown(path, *, format_hint=None) -> str | None — lazy import markitdown, graceful None на ImportError + warning в stderr (не блокирует TAUSIK без markitdown installed)
3. CLI: tausik doc extract <file> [--format=X] — печатает markdown на stdout, exit 1 если markitdown не установлен
4. Новый skill agents/skills/markitdown/SKILL.md документирует: когда использовать (DOCX/PPTX/XLSX/HTML которые Read tool не покрывает), как установить (pip install markitdown[all]), fallback на /pdf для PDF
5. TAUSIK convention #19 (zero external deps) сохраняется: markitdown — optional, не в bootstrap. README / references упоминает opt-in.
6. Ошибка/граничный случай: ImportError на markitdown → return None + diag (не raise, не block)
7. Ошибка/граничный случай: путь не существует → return None + diag
8. Ошибка/граничный случай: markitdown сам raise (corrupt file) → catch + return None + diag
9. Тесты: mock markitdown class (sys.modules), верифицируем (a) happy path возвращает str, (b) ImportError → None, (c) missing path → None, (d) markitdown raise → None
10. pytest + ruff clean; full suite остаётся зелёным
11. Scope: НЕ трогаем pdf/excel skill (они работают через Claude Code Read), НЕ блокируем pytest на отсутствие markitdown

## Plan

## Rollback

## Journal

- 2026-04-25T11:09:39Z [implementation] — Discovery + AC verified: ✓1 Discovery — TAUSIK не имел "ручных парсеров" (pdf/excel skills делегируют Claude Code Read tool); markitdown добавлен как opt-in capability ✓2 scripts/doc_extract.py с extract_to_markdown(path, format_hint) — lazy import markitdown, graceful None на ImportError + stderr diag ✓3 CLI: tausik doc extract <file> [--format=X], exit 1 на missing/error ✓4 agents/skills/markitdown/SKILL.md с install instructions + redirects PDF → /pdf ✓5 zero-deps convention #19 сохранён: markitdown НЕ в bootstrap, opt-in через user venv ✓6 ImportError → None ✓7 missing path → None ✓8 exception → None (catch RuntimeError, etc.) ✓9 +11 tests + 1 skipif integration test (passes when markitdown installed): is_available, happy_path, format_hint logged, falls_back_to_markdown_attr (old shape compat), missing markitdown, missing path, empty path, exception, unexpected shape, non-string ✓10 pytest 11/11 passed (1 skipped, markitdown not installed locally), ruff clean ✓11 scope: pdf/excel skills untouched, brain_*.py untouched, bootstrap untouched. references/markitdown-integration.md документирует rationale + usage + future webfetch hook integration possibility.
