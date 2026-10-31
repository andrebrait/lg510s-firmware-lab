# Independent blind notes — LG510S core mapping

Phase 1. These notes were written before opening any pinned repository documentation, decoded table, or peer report. Scope deliberately restricted to core ports/MACs and SFP I2C/GPIO roles. No firmware executed or hardware contacted.

## Provenance and inputs
- Seat requested: Gemini4Argon retry. Harness-provided runtime model: `google-antigravity/gemini-4-argon`. This is the runtime label supplied in this session, not independently attested provider internals; no substitution notification is visible.
- Assigned checkout HEAD observed with `git rev-parse --short HEAD`: `6f7d67b`; `scratch/` confirmed ignored by `.gitignore:6`.
- Locally hashed board_conf.ko: `027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70`; rtcore.ko: `d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4`; ski.ko: `ab5244c2058ef8b6ab04ccf0cc5370b8a068ab931c7a063f2d26ede0a69b9cfb`; board.ko: `cf410968f4842a132c135500d479c0938f752535f2a347fecebb74dbe32baf66`.
- Full first dump hashed to `7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48`. Only exact allowlisted environment prefixes were printed. `boardmodel=RTL9303_8264B_2XGE` occurs at flash+0xc7d16 and +0xe0014. The former is also potentially a compiled default, not independent runtime evidence. Other copies not hashed in this bounded review.
- Python standard-library ELF32 big-endian section/symbol/REL decoding written independently in scratch/inspect_elf.py; R_MIPS_32 resolution uses actual symbol index, S plus in-place addend, and preserves section identity. `mips-binutils.py` explicitly supplied transport helper used only to run native existing MIPS objdump/readelf on analysis VM. No prior board interpretation read. Native complete .text/.init.text disassembly retained as scratch/{board_conf,rtcore,ski}-disassembly.txt. board.ko symbol table inspected; it is not the substantial fiber consumer (ski.ko is).
- Two initial inline Python quoting attempts failed with SyntaxError; corrected using saved scripts. Native binutils succeeded. Initial exploratory lookup-table labels in inspect_details.py are not authoritative: actual formatter stack bases, not those script headings, determine meaning.

## Selection chain — static evidence, not active HAL capture
- rootfs/etc/rc loads rtcore, rtk, rtdrv, board_conf, then ski (with optional /mnt/ski_param), then board. No module loading performed here.
- rtcore `ioal_param_hwpIdKey_get` .text+0x18620: selector literals resolved through LO16 symbol indices #321 at +0x18670 (`idType`), #322 at +0x18690 (`integer`), #323 at +0x186d0 (`boardid`), #324 at +0x1874c (`boardmodel`). Integer mode uses boardid; otherwise boardmodel string. No forbidden environment values were inspected.
- `hwp_probe` +0x16df0: calls hwp_forcedProfile_get first (+0x16e90..16ea0), then ioal_param_hwpIdKey_get if no forced identifier, then hwp_profile_find. `hwp_identifier_cmp` +0x16890 compares type 0 strings (44-byte limit) or type 1 numeric IDs. `hwp_forceProfile` +0x1704c can change forced identifier. Static forced identifier .data+0x764 is type2, string `Default None`, ID0, hence not a force at initialization; .data+0x730 is special type2 `default` ID999. Runtime force possible; active selection not directly observed.
- rtcore .data file base 0x301e0. hwp_hwProfile_list .data+0x824 contains raw addend0x33dc with R_MIPS_32 symbol#7 (section .data, S=0), resolving .data+0x33dc, not a guessed symbol name. Header there is type0, name `RTL9303_8264B_2XGE`, ID at .data+0x340c `0x008de842`=9300034. Profile +0x3c at .data+0x3418 has R_MIPS_32 symbol#7 A=0x3434, pointing to switch descriptor .data+0x3434. Header +0x38 count=1.
- board_conf `sys_boardModel_init` .text+0x318..328 reads hwp_myHwProfile->+0x30 ID; matches 576-byte boardModelConfTbl records. ID9300034 at .rodata+0x900, description at +0x93c `RTL9303-4XGE-2XGEF`. `board_conf_get` +0xd04 searches 32-byte boardMap records by sys_boardModelId_ret, caches selected record.
- board_conf .data file base0x8980; boardMap symbol#359 .data+0xc0. Target record .data+0x160 ID0x008de842; reloc at +0x164 -> symbol#145 portConf_9303M4XC2XF S=.rodata+0x1f00,A=0; +0x168 -> symbol#312 fiberConf_9303M4XC2XF S=.rodata+0x387c,A=0. Numeric OEM Board Value1 is NOT SDK ID9300034.

