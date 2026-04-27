#!/usr/bin/env python3
"""
wrap_comments.py
Utility to wrap leading comment lines to a given width.
Usage: python scripts/wrap_comments.py path/to/file.py [width]
"""

import sys
import textwrap
from pathlib import Path


def wrap_comments_in_file(path, width=88, min_width=20):
    p = Path(path)
    if not p.exists():
        print(f"NOT FOUND: {path}")
        return 2
    text = p.read_text()
    lines = text.splitlines()
    new_lines = []
    changed = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            indent = line[: len(line) - len(stripped)]
            low = stripped.lower()
            # Preserve special markers and URLs
            if (
                low.startswith("# type:")
                or low.startswith("# pragma:")
                or "http://" in line
                or "https://" in line
            ):
                new_lines.append(line)
                continue
            comment_text = stripped[1:].lstrip()
            if len(line) > width:
                inner_width = width - len(indent) - 2
                if inner_width < min_width:
                    new_lines.append(line)
                    continue
                wrapped = textwrap.fill(comment_text, width=inner_width)
                for wl in wrapped.splitlines():
                    new_lines.append(f"{indent}# {wl}")
                changed = True
                continue
        new_lines.append(line)
    if changed:
        p.write_text("\n".join(new_lines) + "\n")
        print(f"wrapped: {path}")
    else:
        print(f"no-change: {path}")
    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: wrap_comments.py <file> [width]")
        sys.exit(1)
    path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 88
    sys.exit(wrap_comments_in_file(path, width))


if __name__ == "__main__":
    main()
