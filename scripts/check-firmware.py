#!/usr/bin/env python3
"""Check that a ruyi Mu-Silicium checkout can actually boot the UniXNU payload.

The firmware is not built by this repository, but its *integration* is this
board's responsibility: a DSC or FDF that is missing one module produces a
firmware that boots, shows the UniXNU menu, and then offers no entries - which
looks like a payload problem and is very expensive to diagnose on a phone whose
only console is the panel.

This check compares the checkout against the required-integration list in the
UniXNU porting guide (docs/porting/uefi-firmware.md, "Required integration") and
against two structural rules the EDK II build enforces:

  * every module in the FDF firmware volume must also be listed in the DSC
    [Components] section, or the build fails;
  * the FAT driver needs a Unicode collation provider, so EnglishDxe (or an
    equivalent) must be present when Fat.inf is.

    python3 scripts/check-firmware.py --uefi /path/to/ruyi-Mu-Silicium
    python3 scripts/check-firmware.py            # tries UNIXNU_UEFI, ../uefi-ruyi

Exit status 0 when the integration is complete, 1 otherwise.
"""
import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# The modules the payload path needs, from the UniXNU porting guide. The keys are
# the module INF paths; the values say what breaks without them.
REQUIRED = {
    "UniXNUPkg/Application/UniXNU/UniXNU.inf":
        "the boot menu and configuration reader",
    "UniXNUPkg/Driver/UniXNUDxe/UniXNUDxe.inf":
        "firmware boot-option registration",
    "DarwinBootPkg/Driver/DarwinBoot.inf":
        "the XNU loader - without it UniXNU cannot hand off to the kernel",
    "MdeModulePkg/Universal/Disk/DiskIoDxe/DiskIoDxe.inf":
        "block access for the filesystem driver",
    "FatPkg/EnhancedFatDxe/Fat.inf":
        "the payload's FAT filesystem",
}

# Either the shared driver or a board-local equivalent satisfies payload
# discovery. ruyi ships RuyiInitrdDxe, a port of giulia's driver with the ruyi
# DDR-bank scan rules; the shared UniXNURamDiskDxe is the upstream alternative.
RAMDISK_ALTERNATIVES = (
    "UniXNUPkg/Driver/UniXNURamDiskDxe/UniXNURamDiskDxe.inf",
    "ruyiPkg/Drivers/RuyiInitrdDxe/RuyiInitrdDxe.inf",
)

# The FAT driver requires a Unicode collation service.
COLLATION = (
    "MdeModulePkg/Universal/Disk/UnicodeCollation/EnglishDxe/EnglishDxe.inf",
)

# PartitionDxe is required when the payload carries a partition table. The
# UniXNU boot payload is a bare FAT volume, so it is optional - but a board that
# puts the payload on a partitioned image needs it.
OPTIONAL = {
    "MdeModulePkg/Universal/Disk/PartitionDxe/PartitionDxe.inf":
        "payload on a partitioned image",
}

INF_LINE = re.compile(r"^\s*INF\s+(\S+?\.inf)\s*$", re.M | re.I)
INCLUDE_LINE = re.compile(r"^\s*!include\s+(\S+)\s*$", re.M | re.I)


def resolve_includes(path, seen=None, depth=0):
    """Inline a DSC's !include directives so all its [Components] are visible.

    EDK II splits platform descriptions across .inc fragments: the ruyi DSC
    includes LanaiPkg.dsc.inc, which includes QcomPkg.dsc.inc, and those carry
    components the top-level file never spells out. A checker that reads only
    the top-level DSC reports every one of them as missing.
    """
    if seen is None:
        seen = set()
    if depth > 12 or path in seen or not path.is_file():
        return ""
    seen.add(path)
    out = []
    for line in path.read_text().splitlines(keepends=True):
        match = INCLUDE_LINE.match(line)
        if not match:
            out.append(line)
            continue
        target = match.group(1)
        candidate = find_include(path, target)
        if candidate is not None:
            out.append(resolve_includes(candidate, seen, depth + 1))
        else:
            out.append(line)
    return "".join(out)


def find_include(path, target):
    """Resolve an !include target the way EDK II's PACKAGES_PATH would.

    Mu-Silicium writes platform includes as paths from a package root
    ("LanaiPkg/LanaiPkg.dsc.inc"), not from the including file, so the target is
    looked up relative to the file first and then anywhere in the checkout by
    matching the path suffix.
    """
    for candidate in (path.parent / target, path.parent.parent / target):
        if candidate.is_file():
            return candidate
    # Walk up to the checkout root and search the whole tree once, cheapest
    # match first: the shortest path that ends with the target.
    root = path.parent
    while root.parent != root and (root / "Silicon").is_dir() is False and (root / "Common").is_dir() is False:
        root = root.parent
    if not (root / "Silicon").is_dir() and not (root / "Common").is_dir():
        return None
    suffix = "/" + target.strip("/")
    best = None
    for candidate in root.rglob(Path(target).name):
        if candidate.as_posix().endswith(suffix) and candidate.is_file():
            if best is None or len(candidate.as_posix()) < len(best.as_posix()):
                best = candidate
    return best


def read_board_dsc(repo):
    """The DSC path from board.toml [firmware], without a TOML parser round-trip."""
    text = (repo / "board.toml").read_text()
    match = re.search(r'^dsc\s*=\s*"([^"]+)"', text, re.M)
    return match.group(1) if match else None


