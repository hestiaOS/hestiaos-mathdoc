#!/usr/bin/env node
/**
 * render_math.cjs — MathJax Node.js renderer for mathdoc.
 *
 * Reads HTML from stdin, renders LaTeX math via MathJax (SVG output),
 * and writes the rendered HTML to stdout.
 *
 * Delimiter contract:
 *   - Inline math: $...$  (single line, non-greedy)
 *   - Display math: $$...$$ (multi-line, greedy)
 *
 * Usage:
 *   cat input.html | node render_math.cjs > output.html
 *
 * Dependencies (from package.json — exact pinned):
 *   - mathjax-full@3.2.2
 */

// ── MathJax adaptor (lite — no browser DOM required) ──────────────────────
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
const { mathjax } = require("mathjax-full/js/mathjax.js");

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);

// ── Input/Output processors ───────────────────────────────────────────────
const { TeX } = require("mathjax-full/js/input/tex.js");
const { SVG } = require("mathjax-full/js/output/svg.js");
const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

const tex = new TeX({ packages: AllPackages.slice() });
// fontCache: "none" — each SVG is self-contained (required for PDF output)
const svg = new SVG({ fontCache: "none" });

// ── Document (shared — created once for conversion) ──────────────────────
const doc = mathjax.document("", { InputJax: tex, OutputJax: svg });

// ── Render a single math expression ───────────────────────────────────────
function renderExpression(expr, display) {
  try {
    const node = doc.convert(expr, { display: display || false });
    return adaptor.innerHTML(node);
  } catch (e) {
    console.error(`MathJax render error: ${e.message}`);
    if (display) {
      return `<div class="math-error">${expr}</div>`;
    }
    return `<span class="math-error">${expr}</span>`;
  }
}

// ── Main render function ──────────────────────────────────────────────────
function renderHtml(inputHtml) {
  // Process display math $$...$$ first (greedy, multi-line)
  let result = inputHtml.replace(
    /\$\$([\s\S]*?)\$\$/g,
    (_, expr) => renderExpression(expr.trim(), true)
  );

  // Process inline math $...$ (single-line, non-greedy, not $$)
  result = result.replace(
    /(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)/g,
    (_, expr) => renderExpression(expr.trim(), false)
  );

  return result;
}

// ── CLI: read stdin, render, write stdout ─────────────────────────────────
function main() {
  const chunks = [];
  process.stdin.setEncoding("utf-8");

  process.stdin.on("data", (chunk) => chunks.push(chunk));
  process.stdin.on("end", () => {
    const inputHtml = chunks.join("");

    if (!inputHtml.trim()) {
      console.error("No input received on stdin.");
      process.exit(1);
    }

    try {
      const outputHtml = renderHtml(inputHtml);
      process.stdout.write(outputHtml);
    } catch (e) {
      console.error(`Render failed: ${e.message}`);
      process.exit(1);
    }
  });

  process.stdin.on("error", (e) => {
    console.error(`Stdin error: ${e.message}`);
    process.exit(1);
  });
}

main();
