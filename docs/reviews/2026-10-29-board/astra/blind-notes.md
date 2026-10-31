# GPT-6 Astra — sealed Phase 1 (no repository conclusions read)

Seat: openai-codex/gpt-6-astra. Checkout HEAD independently resolved to 6f7d67b6fd378981874d354b512495b99c31d5bc. Only task contract and generic binutils transport were read outside raw artifacts. Codegraph has no index for raw artifacts; built-in tools used. No peers or repository docs read. No hardware actions, builds, tests, package installs or worktree changes outside scratch. This is static firmware research, not pfBlockerNG. No mutations performed (contract prohibits tests and artifact writes outside assigned scratch).

## Provenance and method

All three 16,777,216-byte flash images SHA256: 7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48. Agreement of programmer reads establishes byte repeatability, not independent electrical corroboration.

- board_conf.ko 027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70
- rtcore.ko d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4
- ski.ko ab5244c2058ef8b6ab04ccf0cc5370b8a068ab931c7a063f2d26ede0a69b9cfb
- rtk.ko d1a4b5655b8cf8b0ce0a26f74daf0c8fb7b03897c31e5693498d9c981c4f1988
- board.ko cf410968f4842a132c135500d479c0938f752535f2a347fecebb74dbe32baf66 (symbols only)
- uboot.bin ebda866c948081f28ef3391a3fef48c1de090a0d14de26da7b1ff0cc8f342169
- vmlinux.bin bda0d78d9961a516029604bc973a45fae2423e8e59928f3c798ea528df7ebbfd

