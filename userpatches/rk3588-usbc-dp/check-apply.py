#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Check patch application against the Linux 6.18.55 release archive."""

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile


def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    patchdir = repo / "userpatches/kernel/archive/rockchip64-6.18"
    patches = sorted(patchdir.glob("zzz-rk3588-usbc-dp-*.patch"))
    expected = {}
    for line in (Path(__file__).parent / "patches.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    if {p.name for p in patches} != set(expected):
        raise ValueError("Patch manifest mismatch")
    for p in patches:
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected[p.name]:
            raise ValueError(f"Patch hash mismatch: {p}")
    core = [repo / p for p in (Path(__file__).parent / "core-patches.txt").read_text().splitlines()]
    paths = set()
    for p in core + patches:
        paths.update(re.findall(r"^diff --git a/(.*?) b/", p.read_text(), re.M))
    with tempfile.TemporaryDirectory(prefix="rk3588-dp-apply-") as work:
        root = Path(work)
        with tarfile.open(args.archive) as tf:
            for path in sorted(paths):
                try:
                    data = tf.extractfile("linux-6.18.55/" + path).read()
                except KeyError:
                    continue
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        run(["git", "init", "-q"], root)
        for p in core:
            run(["patch", "--forward", "--batch", "-p1", "-i", str(p)], root)
        run(["git", "add", "."], root)
        for p in patches:
            run(["git", "apply", "--check", str(p)], root)
            run(["git", "apply", str(p)], root)
        run(["git", "add", "-N", "."], root)
        run(["git", "diff", "--check"], root)
        print(f"PASS: {len(patches)} patches apply without fuzz")
        print(f"Checked {len(core)} intersecting Armbian patches")
        print("Full Armbian patch application and package build remain separate checks")


if __name__ == "__main__":
    main()
