# Independent review — Grok 4.7

Seat: Grok 4.7. Worktree `board-evidence-grok47` at `6f7d67b6fd378981874d354b512495b99c31d5bc`. Not the coordinator.

Tools: local Python ELF/reloc decoder, `strings`/`shasum`; MIPS `objdump`/`nm`/`readelf` via the pinned helper on the build VM as `rtlp-builder`. No switch, no build, no docs until notes were sealed.

Blind notes: `scratch/blind-notes.md`, SHA256 `c6e5e70b08bbe3e848c997490372820ca0cc219c6d2110aea805f78929c687a8`, written and hashed before any `docs/` or README read. `idType`/`boardid` absence was already in those notes; the later selector clarification does not change it.

Bytes: three 16 MiB reads, SHA256 `7da7358efce84338f72d58d07bf748714e619b2d576adc144080b99a8f42dc48`. `board_conf.ko` `027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70`. `rtcore.ko` `d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4`.

## Independent mapping

Selection, not a name guess: both U-Boot env copies (`0xc7d16`, `0xe0014`) have `boardmodel=RTL9303_8264B_2XGE`. No `idType=` or `boardid=`. `hwp_forcedProfile_get` sees flag `2` and returns `-1`. `ioal_param_hwpIdKey_get` then uses `boardmodel`. That name is rtcore `.data+0x33dc`, id at `+0x30` = `0x008de842`. `sys_boardModel_init` matches `hwp_myHwProfile+0x30` to `boardModelConfTbl` entry 4 (`.rodata+0x900`): OEM `BGS9303-08`, alias `RTL9303-4XGE-2XGEF`. `board_conf_get` then uses `boardMap` row `.data+0x160` (symbol `boardMap` itself is `.data+0xc0`). CLI `Board Value : %d` was not traced; it is not this id.

Formatter at `board_conf.ko` `text+0x5f0` prints `Type Usr Phy ...` with `%-11s %-4u (%-1u) %-3u ...`. Usr is row `+4`. The column headed Phy is row `+12`. Those values are SDK mac ids, not MDIO addresses. Header word "Phy" is a misleading label. The document's reading is right.

| CLI | media from row `+16` | SDK mac (`+12`) | phy_idx / phy_addr | SerDes id |
|---|---|---|---|---|
| TE1 | 0, PHY-attached (`port +10 = 0x01`) | 0 | 0 / 0 | 2 |
| TE2 | 0 | 8 | 0 / 1 | 3 |
| TE3 | 0 | 16 | 0 / 2 | 4 |
| TE4 | 0 | 20 | 0 / 3 | 5 |
| TE5 | 1, no PHY (`+10 = 0x08`) | 25 | none | 7 |
| TE6 | 1, no PHY | 26 | none | 8 |

SerDes ids are the odd bytes of `swDescp+0x514` (`2,3,4,5,6,7,8,9`); the port record `+4` word is the index, not the id. `+10=0x08` matches every user port of `RTL9303_8XGE` (all phy `0xff`). `+10=0x01` matches PHY-attached ports here. Byte `+2` of the port record is unread by `_hwp_port_parse`; do not call it an MDIO bus.

Not front-panel, but in the same profile: mac 24 (phy_idx 1, phy_addr 0, sds id 6), mac 27 (no PHY, sds id 9), mac 28 (serdes word `0xff`, byte `+8=0x08`, CPU-like). `RTL9303_8264B_8261BE_2XGE` (id `0x008de844`) has the same port/serdes payload and is **absent** from `boardModelConfTbl`. Forcing that name would miss the OEM GPIO/port row.

SFP, only for id `0x008de842`, `board_gpio_init` at `text+0x2684` (sole branch):

| cage | SCL | SDA | MDO | LOS | TX_DIS |
|---|---|---|---|---|---|
| TE5 / FX_0 | internal GPIO 8 | 9 | 14 | 13 | 15 |
| TE6 / FX_1 | internal GPIO 8 | 10 | 17 | 16 | 18 |