## Independent port allocation
board_conf .rodata file base0x2c90; symbol#145 .rodata+0x1f00 size224 = six rows plus sentinel, stride32. Eight BE32 words per row: type, user port, SDK unit, SDK port, media, speed raw enum, duplex enum, attributes. The native formatter .text+0x910..9c4 advances32, prints user from +4, unit +8 (in parentheses), port +12; type table3 =10G, media0=Copper /1=Fiber. It checks +8==0xffff sentinel. ski board_conf_port_get +0x70e10..70e5c independently uses +8 and +12 as pair of lookup inputs, copying rest of row.

| User label | Row .rodata | Raw eight words (decimal) | SDK unit/port | Media |
|---|---|---|---|---|
| TE1 | 0x1f00 | 3,1,0,0,0,15,2,1 | 0/0 | copper |
| TE2 | 0x1f20 | 3,2,0,8,0,15,2,1 | 0/8 | copper |
| TE3 | 0x1f40 | 3,3,0,16,0,15,2,1 | 0/16 | copper |
| TE4 | 0x1f60 | 3,4,0,20,0,15,2,1 | 0/20 | copper |
| TE5 | 0x1f80 | 3,5,0,25,1,15,2,0 | 0/25 | fiber |
| TE6 | 0x1fa0 | 3,6,0,26,1,15,2,0 | 0/26 | fiber |

TE labels follow supplied six-port CLI observation and user-port numbering; not a physical continuity or runtime register measurement. These port numbers are not MDIO addresses or SerDes lanes.

rtcore switch descriptor starts .data+0x3434, port list +0x14, stride20. First bytes at .data+0x3448/345c/3470/3484/3498/34ac/34c0/34d4 are 0,8,16,20,24,25,26,27 (plus sentinel). Therefore there is an extra static SDK MAC24 entry NOT exposed by this board_conf six-port table; do not naively map TE5 to SDK row index4/MAC24. `_hwp_port_parse` +0x12f68..12f94 finds first-byte0xff terminator, advances20. No consumer semantics inferred solely from array ordering.
- `_hwp_serdes_parse` +0x13e94..13f48 uses switch+0x515 two-byte descriptors and maps descriptor first-byte as physical lane; +0x14004 reads per-port word+4 as SerDes descriptor index. Profile raw indices0..7 at per-port +4 map MAC0/8/16/20/24/25/26/27 to lane2/3/4/5/6/7/8/9. Descriptor bytes at .data+0x3949: `02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff`. This is STATIC lane association; attributes0x72/71/70/08 NOT yet decoded as polarity/mode, no physical calibration claim.
- Per-port bytes+1/+2/+3 for first four =0/0/0,0/0/1,0/0/2,0/0/3. Actual external PHY MDIO address/poll programming not established here. No claim that SDK port8 implies MDIO8.

