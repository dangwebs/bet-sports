#!/usr/bin/env python3
"""Simple utility to strip trailing whitespace and clean blank lines.

Usage:
    python3 backend/scripts/clean_whitespace.py <file-path>
"""

import sys
from pathlib import Path


def clean_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Split into lines (preserves content without trailing newlines)
    lines = text.splitlines()
    cleaned = [ln.rstrip() for ln in lines]
    # Ensure file ends with a single newline
    out = "\n".join(cleaned) + "\n"
    path.write_text(out, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: clean_whitespace.py <file>")
        sys.exit(2)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"File not found: {p}")
        sys.exit(1)
    clean_file(p)
    print(f"Cleaned {p}")
