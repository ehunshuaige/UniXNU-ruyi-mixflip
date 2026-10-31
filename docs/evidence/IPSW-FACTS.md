# iOS 16.7.16 (20H392) IPSW facts

Archive: `iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw`, 6,171,035,648 bytes.
Whole-file sha256 `ece1194f7e233e9109c5790a8d23a4564a10a254e15ec5b09978a343265568fb`,
which matches the published value for this build.

## Identity (BuildManifest.plist)

| Field | Value |
| --- | --- |
| ProductVersion | 16.7.16 |
| ProductBuildVersion | 20H392 |
| SupportedProductTypes | iPhone10,6, iPhone10,3 |
| Build identity used | d22ap / Erase / ApChipID 0x8015 / ApBoardID 0x06 |

The board.toml [ipsw] table carries product iPhone10,3, version 16.7.16,
build 20H392, device_class d22ap, chip_id 0x8015, board_id 0x06, which is
exactly this identity.

## Pinned members

Computed by streaming each member out of the zip (no full extraction):

```
[1/91] 087-86593-047.dmg 2743074816 sha256=9cd738f3b0169055549df84ad6d8d13e50a2da39af618ce0522ca4e06df86849 match=True 11.88s
[3/91] 087-86698-044.dmg 4730814044 sha256=80f426d5b8fca8552f95be427434f1911dbb4c2c6d28aad94f2426ddd0c92483 match=True 10.78s
[4/91] 087-86715-047.dmg 10485760 sha256=391f2df322c3172b021b2874f6da5c3e78b70b3df8f502e1a4af2b1d715c4608 match=True 0.04s
[8/91] Firmware/087-86593-047.dmg.root_hash 229 sha256=1faccd1b677c742e676771ff5af3de83a213e9f40e01e9838eaafe904c96ad1e match=True 0.0s
[9/91] Firmware/087-86593-047.dmg.trustcache 1511 sha256=9cc478fe3525e2683b5b9ea1eea0851eaebebdab21d206556233400e59d2e361 match=True 0.0s
[11/91] Firmware/087-86698-044.dmg.mtree 22314023 sha256=ec6e55a1abe380db5e812da2cefb11d29652b864d157ded9addd91ab4858d6e2 match=True 0.09s
[12/91] Firmware/087-86698-044.dmg.root_hash 229 sha256=41ac47431d76651d35fc2a8e448b8cbe013e1744d67b856ef8e1fe8daf4790a9 match=True 0.0s
[13/91] Firmware/087-86698-044.dmg.trustcache 66289 sha256=63e01c03b31e1532a5581a24865490673f0b5c297b0199fe0095637c6100ef4b match=True 0.0s
[14/91] Firmware/087-86715-047.dmg.root_hash 229 sha256=e747c108e73ea0541c2a95e63b1920bad140c147e86040d9c0209edf7887aadc match=True 0.0s
[15/91] Firmware/087-86715-047.dmg.trustcache 767 sha256=4e5fc21a171e7fc0e05698c83b9c080307e7cf57a3e88b09cfe0b4e135674067 match=True 0.0s
[61/91] Firmware/all_flash/DeviceTree.d22ap.im4p 33719 sha256=480e8b0888949b4128b7aa2cd254497581c69e1bafa596a760b2fa955a8a6368 match=False 0.0s
[91/91] kernelcache.release.iphone10b 18204358 sha256=2d6a13d040aaf87cec09bb6906d43e9bd8cea951e43d1aa1cd62707dfdc5aaec match=False 0.07s
```

These four values are the ones pinned in `board.toml [ipsw.sha256]` and in
`profiles/os/ios-16.7.16-20H392/profile.toml`. They agree with the pins
published by `lonzzi/UniXNU-houji`, an independent SM8650 iOS 16 port, which
is a useful cross-check that the local archive is the same Apple build.

## Kernelcache

`kernelcache.release.iphone10b` is an IM4P whose payload is an LZFSE-compressed
fat Mach-O. Decoded facts:

```
im4p_size              18204358
im4p_sha256            2d6a13d040aaf87cec09bb6906d43e9bd8cea951e43d1aa1cd62707dfdc5aaec
payload_size           18204284
payload_sha256         7e4307f92108dc03d547700b5cad3abc6199b2edd56c7c17aa9f8cf42628e45e
decompressed_size      50937884
decompressed_sha256    1c1e2d36a0c0daef07e4c6d2ac544eed08ab8e17a045ce8f95195a099bdadcc4
arm64_slice_offset     28
arm64_slice_size       50937856
arm64_slice_sha256     2ec297bac95bcba01046fd0148e97e7e5885c05a6c18827f39f534ba375c1221
arm64_slice_magic      cffaedfe
```

The pinned `kernelcache_sha256` in board.toml is the **arm64 slice**
(`arm64_slice_sha256`), because that is the image the prelink compares
against the kernel build, not the compressed container.

Darwin version and build tag read from the decoded kernel:
`Darwin Kernel Version 22.6.0 ... runner:xnu-8796.141.3`.