Used native macOS nm, own ELF32 big-endian reader scratch/elfprobe.py, and MIPS readelf/objdump through supplied smoke-verified transport to existing analysis VM. ELF metadata independently cross-checked with readelf: board_conf .rodata file offset 0x2c90, .data 0x8980, .text 0x60, o32/MIPS32r2/ELF REL. Disassemblies captured under scratch/*.dis. Modules inspected, never loaded or executed. Own reader resolves R_MIPS_32 S+A and traces HI16/LO16 with native disassembly rather than assuming unrelocated zero pointers.

## Profile selection: static path, not observed runtime state

The allowlisted boardmodel appears both in compiled loader defaults at 0xc7d16 and saved BDINFO environment at 0xe0014: RTL9303_8264B_2XGE. The environment block at 0xe0000 has big-endian CRC 0x89e491e2, matching CRC32 of 0xe0004..0xeffff. Other allowlisted values: bootcmd=boota, bootdelay=1, baudrate=115200. Compiled bootargs is empty. No non-allowlisted environment values inspected/output.

rtcore rt_util_flashEnv_get at .text 0x1838 uses get_mtd_device_nm("BDINFO") (relocation at 0x185c), reads its bytes, calls rt_util_flashVar_get. ioal_param_hwpIdKey_get .text 0x18620 can select via name boardmodel or via idType="integer" and boardid. Those latter values are outside task environment allowlist: their binary key names/code were decoded, their saved values were NOT examined. hwp_forcedProfile_get .text 0x16790 consults .data+0x764; initial discriminator is 2 (disabled), text "Default None". hwp_forceProfile .text 0x1704c can replace that selector; no direct text relocations to it found in this rtcore object. hwp_probe .text 0x16df0 first tries forced selection, then ioal parameter selection, then hwp_profile_find. Failed input can enter default-profile path; unmatched explicit profile invokes failure handler. Cannot claim active runtime profile solely from flash boardmodel.

rtcore hwp_hwProfile_list .data+0x7a0 includes R_MIPS_32(.data + 0x33dc). Profile at .data+0x33dc has name RTL9303_8264B_2XGE, ID 0x008de842 (=9300034), one switch descriptor; .data+0x3418 relocation -> .data+0x3434. board_conf sys_boardModel_init .text 0x318..0x328 reads hwp_myHwProfile+0x30, NOT CLI OEM Board Value. boardModelConfTbl has 0x240-byte rows; target .rodata+0x900 starts 008de842 and contains RTL9303-4XGE-2XGEF at +0x3c. board_conf_get .text 0xd04 selects boardMap by this ID, 32-byte rows. Target boardMap .data+0x160: ID 008de842; relocs +0x164 -> portConf_9303M4XC2XF; +0x168 -> fiberConf_9303M4XC2XF. rc loads rtcore, rtk, rtdrv before board_conf, then ski before board. Board Value1 is a separate untraced OEM identity; no equivalence inferred.

## Port, PHY and SerDes evidence

board_conf portConf_9303M4XC2XF .rodata+0x1f00 / file+0x4b90, six 32-byte rows plus terminator:

| User | raw 8 big-endian words | switch MAC | MDIO config | SDS descriptor index -> lane |
|---|---|---:|---|---|
| TE1 | 3,1,0,0,0,15,2,1 | 0 | SMI0 addr0 PHYidx0 | 0 -> 2 |
| TE2 | 3,2,0,8,0,15,2,1 | 8 | SMI0 addr1 PHYidx0 | 1 -> 3 |
| TE3 | 3,3,0,16,0,15,2,1 | 16 | SMI0 addr2 PHYidx0 | 2 -> 4 |
| TE4 | 3,4,0,20,0,15,2,1 | 20 | SMI0 addr3 PHYidx0 | 3 -> 5 |
| TE5 | 3,5,0,25,1,15,2,0 | 25 | ff/ff/ff sentinel, no external MDIO PHY | 5 -> 7 |
| TE6 | 3,6,0,26,1,15,2,0 | 26 | ff/ff/ff sentinel, no external MDIO PHY | 6 -> 8 |

Anonymous port formatter .text+0x5f0, loads at 0x940..0x9ac and .rodata.str1.4+0xa8/+0x134 distinguish user number, physical unit, physical port. ski sys_physic_portview_init .text+0xb4cc consumes board_conf_get; .text 0xb684 zero-initializes logical ordinal, 0xb694 increments, 0xb6b0 takes row+12 physical MAC, row+8 unit; b728..b734 consumes user/type. Thus LPort4/5 are zero-based logical TE5/TE6, not MAC4/5 or physical front-panel sockets4/5.

rtcore switch descriptor .data+0x3434 (file 0x33614): ports start +20, stride20, MAC0xff terminator. Rows at .data 0x3448,0x345c,0x3470,0x3484,0x3498,0x34ac,0x34c0,0x34d4,0x34e8. First four bytes are mac_id,phyIdx,smi,phy_addr, word+4 sdsIdx. Proof: hwp_parsedInfo_show .text 0x151d8..0x1523c prints those exact field labels; _hwp_port_parse .text 0x12f68/0x12f80 uses +20 and stride20. Copper raw first words: 00000000,08000001,10000002,14000003. SFP: 19ffffff and 1affffff.

_hwp_serdes_parse 0x13ec0 reads 2-byte lane descriptors at sw+0x515, terminates on lane ff, and 0x13f88..0x13fa0 translates port SDS index to the descriptor lane. Raw .data+0x3949: 02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff 00. Therefore SDS indices ARE NOT lane IDs. Flags high6bits are consumed as mode (e.g. rtk dal_longan_construct_serdesConfig_init 0x1340fc..0x134104). Low2 flags differ for copper; their RX/TX polarity naming not established in this blind pass. Do not guess which bit is RX/TX or board copper crossover wiring.

PHY descriptors at sw+0x590 = .data+0x39c4, 16-byte rows: 00000024 00000000 00000000 04000000; second 00000023 00000000 00000000 01180000; next chipID ff terminator. _phyType_name .rodata+0xb20 relocation entries 35/36 resolve to strings RTL8261BE/RTL8264B. Four copper rows reference PHYidx0, RTL8264B. Extra SDK MAC24 references PHYidx1 SMI1 addr0 lane6 (RTL8261BE), MAC27 lane9 also exists, but neither is exposed by the six-entry board port table. Do NOT make these extra SDK rows front-panel ports. CPU-like MAC28 has attr8, SDSff, no external PHY; exact CPU interpretation stays static SDK evidence, not probing.

## SFP I2C/GPIO

fiberConf at .rodata+0x387c = count2 with R_MIPS_32 relocations to detectConf at 0x38f0 and opticalConf at 0x3888. Optical rows stride52 (13 words):
- LPort4: 4,0,2,0x50,0,20,1,1,0,8,9,0,0
- LPort5: 5,1,2,0x50,0,20,1,1,0,8,10,0,0

The second word is device index0/1; the THIRD word2 is connection mode SOFTWARE GPIO I2C, NOT controller2. board_conf_dump at .text 0x1320..0x1338 branches mode2 to text "Connect by I2C Interface Software using GPIO" (.str+0x37c), mode0/1 to hardware-controller0/1. Formatter prints +36/+40 as SCK/SDA, flags+44/+48 INT/EXT. ski board_fiber_optical_init 0x72478 passes row+4 into i2c_dev_init, stride52. rtcore r9300_i2c_dev_init 0x5958..0x5988 calls drv_software_i2c_init when type2. Thus TE5 software dev0, SCK INT8, SDA INT9, address0x50; TE6 dev1, SCK INT8, SDA INT10, address0x50; delay20 (unit not independently decoded).

Detect rows stride28: [4,1,0,1,1,0x50c,0x4b0] and [5,1,0,1,1,0x620,0x5c4]. Last words are R_MIPS_32 against boardGpio_930x (.data+0x670). Crucially addends refer to ROW+4 substructures: 0x50c=14*92+4, 0x4b0=13*92+4, 0x620=17*92+4, 0x5c4=16*92+4. Ignoring +4 gives off-by-one interpretations.

board_gpio_init jump table .rodata+0x47a0 indexed ID-0x8de827 sends target to .text0x1a8c; comparison at 0x1ae8 recognizes 0x8de842, branches to 0x2684. It fills:
- TE5: MDO_FX_0 INT14, LOS_FX_0 INT13, TX_DIS_FX_0 INT15.
- TE6: MDO_FX_1 INT17, LOS_FX_1 INT16, TX_DIS_FX_1 INT18.
Proof .text 0x2698..0x2730 with helper bodies0x15d0/0x1724/0x1878. Input helpers set direction field0, TX helper sets direction1. Detect formatter OE pointer is +20 and LOS pointer+24; names confirm MDO/LOS. TX-disable is initialized in GPIO setup, not a pointer in detect row.

drv_generalCtrlGPIO_dataBit_get 0xdd38..0xdd44 transforms linear pin into bank=pin>>3, bit=pin&7. rtl9300_gpio_dataBit_get 0x3b74..0x3c08 selects bank0/1/2 bases0/8/16 and reads SoC offset0x330c. Therefore INT8/9/10 = B0/B1/B2, INT13/14/15 = B5/B6/B7, INT16/17/18 = C0/C1/C2. INT0 in helpers is internal-controller selector, not bank0.

Software polarity is partly recoverable: input helper zeroes row+0x30, and ski board_fiber_oeStatus_get0x77174..0x77180 / losStatus_get0x77298..0x772a4 test GPIO substructure+0x2c and return raw==0 when zero. gpio_data_get0x70f24 dispatches directly to general GPIO without inversion. Thus vendor getters treat raw-low as asserted for both presence/OE and LOS under this profile. This does not prove SFP cage electrical polarity; LOS convention may need careful hardware validation. TX helper sets row+0x30=1 but its complete consumer/drive policy not decoded here. Static GPIO assignments are not continuity tests.

## RAM, flash and image

Kernel strings at file0x47f6cc and0x4806d8 are "console=ttyS0,115200 mem=128M". Together with contract live total125196KB, supports 128MiB candidate; not independently read DRAM controller calibration/geometry.

The one-megabyte uboot carve includes BDINFO/SYSINFO: it is NOT the whole LOADER partition. Native MTD kernel name-pointer table .data file0x455450 has seven32-byte records naming LOADER, BDINFO, SYSINFO, JFFS2 CFG, JFFS2 LOG, RUNTIME, OEMINFO. Initial sizes zero; populated by function VA0x801fbe80 from five68-byte flash-size alternatives at file0x455530. 16MiB row file0x455574 words:
01000000, 00000000,000e0000, 000e0000,00010000, 000f0000,00010000, 00100000,00100000, 00200000,00100000, 00300000,00c00000, 00000000,00000000, 00f00000,00100000.
This means native-size candidate LOADER0..0xdffff; BDINFO0xe0000..0xeffff; SYSINFO0xf0000..0xfffff; CFG0x100000+1MiB; LOG0x200000+1MiB; RUNTIME0x300000+12MiB; OEMINFO0xf00000+1MiB (unused pair0,0 also present in table). Init VA0x80474ed4..0x80474ee4 registers7 records; kernel command-line partition parser can supersede built-in array. Read only header at0x100000 confirmed JFFS2 magic; no JFFS2 content read. Existing 2MiB jffs2 carve cannot imply a single2MiB native partition.

fw-image.bin exact12MiB bytes located in dump at0x300000. Its64-byte header is legacy-uImage-shaped with vendor magic0x83800000, headerCRC0xa80f0d16, payload size0x7eae10, load0x80000000, entry0x803345b0, payloadCRC0x6f51b869, OS5 arch5 type2 compression3, version1.1.1.34. CRC32 header with bytes4..7 zero and payload CRC both match. LZMA-alone decompression gives11,336,112 bytes equal to existing vmlinux.bin. No standard27051956 magic located in full flash. This validates stored bytes/format, not arbitrary OpenWrt image acceptance or execution.

Loader narrow string evidence: boota help at0xc5554 says boot application from flash partition; loadb/loady/TFTP command help exists; strings also explicitly say "bootm command is not supported!"0xc50a8 and "tftp command is not supported!"0xca488. Presence of command strings cannot approve RAM boot/recovery. No commands attempted.

## Limits before Phase2

Profile/PHY/SDS/GPIO rows and code are static; supplied live facts establish six CLI ports, model/versions, link snapshots and total memory only. Live HWP profile, raw MDIO IDs, polarity registers, RX calibration, PHY firmware readiness, PCB continuity and bootloader behavior not sampled. Environment override keys outside allowlist deliberately left unexamined. SerDes lowbit polarity semantics and complete MTD dynamic fallback/selection were not exhaustively decoded. No public sources, no peers, no tests or scratch mutations. Some broad disassembly captures include unused exploratory regions; conclusions use only anchors above. No MIPS tool failures occurred; codegraph unavailable because raw path unindexed.
