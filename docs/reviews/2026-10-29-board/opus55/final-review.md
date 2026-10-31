# LG510S independent dump/hardware review — Opus 5.5 seat

## Seat, tools, seal
- **Model/seat:** Opus 5.5 (`anthropic/claude-opus-5-5`). **Worktree:** `review/board-evidence-opus55` at `6f7d67b`. I made no tracked-file, index or HEAD changes. My only writes are under the ignored `scratch/` directory.
- **Tools used:**
  - Pinned VM MIPS binutils, through the contract's transport helper (`objdump -dr`, `readelf -SrsW`).
  - macOS `nm`.
  - My own Python ELF32-BE REL decoder (`scratch/elfdump.py`). It applies the implicit REL addends.
  - My own CRC/env scanner (`scratch/envscan.py`). It prints only allowlisted keys and reports any other key as present or absent.
  - Python `zlib`/`lzma` for the CRC and decompression checks.
- **Not done:** no device access, build, test or lint run. No module was loaded or executed. Nothing was uploaded.
- **Bytes inspected:**
  - All three dumps hash to `7da7358e…2dc48`.
  - Modules: `board_conf.ko` (`027521d7…`), `rtcore.ko` (`d81ba50d…`), `ski.ko` (`ab5244c2…`), `rtk.ko` (`d1a4b565…`). `board.ko` (`cf410968…`) was hashed only, not decoded.
  - Partitions/images: `uboot.bin`, the RUNTIME header and the LZMA payload, `vmlinux.bin`.
  - Files: `rootfs/etc/rc`, plus targeted string hits in `libclicmd`/`libsal`.
- **Blind notes:** `scratch/blind-notes.md`, SHA-256 `b300d15bd72d655749ab0a8057107836776f02843eefe81f4c76bec045ce3e40`. I sealed it read-only at 2026-10-29T22:17:25Z, before opening any repository README, doc or prior report.
  - The parent's later clarification allows outputting `idType`/`boardid`. I had already presence-checked both before sealing: both are **absent**, so there are no values to report.

## Selection chain (static; traced through the code)
1. **Load order.** `rc` loads `rtcore`, then `rtk`, `rtdrv`, `board_conf`, `net`, `defdb`, `ksi`, `osal`, `ski`, `board`, then the `l2g_*` modules. `/mnt/ski_param` can only set `ski`'s `dbgMaskStr`/`ioctl_major`. `rtcore`'s only parameter is `rtcore_num`.
2. **`rtcore` `hwp_probe` (`0x16df0`).**
   - The forced identifier at `.data+0x764` is type 2 ("Default None"), so no profile is forced.
   - `hwp_forceProfile` is neither exported nor called.
   - Lookup order in `ioal_param_hwpIdKey_get` (`0x18620`): it reads `idType`; only if `idType == "integer"` does it read a decimal `boardid`. Otherwise it reads `boardmodel`.
   - All of these come from the MTD named `BDINFO` (`rt_util_flashEnv_get` `0x1838`). That read requires a valid CRC32.
3. **Env actually read.**
   - BDINFO is at flash `0x0e0000`, 64 KiB, and its CRC is valid.
   - `boardmodel=RTL9303_8264B_2XGE`. `idType`/`boardid` are absent; `bootargs` is absent.
   - `bootcmd=boota`, `bootdelay=1`, `baudrate=115200`.
4. **Profile match.** `hwp_profile_find` does a 44-character name compare. Exactly one of the 40 profiles matches: list index 33, at `.data+0x33dc`, with ID `0x008de842` (9300034).
5. **`board_conf.ko`.**
   - It reads `hwp_myHwProfile+0x30` and looks it up in `boardModelConfTbl` entry 4 (`.rodata+0x900`, "RTL9303-4XGE-2XGEF").
   - `boardMap` row `.data+0x160` points to `portConf_9303M4XC2XF`, `fiberConf_9303M4XC2XF`, `ledConf_9303M4XC`, `buttonConf_9303M5XC2XF`, `encryptConf_9303M4XC2XF`, `fan9303M4XC2XF` and `temp9303M5XC2XF`. These come from R_MIPS_32 relocations with addend 0.
6. **Runtime overrides that exist.** Editing BDINFO's `boardmodel`, or adding `idType=integer` plus `boardid`. If BDINFO is missing or its CRC is bad, rtcore takes the `hwp_useDefHwp` path; I did not trace that path. The CLI "Board Value 1" is **not** the SDK ID, and I did not trace its source.

## Per-port and SFP mapping (static)