## SFP I2C and detect/GPIO
- fiberConf symbol#312 .rodata+0x387c words: count2; +4 relocation symbol#176 S=.rodata+0x38f0 A0 (detect); +8 symbol#335 S=.rodata+0x3888 A0 (optical).
- Detect rows stride28 .rodata+0x38f0 and0x390c: `(4,1,0,1,1,ptr,ptr)` and `(5,1,0,1,1,ptr,ptr)`. Formatter +0x11d8..1228: fields logical port, presence mechanism, media-change mechanism, OE enabled, LOS enabled, OE descriptor, LOS descriptor; lookup .rodata+0x1ac0 has None/OE/LOS. Thus logical ports4/5, present selector1=OE; media-change0=None; both OE/LOS enabled. This is not sampled presence/LOS. OE role uses module-detect input, NOT TX-disable/output-enable merely because acronym resembles one.
- Exact detect relocations R_MIPS_32 symbol#227 (boardGpio_930x S=.data+0x670): .rodata+0x3904 A0x50c -> .data+0xb7c; +0x3908 A0x4b0 -> .data+0xb20; +0x3920 A0x620 -> .data+0xc90; +0x3924 A0x5c4 -> .data+0xc34. Each addend is 92*n+4, so descriptor points AFTER the table entry ID: indices14,13,17,16 respectively. Omitting +4 changes field meanings.
- boardGpio_930x size13156=143*92 at .data+0x670. File contains ID-only empty entries; fields are populated by board_gpio_init, so decoding raw zero fields as wiring is WRONG. Jump table .rodata+0x480c for ID9300034 resolves .text+0x1a8c: selects boardGpio_930x, count32. +0x1aec branches ID9300034 to0x2684.
- .text+0x2684..2738 configures table indices14,17 via helper0x15d0 (MDO_FX_0/1), indices13,16 via0x1724 (LOS_FX_0/1), indices15,18 via0x1878 (TX_DIS_FX_0/1). All a1=0 internal GPIO selector; a2 equals corresponding numeric internal pin. Helpers place unit0, selector0, input dir0/default1 for MDO and LOS, output dir1/default0 for TX_DIS. Table entry +48 (descriptor+44) is0 for MDO/LOS,1 for TX_DIS. Inputs and outputs enabled at table+52.

| User label | Logical port | I2C dev | Interface | Addr | SCK | SDA | MDO/OE | LOS | TX_DIS |
|---|---|---|---|---|---|---|---|---|---|
| TE5 | 4 | 0 | software GPIO (2) | 0x50 | INT8 | INT9 | INT14 | INT13 | INT15 |
| TE6 | 5 | 1 | software GPIO (2) | 0x50 | INT8 | INT10 | INT17 | INT16 | INT18 |

- Optical rows .rodata+0x3888/0x38bc, stride52: `4,0,2,0x50,0,20,1,1,0,8,9,0,0`; `5,1,2,0x50,0,20,1,1,0,8,10,0,0`. +0 lport; nested device struct begins+4. `board_conf_dump` +0x1308..154c prints interface2 as software using GPIO, interface0/1 hardware controllers0/1. Printed SCK/SDA selector values +44/+48 zero => INT. IDs0/1 are software device instances, NOT hardware-controller identities. Delay20 raw SDK units, address/data widths1 each (formatter 8 BITS), not measured timing.
- ski board_fiber_optical_init +0x7243c..72494 takes optical rows+4 and increments52; i2c_dev_init+0x71168..71178 calls drv_i2c_dev_init(unit0,device). rtcore r9300_i2c_dev_init+0x5958..5988 dispatches interface2 to drv_software_i2c_init with descriptor+40/+32 (SCK selector/pin) and+44/+36 (SDA selector/pin). This cross-checks actual consumer, not just formatter strings.
- ski gpio_data_get+0x70f24 uses descriptor+0/+4/+8 as unit/bank/pin. board_fiber_oeStatus_get+0x77158..77184 returns1 for raw low with descriptor active marker0. board_fiber_losStatus_get+0x7727c..772a4 similarly returns1 on raw low. However `_fiber_present_detect_monitor` +0x76edc..76f20 and0x77040..7704c enables receiver when LOS raw equals marker0, disables otherwise: raw LOW means receive allowed, raw HIGH suppresses receive. Do not confuse inverted API `losStatus_get` return1 with electrically asserted loss. TX_DIS helper output marker1/default0 is consistent with high-disable/low-enable convention; actual cage polarity/wiring is not physically validated and TX output consumer not fully traced.

## Limits / candidate use
Strong enough for a provisional LG510S core definition: SoC family assumption from supplied target, six user labels and SDK ports0/8/16/20/25/26, copper/fiber split, software I2C common SCK8 with SDA9/10, module-detect14/17, LOS13/16, TX-disable15/18 as static vendor configuration. Do not silently apply GPIO bank translation or substitute MAC24. Need physical/stock-runtime confirmation of selected profile, cage order/continuity, GPIO polarity and availability, PHY MDIO/reset setup and SerDes electrical setup before a hardware-authoritative DTS. No boot/flash approval.

Not researched exhaustively: loader, partitions, RAM, PHY initialization, PHY address meaning, SerDes attribute polarity or PHY firmware. No build/lint/test/formatter/device run. Scratch mutations, if needed for review honesty, must be confined to a private /var/tmp directory and must never execute firmware.
