"""mathdoc.core — Core pipeline: Markdown + LaTeX → HTML → PDF.

Usage:
    from mathdoc.core import mathdoc_pipeline, MathdocConfig, AcademicTheme

    config = MathdocConfig(markdown_text="# Hello $E=mc^2$")
    pdf_bytes = mathdoc_pipeline(config)

    # Mit HestiaOS Corporate Design
    from mathdoc.core import HestiaOSTheme
    config = MathdocConfig(
        markdown_text="# Interner Report",
        theme=HestiaOSTheme(logo_path="./logo.png"),
    )
    pdf_bytes = mathdoc_pipeline(config)
"""

import re
import os
import base64
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional

import markdown
import weasyprint


# ══════════════════════════════════════════════════════════════════════════
# Theming Framework
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class Theme:
    """Basis-Theme für mathdoc-PDFs.

    Steuert das visuelle Erscheinungsbild: CSS, Logo, Header, Seitenzahlen.
    Subklassen können spezifische Voreinstellungen liefern (z.B. AcademicTheme,
    HestiaOSTheme).

    Args:
        css: CSS-String für das Dokument. None = ACADEMIC_CSS (Default).
        logo_path: Pfad zu einem Logo-Bild (PNG). Leer = kein Logo.
        header_title: Titel in der Seitenkopfzeile.
        header_show: Seitenkopfzeile anzeigen.
        page_numbers: Seitenzahlen unten anzeigen.
        primary_color: Primärfarbe (für Akzente, Tabellen-Header, etc.).
    """
    css: Optional[str] = None
    logo_path: str = ""
    header_title: str = "MathDoc"
    header_show: bool = True
    page_numbers: bool = True
    primary_color: str = "#1a1a2e"


@dataclass
class AcademicTheme(Theme):
    """Neutrales, wissenschaftliches Theme — kein Logo, kein Branding.

    Empfohlen für Paper, Preprints, Reports, Konferenz-Submissions.
    Dezente Farben, serifenlose Schrift, Fokus auf Lesbarkeit.
    """
    css: Optional[str] = None  # wird in build_pdf_document mit ACADEMIC_CSS belegt
    logo_path: str = ""
    header_title: str = "MathDoc"
    header_show: bool = True
    page_numbers: bool = True
    primary_color: str = "#1a1a2e"


@dataclass
class HestiaOSTheme(Theme):
    """hestiaOS Corporate Design — mit Logo, Hestia Orange, Space Grotesk.

    Empfohlen für interne Dokumentation, Präsentationen, Kunden-Output.
    """
    css: Optional[str] = None  # wird mit HESTIA_CSS belegt
    logo_path: str = ""
    header_title: str = "MathDoc"
    header_show: bool = True
    page_numbers: bool = True
    primary_color: str = "#E66A2C"


# ══════════════════════════════════════════════════════════════════════════
# CSS: Academic Default (wissenschaftlich, neutral)
# ══════════════════════════════════════════════════════════════════════════
#
# Font-Hinweis: @font-face mit url() wird verwendet statt @import, da
# WeasyPrint @import von Google Fonts nicht zuverlässig lädt, was zu
# Kästchen (□) für nicht-darstellbare Zeichen führen kann.

ACADEMIC_PRIMARY = "#1a1a2e"
ACADEMIC_MUTED = "#555555"
ACADEMIC_LIGHT = "#e0e0e0"
ACADEMIC_SURFACE = "#f5f5f5"
ACADEMIC_ACCENT = "#2c5282"  # dezent blau für code/links

