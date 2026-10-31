# Prelink roots verified against the 20H392 kernelcache

`board.toml [kernel.prelink] roots` and
`profiles/os/ios-16.7.16-20H392/profile.toml` list the kexts the prelink keeps
from the original Apple kernelcache. The prelink tool aborts on a missing
dependency, so every identifier is checked against this build rather than
inherited from another iOS version.

Kernelcache: `kernelcache.release.iphone10b` from 20H392, decompressed arm64
slice, 50,937,856 bytes.
`__PRELINK_INFO` holds 239 kext entries.

Result: **31/31 roots present**.

| # | Bundle identifier | Present | CFBundleVersion |
| --- | --- | --- | --- |
| 1 | `com.apple.AppleFSCompression.AppleFSCompressionTypeZlib` | yes | 1.0.0 |
| 2 | `com.apple.driver.AppleARMPlatform` | yes | 1.0.2 |
| 3 | `com.apple.driver.AppleARMWatchdogTimer` | yes | 1 |
| 4 | `com.apple.driver.AppleAudioClockLibs` | yes | 240.1 |
| 5 | `com.apple.driver.AppleEffaceableStorage` | yes | 1.0 |
| 6 | `com.apple.driver.AppleIISController` | yes | 240.1 |
| 7 | `com.apple.driver.AppleM2ScalerCSCDriver` | yes | 265.0.0 |
| 8 | `com.apple.driver.AppleMobileFileIntegrity` | yes | 1.0.5 |
| 9 | `com.apple.driver.ApplePMGR` | yes | 1 |
| 10 | `com.apple.driver.IODARTFamily` | yes | 1 |
| 11 | `com.apple.filesystems.apfs` | yes | 2142.140.9 |
| 12 | `com.apple.iokit.CoreAnalyticsFamily` | yes | 1 |
| 13 | `com.apple.iokit.IOAVFamily` | yes | 1.0.0 |
| 14 | `com.apple.iokit.IOAudio2Family` | yes | 1.0 |
| 15 | `com.apple.iokit.IOCECFamily` | yes | 1 |
| 16 | `com.apple.iokit.IOCryptoAcceleratorFamily` | yes | 1.0.1 |
| 17 | `com.apple.iokit.IOGPUFamily` | yes | 65.60.1 |
| 18 | `com.apple.iokit.IOHDCPFamily` | yes | 1.0.0 |
| 19 | `com.apple.iokit.IOMobileGraphicsFamily` | yes | 343.0.0 |
| 20 | `com.apple.iokit.IOReportFamily` | yes | 47 |
| 21 | `com.apple.iokit.IOSlowAdaptiveClockingFamily` | yes | 1.0.0 |
| 22 | `com.apple.iokit.IOStorageFamily` | yes | 2.1 |
| 23 | `com.apple.iokit.IOSurface` | yes | 336.60.1 |
| 24 | `com.apple.kec.Libm` | yes | 1 |
| 25 | `com.apple.kec.corecrypto` | yes | 12.0 |
| 26 | `com.apple.kext.AppleMatch` | yes | 1.0.0d1 |
| 27 | `com.apple.kext.CoreTrust` | yes | 1 |
| 28 | `com.apple.security.AppleImage4` | yes | 5.0.0 |
| 29 | `com.apple.security.sandbox` | yes | 300.0 |
| 30 | `com.apple.iokit.IOHIDFamily` | yes | 2.0.0 |
| 31 | `com.apple.iokit.IOHIDEventDriver` | yes | 2.0.0 |

## Display family note

`com.apple.iokit.IOMobileGraphicsFamily` is present, version **343.0.0**,
prelinked executable size 33656 bytes.
Its `__TEXT_EXEC` sha256 in this kernelcache is
`03e4c4d80e4f9c78d4ad03366cd3f1d5894d054ae53cdf06b1a43c81a2eab1cd`.

The earlier ruyi display bring-up audited this family in the **iPadOS 17.7.11**
kernelcache instead, where the same kext's executable sha256 is
`2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b` and its
size differs. Different binaries mean the vtable offsets, abstract slots and
object size recorded there do not describe this build; the display ABI audit
must be re-run against a 20H392 prelink candidate before the display archive
can be built for this profile.
