# LG510S blind notes — Opus 5.5 seat (Phase 1, written BEFORE reading any repo docs/README/prior reports)

Seat: Opus 5.5 (anthropic/claude-opus-5-5). Worktree pinned 6f7d67b6fd378981874d354b512495b99c31d5bc.
Tools: helper `mips-binutils.py` → VM pinned mips-openwrt-linux-musl objdump/readelf (disassembly `-dr`, `readelf -rWS`), macOS `nm`, own Python ELF32-BE REL parser (scratch/elfdump.py: applies implicit REL addends, resolves R_MIPS_32 to section+sym), own CRC/env scanner (scratch/envscan.py, prints only allowlisted keys, others presence-only). No device access, no builds, nothing loaded/executed.

## Inputs (SHA-256)
- lg510s-{1,2,3}.bin: all three = 7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48 (identical reads)
- board_conf.ko 027521d7…0d70 (matches contract); rtcore.ko d81ba50d…eee5c4 (matches); board.ko cf410968…baf66
- ski.ko ab5244c2058ef8b6ab04ccf0cc5370b8a068ab931c7a063f2d26ede0a69b9cfb; rtk.ko d1a4b5655b8cf8b0ce0a26f74daf0c8fb7b03897c31e5693498d9c981c4f1988
- parts/uboot.bin = flash[0x000000,+0x100000] exact; fw-image.bin = flash[0x300000,+0xc00000] exact; jffs2-a.bin = flash[0x100000,+0x200000] exact; jffs2-b.bin = flash[0xf00000,+0x100000] exact (NOT 0x200000); vmlinux.bin == LZMA payload of RUNTIME image (byte-exact, verified by decompressing).

## Flash / image / loader (STATIC)
- Kernel MTD names (vmlinux VA 0x80455450, struct mtd_partition stride 32, sizes 0 = filled at runtime): idx0 LOADER, 1 BDINFO, 2 SYSINFO, 3 "JFFS2 CFG", 4 "JFFS2 LOG", 5 RUNTIME, 6 OEMINFO.
- Layout constant tables right after (VA 0x80455530): per flash size {size, 8×(off,len)}. 16 MiB row: LOADER 0x000000/0xe0000, BDINFO 0x0e0000/0x10000, SYSINFO 0x0f0000/0x10000, JFFS2 CFG 0x100000/0x100000, JFFS2 LOG 0x200000/0x100000, RUNTIME 0x300000/0xc00000, slot6 (0,0) unused, OEMINFO 0xf00000/0x100000. [mapping of slot6/slot7→OEMINFO is INFERENCE from table shape; flash contents agree: JFFS2 magic 0x1985 at 0x100000, 0x200000, 0xf00000; SYSINFO 0xf0000 fully 0xFF].
- BDINFO @0x0e0000 len 0x10000: U-Boot env, CRC32 (BE word at +0) valid. Allowlisted: boardmodel=RTL9303_8264B_2XGE, bootcmd=boota, bootdelay=1, baudrate=115200; bootargs ABSENT. idType ABSENT, boardid ABSENT (presence check). ledModeInitSkip present. 5 further keys withheld.
- Loader: "U-Boot 2011.12.(1.0.0.2) (Sep 11 2024 - 13:14:20)" (uboot.bin+0xc7ca0). Built-in default env (uboot.bin+0xc7d16…): boardmodel=RTL9303_8264B_2XGE, bootargs= (empty), bootcmd=boota, bootdelay=1, baudrate=115200. Command "boota - boot application image from flash partiton". Reset word 0x0bf0117c = j 0xbfc045f0.
- RUNTIME @0x300000: 64-byte uImage-layout header with magic 0x83800000 (not 0x27051956); hcrc a80f0d16 and dcrc 6f51b869 both verify; size 0x7eae10; load 0x80000000; entry 0x803345b0; os/arch/type/comp 05/05/02/03 (Linux/MIPS/kernel/LZMA); name "1.1.1.34"; time 2025-03-29 06:45:57 UTC. Residual non-image bytes after 0xaeae50 (0x2e-byte HTTP multipart boundary text + 0x64f9-byte blob @0xaed000) — not part of the CRC'd image.
- Kernel built-in cmdline "console=ttyS0,115200 mem=128M" (vmlinux 0x47f6cc). Live MemTotal 125196 KB is consistent with mem=128M (consistency, not proof of DRAM size).

