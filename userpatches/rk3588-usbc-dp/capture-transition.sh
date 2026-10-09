#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Read display state without invoking connector detection.
set -u
shopt -s nullglob
printf 'Transition label: %s\n' "${1:-unspecified}"
date -Ins
uname -r
for entry in /sys/class/drm/card*-*/{status,enabled,modes} /sys/kernel/debug/dri/*/state; do
	printf '\n%s\n' "$entry"
	cat "$entry"
done
printf '\nClock state\n'
cat /sys/kernel/debug/clk/clk_summary
printf '\nKernel diagnostics\n'
dmesg | grep -Ei 'dpdiag|POST_BUF_EMPTY|underflow|dsp_hold|vblank|flip_done|commit.*timed out'
