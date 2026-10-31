# Display field offsets in the 20H392 kernelcache — preliminary

**Status: partially derived.** The vtable facts are complete and committed in
`drivers/RuyiDisplay/mobile-graphics-legacy-abi.json`. The *private field layout*
is not, and the driver needs it: the iPadOS 17 reference driver addresses the
original object at fixed byte offsets, and every one of those is specific to the
binary.

This file records what has been established so far and how, so the work is not
repeated.

## Why the fields are needed at all

The display component reuses Apple's genuine `IOMobileFramebufferLegacy`
implementation and only replaces the abstract leaves. To do that the driver has
to read and write original state — the mode dimensions, the pending swap queue —
through the object it allocated. The reference driver does it with offsets such
as `+5808`, `+5480`, `+2960`. Those numbers belong to the iPadOS 17.7.11 binary:

| Object | iPadOS 17.7.11 | iOS 16.7.16 (20H392) |
| --- | --- | --- |
| instance size | `0x18a0` | **`0x1660`** |
| width | `+5808` (`0x16b0`) | candidate `0x1458` |
| height | `+5812` (`0x16b4`) | candidate `0x145c` |
| swap queue head | `+5480` (`0x1568`) | not located |
| swap queue tail pointer | `+5488` (`0x1570`) | not located |
| request `next` | `+2960` (`0xb90`) | not located |
| request `previous-link` | `+2968` (`0xb98`) | not located |

The object is 234 bytes smaller than the iPadOS one, so no offset carries over.

## Method

Offsets are found by reading the family's own `__TEXT_EXEC` for large
unsigned-offset loads and stores whose base is one of `x0`..`x7` (the AArch64
`LDR`/`STR` immediate forms), then reading the surrounding code to see what the
field is used for. Scanning the whole family for accesses at `>= 0x1000` gives a
short list, because a class this size has few fields that far in:

```
0x1458 0x145c 0x1470 0x1484 0x1490 0x1498 0x1620 0x1624 0x1640
```

## What is established

`0x1458` and `0x145c` are two adjacent `uint32` fields, each with a dedicated
one-instruction getter:

```
0xfffffff005c24788:  ldr w0, [x8, #0x1458]
0xfffffff005c2478c:  add sp, sp, #0x10
0xfffffff005c24790:  ret

0xfffffff005c247a0:  ldr w0, [x8, #0x145c]
0xfffffff005c247a4:  add sp, sp, #0x10
0xfffffff005c247a8:  ret
```

and a nearby copy-out routine that reads both and stores each into a
caller-owned structure:

```
0xfffffff005c247dc:  ldr   w8, [x8, #0x1458]   ; then str w8, [x9]
0xfffffff005c24804:  ldr   w8, [x8, #0x145c]   ; then str w8, [x9]
```

Two adjacent `uint32` fields, individually readable and jointly exported to a
caller, is the shape the reference driver knows as the framebuffer width and
height. That matches, but it is **inferred from shape, not confirmed by
execution**: nothing here proves which is width and which is height, and this has
not been checked against a live object.

`0x1470`, `0x1484`, `0x1490`, `0x1498`, `0x1620`, `0x1624` and `0x1640` are
accessed but not yet classified.

## Not located

The pending swap queue. In the iPadOS object it is a tail queue at `+0x1568`
with the tail pointer at `+0x1570`, and each request carries `next` at `+0xb90`
and `previous-link` at `+0xb98`. Scanning the 20H392 family for 64-bit accesses
at `>= 0x1200` finds **none**, so the queue in this binary is either at a lower
offset or reached through a pointer rather than being embedded. It has to be
found before the swap path can be implemented.

## How to continue

1. Start from the swap/completion slots that the abstract-slot list names, since
   the queue is only touched by the swap path:
   `[211, 212, 242, 243, 292, 293, 321, 322, 329]`.
2. For each, read the function body and record every base-relative access; the
   queue head/tail will appear in the slot that enqueues and the slot that
   completes.
3. Confirm width/height against a live prelink run, or by finding the setter that
   writes both from a mode-change entry point, before the driver relies on them.
