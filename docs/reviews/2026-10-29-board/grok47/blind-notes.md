# Phase 1 blind notes — Grok 4.7

Seat: Grok 4.7. Worktree `<worktrees>/review/board-evidence-grok47` HEAD `6f7d67b6fd378981874d354b512495b99c31d5bc`. Written before any repository README or `docs/` read. No peer scratch. No switch access.

## Tools and bytes

- Local: Python ELF/relocation decoder, `strings`, `file`, `shasum`. macOS `nm` only for a first symbol list; sizes and relocations taken from the VM binutils helper.
- Helper: `<worktrees>/review/board-evidence/scratch/model-review/mips-binutils.py` → the build VM as `rtlp-builder`, pinned `mips-openwrt-linux-musl-{objdump,nm,readelf}`. Disassembled `sys_boardModel_*`, `board_conf_get`, `board_gpio_init`, `hwp_probe`, `hwp_forcedProfile_get`, `hwp_identifier_cmp`, `ioal_param_hwpIdKey_get`, `_hwp_port_parse`, `_hwp_serdes_parse`, `drv_i2c_dev_init`, `drv_generalCtrlGPIO_pin_init`, ski `board_conf_port_get`, `board_fiber_*`, `i2c_dev_init`, `gpio_init`.
- Dumps: `lg510s-{1,2,3}.bin` each 16777216 bytes, SHA256 `7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48` (three reads identical).
- `board_conf.ko` SHA256 `027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70`, BuildID `edb5ecc287d3e9882d641f5d47dbc9219d0a1324`.
- `rtcore.ko` SHA256 `d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4`.
- `board.ko` SHA256 `cf410968f4842a132c135500d479c0938f752535f2a347fecebb74dbe32baf66` (only `board_vendor_init` / `init_module`).
- `rootfs/etc/rc` SHA256 `ad0465156dd0f7d0e876481823999c7c7a04a48769092d4c55048987c6daf679`. Load order: `rtcore.ko`, `rtk.ko`, `rtdrv.ko`, then `board_conf.ko`, later `board.ko`.
- `parts/uboot.bin` is an exact prefix of the dump (1048576 bytes). `parts/fw-image.bin` matches dump at `0x300000` (12582912 bytes). These carves are not treated as a partition map; boundaries below are from magics in the dump.

## Flash / loader (non-secret)

- `0x000000-0x0FFFFF`: loader image. Version token `1.0.0.2` at file `0xc7cb0` (matches the given live loader string; not a mapping).
- U-Boot env, both copies, allowlisted keys plus selector keys:
  - `0xc7d16` and `0xe0014`: `boardmodel=RTL9303_8264B_2XGE`
  - `bootcmd=boota`, `bootdelay=1`, `baudrate=115200`, `bootargs=` empty
  - exact keys `idType=` and `boardid=` are absent (0 hits). Exact key `board=` is absent.
- `0x100000`: JFFS2 magic `0x1985`. Contents not read.
- `0x300000`: firmware payload. ASCII `1.1.1.34` at `0x300020`. Region length matches the 12 MiB carve, ends `0xF00000`.
- `0xF00000`: JFFS2 magic `0x1985` through end of 16 MiB. Contents not read.
- `rt_util_flashEnv_get` offset inside the loader was not fully traced. Both env copies agree on `boardmodel`, so either copy yields the same profile name.

## Profile selection chain (do not confuse with CLI Board Value)

CLI format string in `libclicmd.so.0.0` at file `0xa9df0` is `Board Value        : %d`. The integer source was not traced. Live "Board Value 1" is not an SDK profile id and is not an index into `boardModelConfTbl`.

### SDK hardware profile (`rtcore.ko`)

`hwp_identifier` is 52 bytes: `+0` type (0 = name, 1 = numeric id), `+4` name (44 bytes), `+48` id. `hwp_identifier_cmp` strcmp's names when type is 0, compares `+48` when type is 1, else returns 0.

`hwp_hwProfile_list` (`.data+0x7a0`, 40 pointers then NULL). Relevant rows, id is the word at profile `+0x30`:

| list idx | `.data` | id | name |
|---|---|---|---|
| 33 | `0x33dc` | `0x008de842` | `RTL9303_8264B_2XGE` |
| 35 | `0x2554` | `0x008de844` | `RTL9303_8264B_8261BE_2XGE` |
| 14 | `0x1287c` | `0x008de82f` | `RTL9303_8XGE` |

Full list ids `0x008de821`..`0x008de848` with gaps. `0x008de844` is in rtcore and **not** in `board_conf` `boardModelConfTbl`.