`portConf_9303M4XC2XF` (`.rodata+0x1f00`) has 32-byte rows: {type, usr, unit, MAC, media, speed, duplex, attr}.
- The row layout is proven by the vendor formatter at `.text 0x5f0`.
- `ski` `board_conf_port_get` (`0x70da0`) matches on `(unit, MAC)`, which confirms that word 3 is the MAC.
- `ski` `sys_physic_portview_init` (`0xb4cc`) uses the row index as the logical port (lport).

PHY, MDIO and SerDes values come from rtcore's hwp profile, with port-row layout taken from `hwp_parsedInfo_show`. The hwp lookup tables: the PHY table is at `swDescp+1424` and the type names at `.rodata+0xb20`; the SerDes table is at `swDescp+1301`, as 2-byte {id, mode} pairs.

| CLI* | lport | MAC | Media | PHY / SMI bus / MDIO addr | SerDes (hwp mode byte) |
|---|---|---|---|---|---|
| TE1 | 0 | 0 | Cu 10G | RTL8264B / 0 / 0 | SDS2 (`0x72`) |
| TE2 | 1 | 8 | Cu | RTL8264B / 0 / 1 | SDS3 (`0x71`) |
| TE3 | 2 | 16 | Cu | RTL8264B / 0 / 2 | SDS4 (`0x72`) |
| TE4 | 3 | 20 | Cu | RTL8264B / 0 / 3 | SDS5 (`0x71`) |
| TE5 | 4 | 25 | SFP+ | — | SDS7 (`0x08`) |
| TE6 | 5 | 26 | SFP+ | — | SDS8 (`0x08`) |

\* TEn = usr n = lport n−1 is an [INFERENCE]: I did not trace the CLI naming. The six-row count matches the live TE1..TE6.

**hwp profile is a superset of the front panel.** It also declares:
- MAC24: an RTL8261BE on SMI bus 1, address 0, using SDS6 (mode `0x70`).
- MAC27: SDS9 (mode `0x08`).
- CPU port: MAC28.

`board_conf` does not expose MAC24 or MAC27. The loader carries an identical copy of the profile, but it comes from the same SDK database, so it is **not independent**.

**SFP control.** The boardGpio entries are filled by `board_gpio_init` case `0x8de842` (`.text 0x2684`), in the internal SoC GPIO domain (dev 0). Expander devices 1–3 are not enabled, because `gGpioIdSum` is 32.

| Cage | I²C @ `0x50` (SW bit-bang) | MOD_ABS ("MDO") | LOS | TX_DISABLE |
|---|---|---|---|---|
| TE5 / lport 4 | SCL 8, SDA 9 | 14 | 13 | 15 [cage binding is an INFERENCE] |
| TE6 / lport 5 | SCL 8 (shared), SDA 10 | 17 | 16 | 18 [cage binding is an INFERENCE] |

**How each column is bound:**
- **I²C:** `opticalConf` row+4 is passed to `drv_i2c_dev_init` and then `r9300_i2c_dev_init` (`rtcore 0x58dc`). Type 2 calls `drv_software_i2c_init(sclDev, sclPin, sdaDev, sdaPin)`.
- **MDO/LOS:** bound to each cage through `detectConf` (`.rodata+0x38f0`). It points at `boardGpio_930x` entries 14/13 and 17/16 (each pointer is entry+4). The `ski` consumers `board_fiber_oeStatus_get` (`0x770c0`) and `board_fiber_losStatus_get` (`0x771e4`) read these entries.
- **TX_DIS:** only `board_gpio_init` touches GPIOs 15 and 18. They are set to output, default 0, with the active-high flag set. Nothing imports `boardGpio`/`gpBoardGpio`, and `ski` has no TX-disable logic. The cage assignment therefore rests only on the `_FX_0`/`_FX_1` label suffixes.

**Polarity (traced):**
- The flag at entry+48 is 0 for MDO and LOS. The consumers then compute status as `(pin == 0)`. The flag is 1 for TX_DIS, which starts low.
- Comparing with the live CLI (TE6 absent / LOS asserted, TE5 present / LOS normal) gives [INFERENCE]: MOD_ABS is active-low and LOS is active-high (MSA-standard). TX_DIS = 0 means the laser is on.

**Other board I/O found:**
- **SFP pinmux.** For this ID, `0x19d4` clears bit 10 of switch register `0x200`. rtk's `rtk_longan_reg_list` names that register `GPIO_SEL_CTRL`, and bit 10 is `GPIO18_USBLED_SEL`. This frees GPIO18 for the TE6 TX_DISABLE line.
- **Reset button:** GPIO5, input, default 1. Its active level was not derived.
- **Other software-I²C devices:**
  - "encrypt" authentication chip at `0x50`, SCL 3, SDA 4.
  - ADT7476 fan/temperature controller at `0x2e`, SCL 8, SDA 11. GPIO8 is therefore shared by three buses.
  - Configuration alone does not prove either chip is fitted.
