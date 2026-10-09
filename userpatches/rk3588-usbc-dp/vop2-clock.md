# VP2 DisplayPort clock repair

Match the supplied modes with their pixel clocks.
Preserve 1080p60 and HBR3 ×4 training.

## Evidence

The user supplies these Orange Pi 5 measurements.

| Mode | Requested DCLK, MHz | Actual DCLK, MHz | VP clock control | CR / EQ |
|---|---:|---:|---|---|
| 1920×1080@60 | 148.500 | 148.500 | 0xa | Both pass, first attempt |
| 3840×1920@72 | 573.290 | 396.000 | 0xa | Both pass, first attempt |

Both modes use RGB 8bpc, quad-pixel DPTX, and HBR3 ×4.
The PHY lane map, swing, pre-emphasis, and PLL status match.
Training success does not prove error-free sustained transmission.

`vp_clk_ctrl=0xa` decodes as follows:

- Bits 1:0 encode core divider 2, which means divide by 4.
- Bits 3:2 encode output divider 2, which means divide by 4.

The 72 Hz mode requires a 143.3225 MHz quad-pixel clock.
The measured DCLK gives a 99 MHz quad-pixel clock.
The effective pixel rate is 396 MHz, rather than 573.29 MHz.
The clock error is -30.925%.
The supplied totals imply a 49.732 Hz VOP frame rate at 396 MHz.
This frame rate is calculated, rather than measured at the sink.
DPTX transport calculations still use the requested 573.29 MHz pixel rate.
The producer and transport therefore use different pixel rates.

The clock summary confirms this parent chain:

```text
gpll 1188000000 -> dclk_vop2_src -> dclk_vop2
```

1080p60 uses GPLL divided by 8.
The failing mode selects divider 3, because divider 2 exceeds the requested rate.
The divider driver rounds its divider upward without `CLK_DIVIDER_ROUND_CLOSEST`.
`clk_set_rate()` accepts the resulting rate and returns zero.
A zero return does not establish an exact rate match.

The supplied summary shows no enabled V0PLL consumers.
V0PLL currently selects the 24 MHz bypass.
This snapshot supports assigning V0PLL to VP2 on this board.
It does not establish availability on other boards.

## Vendor comparison

The vendor DCLK helper uses V0PLL when the board selects that parent.
The helper retains a suitable divisible PLL rate.
Otherwise, the helper selects an even divider above a 594 MHz PLL minimum.
The helper sets the PLL rate before setting DCLK.

The vendor PLL driver computes parameters for rates absent from its table.
Linux 6.18.55 instead selects a rate from its table.
Copying the DCLK helper alone cannot produce the supplied clocks.

Primary sources:

- [Vendor DCLK helper](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/gpu/drm/rockchip/rockchip_drm_clk.c#L428).
- [Vendor PLL driver](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/clk/rockchip/clk-pll.c).
- [Mainline divider](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/clk/clk-divider.c?h=v6.18.55).
- [Mainline clock framework](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/clk/clk.c?h=v6.18.55).
- [Mainline PLL driver](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/clk/rockchip/clk-pll.c?h=v6.18.55).

Upstream commit `778dd30867ad783b6903b0aa24a0ab5e97c2dff6` removes VP2's source reparent restriction.
That commit reaches Linus's tree through the Rockchip clock updates.
The [v2 submission](https://lists.infradead.org/pipermail/linux-arm-kernel/2026-March/1107852.html) tests RK3588 Tiger DP.
Removing the restriction alone does not generate these clocks from fixed PLL rates.
This repair retains the restriction to keep VP2 on its assigned V0PLL.

Commit `13b10571cc353448275365ede1a5396d20dfe839` removes rate propagation from VP2's source.
Linux 6.18.55 already contains the resulting flag combination.
The [commit](https://github.com/torvalds/linux/commit/13b10571cc353448275365ede1a5396d20dfe839) explains shared GPLL breakage.
Do not restore `CLK_SET_RATE_PARENT` on that source.

## Patches

- 0901 adds six PLL table rates derived from the supplied EDID clocks.
- 0902 applies vendor PLL selection only to RK3588 VP2 DisplayPort with a V0PLL parent.
- 0903 assigns Orange Pi 5 `DCLK_VOP2_SRC` to `PLL_V0PLL`.

0902 checks PLL rounding before changing the PLL.
0902 propagates clock API errors into the existing diagnostic record.
The board assignment uses standard DT properties.
The board assignment supplies no fixed PLL frequency.
The repair changes no DPTX training, PHY drive, USB, or PD settings.
The repair adds no ACLK setting.
The table additions affect supported rates globally, as the existing driver shares the table.
Existing supported rates retain their parameters.
This DP path changes V0PLL only.

The added rates cover every supplied RGB 8bpc EDID mode, including 1080p59.94.
Other nonstandard modes can require more table rates.
A general fractional PLL solution requires separate upstream work.
See `clock-rates.tsv` for coefficients, VCO, and recalculated rates.
All new coefficients are positive and below 32768.
No signed fractional coefficient change is required.

## Verification

Run `check-apply.py` and `check-clock-rates.py` before building.
See `clock-apply.log`, `clock-rates.tsv`, and `clock-build.log`.
The clock and VOP2 arm64 objects compile.
The Orange Pi 5 DTB compiles and passes graph and parent checks.
Checkpatch reports zero errors and zero warnings.
The checks do not establish hardware operation.
Full package generation requires the user's Docker build.

After booting the rebuilt kernel, compare 1080p60, 1440p60, 1920×1920@72, and both 3840×1920 modes.
Require successful clock API results and a pixel clock error below 0.1%.
For 3840×1920@72, expect DCLK near 573.29 MHz and `vp_clk_ctrl=0xa`.
For 3840×1920@90, expect DCLK near 424.98 MHz and `vp_clk_ctrl=0x5`.
At 90 Hz, the effective pixel clock equals twice DCLK.
Require HBR3 ×4 with successful CR and EQ for both high modes.
Check GPLL remains at 1.188 GHz.
Check HDMI and USB after switching modes.
If corruption remains, inspect VOP underflow and sustained DP errors next.
Do not treat this repair as proof of stable 90 Hz output.

Run the existing Docker kernel command from `high-resolution.md`.
Verify the new packages with `verify.py --clock-repair image.deb dtb.deb headers.deb`.
The flag checks the image's added rates, the VOP2 marker, and the DTB parent.