`hwp_probe`:
1. `hwp_forcedProfile_get` reads `.data+0x764`. Static word is `2`, name `Default None`. Flag `2` is neither `0` nor `1`, so the function returns `-1`. Compiled-in force is inactive.
2. `ioal_param_hwpIdKey_get`: `rt_util_flashEnv_get("idType")`. If that equals `integer`, type=1 and decimal `boardid` is stored at `+48`. Else `rt_util_flashEnv_get("boardmodel")` into the name and type stays 0. Image has no `idType`/`boardid`, and has `boardmodel=RTL9303_8264B_2XGE`.
3. Name is compared with the sentinel at `.data+0x730` (type word `2`, string `default`). Not equal, so `hwp_profile_find` selects the list entry whose name matches.
4. Runtime override that this binary actually implements: change U-Boot `boardmodel` (name) or set `idType=integer` plus `boardid`. Not a `board=` key.

`RTL9303_8264B_2XGE` vs `RTL9303_8264B_8261BE_2XGE` over the 1860-byte span of the former: only diffs are the name (`+0x12..+0x1c`), id byte (`+0x33`: `0x42` vs `0x44`), and the swDescp pointer low bytes (`+0x3e..+0x3f`, expected because the embedded descriptor sits at a different address). Port/serdes payload in that window matches. The `8261BE` name does not encode a different port table here.

### OEM board table (`board_conf.ko`)

`boardModelConfTbl` is `.rodata+0`, 11 × 576 bytes. Word 0 is the id. Strings at `+4` (OEM name), `+0x24` (`RTL9303`), `+0x3c` (OEM profile alias). Byte `+0x34` is 9. Reloc at `+0x38` is `oidAry_rtk931x` for every named row (9 words `1,3,6,1,4,1,0x6a92,1,3`). Rest of each 576-byte record is zero. This table has no port or GPIO pointers.

| idx | id | OEM name | alias at +0x3c |
|---|---|---|---|
| 0 | `0x008de840` | `@GS9303-08` | `RTL9303-8x8261N` |
| 1 | `0x008de832` | `2GS9303-08` | `RTL9302D-24MGE-4XGE` |
| 2 | `0x008de82f` | `/GS9303-08` | `RTL9303-8XGE` |
| 3 | `0x008de841` | `AGS9303-08` | `RTL9302D-16MGE-4XGE` |
| 4 | `0x008de842` | `BGS9303-08` | `RTL9303-4XGE-2XGEF` |
| 5 | `0x008de843` | `CGS9303-08` | `RTL9302D-24MGE-4XGE` |
| 6 | `0x008de845` | `EGS9303-08` | `RTL9303-5XGE` |
| 7 | `0x008de846` | `FGS9303-08` | `RTL9303-7XGE-XGEF` |
| 8 | `0x008de847` | `GGS9303-08` | `RTL9303-7XGE-XGEF_POE` |
| 9 | `0x008de848` | `HGS9303-08` | `RTL9303-8XGE` |
| 10 | `0x008de849` | empty | sentinel |

`sys_boardModel_init` (`text+0x2d0`):
- Reads `hwp_myHwProfile+48` and matches it to word 0. Entry 0 is a special-case compare; the loop starts at entry 1. Index math `v1*(64+512)` is the 576-byte stride and matches the found row (checked for entry 4).
- `board_gpio_model_init` is `jr ra` / return 0. Dead.
- Copies 9 OID words to struct offset 584.
- Reads MTD index 2, 4096 bytes (`mtd_read` with 64-bit `loff_t`, from=0). Scans for key `$LC0` = `board` then `=`, `simple_strtol` base 10. The parsed integer is stored at `sp+736` and never read. `sys_boardModel_set` is then called with the struct already filled from the hwp-id match. The `board=` parse does not change the selected model in this binary. Image has no `board=` key anyway.
- `init_module` sets `glbBoardModel+576` to 4 before init. That word is outside the 576-byte copied record and is not the profile id.

`board_conf_get` walks `boardMap` (`.data+0xc0`, 352 bytes, stride 32) by `sys_boardModelId_ret()` (word 0 of `glbBoardModel`). Sentinel `0x008de849`. Row for `0x008de842` at `+0xa0`:

| + | target |
|---|---|
| 0 | `0x008de842` |
| 4 | `portConf_9303M4XC2XF` |
| 8 | `fiberConf_9303M4XC2XF` |
| 12 | `ledConf_9303M4XC` |
| 16 | `buttonConf_9303M5XC2XF` (not `buttonConf_9303M4XC2XF`) |
| 20 | `encryptConf_9303M4XC2XF` |
| 24 | `fan9303M4XC2XF` |
| 28 | `temp9303M5XC2XF` (no `temp9303M4XC2XF` symbol) |

