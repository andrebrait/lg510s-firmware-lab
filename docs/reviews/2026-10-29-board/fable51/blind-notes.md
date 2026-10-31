# LG510S-4T2XS blind notes — seat Fable 5.1 (Phase 1, sealed before reading any repo docs)

Worktree: <worktrees>/review/board-evidence-fable51 @ 6f7d67b. No docs/README/prior reports opened before this file was written.
Method: own pure-python ELF32-MSB REL parser (scratch/elfdump.py: section headers, symtab, .rel.* with in-place R_MIPS_32 addends resolved to symbol+offset / .rodata.str1.4 strings), Apple llvm-objdump for section/reloc listings, VM-side mips-openwrt-linux-musl-objdump -dr (via the given transport helper) for disassembly of board_conf.ko, rtcore.ko, ski.ko, and two userland .so functions. Raw flash inspected only by offset/CRC/hash; env read restricted to allowlisted keys.

## 0. Inputs verified
- lg510s-1/2/3.bin: all SHA256 7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48 (16777216 B, identical).
- board_conf.ko 027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70; rtcore.ko d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4; board.ko cf410968f4842a132c135500d479c0938f752535f2a347fecebb74dbe32baf66.
- parts/uboot.bin == flash[0:0x100000] (sha256 ebda866c948081f28ef3391a3fef48c1de090a0d14de26da7b1ff0cc8f342169); parts/fw-image.bin == flash[0x300000:0xf00000] (sha256 71a626ba586d0605aa68c5af9ad0e5acd2df56bd0b16682e850e4855f1dcf2c2).
- parts/vmlinux.bin (11336112 B, sha256 bda0d78d9961a516029604bc973a45fae2423e8e59928f3c798ea528df7ebbfd) == lzma-alone decompression of flash[0x300040 : 0x300040+0x7eae10] (verified with python lzma, byte-equal).

## 1. Flash / RAM / image layout (STATIC facts)
Kernel static MTD table (vmlinux.bin file offset 0x455450, 7 x 32-byte `struct mtd_partition`, names at 0x40c294: LOADER, BDINFO, SYSINFO, "JFFS2 CFG", "JFFS2 LOG", RUNTIME, OEMINFO; sizes/offsets zero -> filled at runtime from the layout words at 0x455530):
- layout keyed by flash size; 16 MiB (0x01000000) row: LOADER 0x000000+0xe0000, BDINFO 0x0e0000+0x10000, SYSINFO 0x0f0000+0x10000, JFFS2 CFG 0x100000+0x100000, JFFS2 LOG 0x200000+0x100000, RUNTIME 0x300000+0xc00000, (unused 0,0), OEMINFO 0xf00000+0x100000. 8 MiB row has RUNTIME 0x300000+0x500000; a 32 MiB row follows.
- U-Boot has the same 7 names (uboot.bin 0xcfbe4, 16-byte stride: LOADER, BDINFO, SYSINFO, JFFS2_CFG, JFFS2_LOG, RUNTIME1, OEMINFO).
- Flash content checks: 0x100000, 0x200000, 0xf00000 start with JFFS2 magic 19 85 20 03; 0xf0000 (SYSINFO) begins 0xff-filled; 0x300000 = runtime image.
- Kernel cmdline string in vmlinux.bin (0x47f6cc): `console=ttyS0,115200 mem=128M`. Linux 3.18.24, "gcc 4.8.5 Realtek MSDK-4.8.5p1 Build 2536", built Sat Mar 29 06:45:49 UTC 2025. => RAM 128 MiB (consistent with live 125196 KB).
- Loader: "U-Boot 2011.12.(1.0.0.2) (Sep 11 2024 - 13:14:20)" (uboot.bin 0xc7ca0), prompt "RTL9300# ", boot banner "Board: RTL9300 CPU:%dMHz LX:%dMHz DDR:%dMHz", "Delay...(Hit any key to read or waiting for 8 hours~) ". Loader XIP vectors 0x9fc04fd0/0x9fc05008/... at flash offset 0x28 (kseg1 flash base 0x9fc00000). U-Boot data pointers 0x83f1xxxx/0x83f86548 => relocated U-Boot lives just under 64 MiB (so the loader apparently assumes <=64 MiB while the kernel uses 128M) [INFERENCE from pointer values].
- Runtime image header at 0x300000 (64 bytes, then LZMA): +0 0x83800000 (load addr of blob, INFERENCE), +4 0xa80f0d16 (unknown/magic), +8 0x67e79725 = Unix time 2025-03-29 06:45 UTC (matches kernel build), +0xc 0x007eae10 = payload length (verified: CRC32 over exactly that many bytes from 0x300040 = 0x6f51b869 = header +0x18), +0x10 0x80000000 (kernel load), +0x14 0x803345b0 (entry; vmlinux.bin+0x3345b0 starts with mfc0 t0,c0_status = kernel_entry), +0x1c bytes 05 05 02 03 (unknown), +0x20 "1.1.1.34". LZMA props 5d, dict 0x02000000, uncompressed size 0x00acf9b0 = 11336112.
- U-Boot commands seen: boota ("boot application image from flash partiton", bootcmd=boota), upgrade loader|loaderforce|runtime|rom [FILENAME] (TFTP-based; default names u-boot.bin / vmlinux.bix / rom.bix), "tftp command is not supported!", "rtk command is not supported!", setenv/printenv for env and for "system information" variables, PHY test strings, "Force port28 link down", "10gMedia set Unit %u Port %u", sds mode words fiber10g/fiber1g/dac50cm/dac100cm.

