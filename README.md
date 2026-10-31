# UniXNU-ruyi

UniXNU device repository for the **Xiaomi MIX Flip** (`ruyi`, Qualcomm SM8650 /
Snapdragon 8 Gen 3), running the **iOS 16.7.16 (20H392) userland of the iPhone X**
on a self-built Darwin 22 kernel.

This repository is the *board layer*: the device tree, component selection,
kernel configuration, firmware inputs, payload parameters and the porting record.
Shared build tooling, drivers and OS profiles come from
[UniXNU](https://github.com/UniXNU/UniXNU).

## Scope: software rendering, internal display only

Two constraints define this port, and both are structural rather than aspirational:

1. **No GPU driver.** CoreAnimation composites on the CPU and the result is copied
   into the scanout buffer the bootloader hands over. `board.toml` selects no GPU
   component at all, so no Adreno driver, no GPU firmware and no Metal frontend is
   built or loaded. Switching to a GPU path would mean selecting GPU components,
   not uncommenting code.

2. **Internal display only.** The internal folding panel is 1224 x 2912 native
   pixels (2912 x 1224 as the user sees it), 32-bit, stride 4896 bytes. The cover
   display has no node, no property, no component and no kernel argument here.

`scripts/check-scope.py` enforces both rules over the device tree, configuration,
patch series and board package.

## Status

**This port has not been booted from this repository.** The record is explicit
about which links are verified and which are not:

| Link | State |
| --- | --- |
| Board DTS compiles; ADT generates | host-verified |
| IPSW identity and member pins | host-verified, cross-checked against an independent SM8650 iOS 16 port |
| Prelink roots exist in the target kernelcache | host-verified, 31/31 |
| Porting record passes the UniXNU checker | host-verified, 13 areas |
| Display ABI audited against this kernelcache | host-verified - see below |
| Firmware payload wiring | host-verified by `check-firmware.py`; firmware not built |
| Kernel builds and prelinks | **not run** - needs a macOS runner or the Linux toolchain |
| Display driver builds | **blocked** - two inputs still missing |
| Boots to SpringBoard on the internal panel | **not demonstrated** |

### The display ABI, and what is still missing

The earlier ruyi bring-up device-verified a CPU-copy display driver, but audited
its ABI against the **iPadOS 17.7.11** kernelcache. This profile runs the iOS
16.7.16 kernelcache, where `IOMobileGraphicsFamily` is a different binary, so
those facts do not apply.

That audit has now been redone from the pinned kernelcache and is committed as
`drivers/RuyiDisplay/mobile-graphics-legacy-abi.json`:

| Fact | iOS 16.7.16 (20H392) | iPadOS 17.7.11 (for contrast) |
| --- | --- | --- |
| `IOMobileGraphicsFamily` | 343.0.0 | - |
| `__TEXT_EXEC` sha256 | `03e4c4d8…` | `2e044ee6…` |
| Legacy vtable | `0xfffffff006def8e0` | - |
| virtual entries | **338** | 358 |
| abstract slots | `[211, 212, 242, 243, 292, 293, 321, 322, 329]` | `[211, 213, 245, 246, 306, 307, 337, 338, 345]` |
| C2 constructor | `0xfffffff005c0bbc8` | - |
| instance size | **0x1660** | 0x18a0 |

The two binaries differ in both slot count and abstract set, which is exactly why
the old audit could not be reused: a driver built from it would link and then
dispatch through the wrong entries.

The instance size is derived statically rather than from a live run: the
derived-meta-class constructor at `0xfffffff005c0bc94` passes the class-name
string, the superclass meta class and `MOVZ w3,#0x1660` to
`OSMetaClass::OSMetaClass`, and that third argument is the size `alloc()` uses.

The archive still cannot be built: the nine **backend leaf implementations** for
the abstract slots above and the original-bindings assembly are not written yet.
`scripts/build-gop-legacy-display.py` verifies the committed audit against the
pinned kernelcache and then stops with that list.

## Repository layout

```text
board.toml              format 2 board description and component selection
porting.toml            the authoritative porting record (13 areas)
configs/ruyi_defconfig  kernel configuration for the software-render profile
dts/ruyi.dts            board device tree (internal panel only)
patches/xnu/series      board patch series (empty: no board patches yet)
scripts/check-scope.py    enforces "no GPU driver, no cover display"
scripts/check-tree.py     compiles the DTS and validates the generated ADT
scripts/check-pins.py     catches truncated sha256 pins
scripts/check-firmware.py checks the ruyi UEFI DSC/FDF payload wiring
scripts/build-gop-legacy-display.py  display archive builder (fails with the remaining work)
soc/sm8650/             board-local SM8650 resource slice
drivers/RuyiDisplay/    the audited iOS 16 display ABI
firmware/               the ruyi UEFI payload-integration patch and its rationale
docs/evidence/          raw reads the record cites (FDT facts, IPSW facts, prelink roots)
```

## Building

From a UniXNU checkout:

```sh
./unixnu defconfig ruyi_defconfig -D ../UniXNU-ruyi
./unixnu status --json -D ../UniXNU-ruyi
./unixnu build kernel -D ../UniXNU-ruyi
```

The kernel step needs the UniXNU macOS toolchain or `scripts/linux/setup-toolchain.py`.
The firmware step additionally needs a ruyi Mu-Silicium checkout via `--uefi`.
Inputs that are not committed (IPSW, kernelcache, trust cache, Data seed) are
supplied with `--ipsw`, `--kernelcache`, `--trust-cache` and `--data-ramdisk`.

Checks that run anywhere:

```sh
python3 scripts/check-scope.py                       # no GPU driver, no cover display
python3 ../UniXNU/scripts/porting-record.py check --device .
```

## Evidence discipline

Every hardware constant in `board.toml` and `dts/ruyi.dts` is traceable to either
the device's own live device tree (`docs/evidence/RUYI-FDT-FACTS.md`) or the pinned
IPSW (`docs/evidence/IPSW-FACTS.md`). Nothing is inherited from another SM8650
phone on the grounds that it shares a SoC. Where a value is not yet measured, the
record says so and the build refuses it rather than guessing.

## References

- [Porting](https://unixnu.com/porting/) - [device repository](https://unixnu.com/porting/device-repository) - [records](https://unixnu.com/porting/records)
- [Device tree](https://unixnu.com/porting/device-tree) - [display](https://unixnu.com/porting/display)
- [GopFramebuffer](https://unixnu.com/drivers/gop-framebuffer) - the display component this profile uses

## Licence

The device tree, configuration and scripts in this repository are
BSD-3-Clause. Apple's IPSW, kernelcache, trust caches and vendor firmware are not
distributed here; they are local build inputs.
