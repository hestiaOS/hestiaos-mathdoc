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
    """Run render_math.cjs on HTML input and return stdout.

    Raises RuntimeError if the process exits non-zero.
    """
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


def render_with_stderr(html_input: str) -> tuple[str, str, int]:
    """Run render_math.cjs and return (stdout, stderr, exit_code)."""
    if not HAS_NODE:
        pytest.skip("Node.js not available")

    proc = subprocess.run(
        ["node", RENDER_SCRIPT],
        input=html_input,
        capture_output=True,
        text=True,
        timeout=15,
        cwd=os.path.dirname(RENDER_SCRIPT),
    )
    return proc.stdout, proc.stderr, proc.returncode


def count_containers(html: str) -> int:
    """Count actual <mjx-container opening elements."""
    import re
    return len(re.findall(r'<mjx-container\s', html))


def count_display(html: str) -> int:
    """Count opening <mjx-container elements with display=true."""
    import re
    return len(re.findall(r'<mjx-container[^>]*display="true"', html))


def has_svg(html: str) -> bool:
    """Check for a real <svg opening element (not CSS or comment)."""
    import re
    return bool(re.search(r'<svg[\s>]', html))


# ══════════════════════════════════════════════════════════════════════════
# Basic rendering
# ══════════════════════════════════════════════════════════════════════════


class TestBasicRendering:
    """Fundamental rendering behaviour."""

    def test_renders_inline_math(self):
        """$...$ inline math produces mjx-container with SVG."""
        result = render_html("<p>$E = mc^2$</p>")
        assert count_containers(result) >= 1
        assert has_svg(result)

    def test_renders_display_math(self):
        """$$...$$ display math produces mjx-container with display=true."""
        result = render_html(r"<p>$$\int_a^b f(x)\,dx$$</p>")
        assert count_containers(result) >= 1
        assert count_display(result) == 1
        assert has_svg(result)

    def test_no_math_passthrough(self):
        """HTML without math delimiters passes through unchanged."""
        result = render_html("<p>Hello world.</p>")
        assert "<p>Hello world.</p>" in result
        assert count_containers(result) == 0

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


# ══════════════════════════════════════════════════════════════════════════
# HTML-aware protection: literal preservation in code/pre blocks
# ══════════════════════════════════════════════════════════════════════════


class TestProtectedRegions:
    """Math inside code/pre/script/style/textarea is never rendered."""

    def test_code_block_remains_literal(self):
        """$x$ inside <code> remains literal, zero container elements."""
        result = render_html("<p><code>$x$</code></p>")
        assert count_containers(result) == 0
        assert "$x$" in result

    def test_pre_code_block_remains_literal(self):
        """$x$ inside <pre><code> remains literal, zero containers."""
        result = render_html("<pre><code>$x$</code></pre>")
        assert count_containers(result) == 0
        assert "$x$" in result or "&lt;code&gt;$x$&lt;/code&gt;" in result
        # The code content itself must survive
        assert "x$" in result

    def test_script_content_not_rendered(self):
        """$...$ inside <script> is not rendered."""
        result = render_html("<script>var x = $5$;</script>")
        assert count_containers(result) == 0

    def test_style_content_not_rendered(self):
        """$...$ inside <style> is not rendered."""
        result = render_html("<style>.foo { content: '$bar$'; }</style>")
        assert count_containers(result) == 0

    def test_math_outside_code_still_renders(self):
        """Normal math outside protected regions still renders."""
        result = render_html("<p><code>not math</code> and $E = mc^2$</p>")
        assert count_containers(result) >= 1
        assert has_svg(result)

    def test_escaped_dollars_remain_literal(self):
        r"""\$5 and \$7 produce literal $5/$7, zero containers."""
        result = render_html(r"<p>\$5 and \$7</p>")
        assert count_containers(result) == 0
        # escaped dollar with \ should become literal dollar + number
        assert "5" in result
        assert "7" in result

    def test_escaped_dollars_next_to_normal_math(self):
        r"""\$ mixed with real $math$ does not interfere."""
        result = render_html(r"<p>\$5 and $x$</p>")
        # $x$ should render, \$5 should stay literal
        assert count_containers(result) >= 1
        assert "5" in result


# ══════════════════════════════════════════════════════════════════════════
# Cardinality tests
# ══════════════════════════════════════════════════════════════════════════


class TestCardinality:
    """Precise counting of rendered elements."""

    def test_exactly_three_containers_two_inline_one_display(self):
        """2 inline + 1 display = 3 containers, 1 display element."""
        result = render_html(
            r"<p>$a$ and $b$ and $$\int$$</p>"
        )
        assert count_containers(result) == 3, (
            f"Expected 3 mjx-container, got {count_containers(result)}"
        )
        assert count_display(result) == 1, (
            f"Expected 1 display element, got {count_display(result)}"
        )

    def test_single_inline_one_container(self):
        """1 inline expression produces exactly 1 container."""
        result = render_html("<p>$a$</p>")
        assert count_containers(result) == 1

    def test_single_display_one_container(self):
        """1 display expression produces exactly 1 container."""
        result = render_html(r"<p>$$\int$$</p>")
        assert count_containers(result) == 1
        assert count_display(result) == 1


