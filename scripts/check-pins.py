#!/usr/bin/env python3
"""Check that every 64-hex-digit pin in this repository is actually 64 digits.

A truncated sha256 is the worst kind of pin: it looks like a hash, it compares
like a hash, and it silently never matches. This repository pins Apple's
kernelcache and IPSW members, so a one-character typo turns a build guard into a
permanent false failure (or, worse, into no guard at all if the comparison is
written the other way round).

This check is cheap and catches that class of mistake before it reaches a build.

    python3 scripts/check-pins.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Files that carry pins. Evidence prose is included on purpose: a wrong hash
# quoted in documentation is just as misleading as one in a config.
SUFFIXES = {".toml", ".json", ".md", ".py", ".log"}
SKIP_DIRS = {".git", "out", "build", "__pycache__"}
SKIP_FILES = {"scripts/check-pins.py"}

# A hex run of 40..80 characters that is not part of a longer word.
HEX_RUN = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{40,80}(?![0-9a-fA-F])")
# Things that are legitimately not sha256: git revisions (40), sha1 (40),
# and the 96-character sha384 quotes used in the IPSW facts.
EXPECTED = {40, 64, 96}

problems = []


def main():
    for path in sorted(REPO.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.as_posix() in SKIP_FILES:
            continue
        if path.suffix.lower() not in SUFFIXES:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for match in HEX_RUN.finditer(line):
                value = match.group()
                if len(value) in EXPECTED:
                    continue
                problems.append((rel.as_posix(), number, len(value), value[:20] + "..."))

    if problems:
        print(f"pin check FAILED: {len(problems)} malformed hex pin(s)\n")
        for where, line, length, preview in problems:
            print(f"  {where}:{line}  {length} hex digits (expected 40, 64 or 96)  {preview}")
        print()
        print("A truncated sha256 never matches. Fix the pin or, if the value is")
        print("genuinely not a hash, do not format it as a bare hex run.")
        return 1

    print("pin check PASSED: every hex pin is a complete 40, 64 or 96 digits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
