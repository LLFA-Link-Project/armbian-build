# Orange Pi 5 USB-C DisplayPort

Enable USB-C DP Alt Mode on Orange Pi 5 with Linux 6.18.55.
Expose the HMD through DRM/KMS.
The 60-patch baseline passes Armbian package generation and package verification.
The user confirms 1080p60 output on Orange Pi 5 with arpara 5K.
Higher modes show corruption.
See `high-resolution.md` for diagnostic patch 0801 and log collection.
The user supplies diagnostic logs from patch 0801.
See `vop2-clock.md` for clock repair patches 0901–0903.
The user confirms correct clocks and HBR3 ×4 after the clock repair.
High-resolution output initially shows corruption, then blackouts, then correct video within the same modetest execution.
The user withdraws the earlier requirement for a second execution.
See `modeset-sequence.md` for diagnostic patch 1001.
The supplied hardware logs contain patch 1001 records.
See `build-result.md` for baseline package paths, hashes, and log paths.

## Baseline

- Board: Orange Pi 5, RK3588S. This patch does not target Orange Pi 5 Plus.
- Framework baseline: `813ae7cf3`.
- Kernel: `v6.18.55`, stable revision `725bd2f3c81d54edccb66fead01d4c0c222e2231`.
- Source: [Linux 6.18.55 archive](https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.55.tar.xz).
- DTB: `rockchip/rk3588s-orangepi-5.dtb`.
- Board DTS: `arch/arm64/boot/dts/rockchip/rk3588s-orangepi-5.dts`.
- Shared board DTSI: `rk3588s-orangepi-5.dtsi`.
- SoC includes: `rk3588s.dtsi`, `rk3588-base.dtsi`.
- `KERNELPATCHDIR`: `archive/rockchip64-6.18`.
- User patches: `userpatches/kernel/archive/rockchip64-6.18/zzz-rk3588-usbc-dp-*.patch`.

The existing package log records a remote cache download, rather than local compilation.
See `output/logs/log-kernel-59eec7e6-dc1f-4fbd-a344-a785c0e74737.log`, lines 103–132.
Existing packages do not validate these changes.

## Phase A: baseline findings

Linux 6.18.55 contains TCPM, FUSB302, DP Alt Mode, DPTX, and the RK3588 USB-DP PHY.
The board enables Type-C USB roles and the orientation switch.
The board leaves DP0 disabled and omits the DP graph and local DP capabilities.
The driver paths also lack the reviewed OOB HPD and PHY reset coordination changes.
Enabled Kconfig symbols cannot replace these connections.

| Stage | Evidence or required verification |
|---|---|
| 1. Partner detection | User reports `port0-partner`. |
| 2. Alt Mode discovery | User reports SVID `ff01`, mode `1`. |
| 3. Negotiation | User reports `active=no`. Local DP capabilities are absent from the baseline DTS. |
| 4. Orientation and mux | Baseline registers the PHY switch. Confirm the negotiated assignment on hardware. |
| 5. PHY DP operation | Upstream PHY changes handle mode changes, orientation, and PHY reset notifications. |
| 6. DPTX probe and bind | Baseline DP0 is disabled. The patch enables DP0 and its VOP/PHY graph. |
| 7. HPD | FUSB302 HPD bridge, DRM OOB handling, and Rockchip HPD forcing complete this path. |
| 8. DRM connector | No DP connector exists in the reported state. Confirm bridge attachment on hardware. |
| 9. EDID and DPCD | Existing AUX code handles reads. Hardware verification remains pending. |
| 10. Link training | Existing DPTX code handles training. Hardware verification remains pending. |
| 11. KMS mode setting | Existing DRM code handles modes. Hardware verification remains pending. |

These findings explain the missing connector and incomplete negotiation.
These findings do not prove the running kernel uses the same DTB.
Inspect the live DT before comparing results.

## Upstream sources