SCL/SDA: `r9300_i2c_dev_init` calls `drv_software_i2c_init` with device `+32` (8) and `+36` (9 then 10) when the unit interface word `+8 == 2`. The write path sets the `+36` pin to output before shifting data; 8 is the other, shared line. EEPROM address `0x50` is device `+8`, passed to `drv_software_i2c_type_set`. Delay field is device `+16` = 20; unit unknown. FX_0/FX_1 → TE5/TE6 is 0-based fiber API index 4/5 (`rsd_fiber_*` bounds-checks against `logic_port_count-1` and does not subtract 1) lined up with 1-based `portConf` users 5 and 6. Not a string that says TE5.

LOS/TX_DIS software polarity: registration leaves gpio descriptor `+44` at 0; `board_fiber_losStatus_get` / `oeStatus_get` invert when that field is 0. Active-low in the vendor status path. Not a scope result. MOD-DEF polarity not traced. Static `boardGpio_930x` slots are zeros apart from the slot id; the pins above come from the init calls, not from those zeros.

Also confirmed, not a recommendation: that same branch calls `ioal_mem32_read/write` of offset `0x200`, AND with `0xfffffbff` (clears bit 10). Meaning unknown.

## Claim grades

| claim | grade |
|---|---|
| TE1..TE6 → mac 0, 8, 16, 20, 25, 26; not MDIO, not SerDes lane | static fact. Formatter + profile. Live media/link states were not re-queried |
| `boardmodel` → profile `0x33dc` id `0x008de842` → OEM alias `RTL9303-4XGE-2XGEF` | static fact |
| Board Value 1 ≠ that id | confirmed as a distinction; the integer source is still unknown |
| SFP GPIO and software I²C pins in the table above | static fact, not continuity |
| software LOS/TX_DIS active-low | static fact the docs leave open |
| PHY addresses and SerDes ids above | static fact the docs call unverified / still needed |
| mac 24 and 27 exist and are not TE ports | static fact, omitted |
| `0x200` bit 10 clear | disassembly fact; meaning unknown. Doc is accurate |
| image magic `0x83800000`, size word `0x007eae10` (8302096), load `0x80000000`, entry `0x803345b0`, name `1.1.1.34` | static fact from dump `0x300000` |
| loader `1.0.0.2`, `bootcmd=boota`, `baudrate=115200`, `bootdelay=1` | static fact |
| live SSH, host key, link states, RAM 125196 KB, fiber module present/absent | live-observed by the author. This seat did not open the switch. Not reconfirmed |
| QEMU/Malta results in `offline-validation.md` | declined. Not re-run |
| JFFS2 file contents, flash chip marking, UART voltage | declined. Not inspected |
| env `ipaddr`/`serverip` printed in `firmware.md` | not re-read and not repeated |

## Corrections

1. `docs/board4-investigation.md` line that places `boardMap` at `.data + 0x160`. The symbol is `.data+0xc0`, size 352, stride 32. `.data+0x160` is the `0x008de842` **row** (`boardMap+0xa0`). Bindings named there are the right row. Treating `0x160` as the table base and then adding `0xa0` would skip to a later board.

2. Same file, comparison table and next gate: "PHY/SerDes details still unverified" / "still need evidence". The profile already has phy_addr and SerDes id (table above). They are not live-validated and must not be copied from the Sirivision DTS. They are not unknowable. A candidate DTS can carry them as static-only. Polarity of SerDes is still unknown (even bytes `0x72/0x71/0x70/0x08` beside the id list are unread).

3. Same file, SFP polarity "remain to be validated". Electrical polarity is still open. Vendor LOS and TX_DIS status code treats descriptor `+44==0` as inverted. Do not emit `GPIO_ACTIVE_HIGH` from silence.

4. `docs/firmware.md` "quad RTL8264B / two 10G SerDes" drops mac 24 (second PHY, sds 6) and mac 27 (sds 9). Fine as a front-panel summary. Wrong if used as the silicon port list. `0x008de844` is the name that mentions 8261BE; it is not the selected id, and it is not in the OEM table.

