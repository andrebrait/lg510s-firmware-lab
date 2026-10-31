# Independent LG510S board-evidence review — 2026-10-29

## Conclusion and scope

The original six-port allocation survives independent decoding. The previous notes were too pessimistic about what could be recovered before UART: target PHY addresses, SerDes lanes and polarity controls, native partition defaults and loader control flow are present in the dump. Conversely, some GPIO/polarity and loader claims needed correction. None of this establishes physical wiring, a successful target boot or permission to flash.

Initial reviews completed on Opus 5.5, Fable 5.1, GPT-6 Astra and Grok 4.7. After the original Gemini request failed, a fresh Gemini 4 Argon retry completed a bounded core port/SFP review and independently reproduced those allocations and lane associations. All five completed seats sealed raw-evidence notes before reading the pinned documents. Model attribution follows the harness-exposed labels, not independent provider attestation. See the [reports, hashes, deviations and provenance](reviews/2026-10-29-board/README.md). Follow-ups are not extra independent samples: Fable's loader continuation explicitly ran on GPT-6.1-Sol, and the original failed Gemini seat's resumed Sol analysis is excluded from the Gemini count.

This review used local binary reads, CRC/hash checks, independent big-endian ELF relocation decoding and native GNU MIPS disassembly. The parent re-carved the modules image from the original dump and compared the inspected modules byte-for-byte with that extraction. No firmware/module was executed; no switch was contacted, reconfigured, rebooted or flashed. Previous live observations remain separately attributed in the [spare-board investigation](board4-investigation.md).

The subsequent [live UART and U-Boot validation](uart-uboot-validation.md) confirmed the selected profile, native flash map, GPIO bit layout, RTL8264B PHY IDs and SMI routing on the spare unit. The configured MAC 24 PHY does not respond.

## Evidence and selection

The final parent smoke check passed 14 assertions over the three dump hashes, module hashes, BDINFO CRC, safe selector keys, six OEM MAC rows, packed PHY/lane/control rows, native partition source row, both compiled command-line copies, stock LZMA declared length and reference/staging range intersection. Control-flow interpretations additionally use native disassembly; these assertions are not hardware tests.

All three programmer reads have SHA-256 `7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48`. Saved BDINFO's stored and computed CRC32 both equal `0x89e491e2`. Exact allowlisted key matching finds `boardmodel=RTL9303_8264B_2XGE`, `bootcmd=boota`, `bootdelay=1`, `baudrate=115200`; `idType`, `boardid` and saved `bootargs` are absent. No full environment or private configuration is reproduced.

`hwp_probe` can prefer forced selection, then name/numeric environment selection. The compiled forced discriminator is disabled (`rtcore .data+0x764`, value 2); the saved keys take the name path to profile `0x008de842` at `.data+0x33dc`. The profile points to switch descriptor `.data+0x3434`. This establishes the expected saved/default selection, not a live pointer read. OEM `Board Value: 1` is a different namespace.

In `board_conf`, the matching `boardMap` row is `.data+0x160` (symbol base `0xc0`), selecting the six-row OEM port table and two-cage fiber tables. `sys_boardModel_init` also reads `bootmsg` from MTD index 2 under the native default map; it does not replace the SDK board ID. Duplicate local `$LC0` symbols were resolved by relocation symbol index/addend, not by name.

## Static port, PHY and SerDes configuration

These are vendor-requested settings, not measured bus routing, PHY identification or register readback. SMI selector numbers are not automatically Linux MDIO bus numbers. TX/RX values below are vendor SerDes inversion controls, not translated DT flags.

| CLI port | SDK MAC | Vendor SMI selector | Configured PHY address | SerDes table index → lane | TX / RX invert |
|---|---:|---:|---:|---|---|
| TE1 | 0 | 0 | 0 | 0 → 2 | 0 / 1 |
| TE2 | 8 | 0 | 1 | 1 → 3 | 1 / 0 |
| TE3 | 16 | 0 | 2 | 2 → 4 | 0 / 1 |
| TE4 | 20 | 0 | 3 | 3 → 5 | 1 / 0 |
| TE5 | 25 | ff sentinel | ff sentinel | 5 → 7 | 0 / 0 |
| TE6 | 26 | ff sentinel | ff sentinel | 6 → 8 | 0 / 0 |

Proof anchors:

- `board_conf .rodata+0x1f00`, 32-byte rows: formatter loads user port at +4 and SDK MAC at +12. The six rows, not the larger SDK descriptor, define exposed front-panel ports.
- `rtcore .data+0x3434+20`, 20-byte rows: `hwp_parsedInfo_show` labels `mac_id`, `phyIdx`, `smi`, `phy_addr`, `sdsIdx`. `_rtl9300_smiAddr_init` in `rtk` reads original row byte +2 at `0x250c4` and calls `_rtl9300_port_smiSel_set`; selector 0 is consumed initialization data, not merely a formatter label.
- `rtcore .data+0x3949`: `02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff 00`. The first byte is the lane; the second combines mode family and low polarity bits. An index is not a lane.
- `rtk:dal_longan_construct_macConfig_init` tests control bit 1 for page 6/register 2 bit 13 and control bit 0 for bit 14. `phy_9300_polar_get` and the TX/RX-labelled `dal_phy_polar_set` diagnostic identify these as RX and TX respectively. Mode-family encodings are `0x70` for the copper entries and `0x08` for the fiber entries; this review does not substitute unproved Linux mode names.
- `rtcore .data+0x39c4` describes one RTL8264B four-port PHY group (type 36, base MAC 0). A second descriptor names RTL8261BE (type 35, base MAC 24); extra MACs 24/27 are absent from the OEM six-port table. Their presence in a reusable SDK profile does not prove fitted extra hardware or additional usable ports.

Analog calibration, PHY-side settings, live IDs, patch readiness and Linux binding translation remain unverified.

## Static SFP configuration and limits