ACADEMIC_CSS = f"""
@font-face {{
    font-family: 'Inter';
    font-style: normal;
    font-weight: 300 700;
    src: url(https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2) format('woff2');
}}

@page {{
    size: A4;
    margin: 2.2cm 2cm 2.5cm 2cm;
    @bottom-center {{
        content: counter(page);
        font-size: 9pt;
        color: {ACADEMIC_MUTED};
        font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    }}
    @top-left {{
        content: "MathDoc";
        font-size: 7.5pt;
        color: {ACADEMIC_MUTED};
        font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
        font-style: italic;
    }}
}}

body {{
    font-family: "Inter", "DejaVu Serif", "Liberation Serif", serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: {ACADEMIC_PRIMARY};
    background: #ffffff;
}}

.logo-header {{
    text-align: center;
    margin-bottom: 0.6cm;
    padding-top: 0.3cm;
}}
.logo-header img {{
    height: 1.8cm;
    width: auto;
}}

h1 {{
    font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 20pt;
    font-weight: 700;
    margin-top: 1.2cm;
    margin-bottom: 0.3cm;
    color: {ACADEMIC_PRIMARY};
    border-bottom: 2.5px solid {ACADEMIC_LIGHT};
    padding-bottom: 0.3cm;
    page-break-before: always;
    letter-spacing: -0.02em;
}}
h1:first-of-type {{
    page-break-before: avoid;
    margin-top: 0;
}}

h2 {{
    font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 14pt;
    font-weight: 600;
    margin-top: 0.8cm;
    margin-bottom: 0.25cm;
    color: {ACADEMIC_PRIMARY};
    border-bottom: 1px solid {ACADEMIC_LIGHT};
    padding-bottom: 0.15cm;
    letter-spacing: -0.01em;
}}

h3 {{
    font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 12pt;
    font-weight: 600;
    margin-top: 0.6cm;
    margin-bottom: 0.2cm;
    color: #333333;
}}

h4 {{
    font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 11pt;
    font-weight: 500;
    margin-top: 0.4cm;
    margin-bottom: 0.15cm;
    color: {ACADEMIC_MUTED};
}}

p {{
    text-align: justify;
    margin: 0.2cm 0;
    orphans: 3;
    widows: 3;
}}

code {{
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Courier New", monospace;
    font-size: 8.5pt;
    background: {ACADEMIC_SURFACE};
    padding: 1px 5px;
    border-radius: 3px;
    color: {ACADEMIC_ACCENT};
}}

pre {{
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Courier New", monospace;
    font-size: 8pt;
    background: {ACADEMIC_SURFACE};
    border: 0.5px solid {ACADEMIC_LIGHT};
    border-left: 3px solid {ACADEMIC_ACCENT};
    padding: 0.3cm;
    margin: 0.3cm 0;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.35;
    page-break-inside: avoid;
    border-radius: 0 4px 4px 0;
}}
pre code {{
    background: none;
    padding: 0;
    font-size: 8pt;
    color: {ACADEMIC_PRIMARY};
}}

blockquote {{
    border-left: 3px solid {ACADEMIC_LIGHT};
    margin: 0.3cm 0;
    padding: 0.15cm 0.5cm;
    background: {ACADEMIC_SURFACE};
    font-style: italic;
    color: #333333;
    border-radius: 0 4px 4px 0;
}}

table {{
    border-collapse: collapse;
    width: 100%;
    margin: 0.35cm 0;
    font-size: 9pt;
    page-break-inside: avoid;
    border-radius: 4px;
    overflow: hidden;
}}
th, td {{
    border: 0.5px solid {ACADEMIC_LIGHT};
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
}}
th {{
    background: {ACADEMIC_PRIMARY};
    color: white;
    font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}}
tr:nth-child(even) {{
    background: {ACADEMIC_SURFACE};
}}

ul, ol {{
    margin: 0.15cm 0;
    padding-left: 1cm;
}}
li {{
    margin: 0.06cm 0;
}}

strong {{
    color: {ACADEMIC_PRIMARY};
    font-weight: 600;
}}
em {{
    color: #333333;
}}
a {{
    color: {ACADEMIC_ACCENT};
    text-decoration: none;
    border-bottom: 0.5px solid {ACADEMIC_ACCENT};
}}

hr {{
    border: none;
    border-top: 0.5px solid {ACADEMIC_LIGHT};
    margin: 0.4cm 0;
}}

dt {{
    font-weight: 600;
    margin-top: 0.2cm;
    color: {ACADEMIC_PRIMARY};
    font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
}}
dd {{
    margin-left: 0.5cm;
    margin-bottom: 0.1cm;
}}

mjx-container {{
    display: inline-block;
    text-align: left;
    line-height: 0;
    font-size: 1.05em;
}}
mjx-container[display="true"] {{
    display: block;
    text-align: center;
    margin: 0.4em 0;
    font-size: 1em;
}}
mjx-container svg {{
    display: inline-block;
    vertical-align: middle;
    overflow: visible;
}}

h1, h2, h3, h4 {{
    page-break-after: avoid;
}}

@media print {{
    body {{
        font-size: 10pt;
    }}
    pre {{
        font-size: 7.5pt;
    }}
}}
"""

