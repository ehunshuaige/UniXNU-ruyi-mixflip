#!/usr/bin/env python3
"""Build the CPU-copy display archive for the ruyi software-render profile.

STATUS: the ABI facts for this kernelcache are now audited and committed
(drivers/RuyiDisplay/mobile-graphics-legacy-abi.json), but the archive still
cannot be built, because two inputs remain:

  1. the object size (`legacy.instance_bytes`) is not derivable from the
     kernelcache - see the JSON's instance_bytes_note; and
  2. the backend leaf implementations and the original-bindings assembly are
     not written for this profile yet.

This script therefore validates the committed audit against the pinned
kernelcache and then stops with the precise remaining work. It fails rather than
emitting an archive built from unverified layout facts.

What the audit established (iOS 16.7.16 / 20H392)
-------------------------------------------------
`com.apple.iokit.IOMobileGraphicsFamily` version 343.0.0,
`__TEXT_EXEC` sha256 03e4c4d80e4f9c78d4ad03366cd3f1d5894d054ae53cdf06b1a43c81a2eab1cd

  Legacy vtable fn0        0xfffffff006def8e0
  virtual entries          338
  abstract slots           [211, 212, 242, 243, 292, 293, 321, 322, 329]
  C2 constructor           0xfffffff005c0bbc8  (stores that vtable)
  newUserClient (slot 141) overridden by Legacy

This differs from the iPadOS 17.7.11 audit the earlier ruyi bring-up recorded
(358 entries, abstract slots [211, 213, 245, 246, 306, 307, 337, 338, 345],
text sha256 2e044ee6...). The two are different binaries, so that audit cannot be
reused here - which is exactly why this script checks the hash instead of
trusting the committed JSON.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
AUDIT = REPO / "drivers/RuyiDisplay/mobile-graphics-legacy-abi.json"

# The kernelcache this profile pins, relative to the device repository or given
# with --kernelcache. Its decompressed arm64 slice is what the audit read.
EXPECTED_SLICE_SHA256 = "2ec297bac95bcba01046fd0148e97e7e5885c05a6c18827f39f534ba375c1221"
EXPECTED_TEXT_SHA256 = "03e4c4d80e4f9c78d4ad03366cd3f1d5894d054ae53cdf06b1a43c81a2eab1cd"
EXPECTED_ENTRIES = 338
EXPECTED_ABSTRACT = [211, 212, 242, 243, 292, 293, 321, 322, 329]


def fail(*lines):
    for line in lines:
        print(line, file=sys.stderr)
    sys.exit(1)


def main():
    argv = sys.argv[1:]
    cache = None
    if "--kernelcache" in argv:
        cache = Path(argv[argv.index("--kernelcache") + 1])
    if not AUDIT.is_file():
        fail("build-gop-legacy-display.py: no ABI audit committed",
             f"  expected {AUDIT}")
    audit = json.loads(AUDIT.read_text())
    source = audit["source"]
    legacy = audit["legacy"]

    # The committed audit must describe THIS profile's kernelcache, not another.
    problems = []
    if source["kext_text_exec_sha256"] != EXPECTED_TEXT_SHA256:
        problems.append(f"audit was taken from kext text {source['kext_text_exec_sha256']}, "
                        f"expected {EXPECTED_TEXT_SHA256}")
    if source["decompressed_arm64_slice_sha256"] != EXPECTED_SLICE_SHA256:
        problems.append("audit pins a different kernelcache slice")
    if legacy["virtual_entries"] != EXPECTED_ENTRIES:
        problems.append(f"audit records {legacy['virtual_entries']} vtable entries, "
                        f"expected {EXPECTED_ENTRIES}")
    if legacy["abstract_slots"] != EXPECTED_ABSTRACT:
        problems.append(f"audit records abstract slots {legacy['abstract_slots']}, "
                        f"expected {EXPECTED_ABSTRACT}")
    if problems:
        fail("build-gop-legacy-display.py: the committed ABI audit does not describe "
             "this profile's kernelcache:", *[f"  - {p}" for p in problems])

    # If a kernelcache was supplied, verify it is the audited binary.
    #
    # The pin covers the *arm64 slice* of the decompressed fat Mach-O, because
    # that is what `unixnu ipsw` writes to kernelcache.decompressed and what the
    # prelink compares. Hashing the whole file (the compressed IM4P, or the fat
    # container) gives a different digest; accept the slice either way.
    if cache is not None:
        if not cache.is_file():
            fail(f"build-gop-legacy-display.py: kernelcache not found: {cache}")
        raw = cache.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != EXPECTED_SLICE_SHA256:
            # A fat Mach-O (0xcafebabe) with one arm64 slice: hash that slice.
            if raw[:4] == b"\xca\xfe\xba\xbe":
                count = struct.unpack_from(">I", raw, 4)[0]
                slices = [struct.unpack_from(">5I", raw, 8 + 20 * i) for i in range(count)]
                arm64 = [s for s in slices if s[0] == 0x0100000C]
                if len(arm64) == 1:
                    _, _, offset, size, _ = arm64[0]
                    digest = hashlib.sha256(raw[offset:offset + size]).hexdigest()
        if digest != EXPECTED_SLICE_SHA256:
            fail("build-gop-legacy-display.py: kernelcache is not the audited one",
                 f"  {cache}", f"  arm64 slice sha256 {digest}",
                 f"  expected {EXPECTED_SLICE_SHA256}")

    print("build-gop-legacy-display.py: ABI audit verified against the pinned kernelcache",
          file=sys.stderr)
    print(f"  Legacy vtable fn0 {legacy['vtable_fn0']}, {legacy['virtual_entries']} entries",
          file=sys.stderr)
    print(f"  abstract slots {legacy['abstract_slots']}", file=sys.stderr)
    print(f"  C2 constructor {legacy['constructor_va']}", file=sys.stderr)
    fail("",
         "build-gop-legacy-display.py: cannot emit the display archive yet. Remaining work:",
         "  1. legacy.instance_bytes - the object size is not in the kernelcache; read it from",
         "     a live prelink run (the iPadOS value 0x18a0 belongs to a different binary).",
         "  2. the backend leaf implementations for the abstract slots above, and the",
         "     original-bindings assembly that binds every non-overridden slot to its exact",
         "     address in this kernelcache.",
         "",
         "  Adapt UniXNU/UniXNU-sheng scripts/build-gop-legacy-display.py for the structure,",
         "  but take every address from drivers/RuyiDisplay/mobile-graphics-legacy-abi.json.",
         "",
         "  See the display area of porting.toml.")


if __name__ == "__main__":
    main()
