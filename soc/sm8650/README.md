# SM8650 resource slice (board-local)

This directory is a **board-local SoC slice**, not a separate repository and not
a generic SM8650 driver. It exists so that `board.toml` can name a
`soc_source` the way format 2 expects, without pretending that an upstream
`UniXNU-sm8650-common` repository exists.

`kerrinz/UniXNU-zorn` uses the same arrangement for the same SoC. If a shared
SM8650 repository is created later, this slice moves there and the device
repository keeps only board differences.

## What is here

| Path | Contents |
| --- | --- |
| `soc.toml` | SoC identity and the component selection shared by SM8650 parts |
| `dts/sm8650.dtsi` | GICv3, generic timer, CPU topology, UFS host and PHY |
| `configs/sm8650.config` | Kernel configuration every SM8650 device needs |

## What is deliberately absent

- **GPU**: no Adreno, GMU, GPU SMMU or firmware resource. A device selecting this
  slice cannot acquire a GPU driver from it.
- **Display**: the panel, DSI channels and scanout reservation are board wiring,
  so they stay in the device DTS. This is also what keeps the cover display out
  of the shared layer.
- **Power, regulators and PMIC**: board policy, not SoC identity.

## Provenance

Every address and interrupt is read from the ruyi device's own live device tree
and quoted in the device repository's `docs/evidence/RUYI-FDT-FACTS.md`. The
slice is checked against the board DTS by `scripts/check-tree.py`.