# ── Alias für Abwärtskompatibilität ──────────────────────────────────────
DEFAULT_CSS = ACADEMIC_CSS


# ══════════════════════════════════════════════════════════════════════════
# CSS: HestiaOS Corporate Design
# ══════════════════════════════════════════════════════════════════════════
#
# Font-Hinweis: @font-face mit url() wird verwendet statt @import, da
# WeasyPrint @import von Google Fonts nicht zuverlässig lädt, was zu
# Kästchen (□) für nicht-darstellbare Zeichen führen kann.

HESTIA_ORANGE = "#E66A2C"
HESTIA_ORANGE_DARK = "#C84F18"
HESTIA_DARK = "#2F3136"
HESTIA_GRAPHITE_2 = "#3D4148"
HESTIA_MUTED = "#767C86"
HESTIA_LIGHT = "#E9EAEC"
HESTIA_WHITE = "#FFFFFF"
HESTIA_SURFACE = "#F7F8FA"

HESTIA_CSS = f"""
@font-face {{
    font-family: 'Space Grotesk';
    font-style: normal;
    font-weight: 400 700;
    src: url(https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mPbF4Cw.woff2) format('woff2');
}}
@font-face {{
    font-family: 'Inter';
    font-style: normal;
    font-weight: 300 700;
    src: url(https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2) format('woff2');
}}

@page {{
    size: A4;
    margin: 2.2cm 2cm 2.5cm 2cm;
    @bottom-center {{
        content: counter(page);
        font-size: 9pt;
        color: {HESTIA_MUTED};
        font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
    }}
    @top-left {{
        content: "MathDoc";
        font-size: 7.5pt;
        color: {HESTIA_MUTED};
        font-family: "Inter", "DejaVu Sans", "Liberation Sans", sans-serif;
        font-style: italic;
    }}
}}

body {{
    font-family: "Inter", "DejaVu Serif", "Liberation Serif", serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: {HESTIA_DARK};
    background: {HESTIA_WHITE};
}}

.logo-header {{
    text-align: center;
    margin-bottom: 0.6cm;
    padding-top: 0.3cm;
}}
.logo-header img {{
    height: 1.8cm;
    width: auto;
}}

h1 {{
    font-family: "Space Grotesk", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 20pt;
    font-weight: 700;
    margin-top: 1.2cm;
    margin-bottom: 0.3cm;
    color: {HESTIA_DARK};
    border-bottom: 2.5px solid {HESTIA_ORANGE};
    padding-bottom: 0.3cm;
    page-break-before: always;
    letter-spacing: -0.02em;
}}
h1:first-of-type {{
    page-break-before: avoid;
    margin-top: 0;
}}

h2 {{
    font-family: "Space Grotesk", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 14pt;
    font-weight: 600;
    margin-top: 0.8cm;
    margin-bottom: 0.25cm;
    color: {HESTIA_DARK};
    border-bottom: 1px solid {HESTIA_LIGHT};
    padding-bottom: 0.15cm;
    letter-spacing: -0.01em;
}}

h3 {{
    font-family: "Space Grotesk", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 12pt;
    font-weight: 600;
    margin-top: 0.6cm;
    margin-bottom: 0.2cm;
    color: {HESTIA_GRAPHITE_2};
}}

h4 {{
    font-family: "Space Grotesk", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 11pt;
    font-weight: 500;
    margin-top: 0.4cm;
    margin-bottom: 0.15cm;
    color: {HESTIA_MUTED};
}}

p {{
    text-align: justify;
    margin: 0.2cm 0;
    orphans: 3;
    widows: 3;
}}

code {{
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Courier New", monospace;
    font-size: 8.5pt;
    background: {HESTIA_SURFACE};
    padding: 1px 5px;
    border-radius: 3px;
    color: {HESTIA_ORANGE_DARK};
}}

pre {{
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Courier New", monospace;
    font-size: 8pt;
    background: {HESTIA_SURFACE};
    border: 0.5px solid {HESTIA_LIGHT};
    border-left: 3px solid {HESTIA_ORANGE};
    padding: 0.3cm;
    margin: 0.3cm 0;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.35;
    page-break-inside: avoid;
    border-radius: 0 4px 4px 0;
}}
pre code {{
    background: none;
    padding: 0;
    font-size: 8pt;
    color: {HESTIA_DARK};
}}

blockquote {{
    border-left: 3px solid {HESTIA_ORANGE};
    margin: 0.3cm 0;
    padding: 0.15cm 0.5cm;
    background: {HESTIA_SURFACE};
    font-style: italic;
    color: {HESTIA_GRAPHITE_2};
    border-radius: 0 4px 4px 0;
}}

table {{
    border-collapse: collapse;
    width: 100%;
    margin: 0.35cm 0;
    font-size: 9pt;
    page-break-inside: avoid;
    border-radius: 4px;
    overflow: hidden;
}}
th, td {{
    border: 0.5px solid {HESTIA_LIGHT};
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
}}
th {{
    background: {HESTIA_DARK};
    color: white;
    font-family: "Space Grotesk", "DejaVu Sans", "Liberation Sans", sans-serif;
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}}
tr:nth-child(even) {{
    background: {HESTIA_SURFACE};
}}

ul, ol {{
    margin: 0.15cm 0;
    padding-left: 1cm;
}}
li {{
    margin: 0.06cm 0;
}}

strong {{
    color: {HESTIA_DARK};
    font-weight: 600;
}}
em {{
    color: {HESTIA_GRAPHITE_2};
}}
a {{
    color: {HESTIA_ORANGE};
    text-decoration: none;
    border-bottom: 0.5px solid {HESTIA_ORANGE};
}}

hr {{
    border: none;
    border-top: 0.5px solid {HESTIA_LIGHT};
    margin: 0.4cm 0;
}}

dt {{
    font-weight: 600;
    margin-top: 0.2cm;
    color: {HESTIA_DARK};
    font-family: "Space Grotesk", "DejaVu Sans", "Liberation Sans", sans-serif;
}}
dd {{
    margin-left: 0.5cm;
    margin-bottom: 0.1cm;
}}

mjx-container {{
    display: inline-block;
    text-align: left;
    line-height: 0;
    font-size: 1.05em;
}}
mjx-container[display="true"] {{
    display: block;
    text-align: center;
    margin: 0.4em 0;
    font-size: 1em;
}}
mjx-container svg {{
    display: inline-block;
    vertical-align: middle;
    overflow: visible;
}}

h1, h2, h3, h4 {{
    page-break-after: avoid;
}}

@media print {{
    body {{
        font-size: 10pt;
    }}
    pre {{
        font-size: 7.5pt;
    }}
}}
"""


