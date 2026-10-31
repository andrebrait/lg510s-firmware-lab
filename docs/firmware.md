# Firmware findings — 2026-10-28

## Devices and evidence

The programmer dump came from the spare unit, not the production unit. Both report LG510S-4T2XS and vendor firmware 1.1.1.34. Never substitute a complete dump between units: it includes device identity, configuration and private keys.

The flash marking is Winbond `25Q128JVSO 2302`, detected by flashrom 1.8.0 as `W25Q128.V` (16384 kB). JV is a 3.3 V part; the user's programmer outputs 3.3 V. The unit was unpowered during three read-only CH341A/SOP8-clip reads. Each read was 16777216 bytes and had SHA-256:

```text
7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48
```

Local source files: `~/lg510s-dump/lg510s-{1,2,3}.bin`.
An off-site copy was read back and hashed.

## Observed carving windows

| Range | Contents |
|---|---|
| `0x000000–0x0fffff` | Bootloader and environment region (not separate partition boundaries established by a boot log) |
| `0x100000–0x2fffff` | JFFS2: startup-config, SSH host keys and TLS/HTTP key material |
| `0x300000–0xefffff` | Firmware image region; 64-byte Realtek/uImage-style header then LZMA payload |
| `0xf00000–0xffffff` | JFFS2; extraction returned no files |

These are aggregate extraction ranges, not individual partition boundaries. Subsequent constructor/table decoding recovered the [native 16 MiB default partition map](board-evidence-review.md#native-default-flash-map), including separate LOADER/BDINFO/SYSINFO and CFG/LOG regions. Runtime overrides and the update/write contract remain unverified.

Image magic: `0x83800000`; name: `1.1.1.34`; compressed payload: 8302096 bytes at `0x300040`; load address `0x80000000`; entry `0x803345b0`. LZMA produces 11336112 bytes of kernel data. A gzip archive at kernel-relative offset `0x4888bc` expands to a 7958528-byte newc initramfs.

The initramfs contains:

| File | Format / measured size |
|---|---|
| `sqfs.img` | SquashFS 4.0, xz; 4365245 bytes; 829 inodes |
| `modsqfs.img` | SquashFS 4.0, xz; 1614065 bytes; 47 inodes |
| `init` | Stripped, dynamically linked big-endian MIPS32r2 ELF, not a shell script |

Kernel banner: Linux 3.18.24; GCC 4.8.5 / Realtek MSDK-4.8.5p1 Build 2536; built March 29, 2025. Userspace interpreter: `/lib/ld-uClibc.so.0`.

## Board and bootloader

U-Boot identifies as `2011.12.(1.0.0.2)`, built September 11, 2024. Environment strings include:

```text
boardmodel=RTL9303_8264B_2XGE
bootcmd=boota
bootdelay=1
baudrate=115200
```

The expected saved/default profile describes RTL9303, one RTL8264B four-port PHY group and two exposed SFP+ cages, not four separately identified PHY chips or a SoC limited to two SerDes lanes. The [independent review](board-evidence-review.md) reconstructs selection precedence, configured PHY/lane/polarity values and actual loader handlers. The [live UART validation](uart-uboot-validation.md) confirms console access and the Esc autoboot interrupt. TFTP RAM boot from `0x84000000`, which avoids the staging/decompression overlap hazard, and the OpenWrt flash install are recorded in [OpenWrt on the LG510S-4T2XS](openwrt.md). The active `bootm` path does not check the stock magic word; GUI updater acceptance remains unproved.

## Important files

Extracted paths are relative to `~/lg510s-dump/`:

- `rootfs/etc/inetd.conf`: SSH invokes `/bin/sshd -i`; Telnet invokes `/bin/telnetd`.
- `rootfs/etc/sshd_config`: OpenSSH configuration, RSA/DSA host keys under `/mnt/ssh`, authorized keys path under `/mnt/ssh`.
- `rootfs/etc/passwd`: root's shell is `/bin/cli`. Do not infer unrestricted Linux access from SSH connection success.
- `sqfs/bin/`: `sshd` (OpenSSH 6.2), `telnetd`, `cli`, `handler`, `boa`, `snmpd`, `zebra`, `diag`, `ksid` and other vendor daemons.
- `sqfs/lib/`: `libsal`, `libcfg`, `libclicmd`, `libvty`, `libipc`, `libglue`, `libcJSON`, OpenSSL and Net-SNMP libraries.
- `sqfs/home/web/cgi/`: `get.cgi`, `set.cgi`, `httpuploadruncfg.cgi`, `httprestorecfg.cgi` and related upload handlers.
- `sqfs/home/web/web_org/html/`: page templates, including hidden AAA forms. These are firmware artifacts, not included in this repository.
- `modsqfs/lib/modules/3.18.24/`: `rtcore.ko`, `rtk.ko`, `rtdrv.ko`, plus `l2g_stp`, `l2g_lacp`, `l2g_lldp`, `l2g_igmp`, `l2g_erps`, `l2g_dhcp`, `l2g_isg`, `l2g_dai`, `l2g_loopback` and other vendor modules.
- `jffs2-a/startup-config`: Cisco-like KT-NOS text with global commands and interface sections. It belongs to the spare unit.

## Further extraction

The included unpacker carves images but deliberately does not create device nodes, symlinks or arbitrary archive paths. To inspect filesystems, use an isolated directory/container:

```sh
unsquashfs -no-xattrs -d "$HOME/lg510s-userland-new" "$HOME/lg510s-unpacked-new/sqfs.img"
unsquashfs -no-xattrs -d "$HOME/lg510s-modules-new" "$HOME/lg510s-unpacked-new/modsqfs.img"
```

JFFS2 extraction succeeded with Jefferson under Python 3.12 in a container. The installed Python 3.15 failed inside `dissect.cstruct` (`Cannot use capturing groups in re.Scanner`); do not mistake that extractor failure for a damaged dump. Host cpio could extract regular initramfs files but could not create device nodes without privileges; those warnings did not invalidate the regular-file extraction.

## Source references

The Realtek/D-Link GPL reference SDK includes `longan` RTL930x code and RTL8264B PHY code:
https://github.com/youngfunchina/realtek-switch-doc/tree/main/sources/rtk-dms1250

Public availability is not a conclusion about licensing or redistributability of every component. Exact vendor firmware sources and the binary modules' source have not been obtained.