`buttonConf_9303M4XC2XF` and `buttonConf_9303M5XC2XF` are identical 16 bytes (`... 04 ...`). Symbol cross-wire is real; button bytes are not. `temp9303M5XC2XF` is 4 zero bytes.

Link that is actually in the image, not a name guess: env `boardmodel=RTL9303_8264B_2XGE` → rtcore profile id `0x008de842` → `boardMap` row → `portConf_9303M4XC2XF` / fiber tables. Alias string `RTL9303-4XGE-2XGEF` is a label in the OEM record, not the SDK object name.

## TE / MAC / SerDes / PHY

SDK port records are 20 bytes, scanned from `swDescp+20` until mac byte `>= 63` or `0xff`. Confirmed consumers in `_hwp_port_parse` / `_hwp_serdes_parse`:

- `+0` mac id (`< 64`)
- `+1` phy index; `0xff` or `99` means no PHY
- `+3` phy address, stored into the mac→phyAddr table
- `+4` big-endian word: serdes **index** into the id table when `>= 0` and not `255`; negative would be a lane bitmask (not used by these records)
- `+8/+9/+10` attribute bytes. Parser tests bits; names not in a header here. Comparison: `RTL9303_8XGE` user ports are all phy `0xff` and byte `+10 = 0x08`. On `8264B_2XGE`, phy-attached ports have `+10 = 0x01` and serdes-only ports have `+10 = 0x08`. So `+10 = 0x08` tracks "no external PHY / serdes medium" and `+10 = 0x01` tracks "PHY attached". Not a scope measurement.
- mac `0x1c` has `+8 = 0x08` and serdes word `0xff` on 8XGE, 8264B_2XGE, and 8261BE_2XGE. Treated as CPU/internal, not a front-panel port.

`swDescp` for `RTL9303_8264B_2XGE` is profile `+0x58` (pointer at `+0x3c`). Chip word `0x93036810`. Serdes id table at `swDescp+0x514`, stride 2, ids at the odd bytes until `0xff`. Static ids: `2,3,4,5,6,7,8,9` (count 8). Even bytes between them (`0x72,0x71,0x72,0x71,0x70,0x08,0x08,0x08`) are not read by that scan. Not polarity.

Port records (profile `+0x6c` onward):

| mac | phy_idx | byte +2 (unread by port parser) | phy_addr | sds index | sds id | byte +10 |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 2 | 0x01 |
| 8 | 0 | 0 | 1 | 1 | 3 | 0x01 |
| 16 | 0 | 0 | 2 | 2 | 4 | 0x01 |
| 20 | 0 | 0 | 3 | 3 | 5 | 0x01 |
| 24 | 1 | 1 | 0 | 4 | 6 | 0x01 |
| 25 | 0xff | 0xff | 0xff | 5 | 7 | 0x08 |
| 26 | 0xff | 0xff | 0xff | 6 | 8 | 0x08 |
| 27 | 0xff | 0xff | 0xff | 7 | 9 | 0x08 |
| 28 | 0xff | 0xff | 0xff | none (`0xff`) | none | 0xff |

`portConf_9303M4XC2XF` is 6 × 32-byte records then `0xffff` terminator. `board_conf_port_get` matches record `+8` and `+12` (not `+4`). All six have `+8 = 0`. `+12` values are the SDK mac ids. `+4` is 1..6. `+16` is 0,0,0,0,1,1.

| logical `+4` | unit `+8` | mac `+12` | `+16` | SDK phy/sds from the table above |
|---|---|---|---|---|
| 1 | 0 | 0 | 0 | phy 0 addr 0, sds id 2, PHY-attached |
| 2 | 0 | 8 | 0 | phy 0 addr 1, sds id 3 |
| 3 | 0 | 16 | 0 | phy 0 addr 2, sds id 4 |
| 4 | 0 | 20 | 0 | phy 0 addr 3, sds id 5 |
| 5 | 0 | 25 | 1 | no PHY, sds id 7, serdes medium |
| 6 | 0 | 26 | 1 | no PHY, sds id 8, serdes medium |

No external caller of `board_conf_port_get` was found (only an address reloc inside `ski_board_cmd_mux`). The 1..6 field is the only 6-wide front-panel index in this table and matches the live TE1..TE6 count. It is the OEM logical port, not a second mac id. Mac 24 (second PHY, addr 0, sds id 6), mac 27 (sds id 9), and mac 28 are in the SDK profile and **absent** from `portConf`. They are not TE1..TE6. Do not map TE5/TE6 onto mac 24/27.