# ══════════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class MathdocConfig:
    """Configuration for the mathdoc pipeline.

    Args:
        markdown_text: The Markdown source text (with optional LaTeX $...$).
        markdown_file: Path to a Markdown file (alternative to markdown_text).
        strip_frontmatter: Remove YAML frontmatter (---...---) before processing.
        theme: Theme instance controlling CSS, logo, header, colors.
               If None, uses AcademicTheme().
        css: Custom CSS string (overrides theme.css if set).
        header_title: Title shown in PDF page header (overrides theme.header_title).
        mathjax_js: Path to the MathJax renderer script (render_math.cjs).
        output_path: Path for the generated PDF. If empty, returns bytes.
        timeout: Timeout in seconds for MathJax rendering.
    """
    markdown_text: str = ""
    markdown_file: str = ""
    strip_frontmatter: bool = True
    theme: Optional[Theme] = None
    css: Optional[str] = None
    header_title: str = ""
    mathjax_js: str = ""
    output_path: str = ""
    timeout: int = 30


# ══════════════════════════════════════════════════════════════════════════
# Math Protection (prevent Markdown parser from corrupting LaTeX)
# ══════════════════════════════════════════════════════════════════════════

def protect_math(md_text: str) -> tuple[str, dict[str, str]]:
    """Replace $...$ and $$...$$ with placeholders to protect from Markdown.

    Python's markdown library interprets curly braces `{...}` inside LaTeX
    commands like \\text{KGA} as attribute syntax, corrupting the formula.

    Returns:
        (protected_text, placeholder_dict) where placeholder_dict maps
        placeholders back to original math expressions.
    """
    placeholders: dict[str, str] = {}
    counter: int = 0

    def _replace(match: re.Match) -> str:
        nonlocal counter
        ph = f"\u23ceMATH{counter:04d}\u23ce"
        counter += 1
        placeholders[ph] = match.group(0)
        return ph

    # Step 1: Protect display math $$...$$ (multi-line capable)
    while True:
        m = re.search(r'\$\$(.*?)\$\$', md_text, flags=re.DOTALL)
        if not m:
            break
        md_text = md_text[:m.start()] + _replace(m) + md_text[m.end():]

    # Step 2: Protect inline math $...$ (single-line only)
    md_text = re.sub(
        r'(?<!\$)\$(?!\$)([^$]+?)(?<!\$)\$(?!\$)',
        _replace,
        md_text,
    )

    return md_text, placeholders


