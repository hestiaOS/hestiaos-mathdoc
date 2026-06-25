"""Tests for the MathJax render_math.cjs via subprocess."""

import subprocess
import os

import pytest


RENDER_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "render_math.cjs"
)

HAS_NODE = (
    subprocess.run(
        ["node", "--version"], capture_output=True, text=True
    ).returncode
    == 0
)

HAS_MATHJAX = HAS_NODE and os.path.exists(
    os.path.join(
        os.path.dirname(__file__), "..", "node_modules", "mathjax-full"
    )
)


def render_html(html_input: str) -> str:
    """Run render_math.cjs on HTML input and return stdout."""
    if not HAS_NODE:
        pytest.skip("Node.js not available")
    if not HAS_MATHJAX:
        pytest.skip("mathjax-full not installed (run npm install first)")

    proc = subprocess.run(
        ["node", RENDER_SCRIPT],
        input=html_input,
        capture_output=True,
        text=True,
        timeout=15,
        cwd=os.path.dirname(RENDER_SCRIPT),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"render_math.cjs failed (exit {proc.returncode}): {proc.stderr}"
        )
    return proc.stdout


class TestRendererCli:
    """Tests for the render_math.cjs CLI."""

    def test_renders_inline_math(self):
        """$...$ inline math produces SVG output."""
        result = render_html("<p>$E = mc^2$</p>")
        assert "<svg" in result
        assert 'xmlns="http://www.w3.org/2000/svg"' in result

    def test_renders_display_math(self):
        """$$...$$ display math produces block SVG output."""
        result = render_html(r"<p>$$\int_a^b f(x)\,dx$$</p>")
        assert "<svg" in result
        # Display math uses taller SVG (integral has larger vertical extent)
        assert 'ex;"' in result

    def test_no_math_passthrough(self):
        """HTML without math delimiters passes through unchanged."""
        result = render_html("<p>Hello world.</p>")
        assert "<p>Hello world.</p>" in result

    def test_empty_input_errors(self):
        """Empty stdin should exit with error."""
        proc = subprocess.run(
            ["node", RENDER_SCRIPT],
            input="",
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(RENDER_SCRIPT),
        )
        assert proc.returncode != 0

    def test_multiple_expressions(self):
        """Multiple math expressions are all rendered as SVG."""
        result = render_html(r"<p>$a$ and $b$ and $$\int$$</p>")
        # Count SVG elements rendered
        count = result.count("<svg")
        assert count >= 2  # at minimum the two inline + display