## Profile selection chain (STATIC, code-traced)
1. rc: insmod rtcore → rtk → rtdrv → board_conf → net → defdb → ksi → osal → ski [args from /mnt/ski_param if present] → board → l2g_*.
2. rtcore `hwp_probe` (.text 0x16df0): `hwp_forcedProfile_get` reads static forced identifier .data+0x764 {type=2,"Default None"} → type 2 ⇒ returns -1 (not forced). Then `ioal_param_hwpIdKey_get` (0x18620): `rt_util_flashEnv_get("idType")`; only if =="integer" → type=1 and decimal `boardid`; else `boardmodel` string (44 B). `rt_util_flashEnv_get` (0x1838) reads whole MTD named "BDINFO" and `rt_util_flashVar_get` requires CRC32 over len-4 to match first word. Then compare to default identifier .data+0x730 {type 2,"default",id 999} (match ⇒ hwp_useDefHwp=1), else `hwp_profile_find` (strncmp-44 by name) over `hwp_hwProfile_list` (.data+0x7a0, 40 pointers, NULL-terminated).
3. With BDINFO above: name match is unique → list index 33 → profile object .data+0x33dc, name "RTL9303_8264B_2XGE", id word +0x30 = 0x008de842 = 9300034, swDescp ptr +0x3c → .data+0x3434, chip word 0x93036810.
4. board_conf.ko: `sys_boardModel_init` (.text 0x2d0) takes `hwp_myHwProfile->+0x30` (9300034), linear search `boardModelConfTbl` (.rodata 0, 11×576 B, sentinel 0x8de849) → entry 4 (.rodata+0x900) names "GS9303-08"/"RTL9303"/"RTL9303-4XGE-2XGEF". `board_conf_get` (0xd04) matches `sys_boardModelId_ret()` against `boardMap` (.data+0xc0, 11×32 B) → row .data+0x160: {0x8de842, portConf_9303M4XC2XF (.rodata+0x1f00), fiberConf_9303M4XC2XF (+0x387c), ledConf_9303M4XC (+0x3718), buttonConf_9303M5XC2XF (+0x4850), encryptConf_9303M4XC2XF (+0x48f0), fan9303M4XC2XF (+0x4a9c), temp9303M5XC2XF (+0x4ae8)} (all R_MIPS_32 relocs in .rel.data, addend in word = 0).
5. board_conf also reads mtd index 2 (= SYSINFO, erased) for "bootmsg" only — not board selection.
6. Runtime overrides that DO exist: (a) editing BDINFO `boardmodel`, or adding `idType=integer`+`boardid=<n>` (U-Boot setenv); (b) `hwp_forceProfile()` (rtcore 0x1704c, writes forced identifier .data+0x764) — not in __ksymtab, no call site in rtcore, no module imports it ⇒ unused in this image; (c) ski.ko params are only `dbgMaskStr`(charp) and `ioctl_major`(uint) — /mnt/ski_param cannot change the board. rtcore param `rtcore_num`(int) only. BDINFO missing/CRC-bad ⇒ default-HWP path (`hwp_useDefHwp`), not traced further.
7. CLI "Board Value 1" (libclicmd fmt "Board Value        : %d" next to PSU strings) is NOT 9300034; source not traced. Hypothesis only: board_conf `ledConf_board_bit0/1/2` = input-configured internal pins 21/22/23 (strap bits?) — UNVERIFIED.

## Port map (STATIC) — portConf_9303M4XC2XF .rodata+0x1f00, 7×32 B, terminator w2==0xffff
Row words {w0 type, w1 usr, w2 unit/dev, w3 phy(MAC), w4 media, w5 speed, w6 duplex, w7 attr}. Field meaning proven by formatter at board_conf .text 0x5f0 ("%-11s %-4u (%-1u) %-3u …", Type/Usr/Phy) and consumer ski `board_conf_port_get` (0x70da0: matches w2==unit && w3==port) and ski `sys_physic_portview_init` (0xb4cc: row index → logical port; stores (w2,w3)).
| row/lport | usr | MAC (w3) | type | media | attr | raw row |
|---|---|---|---|---|---|---|
| 0 | 1 | 0 | 10G | Copper | 1 | 3,1,0,0,0,0xf,2,1 |
| 1 | 2 | 8 | 10G | Copper | 1 | 3,2,0,8,0,0xf,2,1 |
| 2 | 3 | 16 | 10G | Copper | 1 | 3,3,0,0x10,0,0xf,2,1 |
| 3 | 4 | 20 | 10G | Copper | 1 | 3,4,0,0x14,0,0xf,2,1 |
| 4 | 5 | 25 | 10G | Fiber | 0 | 3,5,0,0x19,1,0xf,2,0 |
| 5 | 6 | 26 | 10G | Fiber | 0 | 3,6,0,0x1a,1,0xf,2,0 |
TE<n> ↔ usr n ↔ lport n-1 is INFERENCE (CLI prefix/numbering not traced in libclicmd); the 6-row count matches live TE1..TE6.