def restore_math(html: str, placeholders: dict[str, str]) -> str:
    """Restore math placeholders back to original LaTeX."""
    for ph, original in placeholders.items():
        html = html.replace(ph, original)
    return html


# ══════════════════════════════════════════════════════════════════════════
# Step 1: Markdown → HTML
# ══════════════════════════════════════════════════════════════════════════

def markdown_to_html(
    md_text: str,
    strip_frontmatter: bool = True,
) -> str:
    """Convert Markdown text to HTML, protecting LaTeX math from corruption.

    Args:
        md_text: Raw Markdown text (may contain YAML frontmatter and LaTeX).
        strip_frontmatter: Remove YAML frontmatter (---...---) blocks.

    Returns:
        HTML string with LaTeX math preserved in $...$ / $$...$$ delimiters.
    """
    # Strip YAML frontmatter
    if strip_frontmatter:
        md_text = re.sub(
            r'^---\n.*?\n---\n', '', md_text, count=1, flags=re.DOTALL
        )
        md_text = re.sub(
            r'^---\n.*?\n---\n', '', md_text, count=1, flags=re.DOTALL
        )

    # Protect LaTeX math from Markdown parser corruption
    protected_text, placeholders = protect_math(md_text)

    # Convert Markdown → HTML
    html_body = markdown.markdown(
        protected_text,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.nl2br',
        ],
    )

    # Restore math placeholders
    html_body = restore_math(html_body, placeholders)

    return html_body


# ══════════════════════════════════════════════════════════════════════════
# Step 2: MathJax Rendering (Node.js)
# ══════════════════════════════════════════════════════════════════════════

