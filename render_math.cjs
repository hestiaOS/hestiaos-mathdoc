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
 * HTML-awareness:
 *   Content inside <code>, <pre>, <script>, <style>, <textarea>
 *   is protected and never processed for math rendering.
 *   Escaped dollars (\$) are preserved as literal $ and never
 *   treated as math delimiters.
 *
 * Usage:
 *   cat input.html | node render_math.cjs > output.html
 *
 * Dependencies (from package.json — exact pinned):
 *   - mathjax-full@3.2.2
 */

// ── MathJax adaptor (lite — no browser DOM required) ──────────────────────
let adaptor, mathjax, tex, svg, doc;
try {
  const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
  const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
  mathjax = require("mathjax-full/js/mathjax.js").mathjax;

  adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);

  const { TeX } = require("mathjax-full/js/input/tex.js");
  const { SVG } = require("mathjax-full/js/output/svg.js");
  const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

  tex = new TeX({ packages: AllPackages.slice() });
  svg = new SVG({ fontCache: "local" });
  doc = mathjax.document("", { InputJax: tex, OutputJax: svg });
} catch (e) {
  console.error("MathJax initialization failed: " + e.message);
  process.exit(1);
}

// ── HTML escaping for safe error output ───────────────────────────────────
function htmlEscape(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Render a single math expression ───────────────────────────────────────
function renderExpression(expr, display) {
  try {
    const node = doc.convert(expr, { display: display || false });
    const svgHtml = adaptor.innerHTML(node);
    const displayAttr = display ? ' display="true"' : "";
    return (
      '<mjx-container class="MathJax" jax="SVG"' +
      displayAttr +
      ">" +
      svgHtml +
      "</mjx-container>"
    );
  } catch (e) {
    console.error("MathJax render error: " + e.message);
    const escaped = htmlEscape(expr);
    if (display) {
      return (
        '<mjx-container class="MathJax" jax="SVG" display="true">' +
        '<div class="math-error">' +
        escaped +
        "</div></mjx-container>"
      );
    }
    return (
      '<mjx-container class="MathJax" jax="SVG">' +
      '<span class="math-error">' +
      escaped +
      "</span></mjx-container>"
    );
  }
}

// ── Math rendering on unprotected text ────────────────────────────────────
function renderMathInText(text) {
  // Process display math $$...$$ first (greedy, multi-line)
  let result = text.replace(
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

// ── HTML tag-aware protection ────────────────────────────────────────────
// Protected regions (code, pre, script, style, textarea) have their
// content replaced with opaque placeholders before math rendering.
// Escaped dollars (\$) are also protected so they render as literal $.

let protectCounter = 0;
const protectMap = new Map();
const PROT_TAGS = ["style", "script", "textarea", "pre", "code"];

function nextPlaceholder() {
  return "\x00MJPROT" + (protectCounter++) + "\x00";
}

function protectHtml(html) {
  protectCounter = 0;
  protectMap.clear();

  let result = html;

  // Step 1: Protect escaped dollars (\$ --> literal $ placeholder)
  result = result.replace(/\\(\$)/g, (_, d) => {
    const ph = nextPlaceholder();
    protectMap.set(ph, d);
    return ph;
  });

  // Step 2: Protect HTML tag regions
  // Process tags in order: style, script, textarea, pre, code.
  // outer-to-inner: pre is processed before code, so
  // <pre><code>$x$</code></pre> is captured as one block.
  for (const tag of PROT_TAGS) {
    const re = new RegExp(
      "<" + tag + "(\\s[^>]*)?>[\\s\\S]*?<\\/" + tag + ">",
      "gi"
    );
    result = result.replace(re, (match) => {
      const ph = nextPlaceholder();
      protectMap.set(ph, match);
      return ph;
    });
  }

  return result;
}

function restoreHtml(result) {
  // Restore in insertion order (oldest placeholder first) so nested
  // placeholders are resolved correctly.
  for (const [ph, original] of protectMap) {
    result = result.split(ph).join(original);
  }
  return result;
}

// ── Main render function ──────────────────────────────────────────────────
function renderHtml(inputHtml) {
  // 1. Protect tag regions and escaped dollars
  const protectedHtml = protectHtml(inputHtml);
  // 2. Render math in unprotected text only
  const renderedHtml = renderMathInText(protectedHtml);
  // 3. Restore protected regions
  const result = restoreHtml(renderedHtml);
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
      console.error("Render failed: " + e.message);
      process.exit(1);
    }
  });

  process.stdin.on("error", (e) => {
    console.error("Stdin error: " + e.message);
    process.exit(1);
  });
}

main();
