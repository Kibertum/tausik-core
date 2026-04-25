---
name: markitdown
description: "Convert DOCX / PPTX / XLSX / HTML / EPUB to markdown via Microsoft markitdown. Triggers: markitdown, convert document, extract docx, extract pptx, extract xlsx, .docx file, .pptx file, .xlsx file."
effort: fast
context: inline
---

# /markitdown — Document → Markdown extraction

Optional capability built on [Microsoft markitdown](https://github.com/microsoft/markitdown). Wraps `MarkItDown().convert()` so the same flow works whether you call it from a skill, the CLI, or scripts.

## When to use

- DOCX / PPTX / XLSX / HTML / EPUB / MOBI / audio / image — formats Claude Code's built-in `Read` tool doesn't handle
- Batch / non-interactive doc extraction (e.g. inside `/batch` plans)

## When NOT to use

- **PDF** — prefer `/pdf` skill (uses Claude Code's built-in `Read` which has tuned PDF support and pages parameter)
- **Plain text / markdown / code files** — just use `Read`

## Install (opt-in)

TAUSIK convention #19: zero external deps. markitdown is **not** in the bootstrap manifest. Install on demand:

```bash
pip install 'markitdown[all]'           # all converters incl. audio/image OCR
pip install 'markitdown[docx,pptx,xlsx]' # narrower install
```

`tausik doc extract` reports a clear error if markitdown isn't available — it does not crash TAUSIK.

## Usage

### CLI

```bash
.tausik/tausik doc extract path/to/file.docx
.tausik/tausik doc extract slides.pptx --format=pptx
```

Output: markdown on stdout. Exit code 1 if markitdown is missing or extraction fails.

### From scripts

```python
import doc_extract

md = doc_extract.extract_to_markdown("path/to/file.xlsx")
if md is None:
    # markitdown missing, file missing, or extraction failed (diagnostic on stderr)
    fall_back_to_something_else()
else:
    print(md)
```

`extract_to_markdown()` never raises — callers can rely on `None` for graceful degradation.

## Operations

| Command | Action |
|---------|--------|
| `.tausik/tausik doc extract <file>` | Convert to markdown |
| `.tausik/tausik doc extract <file> --format=X` | With format hint (logged, markitdown auto-detects) |
| `python -c "import doc_extract; print(doc_extract.is_available())"` | Check if markitdown is installed |

## Gotchas

- **Audio / image conversion needs extras.** `pip install 'markitdown[all]'` pulls in heavy deps (Azure cognitive services, OCR). Use `[docx,pptx,xlsx]` for office-only.
- **Large XLSX files** can produce huge markdown. Consider `head -n 200` before piping to context.
- **HTML** extraction loses some structure (script/style stripped). Use `Read` for small HTML files.
- **Reserved future use:** `brain_post_webfetch` hook may eventually use `doc_extract` for HTML pages — not implemented yet.
