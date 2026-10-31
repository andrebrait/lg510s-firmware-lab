# Live UART and U-Boot validation — 2026-10-30

## Outcome

The spare unit has a working 3.3 V serial console. U-Boot can be interrupted, and its read-only commands confirmed several dump-derived board facts on live hardware: the selected profile, flash map, GPIO register layout, RTL8264B PHY identity, SMI routing, TE1 port mapping and TE6 presence/I²C. The configured MAC 24 PHY does not respond. U-Boot networking reaches the LAN through TE1.

No flash, persistent-environment (`saveenv`), system-information, boot-command or configuration write was made. Volatile state was changed only by `rtk network on`, MDIO read commands written to the SMI command registers, `rtk i2c init sw` and RAM-only `setenv` of `ipaddr`, `netmask` and `serverip`. The owner performed every power cycle. The production unit was not contacted.

## Console hardware

The PCB is marked `PCB-510S-4T2XS-V1_0_1-19676`. Header `J5`, beside the SFP cages, has silkscreen labels `GND`, `TXD`, `RXD` and `3V3`.

| Measurement, powered | Result |
|---|---|
| `3V3` to `GND` | 3.3 V DC |
| `TXD` to `GND` (idle) | 3.3 V DC |
| `RXD` to `GND` | 0 V |
| `GND` continuity to board ground | Yes |
| `TXD`/`RXD` to `3V3`, `GND` or each other | No continuity |

The DSD TECH SH-U09C5 was set to 3.3 V logic. Only adapter `GND`, `RXD` (to board `TXD`) and `TXD` (to board `RXD`) were connected; `VCC`/`3V3` stayed disconnected. The console runs at 115200 8N1 without flow control. Output and input both work. The stock login on this console is the same vendor CLI as SSH, not a Linux shell.

## Boot output

U-Boot reports:

```text
U-Boot 2011.12.(1.0.0.2) (Sep 11 2024 - 13:14:20)
Board: RTL9300 CPU:800MHz LX:175MHz DDR:600MHz
DRAM:  128 MB
SPI-F: WINBOND/EF4018/MMIO16-1/ModeC 1x16 MB (plr_flash_info @ 83f82dec)
Loading 65536B env. variables from offset 0xe0000
Net:   Net Initialization Skipped
No ethernet found.
Hit Esc key to stop autoboot:  1
## Booting kernel from Legacy Image at 81000000 ...
```

Only **Esc** stops autoboot, and the window is one second. The image header (`1.1.1.34`, load `80000000`, entry `803345b0`, 8302096 data bytes) verifies before decompression.

