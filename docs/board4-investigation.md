# Spare-board read-only investigation — 2026-10-29

## Outcome and scope

Authenticated SSH on the spare switch works and provides the vendor CLI, not a Linux shell. This investigation collected live status and correlated the existing dump with its exact SDK board profile. It did not change switch configuration, enter diagnostic/debug mode, run cable tests, write registers, save configuration, reboot, RAM-boot or flash a switch. The production unit was not contacted.

The work materially narrows the board definition, but does not establish a safe RAM-boot procedure or justify building an installable LG510S image. The current Sirivision reference image must not be booted on this switch.

The subsequent [independent evidence review](board-evidence-review.md) re-derived the mappings from the dump, recovered additional static PHY/SerDes/partition facts and corrected the earlier loader interpretation. Static facts can inform a separately labelled LG510S candidate now; executing it remains a separate hardware/recovery gate.

## Live observations

The SSH server reports OpenSSH 6.2. Its RSA host public key matched the public key extracted from this unit's programmer dump. A task-local, ignored known-hosts file pinned that key, with strict checking enabled; no global SSH settings or trust files were changed. Transport authentication is followed by the vendor's separate username/password prompts.

| Query | Observed result |
|---|---|
| `show version` | Loader 1.0.0.2, September 11, 2024; firmware 1.1.1.34, March 29, 2025 |
| `show info` | Board Value `1`; uptime about 20 hours at inspection |
| `show privilege` | Existing administrator account has CLI privilege 15 |
| `show memory statistics` | Total `125196` KB; used `84548` KB; free `40648` KB; no swap at that snapshot |
| `show cpu utilization` | Current CPU utilization 0% at that snapshot |
| `show flash` | Virtual files include startup configuration, key/certificate files and an `8302096`-byte image |
| `show line` / `show line console` | SSH enabled, Telnet disabled; console session timeout 10 minutes; no UART rate or pinout exposed |
| `show fiber-transceiver interfaces TenGigabitEthernet 5` | Module inserted, LOS normal; DOM measurements reported not supported |
| Same query for port 6 | Module absent, LOS asserted |

The reported RAM total is consistent with a nominal 128 MiB board **[INFERENCE]**. The stock kernel also contains the compiled command line `console=ttyS0,115200 mem=128M` at file offsets `0x47f6cc` and `0x4806d8`. Neither establishes physical capacity, reserved ranges or a usable boot-time RAM map. Do not copy the reference board's 512 MiB declaration.

`show flash` lists application-managed files; it is not `/proc/mtd`, an erase-block map or proof that file size equals partition size. The image size matches the existing dump's compressed payload length.

Final `show interfaces brief` retained the initial link states. Sessions were closed with two `exit` commands: the first drops privileged mode, the second closes the CLI. The SSH client returned 255 after vendor session closure; the preceding final status query completed normally.

## Port mapping: live labels plus dump-derived SDK ports

The media/link columns below were observed live. The SDK-port column comes from the dumped board configuration, not a live register or PHY read.

| Front panel / CLI | Media | Observed link | Dump-derived SDK switch port |
|---|---|---|---|
| TE1 | Copper | 10G, full duplex | 0 |
| TE2 | Copper | Down | 8 |
| TE3 | Copper | Down | 16 |
| TE4 | Copper | Down | 20 |
| TE5 | SFP+ / Fiber | 10G, full duplex | 25 |
| TE6 | SFP+ / Fiber | Down | 26 |

These SDK switch-port numbers are **not MDIO PHY addresses or SerDes lane numbers**. The TE5 detailed status advertises support for 10G, 1G and 100M, but only its present 10G link was observed. No speed changes, traffic generation or switching/offload tests were performed.

## Exact static profile and provenance

The existing dump is from this spare unit; see [dump provenance](firmware.md). The live model/firmware and pinned host key correlate the inspected unit with that dump. Active runtime HAL pointers were not read.

Two unstripped ELF32 big-endian MIPS modules provide the relevant static evidence:

| Extracted module | SHA-256 |
|---|---|
| `modsqfs/lib/modules/3.18.24/extra/board_conf.ko` | `027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70` |
| `modsqfs/lib/modules/3.18.24/kernel/drivers/net/switch/rtcore/rtcore.ko` | `d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4` |

The evidence chain is specific, rather than selecting a similarly named board:

