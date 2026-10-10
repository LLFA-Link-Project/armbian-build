# DisplayPort modeset transition diagnostics

Identify why video stabilizes after an initial corruption and blackout.
Preserve the clock repair and link training policy.

## Hardware evidence

The user confirms correct DCLK and successful HBR3 ×4 CR/EQ after patches 0901–0903.
The user corrects the earlier requirement for a second modetest execution.
Starting from visible TTY, output shows corruption, then blackouts, then usually displays correctly without restarting modetest.
The user reports about eight seconds until correct video at both 72 Hz and 90 Hz.
Exact visual event timestamps remain unknown.
The similar delay makes common startup behavior a candidate, despite the different pixel clocks.
The observation does not identify a driver timer or display synchronization as the cause.
The user runs legacy modetest without `-a` and exits with Ctrl-C.
TTY returns after an observable interval.

Recorded commands:

```sh
sudo modetest -M rockchip -s 84:3840x1920-72
sudo modetest -M rockchip -s 84:3840x1920-90
```

Connector 84 and CRTC 82 identify this supplied run only.
Do not assume those IDs remain constant.
The observations establish delayed recovery within one execution, rather than its cause.
They do not establish error-free sustained DP transmission.

The supplied patch 1001 logs show these transitions:

| Mode | Video enable time, seconds after boot | Actual DCLK, Hz | Standby completion | CR/EQ |
| --- | --- | --- | --- | --- |
| 3840×1920@72 | 87.206879, 101.316916 | 573289993 | Completes | Passes |
| 3840×1920@90 | 110.792900, 115.239446, 137.712672, 143.430417 | 424979988 | Completes | Passes |

Every listed invocation performs a full 1080p60-to-high-resolution modeset.
Repeated executions do not skip the modeset in this capture.
The 90 Hz mode uses twice DCLK for its pixel clock.
Hardware timing readback matches the new cached timing after standby release.
VOP2 releases standby about 48 milliseconds before DPTX enables video.
The capture records no further modeset or training during the subsequent high-resolution hold intervals.
Visual timestamps must identify whether recovery occurs inside those intervals.
Link training success does not establish correct video reception throughout those intervals.
VOP2 startup and display synchronization remain candidates.
This capture does not identify either candidate as the cause.

## Source findings

Rockchip uses `drm_atomic_helper_commit_tail_rpm()`.
For a full modeset, the helper performs these stages:

```text
DPTX disable -> video off -> link off -> controller reset
VOP2 disable -> standby completion -> DCLK off
VOP2 enable -> clocks on -> timings -> PLL/DCLK -> cfg_done -> standby release
DPTX enable -> PHY/sink power -> training -> video on
Plane update -> VOP2 flush -> cfg_done -> vblank wait
```

Other bridges can add callbacks between these stages.
The helper skips enable/disable callbacks for plane-only commits.
The supplied repeated executions perform full modesets.

Closing the last userspace DRM file calls `drm_client_dev_restore()`.
The fbdev client can then commit its framebuffer mode.
Record that restore instead of assuming Ctrl-C immediately restores 1080p60.
The supplied capture restores DPTX video about 167–206 milliseconds after removing the high-resolution framebuffer.
That interval excludes any later delay before visible TTY.

Vendor SST DPTX enables the VOP DP gate after video enable.
Vendor gate handling issues cfg_done, waits for configuration, and resets DCLK when loader protection permits.
Vendor disable closes that gate before video disable.
Vendor VOP2 also waits for configuration before entering standby.
Mainline lacks that output-gate callback and uses a controller reset during DPTX disable.
Both VOP2 implementations configure timing and clocks before releasing standby.
These differences remain candidates, not confirmed defects.
Do not add a reset, delay, or gate change from this comparison alone.

Primary sources:

- [Mainline atomic helper](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/gpu/drm/drm_atomic_helper.c?h=v6.18.55): `drm_atomic_helper_commit_tail_rpm`.
- [Rockchip commit policy](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/gpu/drm/rockchip/rockchip_drm_fb.c?h=v6.18.55).
- [DRM file release](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/gpu/drm/drm_file.c?h=v6.18.55): `drm_lastclose`.
- [Vendor DPTX](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/gpu/drm/rockchip/dw-dp.c#L4918).
- [Vendor VOP2 gate](https://github.com/armbian/linux-rockchip/blob/dc098b0048bc7a0cf621779ec62e8a03047f5ca2/drivers/gpu/drm/rockchip/rockchip_drm_vop2.c#L1522).

## Patch 1001

The patch changes DPTX and VOP2 diagnostics only.
The patch retains every register write, reset, wait duration, and training decision.
The patch captures the existing reset poll result without changing error handling.
Register reads execute only when their dynamic debug records are enabled.
Register reads occur before device clocks or runtime references are released.
The patch reads configuration registers, rather than interrupt acknowledgement registers.

Records include:

- VOP2 old/new active, enable, clock, and modeset flags.
- Old/new primary framebuffer IDs and formats, plus new stride and modifier.
- Enable/disable/flush stages, standby completion, and PLL update results.
- VOP2 cached values and direct MMIO values, including timings and divider settings.
- DPTX runtime state, link state, reset poll result, video state, and transport registers.

`state=%p` correlates callbacks within a commit.
An address can be reused for later commits.
A missing plane state means the commit omits that plane, rather than having no framebuffer.
VOP2 regmap caches video port registers until configuration takes effect.
Compare `cached_*` and `hw_*` fields before inferring register state.
Separate reads do not form an atomic hardware snapshot.
Existing VOP2 cached reads do not report regmap read errors.
DPTX read failures emit a separate error record and use a zero placeholder.
Reset HPD is valid only when its poll returns zero.

## Build and verification

65 patches apply without fuzz after seven intersecting Armbian patches.
The changed arm64 objects compile.
Checkpatch reports zero errors and zero warnings.
See `sequence-apply.log`, `sequence-build.log`, and `sequence-style.log`.
The supplied hardware logs contain patch 1001 records.
Local package verification and hardware regression tests remain pending.

Run the existing Docker kernel command:

```sh
./compile.sh kernel BOARD=orangepi5 BRANCH=current \
  KERNELBRANCH=tag:v6.18.55 KERNEL_CONFIGURE=no \
  ENABLE_EXTENSIONS=rk3588-usbc-dp ARTIFACT_IGNORE_CACHE=yes \
  PATCHES_TO_GIT=yes
```

Verify the new packages:

```sh
python3 userpatches/rk3588-usbc-dp/verify.py --transitions image.deb dtb.deb headers.deb
```

The flag checks transition records and all clock repair checks.
Copy `capture-transition.sh` to the board under user control.
The script reads state without running modetest or probing connectors.

## Hardware comparison

Enable records after a user-controlled boot of the rebuilt kernel:

```sh
echo 'format dpdiag +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
```

In another terminal, record the complete timeline:

```sh
sudo dmesg --follow --time-format=raw > ~/dp-sequence-dmesg.log
```

Keep modetest running through corruption, blackout, and correct video.
Capture each visible stage from a separate terminal.
Record these snapshots from a separate terminal:

```sh
sudo bash ~/capture-transition.sh tty-before > ~/dp-tty-before.log
sudo bash ~/capture-transition.sh corrupt > ~/dp-corrupt.log
sudo bash ~/capture-transition.sh blackout > ~/dp-blackout.log
sudo bash ~/capture-transition.sh stable > ~/dp-stable.log
sudo bash ~/capture-transition.sh after-ctrl-c > ~/dp-after-ctrl-c.log
sudo bash ~/capture-transition.sh tty-restored > ~/dp-tty-restored.log
```

Run each snapshot at the named stage, not all snapshots consecutively.
Keep modetest running during each active snapshot.
Record visible success or failure beside each snapshot label.
The script records uptime to correlate visible stages with dmesg timestamps.
Use the observed TTY and DRM state as the condition, rather than a fixed sleep.
Record both 72 Hz and 90 Hz sequences, including the preceding mode.
Recheck 1080p60 and HBR3 ×4, then repeat with diagnostics disabled.
Logging can alter timing and can conceal the failure.
Do not clear dmesg, force training, or change PLL settings during this comparison.

Disable the added records:

```sh
echo 'format dpdiag -p' | sudo tee /sys/kernel/debug/dynamic_debug/control
```

Compare modeset flags first, then standby completion, PLL changes, configuration readback, and DPTX reset/video stages.
Check underflow, vblank, and commit timeout messages throughout Ctrl-C and restoration.
A functional fix requires evidence that explains the initial corruption and delayed recovery.
The revised observation requires no kernel change or rebuild yet.
