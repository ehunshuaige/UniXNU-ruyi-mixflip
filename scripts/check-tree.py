#!/usr/bin/env python3
"""Check the ruyi hardware tree and ADT against what the UniXNU components require.

This is a host check: it compiles the board DTS, generates the Apple device tree
exactly the way `unixnu build payload` does, and then verifies that everything
the selected kernel components read is actually present and consistent.

It answers the questions that would otherwise only be answered by a failed boot:

  * does the board DTS compile at all
  * is there exactly one contiguous DRAM range, and does payload.dram_size match
  * are all eight CPUs exported with the right affinities and cluster types
  * does /arm-io/intc carry both GIC ranges and the GICv4 redistributor stride
  * does /chosen carry the identity, NVRAM proxy and memory-map placeholders that
    ArmDTPlatform and DarwinBoot require
  * does the display reservation match the ABL scanout buffer
  * does the cover panel appear anywhere in the compiled tree (it must not)

It makes no claim about hardware behaviour. Run it from a UniXNU checkout:

    python3 ../UniXNU-ruyi/scripts/check-tree.py

or pass the two paths explicitly:

    python3 scripts/check-tree.py --unixnu ../UniXNU --device .
"""
import argparse
import struct
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Apple device tree encoding: property/child counts and lengths are little-endian.
def parse_node(blob, offset=0):
    properties, children = struct.unpack_from("<II", blob, offset)
    offset += 8
    props = []
    for _ in range(properties):
        name = struct.unpack_from("<32s", blob, offset)[0].split(b"\0")[0]
        offset += 32
        length = struct.unpack_from("<I", blob, offset)[0]
        offset += 4
        value = blob[offset:offset + length]
        offset += length + (-length % 4)
        props.append((name, value))
    kids = []
    for _ in range(children):
        child, offset = parse_node(blob, offset)
        kids.append(child)
    return (props, kids), offset


def node_name(node):
    return dict(node[0]).get(b"name", b"").split(b"\0")[0].decode(errors="replace")


def prop(node, name):
    return dict(node[0]).get(name if isinstance(name, bytes) else name.encode())


def find(node, name):
    if node_name(node) == name:
        return node
    for child in node[1]:
        hit = find(child, name)
        if hit:
            return hit
    return None


def u32(value):
    return struct.unpack("<I", value)[0]


def u64(value):
    return struct.unpack("<Q", value)[0]


failures = []
notes = []


