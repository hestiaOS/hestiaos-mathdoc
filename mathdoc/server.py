"""mathdoc.server — MCP server exposing the mathdoc pipeline as tools.

Tools:
  - markdown_to_pdf: Convert Markdown + LaTeX text directly to PDF bytes.
  - markdown_file_to_pdf: Read a Markdown file and convert to PDF.

Usage (stdio):
    python3 -m mathdoc.server

Registration in cline_mcp_settings.json:
    {
      "mathdoc": {
        "command": "python3",
        "args": ["-m", "mathdoc.server"],
        "env": {}
      }
    }
"""

import base64
import json
import os

from mcp.server import FastMCP

from .core import (
    mathdoc_pipeline,
    MathdocConfig,
    AcademicTheme,
    HestiaOSTheme,
)

# ── MCP Server ─────────────────────────────────────────────────────────────

server = FastMCP(
    "mathdoc",
    instructions="""MathDoc — Markdown + LaTeX → PDF Pipeline.

Convert Markdown documents with LaTeX math expressions into professionally 
formatted PDFs.

Features:
- Full LaTeX math rendering via MathJax (inline $...$ and display $$...$$)
- YAML frontmatter stripping
- Theming: Academic (default, wissenschaftlich) or HestiaOS (corporate design)
- Optional logo embedding
- Page headers and footers with page numbers

Available tools:
- `markdown_to_pdf` — Convert Markdown text to PDF (returns base64-encoded PDF)
- `markdown_file_to_pdf` — Read a Markdown file and convert to PDF
""",
)


def _resolve_mathjax_script() -> str:
    """Find the MathJax render script (render_math.cjs) in known locations."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "..", "render_math.cjs"),
        os.path.join(script_dir, "render_math.cjs"),
    ]
    for path in candidates:
        resolved = os.path.abspath(path)
        if os.path.exists(resolved):
            return resolved
    return ""


# ── Theme Registry ─────────────────────────────────────────────────────────

THEMES: dict[str, type] = {
    "academic": AcademicTheme,
    "hestiaos": HestiaOSTheme,
}


def _resolve_theme(theme_name: str, logo_path: str = "", header_title: str = "") -> AcademicTheme | HestiaOSTheme:
    """Resolve a theme by name, optionally with logo and header title."""
    theme_cls = THEMES.get(theme_name, AcademicTheme)
    kwargs = {}
    if logo_path:
        kwargs["logo_path"] = logo_path
    if header_title:
        kwargs["header_title"] = header_title
    return theme_cls(**kwargs)


# ── Tool: markdown_to_pdf ──────────────────────────────────────────────────


@server.tool()
async def markdown_to_pdf(
    markdown_text: str,
    header_title: str = "MathDoc",
    css: str = "",
    strip_frontmatter: bool = True,
    theme: str = "academic",
    include_logo: bool = False,
    output_path: str = "",
) -> str:
    """Convert Markdown text (with optional LaTeX $...$) to a PDF document.

    Args:
        markdown_text: The Markdown source text. May contain LaTeX math
            expressions using $...$ (inline) and $$...$$ (display) delimiters.
        header_title: Title shown in the PDF page header. Default: "MathDoc".
        css: Custom CSS string. If empty, uses the theme's default CSS.
        strip_frontmatter: Remove YAML frontmatter (---...---) before
            processing. Default: True.
        theme: Visual theme. "academic" (default, wissenschaftlich, kein Logo)
            or "hestiaos" (HestiaOS Corporate Design mit Orange-Akzenten).
        include_logo: Embed a logo in the PDF header. For "academic" theme,
            this has no effect (kein Logo im wissenschaftlichen Modus).
            For "hestiaos" theme, embeds the HestiaOS logo. Default: False.
        output_path: Optional file path to write the PDF. If empty, the PDF
            is returned as base64-encoded string.

    Returns:
        A JSON string with:
        - "pdf_base64": base64-encoded PDF content (if output_path is empty)
        - "pdf_path": path to the written PDF file (if output_path is set)
        - "size_kb": file size in KB
    """
    # Logo nur bei hestiaos-theme + include_logo
    logo_path = ""
    if theme == "hestiaos" and include_logo:
        logo_path = _resolve_logo()

    theme_instance = _resolve_theme(theme, logo_path=logo_path, header_title=header_title)

    config = MathdocConfig(
        markdown_text=markdown_text,
        strip_frontmatter=strip_frontmatter,
        css=css if css else None,
        header_title=header_title,
        theme=theme_instance,
        mathjax_js=_resolve_mathjax_script(),
        output_path=output_path,
        timeout=30,
    )

    pdf_bytes = mathdoc_pipeline(config)

    result: dict = {
        "size_kb": len(pdf_bytes) // 1024,
    }

    if output_path:
        result["pdf_path"] = output_path
    else:
        result["pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")

    return json.dumps(result, ensure_ascii=False)


# ── Tool: markdown_file_to_pdf ─────────────────────────────────────────────


@server.tool()
async def markdown_file_to_pdf(
    file_path: str,
    header_title: str = "",
    css: str = "",
    strip_frontmatter: bool = True,
    theme: str = "academic",
    include_logo: bool = False,
    output_path: str = "",
) -> str:
    """Read a Markdown file and convert it to a PDF document.

    Args:
        file_path: Path to the Markdown file to convert.
        header_title: Title shown in the PDF page header. If empty, uses
            the filename (without extension).
        css: Custom CSS string. If empty, uses the theme's default CSS.
        strip_frontmatter: Remove YAML frontmatter (---...---) before
            processing. Default: True.
        theme: Visual theme. "academic" (default, wissenschaftlich, kein Logo)
            or "hestiaos" (HestiaOS Corporate Design mit Orange-Akzenten).
        include_logo: Embed a logo in the PDF header. For "academic" theme,
            this has no effect. For "hestiaos" theme, embeds the HestiaOS logo.
        output_path: Optional file path to write the PDF. If empty, the PDF
            is returned as base64-encoded string.

    Returns:
        A JSON string with:
        - "pdf_base64": base64-encoded PDF content (if output_path is empty)
        - "pdf_path": path to the written PDF file (if output_path is set)
        - "size_kb": file size in KB
    """
    if not os.path.exists(file_path):
        return json.dumps({"error": f"File not found: {file_path}"}, ensure_ascii=False)

    if not header_title:
        header_title = os.path.splitext(os.path.basename(file_path))[0]

    # Logo nur bei hestiaos-theme + include_logo
    logo_path = ""
    if theme == "hestiaos" and include_logo:
        logo_path = _resolve_logo()

    theme_instance = _resolve_theme(theme, logo_path=logo_path, header_title=header_title)

    config = MathdocConfig(
        markdown_file=file_path,
        strip_frontmatter=strip_frontmatter,
        css=css if css else None,
        header_title=header_title,
        theme=theme_instance,
        mathjax_js=_resolve_mathjax_script(),
        output_path=output_path,
        timeout=30,
    )

    pdf_bytes = mathdoc_pipeline(config)

    result: dict = {
        "size_kb": len(pdf_bytes) // 1024,
    }

    if output_path:
        result["pdf_path"] = output_path
    else:
        result["pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")

    return json.dumps(result, ensure_ascii=False)


# ── Logo Resolution (nur für HestiaOS-Theme) ───────────────────────────────


def _resolve_logo() -> str:
    """Find the hestiaOS logo in known locations."""
    # Look relative to this file's directory, then fall back to CWD
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "hestiaos_logo.png"),
        os.path.join(os.getcwd(), "hestiaos_logo.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


# ── Main Entry Point ───────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server over stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