def sections(text):
    """Split an EDK II DSC into {section-name: body} preserving case of bodies."""
    found, current, body = {}, None, []
    for line in text.splitlines():
        header = re.match(r"^\[([A-Za-z_.\s]+)\]\s*$", line)
        if header:
            if current is not None:
                found.setdefault(current, []).extend(body)
            current, body = header.group(1).strip(), []
            continue
        if current is not None:
            body.append(line)
    if current is not None:
        found.setdefault(current, []).extend(body)
    return {name: "\n".join(lines) for name, lines in found.items()}


def in_dsc_components(dsc_sections, module):
    """Is module listed as a component (an uncommented line that is exactly it)?"""
    body = dsc_sections.get("Components", "")
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # A component line may open a library-class override block: "Mod.inf {".
        names = stripped.split()
        if names and names[0].lower() == module.lower():
            return True
    return False


def in_fdf(fdf_text, module):
    """Is module present as an uncommented INF line?"""
    for match in INF_LINE.finditer(fdf_text):
        segment = fdf_text[fdf_text.rfind("\n", 0, match.start()) + 1:match.start()]
        if segment.strip().startswith("#"):
            continue
        if match.group(1).strip().lower() == module.lower():
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uefi", type=Path,
                        help="ruyi Mu-Silicium checkout (default: $UNIXNU_UEFI, then ../uefi-ruyi)")
    parser.add_argument("--device", type=Path, default=REPO, help="device repository")
    args = parser.parse_args()

    uefi = args.uefi
    if uefi is None and os.environ.get("UNIXNU_UEFI"):
        uefi = Path(os.environ["UNIXNU_UEFI"])
    if uefi is None:
        candidate = args.device.parent / "uefi-ruyi"
        if candidate.is_dir():
            uefi = candidate
    if uefi is None or not uefi.is_dir():
        print("check-firmware: no ruyi Mu-Silicium checkout given.", file=sys.stderr)
        print("  pass --uefi DIR, set UNIXNU_UEFI, or place it at ../uefi-ruyi", file=sys.stderr)
        return 2

    dsc_rel = read_board_dsc(args.device)
    if not dsc_rel:
        print(f"check-firmware: {args.device / 'board.toml'} has no [firmware] dsc", file=sys.stderr)
        return 2
    dsc_path = uefi / dsc_rel
    fdf_path = dsc_path.with_suffix(".fdf")
    for path in (dsc_path, fdf_path):
        if not path.is_file():
            print(f"check-firmware: missing {path}", file=sys.stderr)
            return 2

    dsc = sections(resolve_includes(dsc_path))
    fdf_text = fdf_path.read_text()

    problems = []
    present = []

    # 1. Required modules, in both the DSC and the FDF.
    for module, purpose in REQUIRED.items():
        in_d = in_dsc_components(dsc, module)
        in_f = in_fdf(fdf_text, module)
        if in_d and in_f:
            present.append(module)
        elif not in_d and not in_f:
            problems.append(f"{module} is in neither the DSC [Components] nor the FDF ({purpose})")
        elif not in_d:
            problems.append(f"{module} is in the FDF but not in DSC [Components] - the build will fail ({purpose})")
        else:
            problems.append(f"{module} is in DSC [Components] but not in the FDF - it will not be in the firmware volume ({purpose})")

    # 2. Payload discovery: at least one ramdisk driver, wired the same way.
    ramdisk = [m for m in RAMDISK_ALTERNATIVES
               if in_dsc_components(dsc, m) and in_fdf(fdf_text, m)]
    if ramdisk:
        present.append(ramdisk[0])
    else:
        wired = [m for m in RAMDISK_ALTERNATIVES
                 if in_dsc_components(dsc, m) or in_fdf(fdf_text, m)]
        if wired:
            problems.append(f"{wired[0]} is only partially wired (needs both DSC [Components] and FDF)")
        else:
            problems.append("no ramdisk driver is wired: the payload FAT volume is never published "
                            f"({' or '.join(RAMDISK_ALTERNATIVES)})")

    # 3. FAT needs a Unicode collation provider.
    if in_dsc_components(dsc, REQUIRED["FatPkg/EnhancedFatDxe/Fat.inf"]) or \
            in_fdf(fdf_text, REQUIRED["FatPkg/EnhancedFatDxe/Fat.inf"]):
        if not any(in_dsc_components(dsc, m) and in_fdf(fdf_text, m) for m in COLLATION):
            problems.append("Fat.inf is wired but no Unicode collation driver is: "
                            f"add {COLLATION[0]} to both DSC [Components] and FDF")

    # 4. Structural rule: every FDF INF must be a DSC component.
    for match in INF_LINE.finditer(fdf_text):
        line_start = fdf_text.rfind("\n", 0, match.start()) + 1
        if fdf_text[line_start:match.start()].strip().startswith("#"):
            continue
        module = match.group(1).strip()
        if not in_dsc_components(dsc, module):
            problems.append(f"FDF lists {module}, which is not in DSC [Components]: the EDK II build rejects this")

    # Optional modules, reported but not fatal.
    for module, why in OPTIONAL.items():
        if in_dsc_components(dsc, module) and in_fdf(fdf_text, module):
            present.append(module + f"  (optional: {why})")

    print(f"ruyi firmware integration check against {uefi}")
    print(f"  DSC {dsc_rel}")
    print(f"  FDF {dsc_path.with_suffix('.fdf').relative_to(uefi)}")
    print()
    for module in present:
        print(f"  ok   {module}")
    if problems:
        print()
        for problem in problems:
            print(f"  FAIL {problem}")
        print()
        print(f"{len(problems)} problem(s). The firmware would not carry a usable payload.")
        return 1
    print()
    print("PASS: the firmware carries the boot manager, the XNU loader and the")
    print("      block/partition/FAT stack the payload is read through.")
    print("      The firmware itself is not built by this check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