def need(condition, message):
    if not condition:
        failures.append(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--unixnu", type=Path, default=HERE.parent.parent / "UniXNU",
                        help="UniXNU checkout (default: ../UniXNU)")
    parser.add_argument("--device", type=Path, default=HERE.parent,
                        help="device repository (default: this repository)")
    args = parser.parse_args()

    unixnu = args.unixnu.resolve()
    device = args.device.resolve()
    sys.path.insert(0, str(unixnu / "scripts"))
    try:
        from unixnu import devicetree, profiles
        from unixnu.config import load_toml
    except ImportError as error:
        print(f"cannot import the UniXNU build driver from {unixnu}: {error}")
        return 2

    board = load_toml(device / "board.toml")
    os_profile_name = board["board"]["os_profile"]
    os_profile = load_toml(unixnu / "profiles" / "os" / os_profile_name / "profile.toml")

    # Resolve the board-local SoC slice the same way the build driver does: the
    # feeds.toml entry is a local directory, so no network is involved.
    soc_name = board["board"]["soc_source"]
    feeds = tomllib.loads((device / "feeds.toml").read_text())
    entry = next((s for s in feeds.get("source", []) if s.get("kind") == "soc" and s.get("name") == soc_name), None)
    if entry is None:
        failures.append(f"feeds.toml has no soc source named {soc_name!r}")
        return report()
    if entry.get("local"):
        soc_dir = device / entry["local"]
    else:
        failures.append(f"soc source {soc_name!r} is a git source; this check only resolves local slices")
        return report()
    soc = tomllib.loads((soc_dir / "soc.toml").read_text())
    config = profiles.merge(profiles.merge(os_profile, soc), board)
    notes.append(f"SoC slice {soc_name} resolved from {entry['local']} (components: "
                 f"{', '.join(soc.get('components', {}).get('include', [])) or 'none'})")

    # 1. Compile the board DTS.
    source = device / board["device_tree"]["source"].split(":", 1)[1]
    scratch = tempfile.TemporaryDirectory()
    try:
        dtb = Path(scratch.name) / "hardware.dtb"
        command = ["dtc", "-I", "dts", "-O", "dtb", "-o", str(dtb)]
        for directory in board["device_tree"].get("include_dirs", []):
            prefix, _, relative = directory.partition(":")
            if prefix == "soc":
                base = soc_dir
            elif prefix in ("arch", "os"):
                base = unixnu / "profiles" / prefix
            else:
                base = device
            command += ["-i", str(base / relative)]
        result = subprocess.run(command + [str(source)], capture_output=True, text=True)
        need(result.returncode == 0, f"the board DTS does not compile:\n{result.stderr.strip()}")
        if result.returncode:
            return report()
        notes.append(f"board DTS compiles to {dtb.stat().st_size} bytes")

        # 2. Generate the Apple device tree exactly as the payload step does.
        try:
            blob = devicetree.generate(dtb, config, unique_chip_id="0x5357454554000001",
                                       data=True, trust=True)
            hardware_blob = dtb.read_bytes()
        except Exception as error:  # the generator raises its own Error type
            failures.append(f"the ADT generator rejects the tree: {error}")
            return report()
    finally:
        # The hardware DTB is read into memory above; the directory can go.
        scratch.cleanup()

    root, consumed = parse_node(blob)
    need(consumed == len(blob), f"the ADT has {len(blob) - consumed} trailing bytes")
    notes.append(f"ADT generates: {len(blob)} bytes, fully consumed")

    top = {node_name(child): child for child in root[1]}

    # 3. Nodes ArmDTPlatform requires before it will configure().
    for required in ("chosen", "cpus", "arm-io", "defaults", "options"):
        need(required in top, f"ArmDTPlatform requires /{required}; it is absent")

    # 4. /chosen: identity, NVRAM proxy and memory-map placeholders.
    chosen = top.get("chosen")
    if chosen:
        for required in (b"random-seed", b"nvram-bank-size", b"nvram-bank-count",
                         b"nvram-current-bank", b"nvram-proxy-data", b"dram-base",
                         b"dram-size", b"unique-chip-id", b"chip-id", b"crypto-hash-method",
                         b"osenvironment"):
            need(prop(chosen, required) is not None,
                 f"/chosen is missing {required.decode()}, which the platform expert or the userland reads")
        seed = prop(chosen, b"random-seed")
        if seed is not None:
            need(len(seed) == 64, f"/chosen random-seed is {len(seed)} bytes, expected 64")
        memory_map = find(chosen, "memory-map")
        need(memory_map is not None, "/chosen/memory-map is absent")
        if memory_map:
            for required in (b"RAMDisk", b"TrustCache"):
                value = prop(memory_map, required)
                need(value is not None and len(value) == 16,
                     f"/chosen/memory-map/{required.decode()} must be a 16-byte placeholder")

        # DRAM window must match payload.dram_size, which the payload step enforces.
        base, size = prop(chosen, b"dram-base"), prop(chosen, b"dram-size")
        if base and size:
            declared = int(str(board["payload"]["dram_size"]), 0)
            need(u64(size) == declared,
                 f"/chosen dram-size {u64(size):#x} differs from payload.dram_size {declared:#x}")
            notes.append(f"DRAM window {u64(base):#x} + {u64(size):#x} ({(u64(size)) / 2**30:.2f} GiB)")

    # 5. /cpus: eight cores, MPIDR affinities, E/P split, one boot CPU.
    cpus = top.get("cpus")
    if cpus:
        entries = cpus[1]
        need(len(entries) == 8, f"/cpus exports {len(entries)} CPUs; SM8650 has 8")
        affinities = []
        states = []
        for entry in entries:
            reg = prop(entry, b"reg")
            need(reg is not None, f"{node_name(entry)} has no reg")
            if reg:
                affinities.append(u32(reg))
            state = prop(entry, b"state")
            states.append(state.split(b"\0")[0].decode() if state else "")
            need(prop(entry, b"timebase-frequency") is not None,
                 f"{node_name(entry)} has no timebase-frequency")
        need(affinities == [i * 0x100 for i in range(8)],
             f"CPU affinities are {[hex(a) for a in affinities]}, expected 0x0,0x100,...,0x700")
        need(states.count("running") == 1,
             f"{states.count('running')} CPUs are marked running; exactly one boot CPU is expected")
        cluster = {}
        for entry in entries:
            value = prop(entry, b"cluster-type")
            if value:
                cluster[node_name(entry)] = chr(u32(value))
        need(len(cluster) == 8, "every CPU needs a cluster-type for the E/P scheduler split")
        if cluster:
            e = sum(1 for v in cluster.values() if v == "E")
            p = sum(1 for v in cluster.values() if v == "P")
            need(e + p == 8 and e > 0 and p > 0,
                 f"cluster split is {e} E / {p} P; SM8650 needs both clusters populated")
            notes.append(f"CPUs: 8 cores, {e} E / {p} P")

    # 6. /arm-io/intc: both GIC ranges and the GICv4 redistributor stride.
    arm_io = top.get("arm-io")
    if arm_io:
        need(prop(arm_io, b"ranges") is not None, "/arm-io has no ranges")
        intc = find(arm_io, "intc")
        need(intc is not None, "/arm-io/intc is absent; ArmCpu matches on it")
        if intc:
            reg = prop(intc, b"reg")
            need(reg is not None and len(reg) == 32,
                 "/arm-io/intc reg must be two address/size pairs (distributor and redistributors)")
            stride = prop(intc, b"redistributor-stride")
            need(stride is not None, "/arm-io/intc has no redistributor-stride")
            if stride:
                value = u64(stride)
                need(value == 0x40000,
                     f"redistributor-stride is {value:#x}; this is a GICv4 SoC and needs 0x40000")

    # 7. The display reservation must be the ABL scanout buffer.
    #
    # This is checked in the *hardware* FDT, not in the generated ADT: the ADT
    # generator exports only nodes carrying unixnu,adt-name plus the platform
    # nodes, and reserved-memory is a firmware/bootloader concern that stays in
    # the hardware tree. Checking the ADT for it would always fail.
    hardware = devicetree.read_fdt(hardware_blob)
    splash = None
    for candidate in hardware.walk():
        if candidate.name == "framebuffer@fc400000":
            splash = candidate
    need(splash is not None,
         "the hardware tree has no /reserved-memory/framebuffer@fc400000 (the ABL scanout buffer)")
    if splash is not None:
        reg = splash.properties.get("reg")
        label = splash.properties.get("label")
        if reg and len(reg) == 16:
            address, size = struct.unpack(">QQ", reg)
            need(address == 0xFC400000,
                 f"scanout buffer starts at {address:#x}; the ABL splash region is 0xFC400000")
            need(size >= 1224 * 2912 * 4,
                 f"scanout buffer is {size:#x} bytes; 1224x2912x4 needs {1224 * 2912 * 4:#x}")
            notes.append(f"scanout reservation {address:#x} + {size:#x} "
                         f"({size / 2**20:.0f} MiB, a frame needs {1224 * 2912 * 4 / 2**20:.1f} MiB)")
        else:
            need(False, "the scanout reservation has no decodable reg property")
        if label:
            need(label.split(b"\0")[0] == b"cont_splash_region",
                 "the scanout reservation label must stay cont_splash_region; ABL keys the panel on it")
        else:
            need(False, "the scanout reservation has no label; ABL needs cont_splash_region")

    # 8. The cover panel must not be anywhere in the compiled tree.
    def strings_of(node):
        for name, value in node[0]:
            yield name.decode(errors="replace")
            yield value.decode(errors="replace")
        for child in node[1]:
            yield from strings_of(child)

    joined = "\n".join(strings_of(root))
    # Also scan the hardware tree's own property values and node names.
    for candidate in hardware.walk():
        joined += "\n" + candidate.name
        for name, value in candidate.properties.items():
            joined += "\n" + name + "\n" + value.decode(errors="replace")
    for token in ("1208", "1392", "sec_dsc", "sec_p11", "dsi_display1"):
        need(token not in joined, f"the cover panel token {token!r} appears in the compiled ADT")

    # 9. No GPU node should be exported either.
    for token in ("adreno", "gmu", "kgsl", "smmu"):
        need(token not in joined.lower(), f"a GPU-related token {token!r} appears in the compiled ADT")

    return report()


def report():
    print("ruyi hardware tree check")
    print()
    for note in notes:
        print(f"  ok   {note}")
    if failures:
        print()
        for failure in failures:
            print(f"  FAIL {failure}")
        print()
        print(f"{len(failures)} problem(s). The tree does not satisfy the selected components.")
        return 1
    print()
    print("PASS: the board DTS and generated ADT satisfy every checked requirement.")
    print("This is a host check of the tree; it says nothing about hardware behaviour.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
