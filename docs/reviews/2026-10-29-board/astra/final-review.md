# LG510S independent review — GPT-6 Astra

## Provenance / verdict

Actual seat: **openai-codex/gpt-6-astra**. Reviewed all 555 lines of the four assigned documents at `6f7d67b6fd378981874d354b512495b99c31d5bc` only after saving and hashing `scratch/blind-notes.md`:

`c6f13976f083113e5730cdc6bf74242dba86c13005b75a543ee35328daed95b5`

**Verdict: the documented six-port and SFP pin maps survive independent decoding. The evidence is materially richer than the documents report: copper MDIO addresses, actual SerDes lanes, vendor polarity controls and a native flash-size partition table are recoverable. None establishes live wiring or authorizes boot/flash.**

Executed probes: SHA-256 of all three full reads and inspected modules; own big-endian ELF symbol/section/REL decoding; native MIPS readelf/objdump via the supplied existing-VM transport; CRC32 of saved environment and vendor image; LZMA decompression compared byte-for-byte with the existing kernel carve. No firmware/module execution. No switch access, builds, lint, tests, formatters or mutations. Codegraph was unavailable for the unindexed raw-artifact directory; native tools succeeded. No substitute model or extra agents used.

Full-read SHA-256 independently matched `7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48`; board_conf and rtcore hashes matched the contract. Additional inspected binaries: ski `ab5244c2058ef8b6ab04ccf0cc5370b8a068ab931c7a063f2d26ede0a69b9cfb`; rtk `d1a4b5655b8cf8b0ce0a26f74daf0c8fb7b03897c31e5693498d9c981c4f1988`; loader/kernel hashes and detailed raw words are in blind notes. Three matching reads and multiple vendor tables are not independent physical corroboration.

## Independent port/PHY/SerDes map — STATIC, conditional on profile selection

| CLI | Logical index | SDK MAC | SMI / MDIO address | PHY index | SDS index → lane | Vendor TX/RX polarity controls |
|---|---:|---:|---|---:|---|---|
| TE1 | 0 | 0 | 0 / 0 | 0 | 0 → 2 | 0 / 1 |
| TE2 | 1 | 8 | 0 / 1 | 0 | 1 → 3 | 1 / 0 |
| TE3 | 2 | 16 | 0 / 2 | 0 | 2 → 4 | 0 / 1 |
| TE4 | 3 | 20 | 0 / 3 | 0 | 3 → 5 | 1 / 0 |
| TE5 | 4 | 25 | ff sentinels: no external PHY | ff | 5 → 7 | 0 / 0 |
| TE6 | 5 | 26 | ff sentinels: no external PHY | ff | 6 → 8 | 0 / 0 |

Proof anchors:

- `board_conf.ko`: `.rodata+0x1f00`, six 32-byte rows; formatter `.text+0x940..0x9ac` distinguishes user/unit/physical-port fields. `ski:sys_physic_portview_init+0x1b8..0x268` builds zero-based logical ordinals from those rows. All four copper ports reference **one RTL8264B PHY descriptor**, not four independently identified chips.
- `rtcore.ko`: profile `.data+0x33dc`, ID `0x008de842`; R_MIPS_32 at `.data+0x3418` resolves switch descriptor `.data+0x3434` (file `0x33614`). Port rows start descriptor+20, stride20. `hwp_parsedInfo_show` `.text+0x151d8..0x1523c` explicitly prints `mac_id`, `phyIdx`, `smi`, `phy_addr`, `sdsIdx`. Copper first words: `00000000 08000001 10000002 14000003`; these are packed fields, not four MDIO addresses equal to MAC numbers.
- SerDes array `.data+0x3949`: `02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff 00`. `_hwp_serdes_parse` at `0x13ec0`, `0x13f88..0x13fa0` proves 2-byte rows and the **index-to-lane indirection**. Using indices0..3/5/6 as lanes is wrong.
- PHY array `.data+0x39c4`: type36/port-count4/base-MAC0, then type35/count1/base-MAC24. `_phyType_name` relocations at `.rodata+0xbac/+0xbb0` resolve type35/36 to RTL8261BE/RTL8264B. Extra SDK MAC24/27 records are absent from the front-panel board table; do not expose them as additional cages.
- **Post-seal additional decoding:** `rtk:dal_longan_construct_macConfig_init` at `0x132bc4..0x132c70` maps descriptor flag bit1 to SerDes page6/register2 bit13 and page0/register0 bit9; flag bit0 to bits14/8. `phy_9300_polar_get` at `0x1dad0..0x1dae0` plus its RX/TX inconsistency diagnostics identifies the former as RX and latter TX. `dal_phy_polar_set` at `0x15dcf4..0x15dd20`, format string `.rodata.str1.4+0x10c88`, independently labels struct+0 TX and +4 RX. Hence the table above reports vendor control values; do not blindly translate enum1 into a Linux binding without checking that binding. Blind notes already sealed the raw flags/lane map but explicitly left TX/RX naming unresolved.

