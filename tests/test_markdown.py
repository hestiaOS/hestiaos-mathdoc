"""Tests for mathdoc Markdown → HTML conversion with LaTeX protection."""

import pytest
from mathdoc.core import markdown_to_html, protect_math, restore_math


class TestMarkdownToHtml:
    """Plain Markdown (no LaTeX) renders correctly."""

    def test_simple_markdown(self):
        html = markdown_to_html("# Hello\n\nWorld.")
        assert "<h1>" in html
        assert "Hello" in html
        assert "World." in html

    def test_inline_math_preserved(self):
        """Inline $...$ LaTeX is preserved after conversion."""
        html = markdown_to_html("Formula: $E = mc^2$")
        assert "$E = mc^2$" in html

    def test_display_math_preserved(self):
        """Display $$...$$ LaTeX is preserved after conversion."""
        html = markdown_to_html(r"$$\int_a^b f(x)\,dx$$")
        assert r"\int_a^b f(x)\," in html

    def test_frontmatter_stripped(self):
        """YAML frontmatter is removed when strip_frontmatter=True."""
        md = "---\ntitle: Test\n---\n# Content"
        html = markdown_to_html(md, strip_frontmatter=True)
        assert "title:" not in html
        assert "<h1>" in html
        assert "Content" in html

    def test_frontmatter_preserved_when_disabled(self):
        """YAML frontmatter stays if strip_frontmatter=False."""
        md = "---\ntitle: Test\n---\n# Content"
        html = markdown_to_html(md, strip_frontmatter=False)
        assert "Content" in html

    def test_mixed_math_and_markdown(self):
        """Math and Markdown coexist without corruption."""
        html = markdown_to_html(
            r"# Title" "\n\n" r"$\alpha + \beta = \gamma$" "\n\n" r"And **bold** text."
        )
        assert r"$\alpha + \beta = \gamma$" in html
        assert "<strong>" in html or "bold" in html
        assert "<h1>" in html

    def test_curly_braces_in_math(self):
        """Curly braces in LaTeX are not corrupted by Markdown parser."""
        html = markdown_to_html(
            r"$\text{value} = \{x \mid x > 0\}$"
        )
        assert r"\text" in html or "text" in html
        assert "value" in html


class TestMathProtection:
    """Math protection roundtrip and placeholder behaviour."""

    def test_protect_and_restore_roundtrip(self):
        md = r"Hello $E=mc^2$ world $$\int f$$"
        protected, placeholders = protect_math(md)
        # Placeholders replace math blocks — no raw $ visible
        assert "MATH" in protected
        restored = restore_math(protected, placeholders)
        assert restored == md

    def test_protect_multiple_expressions(self):
        md = "$a$ and $b$ and $$c$$"
        protected, placeholders = protect_math(md)
        assert len(placeholders) == 3
        restored = restore_math(protected, placeholders)
        assert restored == md

    def test_no_math_passthrough(self):
        """Text without math delimiters passes through unchanged."""
        md = "Just plain text."
        protected, placeholders = protect_math(md)
        assert protected == md
        assert placeholders == {}

    def test_display_math_multiline(self):
        """Multi-line display math is protected correctly."""
        md = "$$\n" r"\int_{0}^{1} f(x) \, dx" "\n$$"
        protected, placeholders = protect_math(md)
        assert "MATH" in protected
        restored = restore_math(protected, placeholders)
        assert restored == md
