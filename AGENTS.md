# Device agent guide - UniXNU-ruyi

This repository is the board layer for the Xiaomi MIX Flip (`ruyi`, SM8650).
It owns the device tree, component selection, kernel configuration, firmware
inputs, payload parameters and the porting record. Shared tooling, drivers and OS
profiles belong to UniXNU.

## Two rules that override everything else

1. **No GPU driver.** The milestone is SpringBoard appearing with CoreAnimation
   compositing on the CPU. Do not add `Adreno740`, `AdrenoMetal`, `AdrenoPM4`,
   `AdrenoFirmware`, `ArmSmmu4K`, `AirNir` or any GPU firmware, GPU kernel
   argument or GPU code path. Software rendering is a component selection, not a
   switch to re-enable later.

2. **Internal display only.** The internal panel is 1224 x 2912, stride 4896.
   The cover display must not appear as a node, property, dimension, component or
   argument. It is outside the design boundary, not an unimplemented feature.

`python3 scripts/check-scope.py` enforces both over the device tree,
configuration, patch series and board package. Run it before every commit.

## Read first

| Task | Required reading |
| --- | --- |
| Every change | [Porting](https://unixnu.com/porting/), [device repository](https://unixnu.com/porting/device-repository), [records](https://unixnu.com/porting/records), UniXNU `components.toml` |
| Hardware | [Device tree](https://unixnu.com/porting/device-tree), `docs/evidence/RUYI-FDT-FACTS.md` |
| Display | [Display](https://unixnu.com/porting/display), [GopFramebuffer](https://unixnu.com/drivers/gop-framebuffer) |
| Images | [Prelink](https://unixnu.com/concepts/prelink), [payload](https://unixnu.com/concepts/payload), [UEFI](https://unixnu.com/porting/uefi-firmware) |
| Verification | [Building](https://unixnu.com/building), [bring-up](https://unixnu.com/porting/bring-up) |

Also read `porting.toml` before touching any area: it carries the per-area
findings, limits and next action, and it is the shared record the documentation
site renders.

## Evidence discipline

Every hardware constant must have a source in one of exactly two places:

1. the device's own live device tree (`docs/evidence/RUYI-FDT-FACTS.md`), or
2. a value measured on a ruyi device, recorded in `porting.toml` with the
   observation that produced it.

A value from another SM8650 phone is **not** a source, even when the SoC is
identical. When a value is not yet measured, record the gap in `porting.toml`
`limits` and leave the build failing rather than guessing.

When you add a constant, update the owning area's `findings` or `evidence` in
`porting.toml` in the same change, then run:

```sh
python3 ../UniXNU/scripts/porting-record.py check --device .
```

## Status discipline

The record distinguishes `planned`, `implemented`, `host-verified` and
`device-verified`. Do not promote an area because the code looks right:

- `implemented` needs source in this repository.
- `host-verified` needs a command, its result, and a full 40-character revision.
- `device-verified` needs a ruyi device observation identifying the firmware and
  image.

Nothing here is `device-verified`. The display ABI **has** been audited from the
pinned 20H392 kernelcache itself (`drivers/RuyiDisplay/mobile-graphics-legacy-abi.json`),
so the vtable, abstract slots and instance size are this binary's. The private
*field offsets* the driver also needs are only partly derived — see
`docs/evidence/DISPLAY-FIELD-OFFSETS-20H392.md` before writing the display
backend.

## Work

Search the UniXNU component catalog before adding a capability, and preserve the
canonical component IDs and runtime identifiers it records. Keep board wiring and
board policy here; keep shared controller operations in a component or SoC
repository.

```sh
./unixnu defconfig ruyi_defconfig -D ../UniXNU-ruyi
./unixnu status --json -D ../UniXNU-ruyi
./unixnu build kernel -D ../UniXNU-ruyi
python3 scripts/check-scope.py
```

Record commands, revisions, outputs and unresolved inputs. Report build results
and hardware results separately.

## Open work, in order

1. Finish the display driver: derive the remaining private field offsets
   (the pending swap queue is not located yet), then write the nine backend
   leaves and the original-bindings assembly. The vtable facts are done; see
   `drivers/RuyiDisplay/mobile-graphics-legacy-abi.json`.
2. Publish a ruyi Mu-Silicium checkout so the firmware step has a `--uefi` input.
3. Build the kernel and payload on a macOS runner; record the prelink report.
   `.github/workflows/kernel.yml` does this on dispatch.
4. Boot with `cpus=1`, confirm the console and timer, then `cpus=8`.
5. Only then attempt the desktop milestone, and record what actually appears.

## Porting record

`porting.toml` is the shared maintainer and agent record. Update each affected
area's findings or evidence with its code change, and keep the completion level
supported by the evidence you actually have. Read the
[record guide](https://unixnu.com/porting/records) for the schema and the
completion levels.
