# High-resolution DisplayPort diagnostics

Record each mode's clocks, link settings, training, transport, and PHY settings.
Find the cause before changing link or PHY policy.

## Hardware evidence

The user tests Orange Pi 5 with arpara 5K.
DP-1 displays 1920×1080 at 60 Hz correctly.
Higher modes show corruption, bands, blackouts, or flicker.
The user supplies the following `modetest -M rockchip -c` timings.

| Mode | Pixel clock, MHz | htotal × vtotal | RGB 8bpc demand, Gbit/s | DCLK request, MHz | Actual DCLK |
|---|---:|---|---:|---:|---|
| 1920×1080 @60 | 148.500 | 2200 × 1125 | 3.564 | 148.500 | 148.500 MHz |
| 2560×1440 @60 | 236.110 | 2688 × 1464 | 5.667 | 236.110 | Pending log |
| 1920×1920 @72 | 286.660 | 2048 × 1944 | 6.880 | 286.660 | Pending log |
| 3840×1920 @72 | 573.290 | 4096 × 1944 | 13.759 | 573.290 | 396.000 MHz |
| 3840×1920 @90 | 849.960 | 4848 × 1948 | 20.399 | 424.980 | Pending log |
| 2544×2544 @70 | 526.750 | 2928 × 2570 | 12.642 | 526.750 | Pending log |

Demand equals pixel clock multiplied by 24 bits per pixel.
The calculation includes blanking through the supplied pixel clock.
The DCLK column predicts the current RK3588 DP calculation for progressive RGB modes.
The calculation chooses a DCLK divisor of 1, 2, or 4 below 600 MHz.
VOP then divides DCLK for the four-pixel DP input.
At 849.960 MHz, DP input needs 212.490 MHz, while the requested DCLK is 424.980 MHz.
Read `vp_clk_ctrl` to confirm the programmed core and output dividers.
Read actual clocks before treating these predictions as measurements.
Read logged `bpc`, `bpp`, and `color` before using the RGB bandwidth column.

## HBR3 × four lanes

The current controller limit is 810000 kHz, equivalent to HBR3.
The PHY accepts 8100 Mbit/s and up to four DP lanes.
These software limits do not establish sink support or successful negotiation.

| Link | Payload after 8b/10b coding, Gbit/s |
|---|---:|
| HBR2 ×2 | 8.640 |
| HBR3 ×2 | 12.960 |
| HBR2 ×4 | 17.280 |
| HBR3 ×4 | 25.920 |

3840×1920@90 RGB 8bpc exceeds HBR2 ×4 and fits HBR3 ×4 before additional transport overhead.
3840×1920@72 RGB 8bpc exceeds HBR3 ×2 but fits HBR2 ×4.
2560×1440@60 RGB 8bpc fits HBR2 ×2.
Thus a simple requirement for HBR3 cannot explain every failing mode.

Confirm `sink_rate_khz=810000`, `sink_lanes=4`, and `phy_lanes=4`.
Confirm the successful training result uses `rate_khz=810000` and `lanes=4`.
Type-C assignments C/E provide four DP lanes. Assignment D provides two DP lanes.
Sink capabilities alone do not determine the negotiated lane assignment.
The user confirms HBR3 ×4 with CR and EQ passing on the first attempt.

## Cause candidates and vendor comparison

Compare against Armbian's vendor branch `rk-6.1-rkr7.2` at commit `dc098b0048bc7a0cf621779ec62e8a03047f5ca2`.
The comparison targets RK3588 SST RGB output.

| Area | Finding | Evidence to collect |
|---|---|---|
| Pixel clock | Mainline calls `clk_set_rate(vp->dclk, clock)`. Vendor can also set the parent `v0pll`. | Requested, adjusted, actual DCLK, parent rates, and `clk_summary`. |
| Clock mux | Mainline `dclk_vop2_src` uses `CLK_SET_RATE_NO_REPARENT`. Rounding can depend on the selected parent. | Parent identity, requested/actual mismatch, and output dividers. |
| VOP bandwidth | Mainline does not scale VOP ACLK in this path. | ACLK and `POST_BUF_EMPTY` messages. |
| Link | Training can downgrade the discovered maximum rate. | Sink maximum, negotiated lanes, each attempt, and final rate. |
| PHY | The driver chooses rate-specific voltage tables and maps logical lanes to physical lanes. | Mapping, orientation, swing, pre-emphasis, register values, and PLL status. |
| TU | Vendor SST and mainline use TU=64 with the same average-byte and threshold formulas. | Actual bpp, rate, lanes, average bytes, threshold, and hblank interval. |
| Pixel packing | RK3588 uses quad-pixel DPTX in both drivers. RGB output selects VOP `AAAA` in both wrappers. | `pixel_mode`, mapping, bus format, output mode, and divider registers. |
| Timing fields | Vendor uses `crtc_*` timings. Mainline DPTX uses the copied mode's timing fields. | Requested and adjusted clocks, totals, and atomic state. |
| Video M/N | Neither selected driver explicitly programs named Mvid/Nvid registers. | The patch records a reference ratio, not hardware M/N values. |

Parent clock handling is a concrete implementation difference.
The user confirms the clock mismatch on 3840×1920@72.
See `vop2-clock.md` for the confirmed parent chain and repair.

