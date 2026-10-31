# Reassessing the RTL930x firmware project — 2026-10-28

## Actual objective

The owner wants an independently maintainable, open-source firmware for this switch family, with a straightforward management UI similar to RTLPlayground. Sharing source and release cadence with RTLPlayground's 8051 firmware is optional, not a requirement. This note reassesses existing work; it is not approval to flash, change bootloader settings or resume the old implementation plan unchanged.

The [full vendor-firmware versus RTLPlayground feature comparison](feature-comparison.md) is an annex and a north star for capability planning—not a requirements list, feature-parity commitment or first-release acceptance checklist. It distinguishes software gaps, established hardware differences and unverified limits.

Subsequent evidence: [spare-board read-only investigation, 2026-10-29](board4-investigation.md). The independently built OpenWrt reference image validates the build foundation, not this board; the investigation identifies concrete RAM, port and SFP-wiring differences from that reference.

The [independent dump-evidence reassessment](board-evidence-review.md) subsequently recovered target PHY addresses, SerDes lanes/polarity controls and native partition defaults, and identified a loader staging/decompression hazard. Static candidate work need not wait for UART; execution still requires a validated recovery and loading procedure.

## What the old work really contains

`~/git/rtl930x-firmware` is the build/research project. Its approved October 19 design targets this exact rebadged model (Lianguo LG510S-4T2XS / Horaco ZX510S-4T2XS), RTL9303 with RTL8264B copper PHYs and two SFP+ cages.

| Artifact | Observed state | Reuse decision |
|---|---|---|
| RTLPlayground `feat/platform-seam`, bbda913 | Refactors the 8051 application behind platform.h; historic review/CI recorded in project ledger | Preserve as provenance; do not require upstreaming or rebasing the entire seam before hardware bring-up |
| RTLPlayground `feat/linux-userland`, 03b4b91 | Linux HTTP/CLI/auth/config store, netlink/ethtool ports, bridge VLAN/PVID/management IP and FDB; namespace benches | Valuable reusable MIT-licensed application code, not disposable work |
| `rtl930x-firmware` M3 | Buildroot wrapper/skeleton and a written six-task plan; external/configs is empty; sync script, target defconfigs, packages and boot test are absent | Resume selectively after correcting scope and board assumptions; this is not yet a built/booted switch image |
| Private firmware lab, 33719aa | Verified dump, extraction tools, native CGI workflow, authenticated SSH access and operation notes | Keep as the hardware/protocol evidence source, separate from the eventual distributable firmware |

The old Linux backend explicitly defers LAG/LACP, STP, IGMP, LLDP, mirroring/isolation, limits, EEE/flow control, cable test, DNS/NTP/syslog and SNMP. Linux firmware upload returns 501. Its tested namespace implementation is not feature parity with the vendor firmware, and no RTL9303 board boot has been established.

RTLPlayground's checked LICENSE is MIT. Reusing or independently forking its UI/backend does not require continued source sharing, but attribution/license notices must remain. There is no need to force every Linux feature through 8051 memory limits, register-shaped counters, nine-port assumptions or compatibility guards solely to keep one shared tree.

## What SSH changes—and what it does not

On the spare unit, local authentication reaches the vendor CLI prompt. `show version`, `show info`, `show flash` and command help worked. `show flash` reported an 8302096-byte image, matching the dumped header payload size. The exposed `debug` tree concerns protocol diagnostics; it is not a Linux shell command.

Static inspection of `cli` found a separate `vtysh_diagDebug` path with a default-controlled check that can reject remote sessions (`Do not allow remote user to enter debug mode`), plus a diagnostic menu containing Shell. This proves a guarded code path exists, not that remote shell access is enabled on this unit. No diagnostic password guesses, bypass, shell command, reboot or flash write were attempted in this reassessment.

SSH currently provides operational access through the stock CLI. It does not establish Linux-root access, `/proc/mtd` or a RAM-boot path. The [UART console](uart-uboot-validation.md) now provides U-Boot access and the live boot log; recovery and RAM loading remain to be proven.

## Driver/ABI boundary

Stock firmware is Linux 3.18.24 with Realtek SDK `rtcore`, `rtk`, `rtdrv` and `l2g_*` modules and vendor IPC/configuration libraries. The old Linux application expects a modern kernel exposing front-panel netdevs through DSA, rtnetlink, ethtool and the Linux bridge.

