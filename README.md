# mathdoc — Markdown + LaTeX → PDF Pipeline

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue)](LICENSE)

**mathdoc** ist eine Python-Bibliothek, die Markdown-Dokumente mit LaTeX-Matheausdrücken in professionell formatierte PDFs konvertiert — inklusive MathJax-Rendering und flexiblem Theming.

## Pipeline

```
Markdown (.md) ──► HTML ──► MathJax (SVG) ──► WeasyPrint ──► PDF
```

1. **Markdown → HTML** — Konvertiert Markdown (mit optionalem YAML-Frontmatter-Stripping) in HTML. LaTeX-Mathe (`$...$`, `$$...$$`) wird während der Konvertierung geschützt, um Korruption durch den Markdown-Parser zu verhindern.
2. **MathJax-Rendering** — Rendert LaTeX-Matheausdrücke via MathJax (Node.js) in inline-SVG. Fallback zu ungerenderten Formeln, wenn Node.js/MathJax nicht verfügbar ist.
3. **PDF-Erzeugung** — Wrap in vollständiges HTML-Dokument mit Theme-basiertem CSS und generiert PDF via WeasyPrint. Optionales Logo-Einbetten und Seitenkopfzeilen.

## Theming

mathdoc bietet ein flexibles Theming-Framework:

