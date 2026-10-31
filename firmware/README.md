# ruyi UEFI platform package — payload integration

This directory carries the **board-side firmware changes** that the ruyi
Mu-Silicium checkout needs so that DarwinBoot can load the payload. The firmware
is not built by this repository; this records and checks the integration.

## Why this exists

UniXNU's porting guide lists the modules the firmware volume must contain
([required integration](https://unixnu.com/porting/uefi-firmware#required-integration)).
The ruyi `ruyiPkg` inherited from the same-SoC giulia package carried the boot
manager and the XNU loader in its DSC, but:

- the FDF firmware volume listed only `UniXNU.inf` and `UniXNUDxe.inf`, so
  DarwinBoot and the payload filesystem stack were never included;
- no block, partition, disk or FAT driver was wired at all.

A firmware built from that DSC/FDF boots, draws the UniXNU menu, and then offers
**no entries**: the payload FAT volume is never published, so
`\EFI\UniXNU\unixnu.toml` cannot be read. On a phone whose only console is the
panel this looks like a payload problem and is expensive to diagnose.

## What the patch does

`ruyiPkg-payload-integration.patch` applies against a ruyi Mu-Silicium checkout
and adds, to both the DSC `[Components]` and the FDF firmware volume:

| Module | Purpose |
| --- | --- |
| `DarwinBootPkg/Driver/DarwinBoot.inf` | the XNU loader |
| `ruyiPkg/Drivers/RuyiInitrdDxe/RuyiInitrdDxe.inf` | publishes the in-RAM payload as Block I/O |
| `MdeModulePkg/Universal/Disk/PartitionDxe/PartitionDxe.inf` | partition discovery |
| `MdeModulePkg/Universal/Disk/DiskIoDxe/DiskIoDxe.inf` | block access for the filesystem driver |
| `MdeModulePkg/Universal/Disk/UnicodeCollation/EnglishDxe/EnglishDxe.inf` | the collation service FAT requires |
| `FatPkg/EnhancedFatDxe/Fat.inf` | exposes `EFI_SIMPLE_FILE_SYSTEM_PROTOCOL` |

`RuyiInitrdDxe` is board-local rather than the shared `UniXNURamDiskDxe`: it is
the giulia driver adapted with ruyi's own DDR-bank scan rules, so the scan
cannot walk off a bank into unmapped memory. Either driver satisfies the
integration; the check accepts both.

## Applying and checking

```sh
# against the ruyi Mu-Silicium checkout
git -C /path/to/ruyi-Mu-Silicium apply /path/to/UniXNU-ruyi/firmware/ruyiPkg-payload-integration.patch

# verify the integration (no edk2 toolchain needed)
python3 scripts/check-firmware.py --uefi /path/to/ruyi-Mu-Silicium
```

`scripts/check-firmware.py` also enforces two EDK II structural rules the build
would otherwise only reveal late: every FDF `INF` must also be a DSC component,
and a wired FAT driver requires a Unicode collation provider.

## Not verified

The patched firmware has **not been built** from this repository: no edk2
toolchain is available here and no ruyi Mu-Silicium repository is published.
`check-firmware.py` verifies the integration wiring, not that the firmware runs
or that the payload is found on hardware.
