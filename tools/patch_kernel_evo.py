#!/usr/bin/env python3
"""Patch the EVO DTB inside the image's FAT 'KERNEL' (Android boot image v0, gzip kernel + appended DTBs).

Applies the same changes as dts/pocket-evo-fixes.dtsi to the DTB whose model is "AYANEO Pocket EVO":
  - reserved-memory/splash_region@b8000000 (cont_splash_region, no-map)
  - gpio-keys-pocket-evo + evo-keys-default-state (TLMM 85/88/91/109/169/170, pull-up)
Everything else (kernel, ramdisk, cmdline, other DTBs) is copied byte-for-byte.

usage: python3 patch_kernel_evo.py KERNEL KERNEL.new
requires: pip install fdt
"""
import hashlib
import struct
import sys
import zlib

import fdt

MODEL = "AYANEO Pocket EVO"
KEYS = [  # node, label, tlmm gpio, linux,code  (stock Android DT values)
    ("key-aya", "AYANEO", 85, 30),       # KEY_A
    ("key-equal", "EQUAL", 169, 13),     # KEY_EQUAL
    ("key-lc", "LC", 91, 105),           # KEY_LEFT
    ("key-rc", "RC", 88, 106),           # KEY_RIGHT
    ("key-rc2", "RC2", 170, 54),         # KEY_RIGHTSHIFT
    ("key-turbo", "TURBO", 109, 400),
]


def split_dtbs(blob):
    out, o = [], 0
    while o + 8 <= len(blob) and blob[o:o + 4] == b"\xd0\x0d\xfe\xed":
        n = struct.unpack(">I", blob[o + 4:o + 8])[0]
        out.append(blob[o:o + n])
        o += n
    if o != len(blob):
        raise SystemExit("unexpected data after the DTB list")
    return out


def walk(n, path=""):
    p = (path + "/" + n.name) if n.name else ""
    yield (p or "/"), n
    for c in n.nodes:
        yield from walk(c, p)


def patch_dtb(blob):
    t = fdt.parse_dtb(blob)
    names = {n.name for _, n in walk(t.root)}
    if "gpio-keys-pocket-evo" in names or "splash_region@b8000000" in names:
        raise SystemExit("EVO DTB already patched")
    next_ph = max(n.get_property("phandle").data[0] for _, n in walk(t.root)
                  if any(p.name == "phandle" for p in n.props)) + 1
    tlmm = t.get_node("/soc@0/pinctrl@f100000")
    tlmm_ph = tlmm.get_property("phandle").data[0]

    sp = fdt.Node("splash_region@b8000000")
    sp.append(fdt.PropWords("reg", 0x0, 0xB8000000, 0x0, 0x2B00000))
    sp.append(fdt.PropStrings("label", "cont_splash_region"))
    sp.append(fdt.Property("no-map"))
    t.get_node("/reserved-memory").append(sp)

    st = fdt.Node("evo-keys-default-state")
    st.append(fdt.PropStrings("pins", *[f"gpio{g}" for g in sorted(k[2] for k in KEYS)]))
    st.append(fdt.PropStrings("function", "gpio"))
    st.append(fdt.PropWords("drive-strength", 2))
    st.append(fdt.Property("bias-pull-up"))
    st.append(fdt.PropWords("phandle", next_ph))
    tlmm.append(st)

    gk = fdt.Node("gpio-keys-pocket-evo")
    gk.append(fdt.PropStrings("compatible", "gpio-keys"))
    gk.append(fdt.PropStrings("label", "gpio-keys-pocket-evo"))
    gk.append(fdt.PropStrings("pinctrl-names", "default"))
    gk.append(fdt.PropWords("pinctrl-0", next_ph))
    for node, label, gpio, code in KEYS:
        k = fdt.Node(node)
        k.append(fdt.PropStrings("label", label))
        k.append(fdt.PropWords("gpios", tlmm_ph, gpio, 1))  # GPIO_ACTIVE_LOW
        k.append(fdt.PropWords("linux,code", code))
        k.append(fdt.PropWords("linux,input-type", 1))      # EV_KEY
        k.append(fdt.PropWords("debounce-interval", 15))
        gk.append(k)
    t.root.append(gk)
    return t.to_dtb(version=17)


def main(src, dst):
    d = open(src, "rb").read()
    if d[:8] != b"ANDROID!":
        raise SystemExit("not an Android boot image")
    ks, _, rs, _, _, _, _, ps, hv, _ = struct.unpack("<10I", d[8:48])
    if hv != 0:
        raise SystemExit("only boot image header v0 is supported")
    pg = lambda n: (n + ps - 1) // ps * ps
    raw = d[ps:ps + ks]
    z = zlib.decompressobj(31)
    z.decompress(raw)
    gz = raw[:len(raw) - len(z.unused_data)]
    dtbs = split_dtbs(z.unused_data)
    ramdisk = d[ps + pg(ks):ps + pg(ks) + rs]

    hits = [i for i, b in enumerate(dtbs) if fdt.parse_dtb(b).get_property("model").data[0] == MODEL]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one '{MODEL}' DTB, found {len(hits)}")
    dtbs[hits[0]] = patch_dtb(dtbs[hits[0]])

    newk = gz + b"".join(dtbs)
    hdr = bytearray(d[:ps])
    struct.pack_into("<I", hdr, 8, len(newk))
    sha = hashlib.sha1()
    for blob in (newk, ramdisk, b""):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    hdr[576:608] = sha.digest().ljust(32, b"\0")
    out = bytes(hdr) + newk + b"\0" * (pg(len(newk)) - len(newk)) + ramdisk + b"\0" * (pg(rs) - rs)
    out += b"\0" * max(0, len(d) - len(out))
    open(dst, "wb").write(out)
    print(f"patched DTB #{hits[0]} -> {dst} ({len(out)} bytes, md5 {hashlib.md5(out).hexdigest()})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
