#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Collect USB-C DisplayPort state without changing device state.
set -u
shopt -s nullglob

uname -a
printf '\nType-C\n'
for node in /sys/class/typec/* /sys/class/typec/*/*; do
	[[ -d "${node}" ]] || continue
	for attr in svid mode active orientation data_role power_role pin_assignment configuration; do
		[[ -f "${node}/${attr}" ]] || continue
		printf '%s/%s: ' "${node}" "${attr}"
		cat "${node}/${attr}"
	done
done

printf '\nDRM DisplayPort connectors\n'
for node in /sys/class/drm/card*-DP-*; do
	printf '%s\n' "${node}"
	for attr in status enabled modes; do
		[[ -f "${node}/${attr}" ]] || continue
		printf '%s: ' "${attr}"
		cat "${node}/${attr}"
	done
	[[ ! -f "${node}/edid" ]] || wc -c "${node}/edid"
done

printf '\nDriver bindings\n'
for node in /sys/bus/platform/devices/*fde50000* /sys/bus/platform/devices/*fed80000* /sys/bus/i2c/devices/*-0022; do
	printf '%s: ' "${node}"
	readlink "${node}/driver" || true
done
cat /sys/kernel/debug/devices_deferred 2>/dev/null || true

printf '\nDRM state and bridges\n'
for file in /sys/kernel/debug/dri/*/state /sys/kernel/debug/dri/*/encoder-*/bridges /sys/kernel/debug/dri/*/bridges; do
	[[ -f "${file}" ]] || continue
	printf '%s\n' "${file}"
	cat "${file}" 2>/dev/null || true
done

printf '\nTCPM and FUSB302 logs\n'
for file in /sys/kernel/debug/usb/tcpm-*/log /sys/kernel/debug/usb/fusb302-*/log; do
	printf '%s\n' "${file}"
	tail -n 400 "${file}" 2>/dev/null || true
done

printf '\nKernel messages\n'
dmesg 2>/dev/null | grep -Ei 'dw.?dp|usbdp|fusb302|typec|tcpm|displayport|drm|hpd|dpcd|training|SError|defer' || true