## SDK hwp profile RTL9303_8264B_2XGE (STATIC; rtcore .data+0x3434; identical copy in loader uboot.bin+0x8b520+0x58 — same SDK DB, NOT independent)
Port descriptor (20 B at swDescp+20; layout proven by `hwp_parsedInfo_show` 0x151d8…: +0 mac_id, +1 phy_idx, +2 smi, +3 phy_addr, +4 s32 sds_idx, +8 attr, +9 eth, +10 medi):
| MAC | phy_idx | SMI bus | MDIO addr | sds_idx→SerDes | mode byte | eth | medi |
|---|---|---|---|---|---|---|---|
| 0 | 0 (RTL8264B) | 0 | 0 | 0→SDS2 | 0x72 | 0x10 XGE | 0x01 copper |
| 8 | 0 | 0 | 1 | 1→SDS3 | 0x71 | XGE | copper |
| 16 | 0 | 0 | 2 | 2→SDS4 | 0x72 | XGE | copper |
| 20 | 0 | 0 | 3 | 3→SDS5 | 0x71 | XGE | copper |
| 24 | 1 (RTL8261BE) | 1 | 0 | 4→SDS6 | 0x70 | XGE | copper |
| 25 | – (0xff) | – | – | 5→SDS7 | 0x08 | XGE | 0x08 serdes |
| 26 | – | – | – | 6→SDS8 | 0x08 | XGE | serdes |
| 27 | – | – | – | 7→SDS9 | 0x08 | XGE | serdes |
| 28 CPU | – | – | – | 0xff | – | attr 0x08 | – |
- SerDes table swDescp+1301, 2-byte {sds_id, mode} (stride proven in `_hwp_serdes_parse` 0x13ec0/0x13f10), raw "02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff". NO polarity field exists in this SDK's serdes descriptor.
- PHY table swDescp+1424, 16-B entries {u32 type, …, +12 port count, +13 base MAC}: [0] type 36 = "RTL8264B" (rtcore `_phyType_name` table .rodata+0xb20), 4 ports, base MAC 0; [1] type 35 = "RTL8261BE", 1 port, base MAC 24; [2] 0xff end.
- eth/medium bit meanings from `_hwp_port_parse`/`hwp_info_show` mask order (Copper/Fiber/Combo/Serdes; FE/GE/2_5GE/5GE/XGE/SXGE): medi 0x01=Copper, 0x08=Serdes; eth 0x10=XGE.
- Mode byte names NOT derivable (no name table). Facts: `_switch_sdsMode_convert` (rtk 0x1816f8) maps (mode&0xfc)==0x70 → rt_serdesMode 28; `dal_longan_sds_init` (0x127798) treats families (m&0xfc)==0x70 and ==0x08 (and 0x54/0x58 masks) as 10G-rx-calibrated. INFERENCE: 0x70–0x72 = USXGMII-family variants (copper PHY links), 0x08 = 10G fiber-class (likely 10GBASE-R). Why SDS2/4=0x72 vs SDS3/5=0x71: unknown.
- KEY DIVERGENCE: hwp declares 8 front MACs (0,8,16,20,24,25,26,27) incl. an RTL8261BE on SMI1/addr0 (MAC24, SDS6) and a third SerDes port MAC27/SDS9, but board_conf's front-panel portConf exposes only 0,8,16,20,25,26. Whether MAC24's PHY and MAC27's cage exist on the LG510S PCB is UNKNOWN (static config cannot prove absence/presence; hwp is a shared reference profile).
- Board-specific SerDes polarity/tx/rx-cali: rtk `conf_rtl9300_cust_board_list` (BSS, not exported) has 12 relocs, all loads (in `dal_longan_sds_rxCaliConf_cust`, `dal_longan_sds_txParam_cust`, `dal_longan_construc_serdesConfig_cust`), no store ⇒ always NULL ⇒ no custom per-board SerDes config applied. rtk.ko has only one profile-ID-specific constant (0x8de83b, not ours). Polarity: only runtime APIs (`rtk_port_phyPolar_set`, used by interactive sqfs/bin/diag); no boot script found calling them. ⇒ No evidence of inverted polarity anywhere in firmware; PCB polarity remains UNPROVEN.

## SFP / GPIO / I2C (STATIC, board_conf + consumers)
- fiberConf_9303M4XC2XF (.rodata+0x387c): {portNum 2, detectConf*, opticalConf*}.
- detectConf rows (28 B, .rodata+0x38f0) {lport, present-src idx, mediaChg idx, OE-label, LOS-label, OE gpio*, LOS gpio*}; formatter .text 0x10a4–0x1260; src strings .rodata+0x1ac0 {"None","OE","LOS"}:
  - lport4: present via "OE", mediaChg None; OE gpio → boardGpio_930x+0x50c = entry14+4; LOS gpio → +0x4b0 = entry13+4
  - lport5: OE → +0x620 = entry17+4; LOS → +0x5c4 = entry16+4 (entries are 92 B; pointers are entry+4, addend in word)
