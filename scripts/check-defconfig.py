#!/usr/bin/env python3
"""Validate the effective kernel configuration of the software-render profile.

`unixnu defconfig` does not read one file: it concatenates the arch, SoC and OS
fragments selected by `[kernel] config_fragments` and then the device defconfig,
and a later line wins. This reproduces that merge and checks the result, because
two failures are otherwise invisible until a kernel is built:

  * a `CONFIG_XNU_*` name the build scripts never read - it parses, it is
    written to .config, and it silently does nothing;
  * a profile fragment quietly enabling something this profile must not have
    (a GPU driver, or the UFS stack the RAM-disk root route does not use).

    python3 scripts/check-defconfig.py --unixnu ../UniXNU
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Options that must not be enabled in the software-render profile. A GPU driver
# here would contradict the whole point of the port; UFS is off because the root
# filesystem is a RAM disk and enabling it would add an unverified DMA consumer.
FORBIDDEN = re.compile(r"^XNU_(.*(?:GPU|ADRENO|METAL|GMU|SMMU4K|UFS|VIRTIO_BLOCK|RAM_BLOCK|MOBILE_DISPLAY|ARMVIRT).*)$")

# Options this profile depends on. If one of these is not actually enabled the
# milestone cannot work, so a silent fragment override is worth catching here.
REQUIRED = {
    "XNU_NATIVE_LEGACY_DISPLAY": "the CPU-copy display path this profile exists for",
    "XNU_ARM_DT_PLATFORM": "the platform expert built from the board DTS",
    "XNU_ARMCPU": "the GICv3 and timer driver",
    "XNU_DT_PANIC_REGION": "panic region from the device tree instead of Apple's fixed address",
}


def parse(text):
    """Parse a defconfig the way unixnu.config.parse_config does."""
    values = {}
    errors = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        unset = re.fullmatch(r"#\s*CONFIG_(\w+) is not set", line)
        if unset:
            values[unset.group(1)] = False
            continue
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"CONFIG_(\w+)=(.*)", line)
        if not match:
            errors.append(f"line {number} is not CONFIG_NAME=value: {line}")
            continue
        name, raw = match.groups()
        if raw == "y":
            values[name] = True
        elif raw == "n":
            values[name] = False
        elif raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            values[name] = raw[1:-1]
        elif re.fullmatch(r"-?(0x[0-9a-fA-F]+|\d+)", raw):
            values[name] = int(raw, 16 if raw.lstrip("-").startswith("0x") else 10)
        else:
            errors.append(f"line {number} has an unparseable value: {line}")
    return values, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--unixnu", type=Path, default=REPO.parent / "UniXNU")
    parser.add_argument("--device", type=Path, default=REPO)
    args = parser.parse_args()
    unixnu, device = args.unixnu.resolve(), args.device.resolve()

    board_text = (device / "board.toml").read_text()
    fragments = re.search(r"config_fragments\s*=\s*\[(.*?)\]", board_text, re.S)
    defconfig = re.search(r'defconfig\s*=\s*"([^"]+)"', board_text)
    if not fragments or not defconfig:
        print("check-defconfig: board.toml has no kernel.config_fragments or kernel.defconfig",
              file=sys.stderr)
        return 2
    names = re.findall(r'"([^"]+)"', fragments.group(1))
    os_profile = re.search(r'os_profile\s*=\s*"([^"]+)"', board_text).group(1)

    # Resolve the fragment paths exactly as unixnu does: prefixed paths are
    # relative to that profile root, unprefixed ones to the device repository.
    paths = []
    for entry in names:
        prefix, _, relative = entry.partition(":")
        if prefix == "arch":
            paths.append(unixnu / "profiles/arch/arm64" / relative)
        elif prefix == "os":
            paths.append(unixnu / "profiles/os" / os_profile / relative)
        elif prefix == "soc":
            soc = re.search(r'local\s*=\s*"([^"]+)"', (device / "feeds.toml").read_text())
            if not soc:
                print("check-defconfig: feeds.toml has no local soc source", file=sys.stderr)
                return 2
            paths.append(device / soc.group(1) / relative)
        else:
            paths.append(device / relative)
    paths.append(device / "configs" / defconfig.group(1))

    merged = []
    problems = []
    for path in paths:
        if not path.is_file():
            problems.append(f"configuration fragment missing: {path}")
            continue
        merged.append(path.read_text())
        print(f"  fragment {path}")

    values, errors = parse("\n".join(merged))
    problems.extend(errors)

    print()
    print(f"effective configuration: {len(values)} options")
    for name in sorted(values):
        value = values[name]
        shown = "y" if value is True else "n" if value is False else repr(value)
        print(f"  {name:38} {shown}")

    print()
    for name, value in sorted(values.items()):
        if value is not True:
            continue
        if FORBIDDEN.match(name):
            problems.append(f"{name} is enabled, but this profile must not have it")

    for name, why in REQUIRED.items():
        if values.get(name) is not True:
            problems.append(f"{name} is not enabled ({why})")

    # Every enabled option must actually be read by the build scripts, or it is
    # silently dead configuration.
    scripts = "\n".join(p.read_text(errors="replace")
                        for p in (unixnu / "scripts").rglob("*")
                        if p.is_file() and p.suffix in (".sh", ".py"))
    for name, value in sorted(values.items()):
        if value is not True:
            continue
        if name not in scripts:
            problems.append(f"{name} is enabled but no build script reads it "
                            f"(the option does nothing)")

    if problems:
        print()
        for problem in problems:
            print(f"  FAIL {problem}")
        print()
        print(f"{len(problems)} problem(s) in the effective configuration.")
        return 1
    print()
    print("PASS: the merged configuration enables the software display path,")
    print("      switches nothing forbidden on, and every enabled switch is read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