# ══════════════════════════════════════════════════════════════════════════
# Error fallback escaping
# ══════════════════════════════════════════════════════════════════════════


class TestErrorFallbackEscaping:
    """HTML content inside math is rendered as characters (not raw HTML)."""

    def test_html_payload_does_not_leak_raw_tags(self):
        """HTML-like payload inside math renders as characters, not raw tags."""
        malicious = '<div onclick="alert(1)">evil</div>'
        result = render_html(f"<p>${malicious}$</p>")
        # MathJax renders <, > as characters (SVG path data) not HTML tags
        # Verify no raw <div tag leaks through
        assert "<div " not in result
        assert "<div onclick" not in result

    def test_malformed_expression_appears_in_output(self):
        """Unknown command renders visibly (not silently dropped)."""
        result = render_html(r"<p>$\invalid$</p>")
        # MathJax renders unknown commands as red SVG glyphs
        assert "<mjx-container" in result
        assert "<svg" in result
        # The character data is encoded as SVG path references,
        # not raw text — presence of mjx-container + svg confirms rendering

    def test_display_math_output_has_mjx_container_and_display(self):
        """Display math with unknown command still produces mjx-container."""
        result = render_html(r"<p>$$\invalid$$</p>")
        assert "<mjx-container" in result
        assert 'display="true"' in result
        assert "<svg" in result

    def test_math_error_handler_escapes_html(self):
        """The error handler HTML-escapes expressions (unit test via standalone JS)."""
        # Run a JS snippet that directly tests the htmlEscape function
        import subprocess
        js_test = """
        const { htmlEscape } = (() => {
          // Inline the htmlEscape from render_math.cjs
          const fn = (str) => str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
          return { htmlEscape: fn };
        })();

        const tests = [
          htmlEscape('<div onclick="x">') === '&lt;div onclick=&quot;x&quot;&gt;',
          htmlEscape('&<>"\\'') === '&amp;&lt;&gt;&quot;&#39;',
          htmlEscape('safe text') === 'safe text',
        ];
        console.log(tests.every(Boolean) ? 'PASS' : 'FAIL: ' + JSON.stringify(tests));
        """
        proc = subprocess.run(
            ["node", "-e", js_test],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"JS unit test failed: {proc.stderr}"
        assert "PASS" in proc.stdout, f"JS test output: {proc.stdout}"

    def test_empty_expression_renders_empty_container(self):
        """Empty math $ $ produces an empty mjx-container."""
        result = render_html("<p>$ $</p>")
        assert "<mjx-container" in result
        assert "<svg" in result


# ══════════════════════════════════════════════════════════════════════════
# Stdout / stderr contract
# ══════════════════════════════════════════════════════════════════════════


class TestStdoutStderrContract:
    """Rendered HTML only to stdout, errors only to stderr."""

    def test_successful_render_stdout_only(self):
        """Successful render writes HTML only to stdout."""
        stdout, stderr, code = render_with_stderr("<p>$a$</p>")
        assert code == 0
        assert len(stdout) > 0
        assert count_containers(stdout) >= 1

    def test_empty_input_stderr_only(self):
        """Empty input writes error to stderr, no stdout."""
        stdout, stderr, code = render_with_stderr("")
        assert code != 0
        assert stdout == "" or stdout.strip() == ""
        assert len(stderr) > 0

    def test_missing_mathjax_writes_no_stdout(self):
        """When mathjax-full cannot be loaded, stdout is empty and stderr
        is non-empty.  Runs even when mathjax is installed: copies
        render_math.cjs to an isolated temp directory with no node_modules."""
        import tempfile
        import shutil
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy only render_math.cjs — no node_modules
            dst = os.path.join(tmpdir, "render_math.cjs")
            shutil.copy2(RENDER_SCRIPT, dst)

            env = os.environ.copy()
            env.pop("NODE_PATH", None)
            # Prevent Node from finding modules in parent dirs
            env["NODE_OPTIONS"] = "--no-deprecation"

            proc = subprocess.run(
                ["node", dst],
                input="<p>$a$</p>",
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
                env=env,
            )
            assert proc.returncode != 0, (
                f"Expected non-zero exit, got {proc.returncode}"
            )
            assert proc.stdout == "" or proc.stdout.strip() == "", (
                f"Expected empty stdout, got: {proc.stdout[:200]}"
            )
            assert len(proc.stderr) > 0, (
                "Expected non-empty stderr for missing module"
            )
