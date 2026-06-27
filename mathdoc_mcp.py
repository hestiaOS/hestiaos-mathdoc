#!/usr/bin/env python3
"""MCP server entry point for mathdoc — Markdown + LaTeX → PDF.
Simple script that Hermes MCP client can connect to via stdio."""
import os
import sys

# Set library path for WeasyPrint on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")

# Add the parent directory so `mathdoc` package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathdoc.server import main

if __name__ == "__main__":
    main()