Do not assume that installing that application on stock Linux will control the switch. Stock front-panel netdev exposure has not been inspected from a Linux shell. A CGI adapter could be a management experiment, but would still rely on the vendor daemon/modules and would not achieve an independently open firmware.

The appropriate replacement remains Linux with the OpenWrt Realtek switch/PCS/PHY work and an independently owned userspace. OpenWrt's checked DSA driver is explicitly GPL-2.0-only:
https://github.com/openwrt/openwrt/blob/main/target/linux/realtek/files-6.18/drivers/net/dsa/rtl83xx/dsa.c

Using its driver/kernel work does not require adopting LuCI, UCI or the entire OpenWrt management stack. However, extracting and maintaining OpenWrt's patch/config/firmware pipeline is real maintenance work; the old M3 plan owns that burden rather than eliminating it.

## Source availability is not blanket licensing

A core D-Link reference SDK file explicitly says it is proprietary Realtek software, usable/distributable only under an authorized license:
https://github.com/youngfunchina/realtek-switch-doc/blob/main/sources/rtk-dms1250/src/dal/longan/dal_longan_port.c

It is not safe to treat the whole public GPL archive as freely reusable source. Use audited open components and independently established board facts; do not import proprietary SDK implementation code into the open replacement on the assumption that public availability grants permission.

OpenWrt packages RTL8264B patch data from a pinned public source and declares GPL-2.0-only:
https://github.com/openwrt/openwrt/blob/main/package/firmware/rtl826x-firmware/Makefile

The checked `conf_rtl8264b.c` has an explicit GPL-2.0-only header, while that source repository's top-level LICENSE is GPLv3. This is a component-level licensing/provenance item to resolve before redistribution, not evidence that the entire vendor stack is open or that the PHY patch has been independently rebuilt from original microcode source.
https://github.com/balika011/realtek_phy_firmware/blob/0cd4abe2b0bf197f75c27088f86a74c7ddb103b4/conf_rtl8264b.c

## Board assumptions that now need revision

- Stock uses header value `0x83800000`; old M3 tasks copy `0x93000000` from another board. The traced active loader path does not check that word, but web-updater acceptance and a distributable image format remain unverified.
- Newly built kernels must use their own linked addresses and a validated loading plan. The current reference payload intersects stock staging, and the loader's overlap check occurs after decompression; nominal RAM capacity is not sufficient protection. TFTP recovery is not hardware-tested.
- The three-read dump and decoded native 16 MiB partition default establish more than carving alone, but are not a runtime `/proc/mtd` map or an update/write contract. Do not repartition bootloader/environment or key/config areas.
- Target MACs, configured PHY addresses, SerDes lanes/polarity controls and SFP GPIO/I²C design are recovered statically. Live IDs/calibration, Linux binding translation, electrical behavior, physical RAM/reservations, LEDs and offload still need board-specific validation.

## Recommended next slice

**Status (2026-10-31):** items 1 and 2 are done. An exact-board OpenWrt image boots, passes traffic on all six ports and is installed on the spare unit's flash with LuCI; see [OpenWrt on the LG510S-4T2XS](openwrt.md) and the [process log](process-log.md). The list below is kept as written.

1. Author a separately labelled LG510S candidate from recovered static facts, now partly confirmed through the [UART console](uart-uboot-validation.md). Prove the recovery path next. Preserve stock firmware and the verified backup; no hardware execution is implied.
2. Resolve memory staging/decompression safety, then build the smallest exact-board RAM-boot image: open kernel/drivers, BusyBox and usable diagnostic access. Execute only after the separately approved recovery/boot gate. Prove all six ports, management connectivity and VLAN isolation before further UI parity work. No flash install yet.
3. Reuse the Linux daemon/UI as an independent fork or selectively lift its tested components. Drop the obligation to maintain a synchronized 8051 seam; do not rewrite working application code merely to change repository ownership.
4. Add management features against native Linux interfaces, choosing established daemons for protocols rather than inheriting placeholders or presenting unsupported states as working features. Preserve a separate recovery shell instead of making the management app the only way in.
5. Design and test persistent configuration and a recoverable upgrade process only after RAM bring-up works. Audit component licenses before publishing a distributable image.

QEMU and namespace tests remain useful, but cannot validate this SoC/PHY pairing, SerDes, hardware VLAN isolation or actual switching throughput. The first gating result should be a recoverable RAM-only boot on the spare unit, not a mass rebase of the RTLPlayground branches.