The [cage GPIO table](board4-investigation.md#sfp-wiring-recovered-from-the-matching-static-configuration) is unchanged numerically, but confidence differs by role:

- Software GPIO I²C uses internal clock 8 and SDA 9/10, EEPROM address `0x50`, delay field 20 (unit not established). Connection type 2 selects software I²C; it is not hardware controller 2.
- Detection records bind TE5 to presence GPIO 14/LOS 13 and TE6 to presence 17/LOS 16. Linear numbering is bank `pin >> 3`, bit `pin & 7`; internal device selector 0 does not mean every pin is bank A.
- The getters normalize raw-low to 1. The CLI consumes presence 1 as Insert and LOS 1 as Normal. Neither an enum called LOS nor a normalized 1 alone establishes a Linux active-low flag.
- GPIO 15/18 are labelled `TX_DIS_FX_0/1`, initialized as outputs at raw 0 with the vendor normal/active-high flag. Pairing 15→TE5 and 18→TE6 is **[INFERENCE]** from the suffix/grouping, weaker than the direct detection-table bindings. No later TX-disable consumer was identified; presence/OE is not TX-disable state.
- Target initialization clears SDK offset `0x200` bit 10. Tracing `ioal_init`'s `0xbb000000` mapped base identifies physical `0x1b000200`; pinned OpenWrt `rtl930x.dtsi` independently labels bit `0x400` as the GPIO18/USB-LED mux. No write was executed.
- The configured ADT7476 (SDA 11, sharing clock 8 with the cages) is not fitted; see the [fan note](openwrt.md#fan). Linux pin ownership and serialized access need deliberate design; multiple independent GPIO-I²C adapters cannot simply be assumed equivalent to the vendor path.

The pinmux cross-reference is pinned to OpenWrt `19483fa9075686e7a627c777e09c0a24163c8323`: [rtl930x.dtsi](https://github.com/openwrt/openwrt/blob/19483fa9075686e7a627c777e09c0a24163c8323/target/linux/realtek/dts/rtl930x.dtsi). It corroborates the named bit function, not the board's electrical state.

## Native default flash map

The stock kernel's zero destination records at file `0x455450` are populated by constructor VA `0x801fbe80`. A five-row flash-size table starts at file `0x455530`; the 16 MiB row is `0x455574`, 17 big-endian words. This is the decoded native default, not a live `/proc/mtd` capture or an installation contract. Command-line partition overrides remain possible.

| Default partition | Offset | Size |
|---|---:|---:|
| LOADER | `0x000000` | `0x0e0000` |
| BDINFO | `0x0e0000` | `0x010000` |
| SYSINFO | `0x0f0000` | `0x010000` |
| JFFS2 CFG | `0x100000` | `0x100000` |
| JFFS2 LOG | `0x200000` | `0x100000` |
| RUNTIME | `0x300000` | `0xc00000` |
| OEMINFO | `0xf00000` | `0x100000` |

The earlier 1 MiB loader/environment and 2 MiB JFFS2 regions were aggregate extraction windows, not separate native partition sizes. Keep all stock identity, configuration and key areas protected. No repartitioning or write recipe follows from this table.

The compiled stock command line contains `console=ttyS0,115200 mem=128M` at kernel-file offsets `0x47f6cc` and `0x4806d8`, consistent with the previously observed 125196 KB total. Physical RAM geometry, bootloader reservations and safe free ranges are still unknown.

## Loader and reference-image hazard

The loader's command records resolve to actual handlers; generic unsupported-command strings are not an adequate availability test. Raw-binary translation is `file offset = VA - 0x83f00000 + 0x5030`.

| Command | Record file offset | Handler VA | Static behavior |
|---|---:|---:|---|
| `boota` | `0xd0ec8` | `0x83f02858` | Reads RUNTIME, validates header/partition bounds, copies header+payload to `0x81000000`, finds and invokes `bootm` |
| `bootm` | `0xd0ef8` | `0x83f03394` | Legacy image parsing, validation/decompression and OS dispatch |
| `tftpboot` | `0xd10d8` | `0x83f05530` | Dispatches network loader with protocol argument 3 |

This is static handler presence, not tested console/network recovery. `boota`'s “bootm command is not supported” message occurs only when command lookup returns null.

The format routine at `0x83f08c1c` always returns legacy format. The adjacent identity routine is `genimg_get_image`, not a magic accessor. The active `bootm` path does not compare the `ih_magic` word. Stock `0x83800000` is therefore recorded as an unchecked header value in this path, **not** a staging address or proof that a GUI updater accepts any replacement magic. Header CRC, architecture/type/compression and conditional payload CRC checks remain distinct.

A more important risk was recovered:

1. `bootm_load_os` passes a nominal 8 MiB output length to the LZMA wrapper.
2. The wrapper at `0x83f0f738` never reads that incoming limit. It derives its bound from the LZMA-alone declared size at source bytes +5..12, then writes the processed length back. Stock declares 11,336,112 bytes, already over 8 MiB. An unknown-size sentinel becomes `0xffffffff`, not a RAM limit.
3. Only **after decompression**, `0x83f02dbc..0x83f02dd8` checks `load < blob_end && blob_start < load_end`, returning -2 on overlap. The valid legacy single-kernel caller continues despite -2; this is not preflight protection.
4. The current Sirivision reference output range is `[0x80100000, 0x812f86b6)`, intersecting stock staging at header `0x81000000` / compressed payload `0x81000040`. It can overwrite unread compressed input; actual corruption for this exact stream depends on decoder consumption/write progression and was not demonstrated. Its ELF+BSS extends to `0x8143beec`, beyond the decoded payload boundary considered by this check.

Being below a nominal 128 MiB ceiling is insufficient. No safe alternate address is inferred, and no target execution is approved. Exact disassembly anchors and the corrected reasoning are in the [attributed loader follow-up](reviews/2026-10-29-board/fable51/loader-overlap-followup.md).

## Reconciliation rather than majority vote

| Disputed claim | Adjudication | Action |
|---|---|---|
| PHY/SerDes details require UART before anything can be written | Static requested values are recoverable; live behavior is not | Record target values now; retain execution gate |
| SerDes descriptor contains no polarity | False; packed low bits are consumed and TX/RX-labelled | Supersede Opus's initial claim with its correction |
| OE is TX-disable; LOS 1 means asserted loss | False for these consumers | Separate presence, LOS normalization and output setup |
| SYSINFO selects another board / parsed value discarded | False; relocation-indexed key is `bootmsg`, copied into global structure | Correct selection narrative |
| SMI field is just printed / necessarily Linux bus 0 | Both too strong; another consumer programs vendor selector 0 | Record vendor intent, not measured/Linux routing |
| Zero partition records mean no recoverable native map | Incomplete analysis; constructor and source table are present | Add static default map, preserve runtime caveat |
| Unsupported strings establish missing `bootm`/TFTP | False inference; command handlers exist | Trace handlers; keep recovery untested |
| 8 MiB caller value or overlap check protects LZMA load | False for this path | Record post-write hazard; do not boot reference image |

The initial reviews are preserved, not rewritten to look correct after the fact. Agreement on one dumped configuration is not independent hardware validation. No further review cycle is needed for the already-resolved documentary disagreements; physical uncertainties remain explicit instead of being voted away.

The successful Gemini retry found no different core mapping. Its refusal to infer PHY/polarity semantics within that bounded scope is not contradictory evidence against the separately traced consumers above. Its generic TX-disable cage table remains subject to the same weaker label-inferred pairing qualification. The retry also ran analysis-only mutations outside its assigned scratch despite the no-tests/scratch-only contract; those are not accepted as repository tests or hardware proof.

## What can proceed and what cannot

**Status (2026-10-31):** the candidate described below was built, validated on hardware and installed on the spare unit; see [OpenWrt on the LG510S-4T2XS](openwrt.md). This section is kept as written before that work.

A separately labelled, unvalidated LG510S candidate can use the six exposed MACs, recovered PHY/lane/control values, internal-GPIO SFP design and stock memory/partition evidence as inputs. It must not copy the reference's 512 MiB declaration, four cages or RTL8231 wiring. Exact OpenWrt binding/driver semantics still need checking before translating vendor controls into a DTS.

Before execution: establish UART voltage/pinout and recovery, actual RAM/reservations/partition overrides, a non-destructive staging/decompression plan, live PHY readiness, GPIO electrical behavior and safe output transitions. Before installation: also prove programmer write/restore, update boundaries and preservation of per-unit data. QEMU cannot establish these hardware properties.

No product code, bootloader setting or switch state was changed by this review. Licensing/redistribution, full driver correctness, traffic/offload and the earlier emulator test counts were not independently re-tested here.