## 2. Board/profile selection chain (STATIC, derived from code)
U-Boot env (BDINFO): flash 0xe0000, 64 KiB, big-endian CRC32 0x89e491e2 over 0xe0004..0xeffff verified. 10 variables. Allowlisted values: baudrate=115200 (first var), boardmodel=RTL9303_8264B_2XGE, bootcmd=boota, bootdelay=1. No bootargs in flash env (bootargs='' only in U-Boot's built-in default env at uboot.bin 0xc7d46). `idType=` and `boardid=` do NOT exist anywhere in flash (the words appear only as code strings in uboot.bin 0xcd384/0xcb2c4 and rtcore.ko). U-Boot's compiled-in default env also carries boardmodel=RTL9303_8264B_2XGE (uboot.bin 0xc7d16).

rtcore.ko (insmod first per rootfs/etc/rc) — hwp_probe (.text 0x16df0):
1. hwp_forcedProfile_get: static identifier at .data+0x764 = {type=2, "Default None", id 0} -> type!=0/1 -> returns -1 (no forced profile in this build).
2. ioal_param_hwpIdKey_get (.text 0x18620): rt_util_flashEnv_get("idType") (reads MTD named "BDINFO" via get_mtd_device_nm, CRC32-checked U-Boot env, key lookup); if value == "integer" -> type 1, parse "boardid" decimal into id; otherwise type 0 and copy "boardmodel" (<=44 chars) as name. Here: name "RTL9303_8264B_2XGE".
3. hwp_identifier_cmp against .data+0x730 {type 2,"default",999}: name compare -> not "default".
4. hwp_profile_find: linear scan of hwp_hwProfile_list (.data+0x7a0, 40 pointers + NULL), first match by 44-char name compare. Profile struct = 0x744 bytes: +0 identifier.type(0), +4 name[44], +0x30 id, +0x34, +0x38 sw count, +0x3c -> swDescp (embedded at +0x58, 0x6ec bytes). Match = list index 33, .data+0x33dc: name RTL9303_8264B_2XGE, id 0x8de842 = 9300034, chip word 0x93036810.
   All 40 profiles enumerated (ids 9300001..9300041 w/ gaps). Relevant RTL9303 ones: 9300015 RTL9303_8XGE, 9300028 RTL9303_8X2_5G, 9300023 RTL9303_8X8226, 9300030 RTL9303_2X8254L_DEMO, 9300031 RTL9303_6x8254L_6xSPI, 9300032 RTL9303_8x8261N, 9300034 RTL9303_8264B_2XGE, 9300036 RTL9303_8264B_8261BE_2XGE, 9300037 RTL9303_8264B_8261BE, 9300038 RTL9303_8264B_3X8261BE_XGE, 9300039 ..._POE, 9300040 RTL9303_8264B_8264B.
   IMPORTANT: swDescp bytes of 9300034, 9300036 and 9300037 are byte-identical (0x6ec bytes; only name/id differ). The SDK profile therefore cannot distinguish "4 copper + 2 SFP" from "5 copper + 2 SFP" variants; the OEM layer does.
   U-Boot carries the same 40-entry table (e.g. uboot.bin 0x08b520 = RTL9303_8264B_2XGE, 0x744 stride); its swDescp is byte-identical to rtcore's (0 diffs).

board_conf.ko (OEM) — sys_boardModel_init (.text 0x2d0): id = hwp_myHwProfile->+0x30 (9300034); linear search boardModelConfTbl (.rodata 0x0, 11 entries x 0x240, sentinel id 0x8de849): entry[4] = {id 9300034, name "GS9303-08", chip "RTL9303", oidCount 9 -> oidAry_rtk931x, desc "RTL9303-4XGE-2XGEF"}. Other entries: 9300032 RTL9303-8x8261N, 9300018 & 9300035 RTL9302D-24MGE-4XGE, 9300015 & 9300040 RTL9303-8XGE, 9300033 RTL9302D-16MGE-4XGE, 9300037 RTL9303-5XGE, 9300038 RTL9303-7XGE-XGEF, 9300039 RTL9303-7XGE-XGEF_POE. (All say name "GS9303-08"/chip RTL9303 — the name field is NOT a board selector.)
   board_conf_get/boardMap (.data 0xc0, 11 x 32 bytes {id, portConf, fiberConf, ledConf, buttonConf, encryptConf, fanConf, tempConf}): 0x8de842 -> portConf_9303M4XC2XF, fiberConf_9303M4XC2XF, ledConf_9303M4XC, buttonConf_9303M5XC2XF, encryptConf_9303M4XC2XF, fan9303M4XC2XF, temp9303M5XC2XF.
   The MTD read in sys_boardModel_init is only `get_mtd_device(NULL,2)` + search for "bootmsg=" (absent in flash -> level 2). It does NOT select the board.
   board.ko: board_vendor_init is `jr ra; move v0,zero` (stub).

Override surfaces (STATIC): U-Boot `setenv boardmodel <name>` (help text present), or `idType=integer` + `boardid=<decimal>`; hwp_forceProfile() exists in rtcore but is compiled with "Default None". No GPIO strap participates in profile selection.

CLI "Board Value" (live=1) is NOT a profile id: libclicmd "Board Value        : %d" <- sal_device_board_id_get -> libglue rsd_device_board_id_get -> ioctl(/dev/ski, 5062) -> ski.ko board_device_boardId_get (.text 0x798b0): value = gpio(bit0) | gpio(bit1)<<1 | gpio(bit2)<<2 where the three GPIO descriptors come from ledConf_9303M4XC ids 11/12/13 -> ledConf_board_bit0/1/2 = {type 2, unit 0, dev 0 (INT), pin 21 / 22 / 23, dir 0 (IN), +0x14=1}. So Board Value 1 == strap GPIO21=1, GPIO22=0, GPIO23=0 (live reading, not a table).

## 3. SDK port table for profile RTL9303_8264B_2XGE (rtcore.ko .data+0x3434, swDescp)
Port descriptor layout derived from _hwp_port_parse/_hwp_serdes_parse: rows of 20 bytes starting at swDescp+0x14, terminated by mac_id 0xff, max 64; +0 mac_id, +1 phy_idx (index into PHY table at swDescp+0x590, 16 B/entry), +2 smi bus, +3 phy_addr, +4..+7 u32 index into the serdes table at swDescp+0x515 (2-byte {sds_id, mode} entries, count byte at +0x514 written at parse; negative = bitmask), +8 attr (0x01 ETH, 0x08 CPU), +9 eth (0x10 for all non-CPU rows here), +10 medium (0x01 copper, 0x08 fiber), +12/+13 LED set indices (copper rows 00/ff, fiber 25,26 ff/01, fiber 27 ff/ff).
Rows (hex): 
 00 00 00 00 00 00 00 00 01 10 01 00 00 ff ...   mac 0  phy0/smi0/addr0  sds-table[0]
 08 00 00 01 00 00 00 01 01 10 01 00 00 ff ...   mac 8  phy0/smi0/addr1  [1]
 10 00 00 02 00 00 00 02 01 10 01 00 00 ff ...   mac 16 phy0/smi0/addr2  [2]
 14 00 00 03 00 00 00 03 01 10 01 00 00 ff ...   mac 20 phy0/smi0/addr3  [3]
 18 01 01 00 00 00 00 04 01 10 01 00 00 ff ...   mac 24 phy1/smi1/addr0  [4]
 19 ff ff ff 00 00 00 05 01 10 08 00 ff 01 ...   mac 25 no PHY, fiber     [5]
 1a ff ff ff 00 00 00 06 01 10 08 00 ff 01 ...   mac 26 no PHY, fiber     [6]
 1b ff ff ff 00 00 00 07 01 10 08 00 ff ff ...   mac 27 no PHY, fiber     [7]
 1c ff ff ff 00 00 00 ff 08 ff ff 00 ff ff ff .. mac 28 CPU
Serdes table (+0x515): (sds 2,mode 0x72) (3,0x71) (4,0x72) (5,0x71) (6,0x70) (7,0x08) (8,0x08) (9,0x08) ff. => mac0->SDS2, mac8->SDS3, mac16->SDS4, mac20->SDS5, mac24->SDS6, mac25->SDS7, mac26->SDS8, mac27->SDS9. Mode enum values are raw (not decoded here); 0x08 is the mode used by every lane of the all-SFP profile RTL9303_8XGE, 0x70/0x71/0x72 appear only on lanes behind 8264B/8261BE/8254L PHYs.
PHY table (+0x590): entry0 {chip 0x24, phy_max 4, base mac 0}; entry1 {chip 0x23, phy_max 1, base mac 24}. chip enum: 0x24 = RTL8264B (profile RTL9303_8264B_8264B has two 0x24), 0x23 = RTL8261BE (from RTL9303_8264B_8261BE naming) [name-derived], 0x28 = CUST1, 0x1f = 8254L.
LED tail (+0x690): 00000001 00000001 0 | set0: 0x0aaa, 0x0a01, 0, ffffffff | set1: 0x0aa8, 0x0a01, 0, ffffffff (raw; not decoded).
MDIO facts: 10G copper PHY addresses 0,1,2,3 on SMI bus 0 (one RTL8264B), 8261BE at addr 0 on SMI bus 1 — the latter is in the shared template and is NOT exposed by the OEM port table (below), so its physical presence on LG510S is unproven.

## 4. OEM port table (board_conf.ko portConf_9303M4XC2XF, .rodata 0x1f00, 32-byte rows, terminator 0000ffff)
Row = {type, usr, w2, mac, media, speed, duplex, attr}; dump format "%-11s %-4u (%-1u) %-3u %-11s %-14s %-8s %-7x" = Type-string[type] Usr (w2) Phy=w3 Media-string[w4] Speed Duplex Attr. Type strings: 0 100M,1 1000M,2 2500M,3 10G,4 LAG,5 Combo_100M,6 Combo_1000M. Media: 0 Copper, 1 Fiber.
 TE1: type 3(10G) usr1 mac 0  Copper speed 0xf duplex 2(Auto) attr 1
 TE2: 10G usr2 mac 8  Copper attr 1
 TE3: 10G usr3 mac 16 Copper attr 1
 TE4: 10G usr4 mac 20 Copper attr 1
 TE5: 10G usr5 mac 25 Fiber  attr 0
 TE6: 10G usr6 mac 26 Fiber  attr 0
The column the OEM prints as "Phy" holds the SDK MAC id (values 0/8/16/20/25/26 cannot be MDIO addresses: the MDIO addresses are 0..3 and fiber ports have none). Siblings: 9303M5XC = macs 0,8,16,20,24 copper; 9303M7XC1XF = 0,8,16,20,24,25,26 copper + 27 fiber; 9303M8XC = 8 copper; 9303_8xgef = 8 fiber. So on LG510S mac 24 and 27 are unused by the OEM UI.
=> TE1..TE4 = SDS2..5 / 8264B addr 0..3 ; TE5 = mac25/SDS7 ; TE6 = mac26/SDS8 (static table facts; link observations live-only).

## 5. SFP I2C / detect GPIO (board_conf.ko + ski.ko)
fiberConf_9303M4XC2XF = {2 fiber ports, detectConf_9303M4XC2XF, opticalConf_9303M4XC2XF}.
opticalConf rows (13 words = 52 B; dump format "%-6u %-8u %-9s 0x%-3x %-7d %-3s_%-2u %-3s_%-2u" = LPort I2CDEV TYPE ID Delay SCK SDA; header for type 2 = "Connect by I2C Interface Software using GPIO"):
 LPort 4: i2cdev 0, type 2 (SW GPIO bit-bang), ID 0x50, delay 20, SCK INT_8, SDA INT_9
 LPort 5: i2cdev 1, type 2, ID 0x50, delay 20, SCK INT_8, SDA INT_10
 ("LPort" = 0-based logical index = usr-1; LPort 4 = TE5 = mac 25, LPort 5 = TE6 = mac 26 — consistent with the 7XC1XF table where the lone fiber port is LPort 7 = usr 8 = mac 27.)
detectConf rows (7 words): {lport, present-mode 1, mediaChg 0, oeStatus-enable 1, losStatus-enable 1, *gpio(OE/MDO), *gpio(LOS)}; pointers go to boardGpio_930x entries (+4): LPort 4 -> entries 14 and 13; LPort 5 -> entries 17 and 16.
boardGpio_930x (.data 0x670) is 143 x 92-byte entries pre-filled only with id=index; the real pins are written at runtime by board_gpio_init (jump table .rodata 0x47a0 on hwp id; id 0x8de842 -> case .text 0x1a8c then 0x2684): entry layout +0 id, +4 unit, +8 dev (0 = INT SoC GPIO, n = EXT RTL8231 n), +12 pin, +16 direction (0 IN / 1 OUT), +20 default, +0x30 polarity/flag, +0x34 valid, +0x3c purpose[32].
 For 0x8de842 (also 9300038/39/40): id14 = INT pin 14 "MDO_FX_0" (in, +20=1); id17 = INT pin 17 "MDO_FX_1"; id13 = INT pin 13 "LOS_FX_0" (in, +20=1); id16 = INT pin 16 "LOS_FX_1"; id15 = INT pin 15 "TX_DIS_FX_0" (out, default 0, +0x30=1); id18 = INT pin 18 "TX_DIS_FX_1". (Here id == pin by coincidence; the helper takes them separately.)
 So SFP0 (TE5/mac25): MOD-ABS GPIO14, LOS GPIO13, TX_DIS GPIO15, SDA GPIO9. SFP1 (TE6/mac26): MOD-ABS GPIO17, LOS GPIO16, TX_DIS GPIO18, SDA GPIO10. SCL GPIO8 shared. Fan/temp ADT7476 (I2C addr 0x2e) also bit-banged on SCL GPIO8 / SDA GPIO11. Reset button INT GPIO5 (hold 5 s -> action 3). Board-ID straps GPIO21/22/23. All "INT" = SoC GPIO numbering as used by drv_generalCtrlGPIO_* (dev 0).
Polarity from ski.ko: board_fiber_oeStatus_get / present-change handler compute present = (pin == 0) when entry +0x30 == 0 (MDO entries) => MOD-ABS active-low (standard). LOS: _fiber_present_detect_monitor calls rsd_port_fiberRxEnable_set(lport, pin == flag(0) ? 1 : 0) => LOS pin high = loss of signal (standard). TX_DIS entries are outputs initialised with default 0 and flag 1 (=> drive low = transmitter enabled; INFERENCE on the SDK pin_init semantics).
Static config proves intent only; it does not prove the copper traces (e.g. whether GPIO 8/9/10 are the SoC HW-I2C pins or plain GPIO lines) — that needs the board or UART.

## 6. Other OEM tables (raw)
ledConf_9303M4XC pairs {id,ptr}: (0, ledConfSys type 6), (1, ledConfAlarm bss), (11,bit0 pin21), (12,bit1 pin22), (13,bit2 pin23), end 14.
buttonConf_9303M5XC2XF (used for 0x8de842 too) -> buttonConfSys {resetGpio5 (INT pin 5, +0x10=1), 1, 0, 0x14, 1, hold5sResetApp {5,0,3}}.
encryptConf_9303M4XC2XF raw: 0x14 2 0x50 2 0x96 1 1 0 3 4 ... 0x01040000 (not decoded).
fan9303M4XC2XF {4,1,ADT7476Fan9303M4XC2XF}; ADT7476Fan: {4, i2cdev 0xa, type 2, addr 0x2e, 0, delay 0xa, 1, 1, 0, SCK 8, SDA 11, ..., fanSpeedCtrl_9303M5XC2XF, 0x13880}. tempADT7476_9303M5XC2XF same pins (i2cdev 0xb).

## 7. Uncertainties / not derivable statically
- Serdes mode enum names for 0x70/0x71/0x72/0x08; LED set bit meanings; "attr" bit0 on copper rows; encryptConf meaning; +0x1c bytes of the runtime header; word +4 of that header; +0x34 word 0x00ff0000 in profiles.
- Whether an RTL8261BE is physically on the LG510S (template includes it at mac24/SMI1/addr0 but OEM hides mac 24).
- Whether SoC GPIO 8/9/10 double as the RTL930x hardware I2C pins (not verifiable from this dump).
- Actual lane polarity/inversion of SDS2..9 (not in these tables), PHY firmware/reset GPIO (rtcore has "PHY Reset GPIO" strings; not traced), DRAM timing (U-Boot computes at runtime).
- MTD index numbering at runtime (board_conf reads index 2; by static order that is SYSINFO).
