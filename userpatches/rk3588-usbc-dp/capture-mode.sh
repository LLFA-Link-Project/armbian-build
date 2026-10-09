#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Capture the current mode without changing display state.
set -u
shopt -s nullglob

printf 'Mode label: %s\n' "${1:-unspecified}"
date -Ins
uname -r
printf '\nType-C assignment\n'
for file in /sys/class/typec/*/{active,svid,orientation} /sys/class/typec/*/displayport/{configuration,pin_assignment}; do
	printf '%s: ' "${file}"
	cat "${file}"
done
printf '\nMode and plane state\n'
modetest -M rockchip -c -p
printf '\nDRM atomic state\n'
for file in /sys/kernel/debug/dri/*/state; do
	printf '%s\n' "${file}"
	cat "${file}"
done
printf '\nClock state\n'
cat /sys/kernel/debug/clk/clk_summary
printf '\nDisplay diagnostics\n'
dmesg | grep -Ei 'dpdiag|POST_BUF_EMPTY|underflow|training|clock recovery|equalization|ROPLL'
