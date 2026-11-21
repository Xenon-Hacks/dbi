#!/usr/bin/env python3
"""Fix DBI's FTP "Save Data" read bug ("File read error (2002-3005) Read out of file range").

Usage: python patch_ftpread.py DBI.nro DBI-ftpfix.nro [--title "DBI FTP fix"]

Finds the save-file stream read method by its code (checked on DBI 912 and 921) and
replaces the 9 instructions after the file read call so the method advances its position by,
and returns, the number of bytes actually read instead of the number requested.
The input file is never modified. Only the standard library is needed.
"""
import argparse, hashlib, struct, sys

# ldr w0,[sp,#0x4c]; cbnz w0,err; ldr x0,[x19,#0x18]; add x0,x0,x20; str x0,[x19,#0x18];
# mov x0,x20; ldp x19,x20,[sp,#0x10]; ldp x29,x30,[sp],#0x190; ret
ORIG = bytes.fromhex("e04f40b9" "00010035" "600e40f9" "0000148b" "600e00f9"
                     "e00314aa" "f35341a9" "fd7bd9a8" "c0035fd6")
# ldr w1,[sp,#0x4c]; cbnz w1,err; ldr x1,[x19,#0x18]; add x1,x1,x0; str x1,[x19,#0x18];
# nop; ldp x19,x20,[sp,#0x10]; ldp x29,x30,[sp],#0x190; ret
# (the ldp x19,x20 stays at the same address: an error path branches to it)
NEW = bytes.fromhex("e14f40b9" "01010035" "610e40f9" "2100008b" "610e00f9"
                    "1f2003d5" "f35341a9" "fd7bd9a8" "c0035fd6")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--title", help="rename the homebrew menu title (NACP)")
    a = ap.parse_args()
    d = bytearray(open(a.src, "rb").read())
    if d[0x10:0x14] != b"NRO0":
        sys.exit("not an NRO")
    if d.count(NEW):
        sys.exit("already patched")
    hits = []
    i = d.find(ORIG)
    while i >= 0:
        if struct.unpack_from("<I", d, i - 4)[0] >> 26 == 0x25:  # preceded by BL
            hits.append(i)
        i = d.find(ORIG, i + 1)
    if len(hits) != 1:
        sys.exit(f"expected one patch site, found {len(hits)}: this DBI version is not supported")
    site = hits[0]
    d[site:site + len(NEW)] = NEW
    print(f"patched at 0x{site:X}")
    if a.title:
        asset = struct.unpack_from("<I", d, 0x18)[0]
        off, _ = struct.unpack_from("<QQ", d, asset + 0x18)
        nacp = asset + off
        for lang in range(16):
            e = nacp + lang * 0x300
            if d[e]:
                d[e:e + 0x200] = a.title.encode()[:0x1ff].ljust(0x200, b"\0")
    open(a.dst, "wb").write(d)
    print(a.dst, "sha256", hashlib.sha256(d).hexdigest())


if __name__ == "__main__":
    main()