MDIO: phy addresses above are what the parser stores as phy address. Which MDIO bus byte `+2` selects was not consumed by `_hwp_port_parse`. Bus number is unknown. No separate PHY chip-id table was decoded beyond the port records (8264 vs 8261 is a name, not a second port map).

## SFP GPIO / I2C

`fiberConf_9303M4XC2XF` is 12 bytes: count `2`, reloc to `detectConf_9303M4XC2XF`, reloc to `opticalConf_9303M4XC2XF`. Raw zeros at `+4/+8` are addends, not NULL.

`detectConf` is 2 × 28 bytes. `board_fiber_oeStatus_get` uses record `+12==1` and GPIO pointer at `+20` (TX disable / OE). `board_fiber_losStatus_get` uses record `+16==1` and GPIO pointer at `+24`. Both flags are 1. Record `+0` is 4 then 5 (0-based indexes of logical ports 5 and 6, if that convention holds). Those GPIO objects in `boardGpio_930x` are zero except word 0 = slot id. `gpio_init` would see pin 0 if called on the static object. The real pin program is `board_gpio_init`, not those static zeros.

`board_gpio_init` compares the hwp id. The only branch to `text+0x2684` is `id == 0x008de83b+7` = `0x008de842`. That block registers:

| role string | GPIO number (a0 and a2) | a1 |
|---|---|---|
| `MDO_FX_0` | 14 | 0 |
| `LOS_FX_0` | 13 | 0 |
| `TX_DIS_FX_0` | 15 | 0 |
| `MDO_FX_1` | 17 | 0 |
| `LOS_FX_1` | 16 | 0 |
| `TX_DIS_FX_1` | 18 | 0 |

Helpers at `text+0x15d0` (MDO), `0x1724` (LOS), `0x1878` (TX_DIS) build a 92-byte descriptor, index `pin*92`, and copy it if slot word 0 already equals the pin id (static slots 13..18 do). `a1=0` is stored at descriptor `+8`. Descriptor `+44` is left 0 by memset; the helpers do not store it. `losStatus_get` / `oeStatus_get` invert the raw GPIO when descriptor `+44` is 0, and do not invert if it is nonzero (double invert back to raw). So the OEM LOS and TX-disable status path treats those pins as active-low **in software**. That is not a scope measurement. MOD-DEF/present polarity was not traced in `_fiber_present_detect_monitor`. Direction (in vs out) is implied by three different callees, not by a decoded direction enum.

FX_0 vs TE5 is an index inference (first fiber in the 6-port table, detect record `+0 = 4`), not a string that says TE5. Static config does not by itself prove the cage is wired to that GPIO; it proves the firmware will program those numbers for this profile id.

`opticalConf`: `i2c_dev_init(optical+4 + i*52)` for count 2. Each record word 0 is 0 then 1 (`< 32`). Word at record `+8` is `0x50` on both (SFP EEPROM address). Record `+4` is 2. Record `+0x10` is `0x14`. Record `+0x20/+0x24` are `8/9` then `8/10`. `drv_i2c_dev_init` memcpy's 48 bytes and calls an ops function pointer; that ops body was not decoded. Do not treat 8/9/10 as proven SCL/SDA. Two I2C devices at address `0x50` are in the table. Controller vs bitbang is unresolved.

## Uncertainties (do not upgrade)

- CLI Board Value integer source.
- Exact `rt_util_flashEnv_get` flash offset (both copies agree).
- Byte `+2` of the SDK port record (possible SMI/bus, unread by `_hwp_port_parse`).
- Serdes even-byte side values; no polarity reader found.
- Whether mac 24 is an unwired 8261 footprint or a management PHY. It is not a TE port in `portConf`.
- I2C pins 8/9 and 8/10.
- Electrical polarity and which cage is FX_0.
- `encryptConf` / fan / LED GPIO not needed for the port map; not fully decoded.
- No UART, no live register read, no claim the running device still has this env if it was changed after the programmer reads.

## What is solid enough to carry into Phase 2

Active image selector is `boardmodel=RTL9303_8264B_2XGE`, SDK id `0x008de842`, OEM row `BGS9303-08` / alias `RTL9303-4XGE-2XGEF`, front-panel logical 1..6 → mac 0,8,16,20,25,26, with 25/26 as the two serdes ports (sds id 7 and 8). SFP software GPIOs for this id are MDO 14/17, LOS 13/16, TX_DIS 15/18, status path active-low. Not a boot/flash approval.