| Theme | Beschreibung | Logo | Schrift | Akzentfarbe |
|-------|-------------|------|---------|-------------|
| **`AcademicTheme`** (Default) | Wissenschaftlich, neutral, kein Branding | ❌ Kein Logo | Inter | dezent blau (#2c5282) |
| **`HestiaOSTheme`** | HestiaOS Corporate Design | ✅ Optional | Space Grotesk + Inter | Hestia Orange (#E66A2C) |
| **`Theme`** (Basis) | Eigene Anpassungen | ✅ Beliebig | frei wählbar | frei wählbar |

## Installation

```bash
# Core-Bibliothek
pip install mathdoc

# Mit MCP-Server-Unterstützung
pip install mathdoc[mcp]
```

### Abhängigkeiten

- **Python ≥ 3.11**
- **Node.js** (für MathJax-Rendering) — optional, Fallback zu ungerenderten Formeln
- **System-Bibliotheken für WeasyPrint** — siehe [WeasyPrint Installation Guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)

## Verwendung

### Akademisches Paper (Default — kein Logo, kein Branding)

```python
from mathdoc import mathdoc_pipeline, MathdocConfig

config = MathdocConfig(
    markdown_text="# Hello World\n\n$E = mc^2$ ist eine bekannte Formel.",
    header_title="Mein Paper",
)
pdf_bytes = mathdoc_pipeline(config)
```

### HestiaOS Corporate Design (mit Logo)

```python
from mathdoc import mathdoc_pipeline, MathdocConfig, HestiaOSTheme

config = MathdocConfig(
    markdown_text="# Jahresbericht 2025\n\n...",
    theme=HestiaOSTheme(
        logo_path="./hestiaos_logo.png",
        header_title="Jahresbericht",
    ),
)
pdf_bytes = mathdoc_pipeline(config)
```

### Eigenes Theme

```python
from mathdoc import mathdoc_pipeline, MathdocConfig, Theme

MEIN_CSS = """
body { font-family: "Times New Roman", serif; color: #000; }
h1 { color: #8B0000; border-bottom: 2px solid #8B0000; }
"""

config = MathdocConfig(
    markdown_text="# Custom Document",
    theme=Theme(css=MEIN_CSS, primary_color="#8B0000"),
)
pdf_bytes = mathdoc_pipeline(config)
```

### Mit Datei

```python
config = MathdocConfig(
    markdown_file="dokument.md",
    strip_frontmatter=True,
    output_path="ausgabe.pdf",
)
mathdoc_pipeline(config)
```

### Pipeline-Schritte einzeln

```python
from mathdoc import markdown_to_html, mathjax_render_html, build_pdf_document
from mathdoc import AcademicTheme

# Schritt 1: Markdown → HTML
html_body = markdown_to_html("# Hallo $\\alpha + \\beta$")

# Schritt 2: MathJax-Rendering
html_rendered = mathjax_render_html(html_body, mathjax_js="./render_math.cjs")

# Schritt 3: PDF bauen (mit Theme)
full_html, pdf_bytes = build_pdf_document(
    html_rendered,
    theme=AcademicTheme(header_title="Mein Dokument"),
)
```

### Als MCP-Server

```bash
python3 -m mathdoc.server
```

Registrierung in `cline_mcp_settings.json`:

```json
{
  "mathdoc": {
    "command": "python3",
    "args": ["-m", "mathdoc.server"],
    "env": {}
  }
}
```

Der Server stellt zwei Tools bereit:

- **`markdown_to_pdf`** — Konvertiert Markdown-Text (mit LaTeX) direkt zu PDF
  - Parameter: `markdown_text`, `header_title`, `css`, `strip_frontmatter`, `theme` ("academic"|"hestiaos"), `include_logo`, `output_path`
- **`markdown_file_to_pdf`** — Liest eine Markdown-Datei und konvertiert sie zu PDF
  - Parameter: `file_path`, `header_title`, `css`, `strip_frontmatter`, `theme`, `include_logo`, `output_path`

## API

### `mathdoc_pipeline(config: MathdocConfig) -> bytes`

Führt die vollständige Pipeline aus. Gibt PDF-Bytes zurück.

### `MathdocConfig`

| Feld | Typ | Default | Beschreibung |
|------|-----|---------|-------------|
| `markdown_text` | `str` | `""` | Markdown-Quelltext |
| `markdown_file` | `str` | `""` | Pfad zu einer Markdown-Datei (Alternative) |
| `strip_frontmatter` | `bool` | `True` | YAML-Frontmatter entfernen |
| `theme` | `Optional[Theme]` | `None` | Theme-Instanz (None = AcademicTheme) |
| `css` | `Optional[str]` | `None` | Benutzerdefiniertes CSS (überschreibt theme.css) |
| `header_title` | `str` | `""` | Titel in der PDF-Seitenkopfzeile (überschreibt theme.header_title) |
| `mathjax_js` | `str` | `""` | Pfad zum MathJax-Renderer-Skript |
| `output_path` | `str` | `""` | Ausgabepfad für PDF (leer = Bytes zurückgeben) |
| `timeout` | `int` | `30` | Timeout für MathJax-Rendering (Sekunden) |

### `Theme` (Basis)

| Feld | Typ | Default | Beschreibung |
|------|-----|---------|-------------|
| `css` | `Optional[str]` | `None` | CSS-String (None = ACADEMIC_CSS) |
| `logo_path` | `str` | `""` | Pfad zum Logo-Bild (leer = kein Logo) |
| `header_title` | `str` | `"MathDoc"` | Titel in der Kopfzeile |
| `header_show` | `bool` | `True` | Seitenkopfzeile anzeigen |
| `page_numbers` | `bool` | `True` | Seitenzahlen unten anzeigen |
| `primary_color` | `str` | `"#1a1a2e"` | Primärfarbe (Akzente, Tabellen-Header) |

### `AcademicTheme(Theme)`

Wissenschaftliches Default-Theme. Kein Logo, dezente Farben, Fokus auf Lesbarkeit.

- `primary_color`: `"#1a1a2e"` (dunkles Nachtblau)
- CSS: `ACADEMIC_CSS` (Inter-Schrift, helle Akzente)

### `HestiaOSTheme(Theme)`

HestiaOS Corporate Design. Mit optionalem Logo, Hestia Orange, Space Grotesk.

- `primary_color`: `"#E66A2C"` (Hestia Orange)
- CSS: `HESTIA_CSS` (Space Grotesk + Inter, Orange-Akzente)

### `markdown_to_html(md_text, strip_frontmatter=True) -> str`

Konvertiert Markdown zu HTML, schützt LaTeX-Mathe vor Korruption.

### `mathjax_render_html(html_body, mathjax_js="", timeout=30) -> str`

Rendert LaTeX-Mathe in HTML via MathJax (Node.js) zu inline-SVG.

### `build_pdf_document(html_body, theme=None, css=None, logo_path="", header_title="") -> tuple[str, bytes]

Wrap HTML in vollständiges Dokument mit Theme/CSS und generiert PDF.

## CSS-Konstanten

- **`ACADEMIC_CSS`** — Neutrales, wissenschaftliches CSS (Default). Kein Branding.
- **`HESTIA_CSS`** — HestiaOS Corporate Design CSS. Mit Orange-Akzenten, Space Grotesk.
- **`DEFAULT_CSS`** — Alias für `ACADEMIC_CSS` (Abwärtskompatibilität).

## Entwicklung

```bash
# Repository klonen
git clone https://github.com/hestiaos/mathdoc.git
cd mathdoc

# Entwicklungs-Abhängigkeiten installieren
pip install -e ".[dev]"

# Tests ausführen
pytest
```

## Lizenz

Apache-2.0 — siehe [LICENSE](LICENSE).