These are requested initialization values, not live registers, analog calibration or PCB pair-continuity measurements.

## Independent SFP mapping — STATIC

| Cage | Software I2C device | SCK | SDA | MDO/presence | LOS | TX-disable |
|---|---:|---|---|---|---|---|
| TE5 / LPort4 | 0 | INT8 / B0 | INT9 / B1 | INT14 / B6 | INT13 / B5 | INT15 / B7 |
| TE6 / LPort5 | 1 | INT8 / B0 | INT10 / B2 | INT17 / C1 | INT16 / C0 | INT18 / C2 |

EEPROM address `0x50`; delay field20, unit unresolved. Optical rows `.rodata+0x3888`, stride52, have device0/1 and **connection type2 = software GPIO I2C**, not hardware controller2. Formatter `board_conf_dump+0x538..0x760` and `rtcore:r9300_i2c_dev_init` at `0x5958..0x5988` confirm dispatch to software I2C.

Detection relocations are `boardGpio_930x + {0x50c,0x4b0,0x620,0x5c4}`: each points to **92-byte row+4**, respectively rows14,13,17,16. `board_gpio_init` target branch `0x2684..0x2730` supplies internal-device selector0 and linear pins; TX-disable is separately initialized as an output. `drv_generalCtrlGPIO_dataBit_get` at `0xdd38..0xdd44` splits linear pin into bank=`pin>>3`, bit=`pin&7`; `rtl9300_gpio_dataBit_get` reads SoC offset`0x330c` with bank bases0/8/16. Thus internal-device0 does NOT mean all pins are bank A.

Software normalization is recoverable but not sufficient for an electrical polarity claim: input helper leaves row+0x30 zero; `ski:board_fiber_oeStatus_get` at `0x77174..0x77180` and `board_fiber_losStatus_get` at `0x77298..0x772a4` then return1 for a raw-low input. Do not equate that returned1 with physical LOS assertion without confirming the API semantics and actual circuit. Complete TX-disable drive policy and replacement-kernel pinmux remain unverified.

## Required documentary corrections / additions

1. **Complete the selection chain before treating the map as a target specification** — `docs/board4-investigation.md:59-65`; `docs/firmware.md:40-51`.
   `hwp_probe` tries a forced selector before `ioal_param_hwpIdKey_get`; that reader selects `boardmodel` by name OR `idType=integer`/`boardid` numerically. The compiled forced selector at rtcore `.data+0x764` is disabled (type2), but `hwp_forceProfile` can replace it. `hwp_identifier_cmp` at `0x16890` implements both comparisons. Saved allowlisted boardmodel matches; live active pointer and non-allowlisted selector values were not examined. Document the conditional path rather than implying boardmodel alone selects it. Existing separation from OEM Board Value1 is correct. Clarify “quad RTL8264B” as a four-port descriptor, not four chips.

2. **Replace undifferentiated unknown PHY/SerDes wording with the static table above** — `docs/board4-investigation.md:91,97,161`; `docs/project-reassessment.md:63`.
   The MDIO0..3, lanes2..5/7..8 and polarity controls come from the exact target profile and its consumers, not a sibling DTS. Live verification remains a gate. Consequence of omitting the distinction: needless UART dependency for recoverable candidate work, or importing sibling lane/polarity values despite having target evidence.

