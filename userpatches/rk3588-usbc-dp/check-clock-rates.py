#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Validate the added PLL coefficients against the supplied display timings."""

from pathlib import Path
import re

patch = Path(__file__).resolve().parents[1] / "kernel/archive/rockchip64-6.18/zzz-rk3588-usbc-dp-0901.patch"
entries = {}
for rate, p, m, s, k in re.findall(r"^\+\s+RK3588_PLL_RATE\((\d+), (\d+), (\d+), (\d+), (\d+)\)", patch.read_text(), re.M):
    rate, p, m, s, k = map(int, (rate, p, m, s, k))
    assert 1 <= p <= 4 and 64 <= m <= 1023 and 0 <= s <= 6
    assert 0 <= k < 32768
    vco = rate * (1 << s)
    assert 2250000000 <= vco <= 4500000000
    actual = (24000000 * m // p + 24000000 * k // (p * 65536)) >> s
    assert 0 <= rate - actual <= 100
    entries[rate] = (p, m, s, k, vco, actual)

print("mode\tpixel_hz\tdclk_hz\tpll_hz\tp\tm\ts\tk\tvco_hz\tpll_actual_hz\tdclk_actual_hz\tppm_error")
for mode, pixel in [("1080p60", 148500000), ("1440p60", 236110000),
                    ("1920x1920p72", 286660000), ("3840x1920p72", 573290000),
                    ("3840x1920p90", 849960000), ("2544x2544p70", 526750000),
                    ("1080p59.94", 148352000)]:
    child = pixel // 4
    dclk = next(child * div for div in (4, 2, 1) if child * div <= 600000000)
    div = (594000000 + dclk - 1) // dclk
    div += div % 2
    pll = dclk * div
    if pll == 594000000:
        p, m, s, k, vco, actual = 2, 198, 2, 0, 2376000000, 594000000
    else:
        p, m, s, k, vco, actual = entries[pll]
    actual_dclk = (actual + div - 1) // div
    ppm = (actual_dclk - dclk) / dclk * 1000000
    assert abs(ppm) < 0.1
    print(f"{mode}\t{pixel}\t{dclk}\t{pll}\t{p}\t{m}\t{s}\t{k}\t{vco}\t{actual}\t{actual_dclk}\t{ppm:.6f}")

assert 1188000000 // 8 == 148500000
assert 1188000000 // 3 == 396000000
assert len(entries) == 6