- **Board-specific SerDes polarity/tuning: none in firmware.** The SerDes descriptor has no polarity field. rtk's `conf_rtl9300_cust_board_list` is never stored to: its 12 relocations are all loads, so it is always NULL. Polarity APIs are reachable only from the interactive `diag`.

## Flash, image and loader (static)
- **Kernel MTD names, in order:** LOADER, BDINFO, SYSINFO, JFFS2 CFG, JFFS2 LOG, RUNTIME, OEMINFO. The `mtd_partition` table is at VA `0x80455450`, with offsets filled at runtime.
- **Layout table at VA `0x80455530`, 16 MiB row:**

| Partition | Offset | Size |
|---|---|---|
| LOADER | 0 | `0xe0000` |
| BDINFO | `0xe0000` | 64 KiB |
| SYSINFO | `0xf0000` | 64 KiB (erased) |
| JFFS2 CFG | `0x100000` | 1 MiB |
| JFFS2 LOG | `0x200000` | 1 MiB |
| RUNTIME | `0x300000` | 12 MiB |
| OEMINFO | `0xf00000` | 1 MiB |

  - The flash contents agree: a CRC-valid env at `0xe0000`, JFFS2 magic at `0x100000`, `0x200000` and `0xf00000`, and the image at `0x300000`.
  - `jffs2-b.bin` is OEMINFO, at `0xf00000`. `jffs2-a.bin` spans both the CFG and LOG partitions.
  - Which table row is chosen at runtime was not traced.
- **RUNTIME header:** uImage layout with magic `0x83800000`. Both hcrc (`a80f0d16`) and dcrc (`6f51b869`) verify. Size `0x7eae10`, load `0x80000000`, entry `0x803345b0`, LZMA, name 1.1.1.34. The LZMA output equals `vmlinux.bin` byte for byte, and the gzip at `0x4888bc` equals `initramfs.cpio`.
- **Loader:** U-Boot 2011.12 (1.0.0.2, built Sep 11 2024). Its default env has `bootargs` empty and the same `boardmodel`. The `boota` image-acceptance logic was not traced.
- **Kernel built-in cmdline:** `console=ttyS0,115200 mem=128M`.

## Claim status
- **Static facts (confirmed):**
  - The 6-port MAC map.
  - Profile `0x8de842` and its selection chain.
  - The SFP I²C, MDO and LOS GPIO numbers and their bindings.
  - The internal-GPIO, software-I²C architecture.
  - Image magic, header and CRCs.
  - That the doc's numbers are SDK switch ports, not MDIO addresses or SerDes lanes.
- **Live observations only:** TE1/TE5 links, MemTotal, Board Value 1, CLI LOS/presence text.
- **Inference:**
  - TEn = lport n−1.
  - TX_DIS cage binding.
  - MSA-sense polarity.
  - Linux GPIO linear numbering equals the SDK index. `ski` converts n to bank (n>>3) and pin (n&7).
  - SerDes mode families: `0x70`–`0x73` maps to `rt_serdesMode` 28 (USXGMII-like) and `0x08` is 10G-fiber-class. I could not recover the mode names.
- **Unknown:**
  - PCB lane polarity.
  - Whether MAC24/27 hardware exists.
  - SerDes mode names, including why the modes alternate `0x72`/`0x71`.
  - LED wiring.
  - Physical DRAM size.
  - Board Value source.
  - Loader image acceptance.
- **Bottom line:** agreement between documents or reviewers is not hardware validation.

## Required doc corrections (graded by what a DTS/image built from the doc would get wrong)
1. **Medium — `board4-investigation.md` L73–76.** The TX_DISABLE column is presented at the same evidence level as I²C, MDO and LOS. Its cage binding is a label-suffix **[INFERENCE]**, with no consumer: no module imports `boardGpio`/`gpBoardGpio`, and only `board_gpio_init` sets 15/18 as OUT=0.
2. **Medium — L78 and L161 ("signal polarity…still need evidence").** Partly derivable:
   - The consumer reads MDO and LOS as active-low, and flags TX_DIS active-high (offsets cited above).
   - The live CLI correlation then supports MOD_ABS active-low and LOS active-high (MSA). Keep the INFERENCE tag on that MSA reading.
