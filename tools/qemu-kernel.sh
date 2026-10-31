#!/bin/sh
# Emulator-only kernel: embeds the existing reference userspace, not an LG510S image.
set -eu
[ "$#" -eq 3 ] || { echo "usage: CROSS_COMPILE=<prefix> sh $0 <linux-source> <new-build-dir> <reference.cpio>" >&2; exit 2; }
src=$(realpath "$1")
archive=$(realpath "$3")
: "${CROSS_COMPILE:?set the existing MIPS cross-toolchain prefix}"
[ -f "$src/Makefile" ] && [ -f "$archive" ]
# mkdir refuses an existing output, including symlinks; no reset/clean fallback.
mkdir "$2"
out=$(realpath "$2")
make -C "$src" O="$out" ARCH=mips CROSS_COMPILE="$CROSS_COMPILE" malta_defconfig
"$src/scripts/config" --file "$out/.config" \
    --enable CPU_BIG_ENDIAN --disable CPU_LITTLE_ENDIAN \
    --enable BLK_DEV_INITRD --set-str INITRAMFS_SOURCE "$archive" \
    --enable PAGE_SIZE_4KB --disable PAGE_SIZE_16KB --disable PAGE_SIZE_64KB \
    --enable INITRAMFS_COMPRESSION_NONE --set-str LOCALVERSION -qemu-validation \
    --disable LOCALVERSION_AUTO --disable MODULES \
    --enable DEVTMPFS --enable DEVTMPFS_MOUNT \
    --enable NAMESPACES --enable NET_NS --enable VETH --enable DUMMY \
    --enable BRIDGE --enable BRIDGE_VLAN_FILTERING --enable VLAN_8021Q \
    --enable INET --enable IPV6 --enable PACKET --enable UNIX \
    --enable PCNET32 --enable MII \
    --enable VIRTIO_PCI --enable HW_RANDOM --enable HW_RANDOM_VIRTIO \
    --enable DEBUG_INFO_NONE --disable SOUND --disable DRM
make -C "$src" O="$out" ARCH=mips CROSS_COMPILE="$CROSS_COMPILE" olddefconfig
for symbol in CPU_BIG_ENDIAN PAGE_SIZE_4KB BLK_DEV_INITRD DEVTMPFS NET_NS VETH BRIDGE BRIDGE_VLAN_FILTERING PCNET32 HW_RANDOM_VIRTIO; do
    grep -qx "CONFIG_${symbol}=y" "$out/.config" || { echo "required emulator kernel feature absent: $symbol" >&2; exit 1; }
done
grep -Fx "CONFIG_INITRAMFS_SOURCE=\"$archive\"" "$out/.config"
make -C "$src" O="$out" ARCH=mips CROSS_COMPILE="$CROSS_COMPILE" -j6 vmlinux
"${CROSS_COMPILE}readelf" -h "$out/vmlinux"
