import gzip
import lzma
import struct
import unittest
import zlib

from tools import firmware


def cpio_file(name, body):
    name = name.encode() + b"\0"
    fields = (1, 0o100644, 0, 0, 1, 0, len(body), 0, 0, 0, 0, len(name), 0)
    head = b"070701" + b"".join(f"{n:08x}".encode() for n in fields) + name
    head += b"\0" * (-len(head) % 4)
    return head + body + b"\0" * (-len(body) % 4)


def image():
    archive = cpio_file("sqfs.img", b"hsqs-test") + cpio_file("modsqfs.img", b"hsqs-modules")
    archive += cpio_file("TRAILER!!!", b"")
    kernel = b"kernel-prefix" + gzip.compress(archive, mtime=0)
    payload = lzma.compress(kernel, format=lzma.FORMAT_ALONE)
    header = struct.pack(">7I4B32s", 0x83800000, 0, 0, len(payload), 0x80000000,
                         0x803345B0, zlib.crc32(payload), 5, 5, 2, 3, b"1.1.1.34")
    header = header[:4] + struct.pack(">I", zlib.crc32(header)) + header[8:]
    flash = bytearray(b"\xff" * (16 * 1024 * 1024))
    flash[0x300000:0x300040 + len(payload)] = header + payload
    return bytes(flash), kernel, archive


class FirmwareTests(unittest.TestCase):
    def test_valid_image_and_nested_archives(self):
        flash, kernel, archive = image()
        info, parts = firmware.unpack_bytes(flash)
        self.assertEqual(info["version"], "1.1.1.34")
        self.assertEqual(parts["kernel.bin"], kernel)
        self.assertEqual(parts["initramfs.cpio"], archive)
        self.assertEqual(parts["sqfs.img"], b"hsqs-test")
        self.assertEqual(parts["modsqfs.img"], b"hsqs-modules")

    def test_payload_corruption_is_rejected(self):
        flash, _, _ = image()
        damaged = bytearray(flash)
        damaged[0x300041] ^= 1
        with self.assertRaisesRegex(ValueError, "payload CRC"):
            firmware.inspect_bytes(damaged)

    def test_header_corruption_is_rejected(self):
        flash, _, _ = image()
        damaged = bytearray(flash)
        damaged[0x300020] ^= 1
        with self.assertRaisesRegex(ValueError, "header CRC"):
            firmware.inspect_bytes(damaged)

    def test_wrong_size_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "16 MiB"):
            firmware.inspect_bytes(b"short")

    def test_no_traversal_or_unrequested_files_are_extracted(self):
        archive = cpio_file("../../escape", b"secret") + cpio_file("sqfs.img", b"hsqs-ok")
        archive += cpio_file("TRAILER!!!", b"")
        self.assertEqual(firmware.squashfs_members(archive), {"sqfs.img": b"hsqs-ok"})

    def test_truncated_cpio_is_rejected(self):
        with self.assertRaises(ValueError):
            firmware.squashfs_members(cpio_file("sqfs.img", b"abc")[:-2])


if __name__ == "__main__":
    unittest.main()
