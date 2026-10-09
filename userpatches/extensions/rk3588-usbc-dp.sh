#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Enable Orange Pi 5 USB-C DisplayPort support.

function custom_kernel_config__rk3588_usbc_dp() {
	[[ "${BOARD}" == "orangepi5" && "${BRANCH}" == "current" ]] || return 0

	opts_y+=(USB_DWC3_ROCKCHIP ROCKCHIP_DW_DP)
	opts_m+=(PHY_ROCKCHIP_USBDP TYPEC_FUSB302 TYPEC_DP_ALTMODE)
}
