#!/usr/bin/env python3
"""Build the CPU-copy display archive for the ruyi software-render profile.

THIS SCRIPT INTENTIONALLY FAILS. It exists so the build stops here with an
explanation instead of failing later with a confusing link error.

Why it cannot build yet
-----------------------
The display component (GopFramebuffer) reuses the kernel's genuine original
IOMobileFramebuffer "Legacy" implementation and only supplies the backend leaves.
To do that safely it must know the exact original class layout for the kernel it
is being linked into: the vtable slot count, the abstract slots, the object size
and a handful of field offsets.

The earlier ruyi bring-up produced exactly those facts and device-verified a
working CPU-copy display on this phone. But it audited them against the
**iPadOS 17.7.11 (21H461)** kernelcache, where
`com.apple.iokit.IOMobileGraphicsFamily` has `__TEXT_EXEC` sha256
`2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b`.

This profile runs the **iOS 16.7.16 (20H392)** kernelcache, where the same kext
is a different binary: version 343.0.0, `__TEXT_EXEC` sha256
`03e4c4d80e4f9c78d4ad03366cd3f1d5894d054ae53cdf06b1a43c81a2eab1cd`.
A driver built from the iPadOS facts would dispatch through the wrong vtable
entries - it would not fail to build, it would fail at runtime in a way that is
very hard to diagnose on a phone whose only console is the panel.

What unblocks it
----------------
1. Produce a prelink candidate from the 20H392 kernelcache:
       ./unixnu build prelink -D ../UniXNU-ruyi
   with `--kernelcache` pointing at the 20H392 kernelcache.
2. Run the shared audit against that candidate:
       python3 scripts/audit-mobile-graphics-legacy.py
   It writes build/display-analysis/mobile-graphics-legacy-abi.json.
3. Copy that JSON to drivers/RuyiDisplay/mobile-graphics-legacy-abi.json, then
   replace this script with the real builder (adapt
   UniXNU/UniXNU-sheng scripts/build-gop-legacy-display.py, which has the same
   structure), pinning the 20H392 family hash rather than 2e044ee6.

Until all three are done, the display archive cannot be produced and the
software-render milestone cannot be reached.
"""
import sys

EXPECTED = "03e4c4d80e4f9c78d4ad03366cd3f1d5894d054ae53cdf06b1a43c81a2eab1cd"
AUDITED = "2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b"

print("build-gop-legacy-display.py: the ruyi display archive cannot be built yet.", file=sys.stderr)
print("", file=sys.stderr)
print("  This profile's kernelcache (iOS 16.7.16 / 20H392) carries", file=sys.stderr)
print(f"    IOMobileGraphicsFamily __TEXT_EXEC sha256 {EXPECTED}", file=sys.stderr)
print("  The recorded ABI audit was taken from the iPadOS 17.7.11 kernelcache:", file=sys.stderr)
print(f"    IOMobileGraphicsFamily __TEXT_EXEC sha256 {AUDITED}", file=sys.stderr)
print("", file=sys.stderr)
print("  Different binary -> the audited vtable offsets, abstract slots and object", file=sys.stderr)
print("  size do not describe this kernel. Re-run scripts/audit-mobile-graphics-legacy.py", file=sys.stderr)
print("  against a 20H392 prelink candidate and commit the result as", file=sys.stderr)
print("  drivers/RuyiDisplay/mobile-graphics-legacy-abi.json first.", file=sys.stderr)
print("", file=sys.stderr)
print("  See the docstring of this file and the display area of porting.toml.", file=sys.stderr)
sys.exit(1)