3. **Add the native-size partition table; zero destination records are not the end of the analysis** — `docs/board4-investigation.md:65,95,101`; supplement `docs/firmware.md:17-26`.
   Kernel file`0x455574` contains the 16MiB alternative in a five-row,68-byte table at`0x455530`. Function VA`0x801fbe80` selects by flash size and populates the previously zero32-byte records at file`0x455450`; jump table file`0x3719b0` and stores through VA`0x801fc204` establish the mapping. Default registration is VA`0x80474ed4..0x80474ee4`; command-line partitions can override it.

   | Native default name | Offset | Size |
   |---|---:|---:|
   | LOADER | `0` | `0xe0000` |
   | BDINFO | `0xe0000` | `0x10000` |
   | SYSINFO | `0xf0000` | `0x10000` |
   | JFFS2 CFG | `0x100000` | `0x100000` |
   | JFFS2 LOG | `0x200000` | `0x100000` |
   | RUNTIME | `0x300000` | `0xc00000` |
   | OEMINFO | `0xf00000` | `0x100000` |

   This is a **decoded static default**, still not `/proc/mtd` or an upgrade/write specification. Under this default, index2 is SYSINFO; `sys_boardModel_init` reads `bootmsg` there, not the SDK board ID. `rt_util_flashEnv_get` independently requests BDINFO by name. The 1MiB loader carve and 2MiB JFFS2 carve are not native partition sizes.

4. **Enrich RAM/polarity qualifications without removing them** — `docs/board4-investigation.md:25,78,90,161`; `docs/project-reassessment.md:63`.
   Kernel bytes at file`0x47f6cc` and`0x4806d8` contain `console=ttyS0,115200 mem=128M`. Record this as compiled stock configuration corroborating the supplied125196KB live total, not physical DRAM geometry or a safe staging range. Add software GPIO normalization and vendor SerDes controls above; keep physical polarity, Linux bindings and calibration unverified.

No wrong six-port mapping, GPIO relocation error or software-I2C/controller confusion was found in the pinned notes. Their no-boot/no-flash warning is justified.

## Other confirmations and limits

Vendor header at flash`0x300000`: magic`0x83800000`, headerCRC`0xa80f0d16`, payload`0x7eae10`, load`0x80000000`, entry`0x803345b0`, payloadCRC`0x6f51b869`. Both CRCs match. LZMA expands to11,336,112 bytes identical to the kernel carve. Saved BDINFO CRC matches`0x89e491e2`. These are integrity/format probes, not boot tests.

Loader strings include boota, loadb/loady/TFTP help AND unsupported bootm/tftp diagnostics. No usable RAM-loading command established. Documented register`0x200` bit10 clear also matches the disassembly; its full meaning remains unknown and it was never executed.

**Live-observed only by supplied contract:** versions, six CLI labels, two10G link snapshots, total memory, OEM Board Value and vendor-CLI-only access. I did not re-observe these. **Unknown:** live HWP selector, actual PHY IDs, current SerDes/polarity/calibration state, electrical SFP wiring, physical RAM reservations, installed MTD overrides, loader acceptance and switching/offload behavior.

## Per-file verdict — four review lenses

| File (complete scope) | Contract conformance | Correctness / unsafe interpretation | Test honesty | Ponytail |
|---|---|---|---|---|
| board4-investigation.md (161 lines) | Independent main mappings confirmed | Amend selection and recoverable static PHY/flash facts; preserve hardware caveats | Static/live distinction is honest; this seat did not repeat device observations | Extend existing tables; no new tooling needed |
| firmware.md (83 lines) | Header/payload/environment claims independently supported | Add native-default partition split and four-port PHY clarification | No boot/recovery success implied | Keep carve table, add one cross-reference to native map |
| project-reassessment.md (73 lines) | Scope and no-install boundary appropriate | Update line63 to separate recovered configuration from live validation | Prior application/source assertions not re-exercised | Small RAM-only slice remains appropriate; no UI work needed for this evidence |
| offline-validation.md (238 lines) | Clearly not hardware acceptance | No contradiction found in its hardware limits | Reports failures and emulator boundaries explicitly; exact counts/results not independently audited here | No additional emulator/framework work justified by this binary review |

Scratch-mutation lens: **not executed**, because the assigned contract explicitly prohibits tests/mutations and allows writes only under this seat’s scratch; no mutation coverage or QEMU reproduction is claimed. Four documentation files—not unrelated product code—were the assigned review surface.

## Candidate boundary

An explicitly unvalidated LG510S candidate can now record six exposed MACs, copper SMI0 addresses0..3 with RTL8264B descriptor, SerDes lane indirection and vendor polarity controls, the internal-GPIO/software-I2C SFP map, nominal128MiB stock configuration and the16MiB native-default partition inventory. Keep stock identity/config/key regions protected. Do not expose extra SDK ports or copy the reference512MiB/expander/four-SFP definition.

Still require hardware/boot evidence before execution: selected runtime profile, PHY identities/patch readiness, analog calibration, SFP electrical levels/polarity/pinmux, actual RAM/reservations/MTD and a recoverable loader path. Declined to judge licensing, unrelated application bugs, prior test counts, live electrical wiring or installability from these bytes.