- boardGpio_930x entries are zero statically; filled by `board_gpio_init` (.text 0x1a2c): jump table .rodata+0x47a0 index id-0x8de827 → case 27 (.text 0x1a8c: gpBoardGpio=boardGpio_930x, gGpioIdSum=32) → id compare chain → 0x2684 block for 0x8de842:
  - 0x19d4: read switch reg 0x0200, clear bit 10, write back. rtk `rtk_longan_reg_list` (stride 148, addr at +128) names reg 0x200 = GPIO_SEL_CTRL; field lsb10 len1 = GPIO18_USBLED_SEL ⇒ frees GPIO18 from USB-LED function (consistent with TX_DIS_FX_1 on GPIO18).
  - helper(id,dev,pin,name): 0x15d0 (MDO, dir IN, default 1), 0x1724 (LOS, dir IN, default 1), 0x1878 (TX_DIS, dir OUT, default 0). Direction=S+16, Default=S+20 per `board_gpio_dump` ("IN"/"OUT").
  - calls: (14,0,14,"MDO_FX_0"), (17,0,17,"MDO_FX_1"), (13,0,13,"LOS_FX_0"), (16,0,16,"LOS_FX_1"), (15,0,15,"TX_DIS_FX_0"), (18,0,18,"TX_DIS_FX_1"). dev 0 = internal SoC GPIO (no external expander enabled: gGpioIdSum 32 < 33 skips dev1–3 init).
  ⇒ SFP A (lport4, usr5, MAC25): MOD_ABS/“MDO” GPIO14, LOS GPIO13, TX_DISABLE GPIO15. SFP B (lport5, usr6, MAC26): MDO GPIO17, LOS GPIO16, TX_DISABLE GPIO18.
  Numbering: SDK internal GPIO linear index; ski `gpio_isr_get` converts n → (n>>3)<<16 | (n&7) (port A/B/C…, 8 pins each) ⇒ 13–18 = B5,B6,B7,C0,C1,C2 in SDK port notation (INFERENCE that Linux otto-gpio linear numbering equals this index).
  Polarity (code-traced): per-pin flag at entry+48 (S+48) is set to 1 only by the TX_DIS helper. ski `board_fiber_oeStatus_get` (0x770c0) and `board_fiber_losStatus_get` (0x771e4) read the pin via `gpio_data_get` then: flag==0 ⇒ status = (pin==0) [`sltiu v1,v1,1`]; flag!=0 ⇒ status = pin. So MDO and LOS are read active-LOW (status 1 when pin low); TX_DIS is flagged active-high and initialised OUT=0.
  Meaning: MDO status1=pin low is consistent with SFP MOD_ABS (low=present). For LOS the firmware's 'status' is also 1 when pin low — what the caller does with it (signal-OK vs loss) was NOT traced, so LOS active level for a DTS is UNRESOLVED (SFP MSA says LOS high = loss; vendor code neither confirms nor refutes PCB inversion). TX_DIS=0 ⇒ laser on under MSA (MSA semantics external knowledge).
- opticalConf rows (52 B, .rodata+0x3888); i2c conf = row+4 passed to `i2c_dev_init`→`drv_i2c_dev_init`→`r9300_i2c_dev_init` (rtcore 0x58dc: type 2 ⇒ `drv_software_i2c_init(sckDev,sckPin,sdaDev,sdaPin)`):
  - lport4: i2c dev 0, type 2 (SW bit-bang over GPIO), addr 0x50, delay 20, addr-width idx1 "8 BITS", SCK INT GPIO8, SDA INT GPIO9
  - lport5: i2c dev 1, type 2, addr 0x50, delay 20, SCK INT GPIO8 (shared), SDA INT GPIO10
- Other board I2C (same SW-GPIO type): encryptConf_9303M4XC2XF dev 20, addr 0x50, SCK GPIO3, SDA GPIO4 (auth/"encrypt chip"); ADT7476Fan9303M4XC2XF / tempADT7476_9303M5XC2XF dev 10/11, addr 0x2e, SCK GPIO8, SDA GPIO11.
- Reset button: buttonConfSys_9303M5XC2XF → resetGpio5 {unit0, dev0, pin5, dir IN, default 1}; hold logic hold5sResetApp. Active level not derived.
- Static config alone does NOT prove PCB wiring; it proves what the vendor firmware drives/reads for profile 9300034.

## Uncertainties / not derived
- SerDes mode names (0x70/0x71/0x72/0x08), PCB lane polarity, RTL8264B-side MDI/lane config, whether MAC24/MAC27 hardware exists, LOS semantic sense and button active level, Board Value source, default-HWP fallback behaviour, LED wiring (ledConf raw only), loader-side boota internals (25 `lui 0x8380` sites, not traced), DRAM chip size.