Research date: 2026-10-09.
Revision values identify the latest submissions found during this investigation.
`patches.tsv` records each selected patch, author, date, status, dependencies, source, adaptation, and SHA-256.
PHY maintainer acceptance does not establish a merge into Linus's tree.

| Group | Selected patches | Status and source |
|---|---|---|
| 00 | DRM bridge lookup APIs, 2 commits | Linus merged: [293a8fd7721a](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=293a8fd7721a90987d9bf149feab60e756dac269), [03d1078112fd](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=03d1078112fddd706b2c1e4a7d98cf18700eb5df). |
| 01 | DPTX v11, 01–15 of 21 | Development series, 2026-08-06: [cover](https://lore.kernel.org/all/20260806-synopsys-dw-dp-improvements-v11-0-0d508505f383@collabora.com/). Linus commits were not found. |
| 02 | PHY part 1 v15, all 16 | PHY maintainer applies patches on 2026-10-03: [thread](https://lore.kernel.org/all/20260915-rockchip-usbdp-cleanup-v15-0-80e2c11d1ce8@collabora.com/). |
| 03 | PHY part 2 v15, all 11 | PHY maintainer applies patches on 2026-10-03: [thread](https://lore.kernel.org/all/20260915-rockchip-usbdp-cleanup-part2-v15-0-8d507cb1174f@collabora.com/). |
| 04 | Rockchip DWC3 glue v16, all 6 | Development series, 2026-09-24: [cover](https://lore.kernel.org/all/20260924-b4-rockchip-dwc3-rockchip-glue-v16-0-126a2e9133c3@collabora.com/). Linus commits were not found. |
| 05 | PHY part 3 v16, all 7 | Development series, 2026-09-30: [cover](https://lore.kernel.org/all/20260930-b4-rockchip-usbdp-cleanup-part3-v16-0-bc144f80afc4@collabora.com/). Linus commits were not found. |
| 06 | FUSB302 HPD bridge and cleanup | Linus merged: [5d79c525405d](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=5d79c525405dcf9611c1f019b0aa05d72f0186ae), [ca927fc45e49](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=ca927fc45e4906bdab42426da044fba4d3584f34). |
| 07 | Orange Pi 5 DTS | Local patch. Hardware testing is pending. |

The [user reference](https://lists.openwall.net/linux-kernel/2026/09/15/2445) is PHY part 2 patch 01/11.
That patch removes PHY HPD handling.
Apply DPTX OOB HPD handling with that patch.
The patch cannot enable DP Alt Mode alone.

Dependencies:

```text
DRM bridge APIs -> DPTX bridge chain and OOB HPD
PHY part 1 -> PHY part 2 -> PHY part 3
PHY notifier API -> DWC3 glue -> PHY part 3
FUSB302 HPD bridge -> Type-C connector HPD -> DPTX OOB HPD
All driver changes -> Orange Pi 5 DP graph
```

DPTX patches 16–21 add SDP/audio features.
This task does not require those patches.
TCPM and DP Alt Mode negotiation remain upstream implementations.
No HMD VID/PID quirk is added.

## Device Tree

The board uses FUSB302 on I2C6, address `0x22`.
The baseline assigns IRQ GPIO0_PD3 and SBU GPIO4_PA5/GPIO4_PA7.
The patch retains these assignments and existing source/sink PDOs.
Board wiring comes from the upstream DTS.
Independent schematic verification remains pending.

DP0 at `fde50000` uses PHY0 at `fed80000`.
The SoC DTSI supplies clocks, AUX clock, resets, VO0 power domain, and `PHY_TYPE_DP`.
The patch reuses these resources.
VOP VP2 connects to DP0. HDMI retains its existing VOP path.

The PHY graph uses port 0 for Type-C orientation, port 2 for DPTX, and port 3 for AUX/SBU.
The patch removes the legacy single PHY port and preserves its endpoint labels.
Each endpoint has a reciprocal `remote-endpoint`.
Existing USB controller PHY references and role endpoints remain in place.

The connector advertises SVID `ff01` and VDO `0x00001c46`.
The VDO advertises DFP_D, HBR3, a receptacle, and assignments C/D/E.
C/E use four DP lanes. D retains two DP lanes and USB3.
The Type-C driver chooses the assignment. The patch does not fix the lane mapping.

## Armbian integration

The framework applies `series` files before regular patches.
The framework sorts regular patches by basename across core and user directories.
The `zzz-` prefix places these patches after current core patches.
No user `series` file is added.
No equivalent standard patch exists in this baseline.

`core-patches.txt` lists the five standard patches that intersect the changed files.
`check-apply.py` checks these patches before the 60 user patches.
This check does not replace the full Armbian patch stage.

The extension enables Rockchip DWC3 glue and the Rockchip DPTX wrapper.
The extension builds FUSB302, DP Alt Mode, and the USB-DP PHY as modules.
The new DRM dependencies require modules because the Armbian config sets `CONFIG_DRM=m`.
Kconfig selects the AUX bridges.

Backport changes retain the Linux 6.18 bridge reset callback, iterator declaration, lane shifts, and DWC3 probe defaults.
Other adaptations preserve upstream behavior against the older resource layout.
The DTS patch is the only new board feature implementation.

The patch directory affects the shared rockchip64 kernel.
Only Orange Pi 5 is the intended test board.
The user tests Orange Pi 5 with arpara 5K.
1080p60 works. Higher modes show corruption.

## Static validation

Checks pass for Linux 6.18.55:

- All 60 patches apply after the five intersecting Armbian patches without fuzz.
- `git diff --check` passes for the resulting changes.
- Changed DRM, PHY, DWC3, FUSB302, and DP Alt Mode objects compile for arm64 with Clang 23.
- Orange Pi 5 DTB compiles.
- DTB checks confirm DP0 status, resource properties, capabilities, VP2 routing, and reciprocal PHY endpoints.
- The extension and diagnostic script pass `bash -n`.

`apply-check.log` and `static-build.log` contain the checks.
Object compilation does not check final linking, modpost, or package generation.
DT schema validation remains pending.

Run the application and DTB checks:

```sh
python3 userpatches/rk3588-usbc-dp/check-apply.py /path/to/linux-6.18.55.tar.xz
python3 userpatches/rk3588-usbc-dp/verify.py --dtb /path/to/rk3588s-orangepi-5.dtb
```

## Phase C: user Docker build

Run this command inside the existing working Armbian Docker environment.
Use the existing repository mount and Docker invocation.
The command builds kernel packages only.

```sh
./compile.sh kernel BOARD=orangepi5 BRANCH=current \
  KERNELBRANCH=tag:v6.18.55 KERNEL_CONFIGURE=no \
  ENABLE_EXTENSIONS=rk3588-usbc-dp ARTIFACT_IGNORE_CACHE=yes \
  PATCHES_TO_GIT=yes
```

Keep the full build log and the generated package paths.
Confirm the log selects `archive/rockchip64-6.18` and applies all `zzz-rk3588-usbc-dp-` patches.
Confirm the build uses the extension and compiles the kernel instead of downloading cached packages.
Do not install the packages during this build phase.

Run the verifier with the three newly generated package paths.
Do not use a wildcard that mixes cached and new packages.

```sh
python3 userpatches/rk3588-usbc-dp/verify.py \
  /path/to/new/linux-image-current-rockchip64_....deb \
  /path/to/new/linux-dtb-current-rockchip64_....deb \
  /path/to/new/linux-headers-current-rockchip64_....deb
```

The verifier checks metadata, release alignment, arm64 Image magic, module architecture, configuration, built-in glue, and the DTB graph.
The verifier prints each package SHA-256.
The verifier needs `zstd` only for zstd-compressed archives or modules.
Review the build log and patched source to establish complete patch application.

## Phase D: hardware checks

Use a separate, user-controlled kernel installation and recovery plan.
This task does not install packages or change `/boot`.
First confirm the kernel release and the live board DT.

```sh
uname -r
tr '\0' '\n' < /sys/firmware/devicetree/base/compatible
sudo dtc -I fs -O dts /sys/firmware/devicetree/base > /tmp/orangepi5-live.dts
lsmod | grep -E 'dw_dp|usbdp|fusb302|typec_displayport|aux.*bridge'
sudo bash userpatches/rk3588-usbc-dp/diagnose.sh > /tmp/orangepi5-usbc-dp.log
modetest -M rockchip -c -e -p
ls -l /sys/class/drm_dp_aux_dev /dev/drm_dp_aux* 2>/dev/null
```

Mount debugfs manually if debugfs is absent:

```sh
sudo mount -t debugfs debugfs /sys/kernel/debug
```

Confirm partner SVID `ff01` and `active=yes`.
Confirm a `card*-DP-*` connector reports `connected`, EDID bytes, and modes.
Connector numbers can change. Use the connector reported by `modetest`.
Read EDID with `edid-decode /sys/class/drm/<connector>/edid`.
Inspect `/sys/kernel/debug/devices_deferred` when DP0 does not bind.
Inspect PHY0, DP0, and FUSB302 driver links in the diagnostic log.
Inspect `/sys/kernel/debug/dri/*/encoder-*/bridges` for the DPTX, PHY AUX bridge, and connector HPD bridge.

Enable additional logs manually when negotiation or training fails:

```sh
sudo sh -c 'echo 0x1ff > /sys/module/drm/parameters/debug'
sudo sh -c 'echo "file drivers/phy/rockchip/phy-rockchip-usbdp.c +p" > /sys/kernel/debug/dynamic_debug/control'
sudo sh -c 'echo "file drivers/gpu/drm/bridge/synopsys/dw-dp.c +p" > /sys/kernel/debug/dynamic_debug/control'
sudo sh -c 'echo "file drivers/gpu/drm/rockchip/dw_dp-rockchip.c +p" > /sys/kernel/debug/dynamic_debug/control'
sudo dmesg -w
sudo cat /sys/kernel/debug/clk/clk_summary
sudo cat /sys/kernel/debug/phy/phy_summary
```

Some kernels omit the optional PHY summary file.
TCPM and FUSB302 logs reside under `/sys/kernel/debug/usb/tcpm-*/log` and `fusb302-*/log`.
Inspect Discover Modes, Enter Mode, DP Status, DP Configure, HPD, lane count, rate, and training messages.
If an AUX character device exists, read its first 16 DPCD bytes:

```sh
sudo dd if=/dev/<actual-drm_dp_aux-device> bs=16 count=1 status=none | od -Ax -tx1
```

Choose an advertised mode and available CRTC from `modetest`.
Release DRM master from the compositor before a manual KMS test.

```sh
sudo modetest -M rockchip -s '<connector_id>@<crtc_id>:<advertised-mode>'
```

Test both cable orientations, repeated hotplug, boot with HMD attached, and boot without HMD.
Test HDMI, USB3 host, and the existing USB device configuration for regressions.
Record EDID, negotiated assignment, lane count, link rate, mode, and complete logs.
Do not force Alt Mode or alter PDOs to bypass failures.

## Remaining work

The user completes the full Armbian build in the existing Docker environment.
New kernel, DTB, and headers packages pass verification.
See `build-result.md` and `package-check.log`.
The user reports working arpara 5K output at 1080p60.
Higher modes require further diagnosis. See `high-resolution.md`.
The available upstream testing includes Orange Pi 5 Plus, rather than this board.
Boot with an attached display and repeated hotplug require particular attention.
Native HMD modes, bandwidth, clock limits, and DSC compatibility remain unverified.
No high-resolution clock workaround or HMD-specific behavior is added.

After hardware tests, the board DTS patch can become an upstream submission.
Keep the driver backports separate from the board submission.
Drop backports when the selected stable kernel contains equivalent upstream changes.
