# Facts read from the ruyi live device tree

Source: `docs/evidence/ruyi-device.dtb` - the FDT the stock ABL hands to
the kernel on a Xiaomi MIX Flip (ruyi). Every hardware value this port
copies is quoted below with the node it came from.

The external (cover) panel appears in one section at the end **only** to
record that this port deliberately does not describe it.

## GICv3 - `/soc/interrupt-controller@17100000`
```
interrupt-controller@17100000 {
                #address-cells = <0x00000001>;
                #interrupt-cells = <0x00000003>;
                #redistributor-regions = <0x00000001>;
                #size-cells = <0x00000001>;
                compatible = "arm,gic-v3";
                interrupt-controller = [];
                interrupts = <0x1 0x9 0x4>;
                phandle = <0x00000001>;
                ranges = [];
                redistributor-stride = <0x0 0x40000>;
                reg = <0x17100000 0x10000 0x17180000 0x200000>;
                msi-controller@17140000 {
                    #msi-cells = <0x00000001>;
                    compatible = "arm,gi
```

## Generic timer - `/timer` (the source of the timebase)
```
timer {
                always-on = [];
                clock-frequency = <0x0124f800>;
                compatible = "arm,armv8-timer";
                interrupts = <0x1 0xd 0xff08 0x1 0xe 0xff08 0x1 0xb 0xff08 0x1 0xc 0xff08>;
                phandle = <0x0000030e>;
            };
```

`clock-frequency = <0x0124f800>` = 19,200,000 Hz. The vendor tree carries
the timebase here, not under `/cpus`; `dts/ruyi.dts` puts the same value on
`/cpus` because that is where the UniXNU ADT generator reads it.

## PSCI - `/psci`
```
psci {
                compatible = "arm,psci-1.0";
                method = "smc";
                cpu-pd0 {
                    #po
```

## ABL scanout buffer - `/reserved-memory/splash_region`
```
splash_region {
                label = "cont_splash_region";
                phandle = <0x000007e6>;
                reg = <0x0 0xfc400000 0x0 0x2b00
```

## UFS host - `/soc/ufshc@1d84000`
```
compatible = "qcom,ufshc"
reg = <0x1d84000 0x3000 0x1d88000 0x8000 0x1d90000 0x9000 0x1da5000 0x2000 0x1da4000 0x10>
interrupts = <0x0 0x109 0x4>
```

## Internal (folding) panel - `qcom,mdss_dsi_n8_42_02_0a_prim_dsc_cmd`
```
qcom,mdss-dsi-panel-name = "xiaomi n8 42 02 0a prim cmd mode dsc dsi panel"
qcom,mdss-dsi-panel-type = "dsi_cmd_mode"
qcom,mdss-dsi-bpp = <0x0000001e>
qcom,dsi-ctrl-num = <0x00000000>
qcom,dsi-phy-num = <0x00000000>
qcom,mdss-dsi-panel-width = <0x000004c8>   (22 identical timing entries)
qcom,mdss-dsi-panel-height = <0x00000b60>   (22 identical timing entries)
qcom,mdss-dsi-panel-framerate = <0x00000018>   (all 22 timing entries: <0x00000018>, <0x0000001e>, <0x00000028>, <0x0000003c>, <0x0000005a>, <0x00000078>)
```

0x4c8 = 1224, 0xb60 = 2912. This is the only panel the port describes.

## CPUs - `/cpus`
```
The vendor tree has no timebase-frequency under /cpus; the value comes
from /timer clock-frequency (above). Affinity and capacity per core:
cpu@0: capacity-dmips-mhz=0x00000400 reg=<0x0 0x0>
cpu@100: capacity-dmips-mhz=0x00000400 reg=<0x0 0x100>
cpu@200: capacity-dmips-mhz=0x00000700 reg=<0x0 0x200>
cpu@300: capacity-dmips-mhz=0x00000700 reg=<0x0 0x300>
cpu@400: capacity-dmips-mhz=0x00000700 reg=<0x0 0x400>
cpu@500: capacity-dmips-mhz=0x00000700 reg=<0x0 0x500>
cpu@600: capacity-dmips-mhz=0x00000700 reg=<0x0 0x600>
cpu@700: capacity-dmips-mhz=0x00000766 reg=<0x0 0x700>
```

Capacities 0x400 (2x A520), 0x700 (5x A720), 0x766 (1x X4) drive the
E/P cluster split in `dts/ruyi.dts`.

## DRAM - `/memory`
```
/memory reg decoded as 2 address cells + 2 size cells:
  0x000816e0800 + 0x000031f800   (0.003 GiB)
  0x00081a40000 + 0x00001bf000   (0.002 GiB)
  0x00081cf5000 + 0x000000b000   (0.000 GiB)
  0x00081f20000 + 0x0000580000   (0.005 GiB)
  0x00082800000 + 0x0002000000   (0.031 GiB)
  0x00084c00000 + 0x0001f00000   (0.030 GiB)
  0x000a2580000 + 0x0035a80000   (0.838 GiB)
  0x000e34b0000 + 0x0014750000   (0.320 GiB)
  0x000fb800000 + 0x0003900000   (0.056 GiB)
  0x000ff3dd000 + 0x0000423000   (0.004 GiB)
  0x000ffe00000 + 0x0000200000   (0.002 GiB)
  0x00880000000 + 0x002f900000   (0.743 GiB)
  0x008b0000000 + 0x0007f00000   (0.124 GiB)
  0x008b8100000 + 0x0001e00000   (0.029 GiB)
  0x008c0000000 + 0x00c0000000   (3.000 GiB)
  0x00980000000 + 0x0180000000   (6.000 GiB)

Contiguous runs of at least 256 MiB:
  0x000a2580000 .. 0x000d8000000   0.838 GiB
  0x000e34b0000 .. 0x000f7c00000   0.320 GiB
  0x00880000000 .. 0x008af900000   0.743 GiB
  0x008c0000000 .. 0x00b00000000   9.000 GiB

Largest run: 0x8c0000000 .. 0xb00000000 = 9 GiB.
dts/ruyi.dts uses exactly that run as the kernel-managed window,
so payload.dram_size = 0x240000000.
```

## Cover (external) panel - EXCLUDED

This vendor node is recorded here only to state the boundary:

```
qcom,mdss-dsi-panel-name = "xiaomi n8 42 02 0a sec cmd mode dsc dsi panel"
qcom,mdss-dsi-panel-width = <0x000004b8>
qcom,mdss-dsi-panel-height = <0x00000570>

0x4b8 = 1208, 0x570 = 1392. EXCLUDED: this port has no node, property,
component or kernel argument for this panel.
```