A [direct upstream test report](https://lists.openwall.net/linux-kernel/2026/08/08/350) associates VOP underflow with 4K120 corruption.
That report tests Orange Pi 5 Plus at 1188 MHz pixel clock.
The report also describes clean output near 586 MHz pixel clock.
It cannot establish the cause of this board's 236.110 MHz failure.
Do not apply that report's ACLK setting without matching evidence.

The source does not establish a safe Mvid/Nvid register address or hardware readback API.
`pixel_to_symbol` equals the requested pixel clock divided by the selected link symbol clock.
This reference can be compared between modes.
Actual M/N verification needs IP documentation or a DP analyzer.

Primary source files:

- [Vendor DPTX](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/gpu/drm/rockchip/dw-dp.c): `dw_dp_video_ts_calculate`, `dw_dp_video_enable`, and RK3588 platform data.
- [Vendor VOP2](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/gpu/drm/rockchip/rockchip_drm_vop2.c): `vop2_calc_cru_cfg` and mode enablement.
- [Vendor clock handling](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/gpu/drm/rockchip/rockchip_drm_clk.c#L428): `rockchip_rk3588_drm_dclk_set_rate`.
- [Mainline clock tree](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/clk/rockchip/clk-rk3588.c?h=v6.18.55): `DCLK_VOP2_SRC` and `DCLK_VOP2`.
- Local patched sources: `cache/sources/linux-kernel-worktree/6.18__rockchip64__arm64`.

## Patch scope

Patch: `zzz-rk3588-usbc-dp-0801.patch`.
The patch adds dynamic debug records in three files:

- `drivers/gpu/drm/bridge/synopsys/dw-dp.c`.
- `drivers/gpu/drm/rockchip/rockchip_drm_vop2.c`.
- `drivers/phy/rockchip/phy-rockchip-usbdp.c`.

The patch records the existing clock request's return value.
The patch preserves mode selection, training limits, voltage tables, and register writes.
The patch adds no DPCD transactions, delays, forced rates, or forced lane assignments.
VOP readback uses existing configuration registers, not interrupt status registers.
PHY register values describe software programming, not measured analog voltage.
PLL `status` is valid when `ret=0`. Failed requests log a zero status placeholder.

Debug records are disabled by default.
Enabled logging can alter training timing.
Compare successful and failing modes with logging enabled, then repeat with logging disabled.
Hardware verification of 1080p60 remains required after the rebuild.

## Validation and build

All 61 patches apply after the intersecting Armbian patches without fuzz.
The three changed arm64 objects compile with Clang 23.
Checkpatch reports zero errors and zero warnings.
See `diagnostics-apply.log`, `diagnostics-build.log`, and `diagnostics-style.log`.
Full package generation for patch 0801 remains pending.
The earlier verified packages contain the 60-patch baseline.

Run the existing Docker build:

```sh
./compile.sh kernel BOARD=orangepi5 BRANCH=current \
  KERNELBRANCH=tag:v6.18.55 KERNEL_CONFIGURE=no \
  ENABLE_EXTENSIONS=rk3588-usbc-dp ARTIFACT_IGNORE_CACHE=yes \
  PATCHES_TO_GIT=yes
```

Verify the new image, DTB, and headers packages:

```sh
python3 userpatches/rk3588-usbc-dp/verify.py --diagnostics \
  /path/to/new/linux-image-current-rockchip64_....deb \
  /path/to/new/linux-dtb-current-rockchip64_....deb \
  /path/to/new/linux-headers-current-rockchip64_....deb
```

`--diagnostics` rejects packages without the diagnostic strings in DPTX, PHY, and VOP2 modules.
The task does not install or boot these packages automatically.

## Hardware log collection

After a user-controlled boot of the diagnostic kernel, mount debugfs if needed.
Enable only the new records:

```sh
sudo mount -t debugfs debugfs /sys/kernel/debug  # Only when absent.
sudo sh -c 'echo "format dpdiag +p" > /sys/kernel/debug/dynamic_debug/control'
sudo grep dpdiag /sys/kernel/debug/dynamic_debug/control
sudo dmesg --follow > /tmp/arpara-dp-live.log
```

Keep `dmesg --follow` running in a separate terminal.
Enable logging before reconnecting the HMD to capture DPCD discovery.
Use the existing display tool to select each supplied mode.
Start with 1080p60. Capture every failing mode separately.
Capture the current mode without changing display state:

```sh
sudo bash userpatches/rk3588-usbc-dp/capture-mode.sh 1920x1080-60 \
  > /tmp/arpara-1920x1080-60.log
```

Repeat with labels `2560x1440-60`, `1920x1920-72`, `3840x1920-72`, and `3840x1920-90`.
Keep each log, the complete live log, and the selected mode's visible result.
Do not clear the kernel log.
Disable the new records after collection:

```sh
sudo sh -c 'echo "format dpdiag -p" > /sys/kernel/debug/dynamic_debug/control'
```

## Decision points

- Nonzero clock return or requested/actual mismatch: investigate CRU parent selection and rate generation first.
- Matching clocks with `POST_BUF_EMPTY`: investigate VOP/DDR bandwidth and plane configuration.
- CR/EQ failures or repeated downgrades: investigate negotiated lanes, PHY configuration, and signal integrity.
- Successful HBR3×4 training with matching clocks: compare TU, packing, timing, and transport before changing PHY values.
- Only two negotiated lanes: verify Type-C assignment before judging high-mode bandwidth.

No cause is confirmed until these hardware records are available.