5. `docs/project-reassessment.md` still lists PHY address, SerDes, and SFP I²C/GPIO as unverified. SFP GPIO/I²C and the static PHY/SerDes numbers above supersede that sentence. The no-flash conclusion does not.

6. `sys_boardModel_init` parses MTD device 2 for key `board` and then discards the integer (`sw` to `sp+736`, never read). The image has no `board=` key. Not an override. `idType=integer` + `boardid` is a real override and is unset.

## Candidate definition now vs later

Can enter a candidate, marked static-not-live, no boot/flash approval:

- SoC profile `RTL9303_8264B_2XGE` / id `0x008de842` / OEM alias `RTL9303-4XGE-2XGEF`.
- Six front-panel ports, mac and SerDes id and phy_addr as in the table. Do not publish mac 24 or 27 as panel ports.
- SFP software I²C on GPIO 8 (SCL) + 9/10 (SDA), addr `0x50`; MDO/LOS/TX_DIS pins above; LOS and TX_DIS active-low in vendor status code.
- Image magic `0x83800000` is what the stock header uses. Loader acceptance of any other magic is untested. Do not treat `0x93000000` as known-good.
- Baud 115200 is the env value, not a proven UART session.

Still needs evidence before a DTS is trusted or any boot is approved:

- Live PHY id, MDIO bus (port byte `+2`), SerDes polarity, electrical GPIO polarity, cage continuity.
- Whether mac 24 is an empty footprint or a real PHY.
- RAM map (125196 KB is a live report this seat did not repeat; not a DTS memory node).
- `/proc/mtd` or a loader `mtdparts` that is actually used. Kernel name strings with zero size/offset are not a map. JFFS2 magics at `0x100000` and `0xF00000` only bound regions.
- Loader command that can RAM-boot. `boota` is set; `bootm`/`tftp` support was not executed. This seat did not disassemble the loader command table.
- UART voltage and pinout.

## Declined / limits

No device access, no module load, no QEMU re-run, no JFFS2 read, no credential or identity output. `rt_util_flashEnv_get`'s flash offset was not traced; both env copies agree on `boardmodel`. Interface-type word `== 2` is the gate into `drv_software_i2c_init`; the optical row supplies the pin and address arguments used by that call. I did not dump a separate static proof that the unit interface word is 2 at rest, so a DTS should not treat optical `+4 == 2` as that gate (different field).

## Verdict

The TE↔mac table, profile id, and SFP GPIO/I²C pin table in `board4-investigation.md` match the binaries. The serious gap is calling PHY address and SerDes id unknowable when the selected profile already has them, plus the `boardMap` base address slip. Nothing here approves boot or flash. Consensus with that document is not hardware validation.

## Per-file

| file | verdict |
|---|---|
| `docs/board4-investigation.md` | Port/profile/SFP pin table holds. Fix `boardMap` base. Add static PHY/SerDes. Do not treat software polarity as unknown. |
| `docs/firmware.md` | Header, env `boardmodel`, layout magics hold. "quad 8264B + two SerDes" is a front-panel summary, not the full profile. |
| `docs/project-reassessment.md` | No-flash conclusion holds. PHY/SerDes/SFP "unverified" sentence is stale after the static decode. |
| `docs/offline-validation.md` | No hardware-mapping contradiction found. QEMU results not re-judged. |


## Supplement — OE vs TX_DIS, LOS 1, smi

Sealed notes are unchanged. This corrects the phase-2 report only.

### oeStatus_get is module-present, not TX-disable

`board_fiber_oeStatus_get` reads detect-row `+0x14` (`ski.ko` `text+0x77158`). Those relocs are `boardGpio_930x+0x50c` and `+0x620`, which are 4 bytes into the slots `board_gpio_init` fills for `MDO_FX_0` (GPIO 14) and `MDO_FX_1` (GPIO 17). `gpio_data_get` takes struct `+4` as the device index (`< 9`) and `+8` as the pin; a pointer at slot+4 therefore reads the MDO pin, not the next slot.

`board_fiber_losStatus_get` reads row `+0x18` (`+0x4b0`, `+0x5c4`): LOS slots, GPIO 13 and 16.

