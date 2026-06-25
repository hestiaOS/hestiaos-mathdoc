"""mathdoc — Markdown + LaTeX → PDF pipeline as a reusable library.

Pipeline:
  1. Read Markdown (with optional YAML frontmatter stripping)
  2. Protect LaTeX math ($...$, $$...$$) from Markdown parser corruption
  3. Convert Markdown → HTML (Python markdown library)
  4. Restore math placeholders
  5. Render LaTeX math via MathJax (Node.js) → SVG inline
  6. Wrap in full HTML document with theme-based CSS
  7. Render HTML → PDF via WeasyPrint

Theming:
  - AcademicTheme (default): neutral, kein Logo, wissenschaftlich
  - HestiaOSTheme: mit Logo, Hestia Orange, Space Grotesk
  - Theme: eigene Anpassungen (CSS, Logo, Farben)

Usage:
    from mathdoc import mathdoc_pipeline, MathdocConfig

    # Academic (Default) — für Paper, Preprints
    config = MathdocConfig(markdown_text="# Hello $E=mc^2$")
    pdf_bytes = mathdoc_pipeline(config)

    # HestiaOS Corporate Design
    from mathdoc import HestiaOSTheme
    config = MathdocConfig(
        markdown_text="# Interner Report",
        theme=HestiaOSTheme(logo_path="./logo.png"),
    )
    pdf_bytes = mathdoc_pipeline(config)

    # Eigenes Theme
    from mathdoc import Theme
    config = MathdocConfig(
        markdown_text="# Custom",
        theme=Theme(css=MY_CSS, primary_color="#ff6600"),
    )
"""

from .core import (
    markdown_to_html,
    mathjax_render_html,
    build_pdf_document,
    mathdoc_pipeline,
    MathdocConfig,
    Theme,
    AcademicTheme,
    HestiaOSTheme,
    ACADEMIC_CSS,
    HESTIA_CSS,
    DEFAULT_CSS,
)

__all__ = [
    "markdown_to_html",
    "mathjax_render_html",
    "build_pdf_document",
    "mathdoc_pipeline",
    "MathdocConfig",
    "Theme",
    "AcademicTheme",
    "HestiaOSTheme",
    "ACADEMIC_CSS",
    "HESTIA_CSS",
    "DEFAULT_CSS",
]