def mathjax_render_html(
    html_body: str,
    mathjax_js: str = "",
    timeout: int = 30,
) -> str:
    """Render LaTeX math ($...$, $$...$$) in HTML via MathJax (Node.js).

    Args:
        html_body: HTML string with $...$ / $$...$$ LaTeX delimiters.
        mathjax_js: Path to the MathJax renderer script (render_math.cjs).
        timeout: Timeout in seconds for the Node.js process.

    Returns:
        HTML body with math rendered to inline SVG (via mjx-container).
        Falls back to original HTML if MathJax is unavailable.
    """
    if not mathjax_js or not os.path.exists(mathjax_js):
        # Try to find render_math.cjs relative to this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(script_dir, "..", "render_math.cjs")
        if os.path.exists(candidate):
            mathjax_js = candidate
        else:
            # Try common locations
            for loc in [
                os.path.join(script_dir, "render_math.cjs"),
            ]:
                if os.path.exists(loc):
                    mathjax_js = loc
                    break

    if not mathjax_js or not os.path.exists(mathjax_js):
        print("⚠️  MathJax-Skript nicht gefunden. Fallback zu ungerenderten Formeln.")
        return html_body

    # Wrap in minimal HTML for MathJax processing
    mathjax_input = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body>
{html_body}
</body>
</html>"""

    try:
        proc = subprocess.run(
            ['node', mathjax_js],
            input=mathjax_input,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(mathjax_js),
        )
        if proc.returncode != 0:
            print(f"⚠️  MathJax-Rendering fehlgeschlagen (exit {proc.returncode})")
            return html_body

        mathjax_output = proc.stdout
        body_match = re.search(
            r'<body>(.*?)</body>', mathjax_output, re.DOTALL
        )
        if body_match:
            rendered = body_match.group(1)
            formula_count = len(re.findall(r'mjx-container', mathjax_output))
            print(f"   ✅ {formula_count} Formeln via MathJax gerendert")
            return rendered
        else:
            print("⚠️  Konnte Body aus MathJax-Output nicht extrahieren")
            return html_body

    except FileNotFoundError:
        print("⚠️  Node.js nicht gefunden. Fallback zu ungerenderten Formeln.")
        return html_body
    except subprocess.TimeoutExpired:
        print("⚠️  MathJax-Rendering zeitüberschreitung. Fallback.")
        return html_body
    except Exception as e:
        print(f"⚠️  MathJax-Fehler: {e}. Fallback.")
        return html_body


# ══════════════════════════════════════════════════════════════════════════
# Step 3: Build PDF Document
# ══════════════════════════════════════════════════════════════════════════

def _resolve_theme(theme: Optional[Theme]) -> Theme:
    """Resolve a theme instance, filling defaults for AcademicTheme/HestiaOSTheme."""
    if theme is None:
        return AcademicTheme()
    if isinstance(theme, AcademicTheme) and theme.css is None:
        theme.css = ACADEMIC_CSS
    if isinstance(theme, HestiaOSTheme) and theme.css is None:
        theme.css = HESTIA_CSS
    if isinstance(theme, Theme) and theme.css is None:
        theme.css = ACADEMIC_CSS
    return theme


def build_pdf_document(
    html_body: str,
    theme: Optional[Theme] = None,
    css: Optional[str] = None,
    logo_path: str = "",
    header_title: str = "",
) -> tuple[str, bytes]:
    """Wrap HTML body in a full document with CSS and generate PDF.

    Args:
        html_body: HTML body content (with math already rendered).
        theme: Theme instance (AcademicTheme, HestiaOSTheme, or custom Theme).
               If None, uses AcademicTheme.
        css: Custom CSS string. Overrides theme.css if set.
        logo_path: Path to a logo image (PNG). Overrides theme.logo_path if set.
        header_title: Title shown in PDF page header. Overrides theme.header_title.

    Returns:
        (full_html_string, pdf_bytes)
    """
    theme = _resolve_theme(theme)

    # Resolve CSS (priority: explicit css > theme.css > ACADEMIC_CSS)
    resolved_css = css or theme.css or ACADEMIC_CSS

    # Resolve header title
    resolved_title = header_title or theme.header_title or "MathDoc"

    # Customize header title in CSS
    css_customized = resolved_css.replace(
        'content: "MathDoc";',
        f'content: "{resolved_title}";',
    )

    # Resolve logo path
    resolved_logo = logo_path or theme.logo_path or ""

    # Logo HTML (Base64-embedded)
    logo_html = ""
    if resolved_logo and os.path.exists(resolved_logo):
        with open(resolved_logo, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = f"""<div class="logo-header">
  <img src="data:image/png;base64,{logo_b64}" alt="Logo">
</div>"""

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
{css_customized}
</style>
</head>
<body>
{logo_html}
{html_body}
</body>
</html>"""

    # Generate PDF via WeasyPrint
    doc = weasyprint.HTML(string=full_html).render()
    pdf_bytes = doc.write_pdf()

    return full_html, pdf_bytes


# ══════════════════════════════════════════════════════════════════════════
# Full Pipeline
# ══════════════════════════════════════════════════════════════════════════

def mathdoc_pipeline(config: MathdocConfig) -> bytes:
    """Run the full Markdown + LaTeX → PDF pipeline.

    Args:
        config: MathdocConfig with all settings.

    Returns:
        PDF bytes.
    """
    # Read input
    if config.markdown_file and not config.markdown_text:
        with open(config.markdown_file, "r", encoding="utf-8") as f:
            md_text = f.read()
    else:
        md_text = config.markdown_text

    # Step 1: Markdown → HTML (with math protection)
    html_body = markdown_to_html(md_text, config.strip_frontmatter)

    # Step 2: MathJax rendering
    html_body = mathjax_render_html(
        html_body,
        mathjax_js=config.mathjax_js,
        timeout=config.timeout,
    )

    # Step 3: Build PDF with theme
    theme = _resolve_theme(config.theme)

    # If markdown_file is set and no explicit header_title, use filename
    header_title = config.header_title
    if not header_title and config.markdown_file:
        header_title = os.path.splitext(os.path.basename(config.markdown_file))[0]

    full_html, pdf_bytes = build_pdf_document(
        html_body,
        theme=theme,
        css=config.css,
        header_title=header_title,
    )

    # Write output if path specified
    if config.output_path:
        os.makedirs(os.path.dirname(config.output_path) or ".", exist_ok=True)
        with open(config.output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"✅ PDF geschrieben: {config.output_path} ({len(pdf_bytes) // 1024} KB)")

    return pdf_bytes