TX_DIS GPIO 15 and 18 are only the third registration helper (`text+0x1878`, strings `TX_DIS_FX_0/1`). Neither status getter uses those slots. `rsd_port_fiberRxEnable_set` calls `rtk_port_fiberRxEnable_set` after a logic-to-physical translation; it does not touch the TX_DIS GPIO slots. TX-disable drive stays a registered pin with no traced getter or setter in this pass.

CLI `cmd_cablediag_fiber_module_show` (`libclicmd.so.0.0` `0x36d40`) is the consumer. GOT `-28832(gp)` is `sal_fiber_oeStatus_get`; `-32524(gp)` is `sal_fiber_losStatus_get`. Strings:

| getter result | OE Present | Loss of Signal |
|---|---|---|
| 0 | Remove | Loss |
| 1 | Insert | Nomarl (firmware spelling; means Normal) |
| other | N/S | N/S |

Normalized 1 is not asserted LOS. It is Normal. Asserted loss is 0. Live "LOS normal" is this 1; "LOS asserted" is this 0. OE 1 is Insert (present), OE 0 is Remove.

The invert in both getters (descriptor field at pointer+44 == 0 → one invert; nonzero → invert twice, i.e. raw) applies to the pointer they actually pass. MDO and LOS helpers leave that field 0, so those two reads are inverted in software before the table above. The TX_DIS helper stores 1 at descriptor `+48`, which is the field a slot+4 pointer's `+44` would see, but no status getter uses that pointer. Do not carry the active-low conclusion onto TX-disable drive.

### smi is a labeled descriptor byte, not a traced MDIO bus

`hwp_parsedInfo_show` at `text+0x15228` prints port-descriptor byte `+2` with `smi=%d` (`$LC87`). Byte `+3` is `phy_addr=%d`. `_hwp_port_parse` still has no offset-2 load, so it does not copy that byte into the parsed mac→bus table. The number is statically in the descriptor (0 on mac 0/8/16/20, 1 on mac 24, `0xff` on mac 25/26/27) and the vendor dump calls it smi. That is the printed field, not a proven MDIO controller index. Do not treat it as the effective bus until a PHY access path is shown to use it.


## Supplement 2 — bootmsg store, vendor SMI selector

Sealed notes unchanged. Two corrections to the phase-2 report.

### The MTD integer is bootmsg level, and it is stored

`.rel.text` at `0x478`/`0x488` uses symbol index 14, `st_value 0x80`, string `bootmsg`. A different `$LC0` (index 8, value 0) is `board` and is not this scan. The earlier "discarded `board=` value" claim was the wrong local symbol.

`sys_boardModel_set(sp+56)` copies 672 bytes plus 3 words = 684. The last word is source offset 680, which is `sp+736`. The `sw` at `530` is that word. `sys_board_bootmsgLevel_ret` reads `glbBoardModel+680`. The integer is the boot-message level, not a board-id override.

The image has no `bootmsg=` key. The scan leaves the value buffer empty, `strlen` is 0, and the delay-slot default `2` is what gets stored. So this dump applies bootmsg level 2, not a parsed env value.

### Descriptor byte +2 is the vendor SMI selector

`rtk.ko:_rtl9300_smiAddr_init` at `0x250c4` does `lbu s1, 2(t8)` on the per-port object pointer from `*(unitMapStruct+unit*8)` at `(port+4)*4+4`. If the byte is not `0xff`, it is `a2` to `_rtl9300_port_smiSel_set` (`0x250d4`). That function (`0x24604`) accepts the selector only if it is `< 4`; otherwise it returns `0xf001` and does not program it.

`_hwp_port_parse` still does not load byte +2. `hwp_parsedInfo_show` labels that same descriptor byte `smi=%d`. The RTL9300 init is the downstream consumer. For this profile the bytes are 0 (mac 0/8/16/20), 1 (mac 24), and `0xff` (mac 25/26/27, skipped). Intended vendor SMI selector, not a traced MDIO transaction and not a Linux bus number.