Not checked: devices, builds/tests/mutations, peer reports, private configurations, boot/flash, or full driver correctness.
Risk: static target evidence is suitable for a labelled candidate and validation plan—not boot or flash approval.


## Post-seal supplement — newly authorized selector keys

After Main explicitly expanded the safe environment allowlist to include `idType` and `boardid`, I inspected only those keys and the original allowlisted keys. The sealed `blind-notes.md` was not changed. This supplement supersedes the earlier final-report limitation that saved selector values were not inspected.

Executed probe: exact NUL-delimited key matching in saved BDINFO bytes `uboot.bin[0xe0004:0xf0000]`, with separate selector matching in the compiled loader region before `0xe0000`. No complete environment or non-allowlisted values were emitted.

| Selector / boot field | Saved BDINFO result | Compiled loader selector result |
|---|---|---|
| `idType` | Absent | Absent |
| `boardid` | Absent | Absent |
| `boardmodel` | `RTL9303_8264B_2XGE` at `0xe0014` | Same at `0xc7d16` |
| `bootargs` | Absent | Not re-examined in this supplement |
| `bootcmd` | `boota` at `0xe0032` | Not re-examined in this supplement |
| `bootdelay` | `1` at `0xe0040` | Not re-examined in this supplement |
| `baudrate` | `115200` at `0xe0004` | Not re-examined in this supplement |

**Refined static conclusion:** with the compiled forced selector disabled (rtcore `.data+0x764` discriminator2), the saved environment takes the name-selection branch: missing `idType` leaves discriminator0, then `ioal_param_hwpIdKey_get` reads `boardmodel` (`.text+0x18684` branches to `0x1873c`, then `0x18748..0x18758`). `hwp_identifier_cmp` compares that exact name, selecting profile `0x008de842`. There is no saved numeric override in this dump.

Finding1 therefore becomes a completeness correction to document the actual precedence and the absence of numeric override, not an unresolved saved-selector conflict. Forced selection remains a code capability; live state or loader modification of the environment was not observed. No change to any port/PHY/SerDes/GPIO finding or no-boot/no-flash verdict.

Not checked: live runtime profile, device environment changes, or boot behavior.
Risk: the saved default selection is now substantially better established, but static evidence still does not certify live hardware state.


## Post-seal reconciliation — encoded SMI versus effective routing

The port table should label its field **encoded SMI selector / configured PHY address**, not an observed MDIO bus or Linux bus number. TE1..TE4 encode selector0 and addresses0..3. No live controller readback or physical routing test was performed.

Targeted additional native disassembly supplies a consumer beyond the formatter:

- `rtcore:_hwp_port_parse` at `.text+0x132f0..0x13300` copies row byte+3 into the parsed PHY-address array. The lack of a byte+2 read in that parser does not establish that the field is unused elsewhere.
- `rtk:_rtl9300_smiAddr_init` at `.text+0x250f8..0x25120` reads each parsed PHY address and calls `_rtl9300_port_phyAddr_set`, skipping ff. At `0x250a8..0x250dc` it separately retrieves the original MAC-indexed port-descriptor pointer, explicitly loads **byte+2** (`0x250c4: lbu s1,2(t8)`), skips ff, and passes that value to `_rtl9300_port_smiSel_set`.
- `_rtl9300_port_smiSel_set` at `0x24604..0x24674` validates selector<4, selects register enum373 for MAC<16 or enum374 for MAC16..27, indexes the per-MAC field table at `.rodata+0x690`, and calls `reg_field_write` with the supplied selector. `rtl9300_init` references `_rtl9300_smiAddr_init` at relocation offsets `0x254c8/0x254cc/0x255d4`.

Thus selector0 is **statically requested routing configuration**, not merely a printed label; successful programming, live selector state, controller-pin wiring and Linux MDIO bus numbering remain unverified. Candidate wording should be “vendor SMI selector0; configured PHY addresses0..3,” not an unconditional “MDIO bus0.” MAC, PHY-address and SerDes-lane numbers are unchanged.

GPIO distinctions retained: MDO/OE getter normalization is not TX-disable drive policy; a LOS getter returning1 on raw-low does not by itself prove electrical LOS assertion or Linux `GPIO_ACTIVE_LOW`. No Linux GPIO or SerDes polarity translation is approved here.

Executed: targeted static disassembly and relocation inspection only, saved under `scratch/`; no device or firmware execution, tests or mutations. Blind notes unchanged.
