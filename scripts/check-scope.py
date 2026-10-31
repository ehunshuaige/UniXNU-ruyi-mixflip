#!/usr/bin/env python3
"""Enforce the ruyi port's two hard scope rules.

  1. No GPU driver. The software-render profile must build and load none of the
     Adreno/Metal stack: no GPU component, no GPU firmware, no GPU kernel
     argument, and nothing in the repository that would compile a GPU driver.

  2. No cover (external) display. The port describes the internal 1224x2912
     panel only. The cover panel (1208x1392) must not appear as a device-tree
     node, a property, a component, a kernel argument or a config value - not
     commented out, simply absent.

This is a source-tree check, not a hardware test: it proves the repository does
not carry these things, and says nothing about what a running kernel does.

    python3 scripts/check-scope.py [REPO]

Exit status 0 when both rules hold, 1 with the offending lines otherwise.
"""
import re
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()

# Components that belong to the GPU stack. Selecting any of them means a GPU
# driver would be built and loaded.
GPU_COMPONENTS = {
    "Adreno740", "AdrenoMetal", "AdrenoPM4", "AdrenoFirmware",
    "ArmSmmu4K", "AirNir", "Sm8550Platform",
}

# Values that only make sense when a GPU path exists.
GPU_ARGUMENTS = {
    "sheng-gpu-power", "sheng-gpu-metal", "sheng-fb-gpu", "sheng-gpu-dcvs",
    "sheng-gpu-addon", "sheng-early-retire", "negroniadreno", "negroniadreno_keep",
    "negronimetal", "ruyigpu",
}

# The cover panel's identifying values. The internal panel is 1224x2912 with a
# 4896-byte stride; the cover panel is 1208x1392.
COVER_PANEL_TOKENS = {
    "sec_dsc_cmd", "sec_p11_dsc_cmd", "mdss_dsi_sec", "dsi_display1",
    "1208", "1392", "0x4b8", "0x570",
}

# The hard rules are about what the port *builds and describes*, so the strict
# scan covers device-tree sources, board/OS configuration, patch series and the
# board package. Prose is deliberately excluded: this repository has to be able
# to state the boundary (that the cover panel is out of scope) in its own
# documentation without the documentation tripping the check.
STRICT_SUFFIXES = {".toml", ".dts", ".dtsi", ".defconfig", ".cfg", ".config", ".py", ".sh", ".yml", ".yaml"}
STRICT_TOP_DIRS = {"dts", "configs", "patches", "scripts", "package"}
SKIP_DIRS = {".git", "out", "build", "__pycache__", "docs"}
# Checkers necessarily name the things they forbid, so they are not scanned.
SKIP_PATHS = {"scripts/check-scope.py", "scripts/check-tree.py"}

problems = []


def rel(path):
    return path.relative_to(REPO).as_posix()


def scan(path):
    text = path.read_text(errors="replace")
    return text.splitlines()


def check_components():
    """board.toml must not select a GPU component."""
    board = REPO / "board.toml"
    if not board.is_file():
        problems.append(("components", rel(board), "board.toml is missing"))
        return
    text = board.read_text()
    match = re.search(r"^include\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not match:
        problems.append(("components", "board.toml", "no [components] include list"))
        return
    selected = re.findall(r'"([^"]+)"', match.group(1))
    for component in selected:
        if component in GPU_COMPONENTS:
            problems.append(("gpu-component", "board.toml",
                             f"[components] include selects GPU component {component!r}"))


def check_tokens(path, lines):
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        # A device-tree comment or a TOML comment that explains the exclusion is
        # allowed to name the thing; code and configuration are not.
        is_comment = stripped.startswith(("#", "//", "/*", "*"))
        for argument in GPU_ARGUMENTS:
            if re.search(rf'\b{re.escape(argument)}\b', line):
                problems.append(("gpu-argument", f"{rel(path)}:{number}", line.strip()[:160]))
        if is_comment:
            continue
        for token in COVER_PANEL_TOKENS:
            # Word-ish match so that a stray "1392" inside another number or a
            # hash does not trip the check, but a node name or a dimension does.
            if re.search(rf'(?<![0-9a-fx]){re.escape(token)}(?![0-9a-f])', line, re.I):
                problems.append(("cover-panel", f"{rel(path)}:{number}", line.strip()[:160]))


def is_strict(path):
    """Device-tree, configuration, patch and board-package files carry the rules."""
    relative = path.relative_to(REPO)
    if relative.as_posix() in SKIP_PATHS:
        return False
    if any(part in SKIP_DIRS for part in relative.parts):
        return False
    if path.suffix.lower() not in STRICT_SUFFIXES:
        return False
    # Top-level board files, or anything under a strict directory.
    if len(relative.parts) == 1:
        return path.suffix.lower() in {".toml", ".py", ".yml", ".yaml"}
    return relative.parts[0] in STRICT_TOP_DIRS


def check_files():
    for path in sorted(REPO.rglob("*")):
        if not path.is_file():
            continue
        if not is_strict(path):
            continue
        check_tokens(path, scan(path))


def check_defconfig():
    """The defconfig must not switch on a GPU driver or the cover panel."""
    for path in sorted((REPO / "configs").glob("*_defconfig")):
        for number, line in enumerate(scan(path), 1):
            if re.match(r"\s*CONFIG_\w*(GPU|ADRENO|METAL|GMU|SMMU4K)\w*\s*=\s*y", line):
                problems.append(("gpu-config", f"{rel(path)}:{number}", line.strip()))


def main():
    check_components()
    check_files()
    check_defconfig()

    if problems:
        print(f"scope check FAILED: {len(problems)} problem(s)\n")
        for kind, where, detail in problems:
            print(f"  [{kind}] {where}: {detail}")
        print()
        print("The ruyi software-render profile must build no GPU driver and must")
        print("describe the internal panel only. Fix the entries above.")
        return 1

    print("scope check PASSED")
    print("  no GPU component is selected in board.toml")
    print("  no GPU kernel argument or GPU configuration switch is present")
    print("  no cover-panel node, dimension or DSI channel appears in the tree")
    print("  (source-tree check only; it makes no claim about a running kernel)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