1. The CRC-valid saved U-Boot environment names `RTL9303_8264B_2XGE`; `idType` and `boardid` are absent. With the compiled forced selector disabled, `hwp_probe` takes the name-selection path. Forced or numeric overrides are code capabilities, not observed active overrides.
2. `rtcore.ko` contains that exact profile in `.data` at `0x33dc`; its name starts at `0x33e0`, and its identifier at profile offset `0x30` is `0x008de842`. The hardware-profile list includes the profile's address.
3. `board_conf.ko:sys_boardModel_init` loads the identifier from `hwp_myHwProfile + 0x30` and selects a `boardModelConfTbl` record using that identifier. Its matching `.rodata` record starts at `0x900` and names `RTL9303-4XGE-2XGEF`.
4. The matching row at `.data + 0x160` is within `boardMap` (symbol base `0xc0`). Its relocations bind `portConf_9303M4XC2XF` and `fiberConf_9303M4XC2XF`.
5. `portConf_9303M4XC2XF` is a six-row table at `.rodata + 0x1f00`, with 32-byte rows and a sentinel. The vendor port formatter loads user port at row offset 4 and physical SDK port at offset 12, establishing the mapping above.

The SDK identifier `0x008de842` is unrelated to live `Board Value: 1`. Under the recovered native partition default, MTD index 2 is SYSINFO; the additional `sys_boardModel_init` read parses `bootmsg`, not an alternative board ID. Live HAL pointers and runtime partition overrides were not inspected.

## SFP wiring recovered from the matching static configuration

`fiberConf_9303M4XC2XF` binds two detection and optical records. The optical table is at `.rodata + 0x3888` with 52-byte rows; the detection table is at `0x38f0`. Relocations were resolved against `boardGpio_930x`, not treated as absolute addresses.

The optical rows select the vendor's software/GPIO I²C path, EEPROM address `0x50`, and delay field `20` (unit not established). `board_gpio_init` dispatch for identifier `0x008de842` selects the internal GPIO table and reaches the setup at `.text + 0x2684`. Its helper arguments bind the following pins and purpose labels:

| Front-panel cage | I²C clock | I²C data | Module detect (`MDO_FX`) | Loss of signal (`LOS_FX`) | Label-inferred TX-disable pairing |
|---|---|---|---|---|---|
| TE5 | Internal GPIO 8 | Internal GPIO 9 | Internal GPIO 14 | Internal GPIO 13 | Internal GPIO 15 |
| TE6 | Internal GPIO 8 | Internal GPIO 10 | Internal GPIO 17 | Internal GPIO 16 | Internal GPIO 18 |

These are **static vendor-configuration facts**, not physical continuity or live GPIO measurements. Detection/LOS cage bindings are consumer-proven; TX-disable pairing rests on `_FX_0`/`_FX_1` labels. The input getters normalize raw-low to 1; the CLI renders presence 1 as Insert and LOS 1 as Normal. This is not approval to copy Linux GPIO polarity flags. TX-disable is separately initialized as an output at raw 0.

The initialization clears SDK offset `0x200` bit 10. Tracing the SDK base and comparing pinned OpenWrt pinctrl identifies physical `0x1b000200`, the GPIO18/USB-LED mux. This was disassembled only. Linux ownership, safe output transitions and electrical behavior remain unverified. GPIO clock 8 is shared across SDA 9/10 and a configured ADT7476 SDA 11: a replacement needs deliberate pin ownership and serialized transfers, not naive independent adapters.

## Why the current reference DTS is not a board definition

Comparison uses the exact OpenWrt commit already built, `19483fa9075686e7a627c777e09c0a24163c8323`:

[Sirivision SR-ST3408F DTS](https://github.com/openwrt/openwrt/blob/19483fa9075686e7a627c777e09c0a24163c8323/target/linux/realtek/dts/rtl9303_sirivision_sr-st3408f.dts).

| Area | Reference definition | Evidence for this spare |
|---|---|---|
| RAM | Two 256 MiB banks, 512 MiB total | Compiled `mem=128M` and about 122 MiB reported usable; physical map unverified |
| Copper port order | SDK ports 0, 8, 16, 20 | Same order; target PHY addresses, lanes and polarity controls independently recovered |
| SFP ports | Four cages on SDK ports 24–27 | Two cages on SDK ports 25 and 26 |
| SFP control/I²C | RTL8231 GPIO expander and hardware I²C master | Internal GPIOs and software I²C |
| Image magic | `0x93000000` | Stock header uses `0x83800000`; active loader path does not check this word; updater acceptance unproved |
| Flash partitions | Specific fixed reference layout | Native 16 MiB default recovered; live overrides/update contract unverified |

The [consolidated evidence table](board-evidence-review.md#static-port-phy-and-serdes-configuration) supplies the target's PHY/SerDes configuration. Do not promote sibling values merely because SDK MAC numbers agree, or confuse configured values with live readback.

## Flash and bootloader limits

The zero-initialized partition records at kernel-file `0x455450` are populated by constructor VA `0x801fbe80` from a flash-size table at file `0x455530`. Its 16 MiB row at `0x455574` supplies the [native default partition map](board-evidence-review.md#native-default-flash-map). This is static default registration, not `/proc/mtd` or a write specification; command-line overrides remain possible. The larger carves are not individual partition sizes.

Loader command-table records resolve to real `boota`, `bootm` and `tftpboot` handlers. `boota` validates/copies the RUNTIME image to `0x81000000`, looks up `bootm` and calls it. The “bootm command is not supported” message is its missing-command fallback, not proof that this dump lacks the handler. `tftpboot` dispatches to the network loader, but network initialization and recovery remain untested.

The active `bootm` format path returns legacy format without checking the header's magic word. This does not establish web-updater acceptance. More importantly, its LZMA wrapper does not enforce the apparent 8 MiB caller limit, and its overlap check runs **after decompression**, then permits legacy single-kernel continuation. The current reference payload overlaps the stock `0x81000000` staging range; actual unread-input corruption was not demonstrated. See the [loader analysis](board-evidence-review.md#loader-and-reference-image-hazard). No command, image or safe address was tested on hardware.

The vendor CLI help exposes operational `show` commands but no Linux-shell or `/proc` reader. The previously identified guarded diagnostic shell path was not entered or bypassed. Consequently, `/proc/mtd`, `/proc/cpuinfo`, `/proc/cmdline`, boot logs, live PHY identifiers and live SerDes configuration remain unavailable through the access used here.

## Reusable read-only procedure

Reuse the existing SSH client and dump-inspection tooling; no new client, dependency or device-side helper is needed for this collection.

Before connecting, compare the device's presented RSA key with the trusted dump public key. Pin the verified public key in an owner-only, untracked known-hosts file. Do not disable host-key checking or commit device keys. The session used:

```sh
ssh -tt -o BatchMode=yes -o HostKeyAlgorithms=+ssh-rsa \
    -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile="$PWD/scratch/board4_known_hosts" admin@<switch IP>
```

Enter the existing credentials only at the vendor prompts. The useful, exercised read-only command set is:

```text
show version
show info
show privilege
show memory statistics
show cpu utilization
show interfaces brief
show interfaces TenGigabitEthernet 1
show interfaces TenGigabitEthernet 5
show fiber-transceiver interfaces TenGigabitEthernet 5
show fiber-transceiver interfaces TenGigabitEthernet 6
show flash
show line
show line console
```

Avoid collecting running/startup configuration or local-user/key listings into committed notes. Do not use cable diagnostics or debug commands as inventory shortcuts.

For offline binary inspection, use GNU MIPS binutils. Apple's `nm` read the symbols and its `objdump` read section bytes, but Apple's disassembler lacked the MIPS target. The existing native OpenWrt cross-toolchain on the build VM supplied the working GNU disassembler. With `BOARD` pointing to the extracted `board_conf.ko` and `MIPS_OBJDUMP` to that cross-toolchain's `mips-openwrt-linux-musl-objdump`, these are the inspected ranges:

```sh
"$MIPS_OBJDUMP" -r -j .data "$BOARD"
"$MIPS_OBJDUMP" -r -j .rodata "$BOARD"
"$MIPS_OBJDUMP" -dr --disassemble=sys_boardModel_init "$BOARD"
"$MIPS_OBJDUMP" -dr --start-address=0x5f0 --stop-address=0xa44 "$BOARD"
"$MIPS_OBJDUMP" -dr --start-address=0x2684 --stop-address=0x273c "$BOARD"
```

Analysis used temporary files under the non-root VM build account and removed them afterward. The vendor modules were not installed, loaded, copied into product source or committed. Reconciled text reports are archived in the private repository; raw binaries and exploratory traces remain outside tracked files.

## Next gate

Superseded: the [live UART and U-Boot validation](uart-uboot-validation.md) captured the console, boot log, MTD map and loader help, and [OpenWrt on the LG510S-4T2XS](openwrt.md) records the RAM boot, the flash install and the recovery path.
