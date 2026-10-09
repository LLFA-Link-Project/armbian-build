# Armbian package build result

Build date: 2026-10-09.
The user runs the existing Docker environment.
Kernel package generation and package verification pass.
Hardware testing remains pending.

- Kernel release: `6.18.55-current-rockchip64`.
- Debian package version: `26.11.0-trunk`.
- Architecture: `arm64`.
- Artifact: `6.18.55-S725b-D4e2e-P3d79-C37a6-Hc23f-HK01ba-Vc222-Bb9ae-R448a`.
- Log: `output/logs/log-kernel-8c1727aa-3f24-44a4-a1c4-9f74e26bc6d7.log`.
- Summary: `output/logs/summary-kernel-8c1727aa-3f24-44a4-a1c4-9f74e26bc6d7.md`.

The build compiles the kernel and runs modpost.
The log lists all 60 user patches and the expected patch directory.
The log contains zero compiler errors and 77 compiler warnings.
The warnings include unrelated panel, HDMI, wireless, and fortify checks.

The framework packages files under `output/packages-hashed/global/` first.
The framework then changes package versions and writes final packages under `output/debs/`.
The framework removes the intermediate package files.
An empty `global/` directory is expected after this build.

## Verified packages

| Package | SHA-256 |
|---|---|
| `output/debs/linux-image-current-rockchip64_26.11.0-trunk_arm64__6.18.55-S725b-D4e2e-P3d79-C37a6-Hc23f-HK01ba-Vc222-Bb9ae-R448a.deb` | `ac8d30c55bf6cceb9342007fa03fc7b23401af6bec1c92c58f50e9b58ccb9406` |
| `output/debs/linux-dtb-current-rockchip64_26.11.0-trunk_arm64__6.18.55-S725b-D4e2e-P3d79-C37a6-Hc23f-HK01ba-Vc222-Bb9ae-R448a.deb` | `fd779d24b44c56c9d280ae0f1e6da5a973220693065f17d7c650cd954614c8f6` |
| `output/debs/linux-headers-current-rockchip64_26.11.0-trunk_arm64__6.18.55-S725b-D4e2e-P3d79-C37a6-Hc23f-HK01ba-Vc222-Bb9ae-R448a.deb` | `e0d98a114e16be58cab1470785db93afdbc54df4f25802540928919815482703` |

`package-check.log` records the verifier output.
The verifier confirms arm64 Image magic and module architecture.
The verifier confirms DPTX, USB-DP PHY, FUSB302, DP Alt Mode, and both AUX bridge modules.
The verifier confirms built-in Rockchip DWC3 glue and the required configuration.
The verifier confirms DP0, VP2, PHY0, Type-C capabilities, and reciprocal DTB endpoints.
The verifier confirms kernel, DTB, and headers release alignment.

The build also produces a `linux-libc-dev-current-rockchip64` package.
The HMD test does not require that package.

## Hardware result

No hardware test runs during this task.
No package is installed on the Orange Pi 5.
No boot file, bootloader, or partition changes during this task.
Use the hardware checks in `README.md` for DP negotiation, HPD, EDID, DPCD, training, and KMS.
The original hardware success condition remains unverified.
