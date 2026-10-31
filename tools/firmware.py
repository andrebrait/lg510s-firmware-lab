#!/usr/bin/env python3
"""Inspect the observed 16 MiB LG510S layout; never access a programmer."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct
import zlib

FLASH_SIZE = 16 * 1024 * 1024
IMAGE_OFFSET = 0x300000
IMAGE_END = 0xF00000
MAX_UNPACKED = 64 * 1024 * 1024


def inspect_bytes(flash):
    if len(flash) != FLASH_SIZE:
        raise ValueError("expected a 16 MiB full flash dump")
    header = bytes(flash[IMAGE_OFFSET:IMAGE_OFFSET + 64])
    magic, hcrc, timestamp, size, load, entry, dcrc, os_id, arch, kind, comp, name = struct.unpack(">7I4B32s", header)
    if magic != 0x83800000 or comp != 3:
        raise ValueError("not the observed Realtek LZMA firmware format")
    if zlib.crc32(header[:4] + b"\0" * 4 + header[8:]) != hcrc:
        raise ValueError("firmware header CRC mismatch")
    if size < 1 or IMAGE_OFFSET + 64 + size > IMAGE_END:
        raise ValueError("firmware payload exceeds its observed partition")
    payload = flash[IMAGE_OFFSET + 64:IMAGE_OFFSET + 64 + size]
    if zlib.crc32(payload) != dcrc:
        raise ValueError("firmware payload CRC mismatch")
    return {"flash_bytes": len(flash), "sha256": hashlib.sha256(flash).hexdigest(),
            "version": name.split(b"\0", 1)[0].decode("ascii", "replace"),
            "timestamp": timestamp, "payload_bytes": size,
            "load_address": hex(load), "entry_address": hex(entry),
            "os": os_id, "architecture": arch, "image_type": kind}


def squashfs_members(archive):
    """Read only two whitelisted regular files from newc; never extract paths."""
    pos = 0
    members = {}
    while pos < len(archive):
        if len(archive) - pos < 110 or archive[pos:pos + 6] not in (b"070701", b"070702"):
            raise ValueError("invalid or truncated newc header")
        fields = [int(archive[pos + 6 + i * 8:pos + 14 + i * 8], 16) for i in range(13)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        name_start, name_end = pos + 110, pos + 110 + namesize
        body_start = (name_end + 3) & ~3
        body_end = body_start + size
        if not namesize or name_end > len(archive) or archive[name_end - 1] != 0 or body_end > len(archive):
            raise ValueError("invalid or truncated newc member")
        name = archive[name_start:name_end - 1]
        if name == b"TRAILER!!!":
            return members
        if name in (b"sqfs.img", b"./sqfs.img", b"modsqfs.img", b"./modsqfs.img"):
            if mode & 0o170000 != 0o100000:
                raise ValueError("requested image is not a regular file")
            key = name.removeprefix(b"./").decode()
            if key in members:
                raise ValueError("duplicate squashfs image in initramfs")
            members[key] = archive[body_start:body_end]
        pos = (body_end + 3) & ~3
    raise ValueError("newc trailer missing")


def unpack_bytes(flash):
    info = inspect_bytes(flash)
    payload = flash[IMAGE_OFFSET + 64:IMAGE_OFFSET + 64 + info["payload_bytes"]]
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=128 * 1024 * 1024)
    kernel = decoder.decompress(payload, max_length=MAX_UNPACKED + 1)
    if len(kernel) > MAX_UNPACKED or not decoder.eof:
        raise ValueError("kernel exceeds extraction limit or is truncated")
    candidates = []
    start = 0
    while True:
        start = kernel.find(b"\x1f\x8b\x08", start)
        if start < 0:
            break
        dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            archive = dec.decompress(kernel[start:], MAX_UNPACKED + 1)
            if len(archive) <= MAX_UNPACKED and dec.eof and archive.startswith(b"070701"):
                candidates.append((archive, squashfs_members(archive)))
        except (ValueError, zlib.error):
            pass
        start += 3
    if len(candidates) != 1:
        raise ValueError(f"expected one gzip/newc initramfs; found {len(candidates)}")
    archive, members = candidates[0]
    if set(members) != {"sqfs.img", "modsqfs.img"}:
        raise ValueError("observed initramfs squashfs images are missing")
    parts = {"uboot.bin": flash[:0x100000], "jffs2-a.bin": flash[0x100000:0x300000],
             "firmware-image.bin": flash[IMAGE_OFFSET:IMAGE_END],
             "jffs2-b.bin": flash[IMAGE_END:], "kernel.bin": kernel,
             "initramfs.cpio": archive, **members}
    return info, parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "unpack"))
    parser.add_argument("dump", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        flash = args.dump.read_bytes()
        if args.action == "inspect":
            info = inspect_bytes(flash)
        else:
            if args.output is None:
                parser.error("unpack requires a new output directory")
            info, parts = unpack_bytes(flash)
            args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
            for name, body in parts.items():
                path = args.output / name
                with path.open("xb") as out:
                    path.chmod(0o600)
                    out.write(body)
        print(json.dumps(info, indent=2))
    except (OSError, ValueError, lzma.LZMAError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