The kernel reports `MTD partitions obtained from built-in array`. Its seven partitions are identical to the [decoded native default map](board-evidence-review.md#native-default-flash-map), so no command-line override is active. U-Boot `flshow` shows the same layout mapped at `0xb4000000`, naming the runtime partition `RUNTIME1`. The SDK prints `Hardware-profile probe (RTL9303_8264B_2XGE)`.

## U-Boot commands

`help` lists `boota`, `bootm`, `bootp`, `tftpboot`, `ping`, `loady`, `loadb`, `loads`, `go`, `iminfo`, memory commands, flash commands, `env`, `saveenv`, `setsys`, `savesys`, `upgrade` and `rtk`. `bdinfo` is absent; `flinfo` printed nothing.

Relevant help details:

- `tftpboot [loadAddress] [[hostIPaddr:]bootfilename]`; networking is initialized by `rtk network on`.
- `loady [ off ] [ baud ]` provides a serial-only loading path.
- `bootm` supports the `start`, `loados`, `cmdline`, `bdt`, `prep` and `go` sub-commands.
- `upgrade runtime`, `upgrade loader` and `upgrade rom` fetch over TFTP with validation; `loaderforce` and `romforce` skip validation. Do not use any `upgrade` command during research.
- `rtk` exposes board-model/ID setters, GPIO set, PHY/SerDes register writes and test modes. Use only the getters listed below.

Three command quirks matter (see [reference cross-check](#reference-cross-check)):

- `rtk pinGet` is **not read-only**. The SDK implementation reconfigures the pin as a plain GPIO input before reading it, and its usage text limits it to internal GPIO 0–7. `rtk pinGet 13` printed `The pinNum (13) is invalid.` and U-Boot stopped responding until a power cycle. Read GPIOs through the data register instead.
- On this loader, `rtk phymmd` and `rtk sdsreg` take four numbers: `rtk phymmd get <ignored> <port> <mmd> <reg>` and `rtk sdsreg get <ignored> <sds> <page> <reg>`. The first number is skipped; the unit comes from U-Boot's current unit. Values accept `0x` hex. This vendor build differs from the published SDK, whose `phymmd` takes three numbers and parses values as decimal.
- `rtk i2c init sw` is **not read-only** either: it sets the given SCL/SDA pins to GPIO outputs driven high before creating the bit-banged bus.

## Live results and dump cross-checks

| Item | Live result | Dump evidence | Verdict |
|---|---|---|---|
| Selected profile | `rtk boardmodel`: `RTL9303_8264B_2XGE`; `rtk boardid`: `<NULL>` | Saved `boardmodel`, no `idType`/`boardid`; profile `0x008de842` | Confirmed; no numeric override |
| Available profiles | 39 profiles, including `RTL9303_8264B_2XGE (9300034)` | `hwp_hwProfile_list` | Consistent |
| GPIO register layout | `md.l b8003300 8`: control `00ffffff`, direction `00000000`, data `002b7ffe` | `rtl9300_gpio_dataBit_get` reads SoC `0x330c` with a native `lw`; bit = bank × 8 + pin | Confirmed: bit *n* of the native word is GPIO *n* |
| Board-ID straps | GPIO 21/22/23 = 1/0/0 | `ski:board_device_boardId_get` = GPIO21 \| GPIO22<<1 \| GPIO23<<2; live CLI `Board Value: 1` | Confirmed; also independently confirms the bit order |
| SFP pins, both cages empty | Presence 14/17 = 1/1; LOS 13/16 = 1/1; TX-disable 15/18 = 0/0; I²C 8/9/10/11 = 1/1/1/1 | Board branch `0x2684` configures only GPIO 13–18 | Consistent with empty cages |
| Passive DAC in cage labelled 6 | Data `00287ff8`: only GPIO 16 and 17 changed from 1 to 0; GPIO 13/14 stayed 1 | TE6 presence 17, LOS 16 | Confirmed: GPIO 17 is TE6 presence (active low); this DAC holds LOS low |
| TE6 EEPROM | Software-I²C device 1 at `0x50`, created with SCL 8 / SDA 10: identifier `0x03` (SFP/SFP+), connector `0x21` (copper pigtail), byte 8 `0x84`, vendor `OEM`; device 0 (empty TE5) returns `FAIL (-1)` | Optical row 2: device 1, SCK 8, SDA 10, address `0x50` | Confirmed: SDA 10 serves TE6. The `already been initialized` message refers only to the shared I²C controller, which the SDK treats as success before creating the device |
| DAC also in cage labelled 5 | GPIO 14 and 13 changed from 1 to 0; I²C device 0 reads identifier `0x03`, connector `0x21` | TE5 presence 14, LOS 13; optical row 1: device 0, SDA 9 | Confirmed: GPIO 14 is TE5 presence and device 0 is TE5 |
| SFP link under U-Boot, TE5 cabled to TE6 | `MAC_LINK_STS` (`0xbb00cb10`, register from pinned OpenWrt `rtl930x.c`) shows only CPU port 28 up after a second read | — | U-Boot does not bring the SFP+ links up with this DAC; the earlier stock-firmware 10G link on TE5 remains the SerDes evidence |
| Bit-banged I²C side effect | After the reads, GPIO direction `00000700` (GPIO 8–10 outputs, as `rtk i2c init sw` configures them); a later device 1 read returned `FAIL (61455)` | — | `61455` is `0xF00F`, the SDK's `RT_ERR_NOT_INIT`; the exact cause was not traced. Reset before trusting further I²C reads |
| Copper port mapping | One LAN cable moved TE1 → TE4. Each time, only the expected port's PCS status 3.1 went `0082` → `0086` and `MAC_LINK_STS` set its bit: TE1 → port 0 (`00E9` AN status, 10G), TE2 → 8, TE3 → 16, TE4 → 20 | OEM table TE1–TE4 = SDK ports 0/8/16/20 | Confirmed live for all four copper ports |
| Copper PHY identity | Ports 0, 8, 16 and 20: MMD1 reg 2/3 = `001C`/`C813` after `rtk network on` | Four-port RTL8264B descriptor | Confirmed: `0x001cc813` is OpenWrt's `RTL_8264B` |
| PHY routing | `SMI_PORT_ADDR` (`0xbb00cb80`) and `POLLING_SEL` (`0xbb00ca08/0c`): ports 0/8/16/20 → bus 0, addresses 0–3; port 24 → bus 1, address 0 | Descriptor SMI selector and PHY address bytes | Confirmed exactly |
| MAC 24 PHY | Raw C45 and C22 reads through the SMI command registers set FAIL (bit 25) and return `ffff`; the same method on port 0 returns `001c`/`c813` | Descriptor names an RTL8261BE at MAC 24 | No PHY answers on the configured path; do not declare MAC 24 |
| `RTL8231 probe (unit 0): (found)` | Printed during boot and `rtk network on` | `rtl8231_probe` prints it whenever the chip family is `0x9300`, without bus access | Not evidence of a fitted RTL8231 |
| RTL8231 init write | `md.l bb00c600 1` = `0000010c` (bit 8 set) | `r9300_rtl8231_init` sets switch register `0xc600` bit 8 | Matches. The SDK names `0xC600` `EXT_GPIO_GLB_CTRL` and bit 8 `EXT_GPIO_EN`, the auxiliary MDIO bus for an external RTL8231; OpenWrt's `pinmux_gpio_mdio_en` sets the same bit. U-Boot enables it although no RTL8231 is fitted, which explains GPIO 1/2 changing state |
| U-Boot networking | After `rtk network on` and RAM-only `setenv ipaddr`/`netmask`/`serverip` (no `saveenv`), `ping` reached the LAN gateway and a Mac. With `autostart` undefined, `tftpboot 81000000 tftp-test.bin` from macOS's built-in TFTP server transferred 1048576 bytes; `crc32 81000000 100000` = `64a3a4fe`, matching the host file | — | RAM loading over TFTP works and is byte-exact; nothing was booted |
| RAM above U-Boot | The same file loaded byte-exact at `0x84000000` and `0x87000000`. CRCs at `0x80000000`/`0x83000000`/`0x85000000` differ from `0x84000000`/`0x87000000`/`0x81000000` respectively | U-Boot runs at `0x83f00000` (command table addresses) | All 128 MiB is distinct, writable RAM with no 64 MiB aliasing; `0x84000000`–`0x87ffffff` can stage an image clear of a kernel decompressed at `0x80000000` |

Register layouts for the SMI checks come from upstream Linux [`mdio-realtek-rtl9300.c`](https://github.com/torvalds/linux/blob/master/drivers/net/mdio/mdio-realtek-rtl9300.c). Raw MDIO reads used its sequence: port mask `0xcb70` = 0, port in `0xcb78` bits 31:16, C45 device/register in `0xcb7c`, then the command in `0xcb74`, and the result in `0xcb78` bits 15:0. Port 0 served as the control. A missing pin-out for SMI bus 1 would produce the same MAC 24 result; either way, nothing answers on the vendor-configured path.

`rtk phyreg get` (Clause 22) returns `Failed!! 0xf00e` even for the working RTL8264B on port 0. The SDK defines `0xF00E` as `RT_ERR_SMI`: the Clause 22 transaction itself fails, so that error alone does not show an absent PHY.

## Reference cross-check

After the live work, each finding that a reference could have answered was checked against the published Realtek SDK (`realtek-switch-doc` `sources/rtk-dms1250`, commit `e74b513`), the RTL9303 datasheet in the same repository, upstream Linux and the pinned OpenWrt tree. These sources are used only as hardware documentation. The vendor U-Boot is a different build from the published SDK, so live behavior remains authoritative where they disagree.

| Finding | Reference | Result |
|---|---|---|
| GPIO data layout | SDK `rtl9300_soc_reg.h`: `PABCD_DIR` `0x3308`, `PABCD_DAT` `0x330C`, port A bits 7:0, B 15:8, C 23:16; datasheet: 24 GPIOs | Matches the live reading (bit *n* = GPIO *n*). The SDK does not name `0x3300`; Linux's Otto driver calls it the pin-control register |
| I²C pins | SDK `swcore_rtl9300.h`: master 1 `GPIO8_SCL_SEL`, master 2 `GPIO17_SCL_SEL`, `I2C_MST_GLB_CTRL` `GPIO9_SDA0` … `GPIO16_SDA7` | Matches the DTS (master 1, SDA 0/1 = GPIO 9/10). Stock also configures an ADT7476 on SDA 2 = GPIO 11, but none is fitted ([fan](openwrt.md#fan)). Master 2 must stay disabled: its SCL is GPIO 17, the TE6 presence input |
| MAC-side SerDes descriptor | SDK `hw_profile.h`: `sds_id`, then `mode:6`, `rx_polarity:1`, `tx_polarity:1`; `rt_serdesMode_t` 28 = `RTK_MII_USXGMII_10GSXGMII`, 2 = `RTK_MII_10GR` | Confirms the dump decode: `0x72` = USXGMII single-port with RX inverted, `0x71` = TX inverted, `0x08` = 10GBASE-R |
| PHY-side polarity | SDK `phy_rtl826xb.c`: VEND1 `0xC1` bit 7 = TX, bit 6 = RX; OpenWrt uses the same bits | Matches the live values and the DTS. Neither stock stage writes these bits at boot. In vendor `rtk.ko` only `phy_826x_ctrl_set` touches `0xC1` (jump-table cases 26 = RX and 27 = TX, as in the SDK enum) and no init path passes those cases; the board customization hook `conf_rtl9300_cust_board_list` is empty; only the userland-ioctl module `rtdrv` imports `rtk_port_phyCtrl_set`; `/etc/rc` runs no `diag`; the RTL8264B patch table has no `0xC1` entry. In U-Boot the same function sits at `0x83f50d54` (dispatch table `0x83fcb1e8`, case 26 → `0x83f51868`, 27 → `0x83f51814`); its 20 direct callers pass cases 25, 28, 29, 30, 50, 99 and 100 only, and no pointer to it is stored anywhere. The PHY's own default is therefore already inverted on this board **[INFERENCE]**; a PHY soft reset (VEND1 `0x145`) keeps the value. OpenWrt's driver overwrites it with "normal" unless the DT says otherwise |
| USXGMII in-band AN | SDK `dal_longan_construct.c`: default for single-port USXGMII is AN enabled, alignment-marker period `0x5078` | The vendor build disables AN on both sides but keeps `0x5078`; OpenWrt enables AN on both sides with period `0x00a4`. Both matched pairs pass traffic; a one-sided mismatch does not |
| Remaining MAC SerDes differences | Vendor `rtk.ko` tables `rtl9300_a_sds_usxgmii_sx_lane0/1` (`{page, reg << 8, value}` triplets) | Stock **Linux** programs the same values OpenWrt does (for example ANA_10G reg 0 `a668`, reg 2 `d020`, TGR_PRO_1 reg `0x10` `4003`); U-Boot uses a different set (`8668`, `d960`, `40aa`). The U-Boot/OpenWrt SerDes 5 diff therefore compares two loaders, not stock against OpenWrt. The table does not touch the AN register |
| Error codes | SDK `error.h` | `0xF00E` = `RT_ERR_SMI`, `0xF00F` = `RT_ERR_NOT_INIT` |
| SFP media in U-Boot | SDK `uboot_cmd.c`: `rtk 10g <port> none\|fiber10g\|fiber1g\|dac50cm\|dac100cm\|dac300cm` | Consistent with U-Boot not bringing SFP links up until media is set **[INFERENCE]**; not exercised |
| System LED | Datasheet strapping table: with `SYS_LED_EN`, GPIO 0 becomes the system-LED pin | Candidate for the front-panel system LED; not yet declared or tested |

## Procedure used

Each session opened the adapter with Python `termios`, sent Esc only while waiting for the autoboot prompt and logged all console bytes to an owner-only directory outside the repository. Commands were checked against an allowlist: `version`, `flshow`, `flinfo`, `iminfo`, `help`, `md`, `crc32` without a save address, the `rtk` getters above, `rtk network on`/`off`, `rtk i2c init sw`/`rtk i2c read`, `setenv` of `ipaddr`, `netmask` and `serverip` only, `ping`, `tftpboot`/`bootm` into `0x84000000`, writes to `0xbb00cb70`–`0xbb00cb7c`, the RTL8264B SerDes window (VEND1 `0x143`) and SerDes 5 registers for bisection, and `reset`. Characters were sent with a short inter-character delay because pasted input can be dropped.

Do not run `printenv` or `printsys` output into shared notes; they contain unit identifiers. Do not run `saveenv`, `setenv` beyond the network keys above, `setsys`, `savesys`, `sf`, `erase`, `flerase`, `protect`, `upgrade`, `go`, `bootm`, `tftpboot`, `loady`, `mw` outside the SMI command registers, or any `rtk` setter until a specific plan is approved.

## Remaining gates

- **SFP LOS and link:** LOS polarity needs an optical module receiving light. U-Boot does not bring SFP+ links up; OpenWrt does (10G over the DAC between TE5 and TE6).
- **Recovery path:** TFTP loading and `bootm` from `0x84000000` work; see [installing](openwrt.md#installing). `loady` remains the serial fallback.
- **Memory plan:** staging at `0x84000000` avoided the [decompression overlap hazard](board-evidence-review.md#loader-and-reference-image-hazard) in practice for a kernel decompressed from `0x80100000` (image plus BSS ends at `0x8143bef0`).
- **Electrical behavior:** TX-disable drive, LOS polarity under light and analog calibration remain unverified. Copper SerDes polarity is proven on all four ports by OpenWrt traffic at 10G.
