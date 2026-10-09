#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Check the Orange Pi 5 DTB and kernel packages without installing packages."""

import argparse
import gzip
import hashlib
import io
import lzma
from pathlib import Path
import struct
import subprocess
import tarfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cells(data):
    require(len(data) % 4 == 0, "Invalid DT cell length")
    return struct.unpack(f">{len(data) // 4}I", data)


def dt_nodes(data):
    require(len(data) >= 40, "Truncated DTB")
    magic, total, start, strings = struct.unpack_from(">4I", data)
    require(magic == 0xD00DFEED and total <= len(data), "Invalid DTB header")
    nodes, stack = {}, []
    pos = start
    while pos < total:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == 1:
            end = data.index(b"\0", pos)
            stack.append(data[pos:end].decode())
            nodes["/".join(stack) or "/"] = {}
            pos = (end + 4) & ~3
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, offset = struct.unpack_from(">2I", data, pos)
            pos += 8
            end = data.index(b"\0", strings + offset)
            name = data[strings + offset:end].decode()
            nodes["/".join(stack) or "/"][name] = data[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            return nodes
        else:
            raise ValueError(f"Invalid DT token: {token}")
    raise ValueError("Missing DT end token")


def check_dtb(data):
    nodes = dt_nodes(data)
    require(b"xunlong,orangepi-5\0" in nodes["/"]["compatible"], "Wrong board DTB")
    dp = next(p for p in nodes if p.endswith("/dp@fde50000"))
    phy = next(p for p in nodes if p.endswith("/phy@fed80000"))
    require(nodes[dp].get("status") == b"okay\0", "DP0 is disabled")
    require(nodes[phy].get("status", b"okay\0") == b"okay\0", "PHY0 is disabled")
    connector = next(p for p, v in nodes.items()
                     if v.get("compatible") == b"usb-c-connector\0")
    alt = nodes[connector + "/altmodes/dp"]
    require(alt["svid"] == b"\xff\x01", "Missing DisplayPort SVID")
    require(cells(alt["vdo"]) == (0x1C46,), "Unexpected DisplayPort capabilities")
    require(phy + "/port" not in nodes, "Legacy PHY port remains")
    handles = {cells(v["phandle"])[0]: p for p, v in nodes.items() if "phandle" in v}

    def remote(endpoint):
        target = handles[cells(nodes[endpoint]["remote-endpoint"])[0]]
        require(handles[cells(nodes[target]["remote-endpoint"])[0]] == endpoint,
                f"Nonreciprocal endpoint: {endpoint}")
        return target

    for port in (0, 2, 3):
        endpoint = phy + f"/ports/port@{port}/endpoint"
        target = remote(endpoint)
        require(target.startswith(dp if port == 2 else connector),
                f"Wrong PHY port {port} target")
    output = dp + "/ports/port@1/endpoint"
    require(remote(output).startswith(phy), "DP output misses PHY0")
    input_ep = dp + "/ports/port@0/endpoint"
    require("/port@2/endpoint@a" in remote(input_ep), "DP input misses VOP VP2")
    for attr in ("clocks", "resets", "power-domains", "phys"):
        require(attr in nodes[dp], f"Missing DP resource: {attr}")
    print("PASS: Orange Pi 5 DP0, VP2, PHY0 and Type-C graph")


def unpack(data):
    if data.startswith(b"\x1f\x8b"):
        return gzip.decompress(data)
    if data.startswith(b"\xfd7zXZ\0"):
        return lzma.decompress(data)
    if data.startswith(b"\x28\xb5\x2f\xfd"):
        return subprocess.run(["zstd", "-dc"], input=data,
                              stdout=subprocess.PIPE, check=True).stdout
    return data


def package(path):
    raw = path.read_bytes()
    require(raw.startswith(b"!<arch>\n"), "Invalid Debian archive")
    members, pos = {}, 8
    while pos + 60 <= len(raw):
        header = raw[pos:pos + 60]
        require(header[58:60] == b"`\n", "Invalid archive member")
        size = int(header[48:58])
        name = header[:16].decode().strip().rstrip("/")
        members[name] = raw[pos + 60:pos + 60 + size]
        pos += 60 + size + size % 2
    require(members.get("debian-binary") == b"2.0\n", "Invalid Debian archive version")

    def files(prefix):
        blob = next(v for k, v in members.items() if k.startswith(prefix + ".tar"))
        with tarfile.open(fileobj=io.BytesIO(unpack(blob)), mode="r:") as tf:
            return {m.name.removeprefix("./"): tf.extractfile(m).read()
                    for m in tf.getmembers() if m.isfile()}

    control = files("control")["control"].decode()
    fields = dict(line.split(": ", 1) for line in control.splitlines()
                  if ": " in line and not line.startswith(" "))
    require(fields["Architecture"] == "arm64", f"Wrong architecture: {path}")
    print(fields["Package"], fields["Version"], hashlib.sha256(raw).hexdigest())
    return fields, files("data")


def check_packages(paths, diagnostics=False):
    packages = {meta["Package"]: (meta, data) for meta, data in map(package, paths)}
    names = [f"linux-{part}-current-rockchip64" for part in ("image", "dtb", "headers")]
    require(set(packages) == set(names), "Provide image, DTB and headers packages")
    require(len({m["Version"] for m, _ in packages.values()}) == 1, "Package version mismatch")
    image, dtb, headers = [packages[name][1] for name in names]
    configs = [(p, v) for p, v in image.items() if p.startswith("boot/config-")]
    require(len(configs) == 1, "Missing unique kernel config")
    release = configs[0][0].removeprefix("boot/config-")
    require(release == "6.18.55-current-rockchip64", f"Unexpected release: {release}")
    config = configs[0][1].decode()
    for key, val in {"DRM_DW_DP": "m", "ROCKCHIP_DW_DP": "y", "DRM_AUX_BRIDGE": "m",
                     "DRM_AUX_HPD_BRIDGE": "m", "PHY_ROCKCHIP_USBDP": "m",
                     "TYPEC_FUSB302": "m", "TYPEC_DP_ALTMODE": "m",
                     "USB_DWC3_ROCKCHIP": "y"}.items():
        require(f"CONFIG_{key}={val}\n" in config, f"Wrong config: {key}")
    kernel = unpack(image["boot/vmlinuz-" + release])
    require(kernel[56:60] == b"ARM\x64", "Missing arm64 Image magic")
    modules = {name: None for name in ("dw-dp", "phy-rockchip-usbdp", "fusb302",
                                      "typec_displayport", "aux-bridge", "aux-hpd-bridge")}
    if diagnostics:
        modules.update({"dw-dp": b"dpdiag caps", "phy-rockchip-usbdp": b"dpdiag PLL",
                        "rockchipdrm": b"dpdiag vop"})
    for module, marker in modules.items():
        candidates = [v for p, v in image.items()
                      if p.startswith("lib/modules/" + release + "/")
                      and p.split("/")[-1].split(".ko")[0] == module and ".ko" in p]
        require(len(candidates) == 1, f"Missing unique module: {module}")
        obj = unpack(candidates[0])
        require(obj.startswith(b"\x7fELF") and struct.unpack_from("<H", obj, 18)[0] == 183,
                f"Wrong module architecture: {module}")
        if module == "dw-dp":
            require(b"USB-C mode" in obj, "DP Alt Mode patch missing")
        if marker:
            require(marker in obj, f"Diagnostic patch missing: {module}")
    builtin = image["lib/modules/" + release + "/modules.builtin"]
    require(b"dwc3-rockchip.ko" in builtin, "Rockchip DWC3 glue missing")
    check_dtb(dtb["boot/dtb-" + release + "/rockchip/rk3588s-orangepi-5.dtb"])
    require(any(p.startswith("usr/src/linux-headers-" + release + "/") for p in headers),
            "Headers release mismatch")
    print("PASS: kernel Image, modules, DTB, headers and package versions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dtb", type=Path)
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("packages", nargs="*", type=Path)
    args = parser.parse_args()
    require(bool(args.dtb or args.packages), "Provide --dtb or three packages")
    if args.dtb:
        check_dtb(args.dtb.read_bytes())
    if args.packages:
        check_packages(args.packages, args.diagnostics)


if __name__ == "__main__":
    main()