3. **Medium — L80 (register `0x200` meaning "not established").** It is `GPIO_SEL_CTRL.GPIO18_USBLED_SEL`, per rtk's own register DB, which frees GPIO18. A DTS or pinctrl that omits this leaves the TE6 TX_DISABLE line ineffective.
4. **Medium — L91, L97, L161; `project-reassessment.md` L63.** "PHY/SerDes details unverified / still need evidence" understates what is recoverable. Static candidates exist: RTL8264B on SMI0 addresses 0–3, SDS2–5 for the copper ports, SDS7/8 for the SFP+ cages, modes as tabled above. They are static only, and still need hardware confirmation.
5. **Medium — `firmware.md` L51.** "quad RTL8264B / two 10G SerDes" is read from the profile name. The profile's actual contents add MAC24 (RTL8261BE, SMI1 address 0, SDS6) and a third SerDes port, MAC27/SDS9. A DTS generated from the hwp profile would add phantom ports. A DTS based on the name would not reveal that the vendor SDK actively drives SMI1, SDS6 and SDS9.
6. **Low — L65 ("MTD index 2 … needs partition map").**
   - That read fetches only `bootmsg`, from SYSINFO (index 2 by table order) [INFERENCE: Linux 3.18 registration order]. SYSINFO is erased.
   - The board comes from the MTD named `BDINFO`, CRC-checked. Step 1 of the chain at L59 should cite that BDINFO env specifically, including that `idType`/`boardid` are absent.
7. **Low/Medium — L95, L101; `firmware.md` L21–24.**
   - A static layout table exists, and the flash contents corroborate it.
   - `0x100000–0x2fffff` is **two** JFFS2 partitions (CFG and LOG). `0xf00000` is OEMINFO. `0x0–0xfffff` splits into LOADER, BDINFO and SYSINFO.
   - Still keep partitions read-only until `/proc/mtd` is seen.
8. **Low — L25.** The stock kernel has `mem=128M` built in. MemTotal therefore cannot measure physical DRAM: it only shows at least 128 MiB. Keeping ≤128 MiB is still correct.
9. **Hygiene — `firmware.md` L47–48.** These lines publish the network env variables `ipaddr` and `serverip`, contrary to the env allowlist.

No numeric disagreement was found in the doc's port map or its SFP GPIO and I²C numbers.

## New recoverable facts (beyond the docs)
- PHY/MDIO and SerDes assignments for every port.
- The RTL8261BE on MAC24 and the MAC27 SerDes port in the vendor profile.
- The absence of any board-specific SerDes configuration.
- The meaning of `GPIO_SEL_CTRL` bit 10.
- MDO/LOS/TX_DIS read and drive sense.
- Reset button on GPIO5.
- ADT7476 and authentication-chip software-I²C buses.
- GPIO8 shared as SCL by three buses. Two separate Linux `i2c-gpio` nodes cannot share it.
- Verified uImage CRCs, the static flash layout table and `mem=128M`.

## Candidate definition now vs later (no boot/flash approval)
- **Usable now, as static vendor-config candidates:**
  - Front ports at MAC 0, 8, 16, 20, 25, 26.
  - RTL8264B on SMI0 addresses 0–3 for the copper ports.
  - SFP+ on SDS7/SDS8.
  - SFP I²C at `0x50`; SCL GPIO8; SDA GPIO9 (TE5) and GPIO10 (TE6).
  - mod-def0 on GPIO14/17; LOS on GPIO13/16; TX_DISABLE on GPIO15/18 (with the TX_DIS cage caveat).
  - Memory ≤128 MiB.
  - All flash partitions read-only.
- **Needs UART or hardware evidence first:**
  - SerDes modes and polarity.
  - RTL8264B firmware/patch.
  - Whether MAC24/27 are fitted (exclude them for now).
  - The shared-SCL I²C binding choice.
  - LEDs, fan/ADT7476, button active level.
  - Physical RAM.
  - Loader acceptance of any image format other than the stock one.

## Declined to judge / limits
- I did not judge: SSH host-key match, flash part marking, rebadge claims, U-Boot `tftp`/`bootm` strings, licensing, the reference Sirivision DTS contents (not opened), or any of `offline-validation.md`'s QEMU results.
- **Areas I did not trace:**
  - The default-HWP fallback path.
  - libclicmd's "Board Value" source.
  - Which runtime partition-layout row is chosen.
  - RTL8264B-side lane configuration.
  - Exact enum names for the SerDes modes.
- **Tool notes:** Xcode objdump cannot disassemble MIPS, so I used the VM helper as instructed. Apart from a harmless BrokenPipe from `head`, nothing failed. No tests were run and no device was touched.

**Verdict:** The doc's profile selection, port map and SFP GPIO/I²C numbers are correct as static vendor configuration. Several items it labels "unknown" are statically recoverable: PHY/SMI addresses, SerDes indices, pinmux and signal sense. Two items are overstated: the TX_DISABLE cage binding is inference only, and the profile name hides two extra vendor-profile ports. Neither the docs nor this review constitute hardware validation.
