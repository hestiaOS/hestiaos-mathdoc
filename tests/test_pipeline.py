"""Tests for themes, PDF document building, and the full pipeline."""

import pytest
from mathdoc import (
    build_pdf_document,
    mathdoc_pipeline,
    MathdocConfig,
    Theme,
    AcademicTheme,
    HestiaOSTheme,
    ACADEMIC_CSS,
    HESTIA_CSS,
)


class TestThemes:
    """Theme class defaults and behaviour."""

    def test_academic_theme_defaults(self):
        theme = AcademicTheme()
        assert theme.primary_color == "#1a1a2e"
        assert theme.logo_path == ""
        assert theme.header_title == "MathDoc"
        assert theme.css is None

    def test_hestia_os_theme_defaults(self):
        theme = HestiaOSTheme()
        assert theme.primary_color == "#E66A2C"
        assert theme.css is None

    def test_custom_theme(self):
        theme = Theme(css="body { color: red; }", primary_color="#ff0000")
        assert theme.css == "body { color: red; }"
        assert theme.primary_color == "#ff0000"

    def test_academic_css_contains_core_styles(self):
        assert "@page" in ACADEMIC_CSS
        assert "A4" in ACADEMIC_CSS
        assert "Inter" in ACADEMIC_CSS
        assert "1a1a2e" in ACADEMIC_CSS

    def test_hestia_css_contains_hestia_colors(self):
        assert "@page" in HESTIA_CSS
        assert "E66A2C" in HESTIA_CSS
        assert "Space Grotesk" in HESTIA_CSS


class TestBuildPdfDocument:
    """PDF document building from HTML."""

    def test_returns_tuple_of_html_and_bytes(self):
        html, pdf = build_pdf_document("<p>Hello</p>")
        assert isinstance(html, str)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100
        assert pdf.startswith(b"%PDF")

    def test_pdf_with_academic_theme(self):
        _, pdf = build_pdf_document("<p>Test</p>", theme=AcademicTheme())
        assert pdf.startswith(b"%PDF")

    def test_pdf_with_hestia_theme(self):
        _, pdf = build_pdf_document("<p>Test</p>", theme=HestiaOSTheme())
        assert pdf.startswith(b"%PDF")

    def test_custom_css_overrides_theme_css(self):
        html, pdf = build_pdf_document(
            "<p>Custom</p>",
            css="body { background: red; }",
        )
        assert "background: red" in html

    def test_header_title_appears_in_html(self):
        html, _ = build_pdf_document(
            "<p>Test</p>", header_title="Mein Dokument"
        )
        assert "Mein Dokument" in html

    def test_empty_body_still_produces_pdf(self):
        _, pdf = build_pdf_document("")
        assert pdf.startswith(b"%PDF")


class TestMathdocPipeline:
    """Full Markdown + LaTeX → PDF pipeline."""

    def test_simple_pipeline_returns_pdf(self):
        pdf = mathdoc_pipeline(
            MathdocConfig(
                markdown_text="# Hello\n\n$E = mc^2$",
                header_title="Test",
            )
        )
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100
        assert pdf.startswith(b"%PDF")

    def test_pipeline_with_academic_theme(self):
        pdf = mathdoc_pipeline(
            MathdocConfig(
                markdown_text=r"# Academic Paper" "\n\n" r"$$\int f$$",
                theme=AcademicTheme(),
            )
        )
        assert pdf.startswith(b"%PDF")

    def test_pipeline_with_hestia_theme(self):
        pdf = mathdoc_pipeline(
            MathdocConfig(
                markdown_text=r"# Corporate Report" "\n\n" r"$\alpha$",
                theme=HestiaOSTheme(),
            )
        )
        assert pdf.startswith(b"%PDF")

    def test_pipeline_with_frontmatter_stripping(self):
        md = "---\ntitle: Secret\n---\n# Real Content\n\n$E = mc^2$"
        pdf = mathdoc_pipeline(
            MathdocConfig(
                markdown_text=md,
                strip_frontmatter=True,
            )
        )
        assert pdf.startswith(b"%PDF")
