# Process log: from a flash dump to OpenWrt on flash

This is the order in which the LG510S work happened, including the conclusions that turned out wrong and how each was corrected. Detailed evidence lives in the linked documents; this page explains how they fit together. Dates are 2026-10-28 to 2026-10-31.

## 1. Starting point

The spare unit ran vendor firmware 1.1.1.34. SSH reached only the vendor CLI. Three programmer reads of the 16 MiB SPI NOR were identical ([firmware findings](firmware.md)). OpenWrt already supported several RTL9303 boards, but none with this port and PHY combination, and an earlier plan had borrowed values from the Sirivision SR-ST3408F reference board.

## 2. Static analysis of the dump

The vendor modules (`board_conf.ko`, `rtcore.ko`, `rtk.ko`, `ski.ko`) and U-Boot were decoded from the dump: board profile selection, front-panel port mapping, PHY addresses, SerDes lanes and polarity bytes, SFP GPIOs, flash layout and loader behavior. Five model reviewers then repeated the analysis independently before reading the existing notes ([evidence review](board-evidence-review.md), [archived reviews](reviews/2026-10-29-board/README.md)).

What was wrong at this stage and corrected later:

- **SerDes polarity "absent".** Two reviewers first concluded the vendor descriptor had no polarity field. The low bits of each descriptor byte are polarity, consumed by the vendor driver; the SDK header later confirmed the layout (`mode:6`, `rx_polarity:1`, `tx_polarity:1`).
- **Module-detect and TX-disable conflated.** "OE" in the vendor table is module presence, not output enable, and a normalized LOS value of 1 means "normal", not "loss".
- **Header value as staging address.** The stock uImage header word `0x83800000` was first read as a staging address. The loader never checks it; `boota` stages at `0x81000000`.
- **Missing loader commands.** "bootm/tftp command is not supported" strings suggested the loader lacked them. The command table contains real handlers; the strings are fallbacks.
- **A hazard found here held up:** the stock loader checks for decompression overlap only after decompressing, so the reference image would overwrite its own unread input at the stock staging address. Every later RAM boot therefore staged at `0x84000000`.

## 3. Serial console and U-Boot

Board photos showed header `J5` labelled `GND TXD RXD 3V3`. Measurements gave 3.3 V logic, so the DSD TECH SH-U09C5 was set to 3.3 V, with VCC left unconnected ([UART validation](uart-uboot-validation.md)). Only Esc stops autoboot, in a one-second window. From there, U-Boot's `help`, `flshow`, `iminfo` and read-only `rtk` getters confirmed the profile and the flash map.

A small Python `termios` driver with a command allowlist ran every U-Boot session and logged it privately. Mistakes in this phase:

- **`rtk pinGet 13` hung U-Boot**, needing a power cycle. The command accepts only GPIO 0–7 and reconfigures the pin before reading it; GPIOs were read through the data register from then on.
- **An Esc byte merged with the first command** (`?ersion`), and several runs failed on script problems: an allowlist that rejected the intended commands, and a power-cycle wait that timed out. None touched flash.

## 4. Live hardware checks, and reading references first

U-Boot reads confirmed the SFP presence and EEPROM per cage, the copper port order, the RTL8264B PHY IDs and their SMI routing, and TFTP loading into RAM.

- **GPIO bit order.** Following a Linux driver note about reversed port order, the first reading was decoded byte-swapped and reported a module in TE5, while the cages were empty. The "Board Value" straps (GPIO 21–23), compared with the vendor code computing that value, showed bit *n* is GPIO *n*. A module test then proved the presence pins.
- **PHY reads failed before `rtk network on`.** The PHYs answer only after U-Boot initializes the switch. The `rtk phymmd` syntax was guessed wrong at first: this loader takes four numbers and ignores the first.
- **MAC 24.** `Failed!! 0xf00e` was first taken as "no PHY". `0xF00E` is the SDK's `RT_ERR_SMI`, which a working PHY also returns for Clause 22. Raw MDIO through the SMI command registers, with port 0 as control, showed nothing answers on MAC 24's path.
- **`RTL8231 probe: (found)`** looked like an I/O expander. The vendor code prints it for every RTL9300-family chip without touching the bus.

Afterwards the owner pointed out that the published Realtek SDK, OpenWrt's sibling boards and the RTL9303 datasheet would have answered several of these questions without probing. A [reference cross-check](uart-uboot-validation.md#reference-cross-check) confirmed every live finding, explained the error codes and the `0xC600` register, and corrected two notes: `rtk pinGet` and `rtk i2c init sw` are not read-only. From then on, each probe started with the references.

## 5. The data path that linked but carried nothing

An exact-board OpenWrt initramfs, built from a new DTS, booted from RAM and linked at 10G, but passed no traffic: the switch counted transmitted frames and received none.

1. **First hypothesis: USXGMII in-band autonegotiation.** Stock leaves it off; OpenWrt turns it on. Enabling it on one side only in U-Boot stopped traffic, so the PCS driver was patched to honor the out-of-band mode. That did not help, and the patch was dropped: OpenWrt enables it on both sides, which works.
2. **Second: other MAC SerDes values.** U-Boot's working SerDes 5 registers were compared with OpenWrt's, and each differing value was bisected inside U-Boot. None mattered. Later the vendor kernel's own tables showed that stock Linux programs the same values as OpenWrt; the bisection had compared U-Boot's tuning, not stock's.
3. **Cause: PHY-side polarity.** Dumps of the RTL8264B's host-side SerDes registers under both loaders, read through a cross-compiled MDIO tool, did not explain it. The OpenWrt PHY driver's code did: it writes the polarity register VEND1 `0xc1` from the DT and defaults to "normal", while U-Boot reads showed the lanes inverted (`0x01a7`/`0x0167`). Stating `tx-polarity`/`rx-polarity` on the PHY nodes fixed traffic with no kernel change.

The follow-up question was where stock sets that inversion. In `rtk.ko`, only the PHY control setter writes `0xc1`, via jump-table cases 26/27, and no boot path passes them. The board customization hook is empty, and only the userland ioctl module imports the setter. In U-Boot, the same function's 20 callers pass other cases. Neither stock stage writes it: it is the PHY's own default on this board, which OpenWrt overwrote.

The fix restated half of a pair. The MAC-side inversions were already in the DTS, copied from the stock descriptor, so clearing the PHY side left each lane inverted once. The sibling port openwrt/openwrt#26090 sets no polarity at all. On 2026-10-31 an image without any of the eight properties was flashed with settings kept: lan1 and then lan2 each carried the uplink at 10G, with the gateway learned on that port. lan1 and lan3 share one inversion pattern and lan2 and lan4 the other, so both are covered, and the overrides were removed. The SFP+ lanes have none either way, which kept a management path if the test had failed.

A side incident: while testing that, a manual PHY soft reset left one PHY in low-power mode, so TE2 later looked broken until a clean reboot.

## 6. Ports, speeds and the bridging loop

All four copper ports passed traffic at 10G, and TE1 also at 5G, 2.5G, 1G and 100M. Both SFP+ cages linked at 10G over a DAC between them.

During the DAC test the copper uplink stayed connected. TE6 had been removed from the bridge only at runtime, and netifd re-added it when the DAC linked, bridging TE5 and TE6 through the cable. The result was a broadcast storm on the home LAN until the owner unplugged copper. The rule since then: unplug uplinks, or remove the port in the saved configuration, before cabling two ports together.

EEE and flow control were first reported as "flow control already negotiated, EEE off by default". The flow-control half was a misread: `ethtool` listed `Symmetric Receive-only` under *Supported* pause frame use, while *Advertised* was `No`. A first-boot defaults script then set netifd's `eee`, `rxpause` and `txpause` on `lan1`-`lan4`. That was the second mistake: `ethtool --json -a` showed `autonegotiate: false`, because netifd forces flow control whenever `rxpause` or `txpause` is set. The script now sets `pause` instead, which keeps pause autonegotiation on; TE1 then negotiated both flow control and EEE. A first negotiation-status table sat in the device configuration dialog; on a phone LuCI hid its header row, leaving unlabelled values, and the dialog showed one port at a time. It moved to a Status -> Ports page, first as a table and then, after review on the owner's phone and desktop, as one card per port; the negotiated state also appears next to Link Speed in the Devices tab. The data now comes from a `luci.getEthtoolStatus` RPC method instead of a shell helper with its own file-exec ACL. The SFP+ ports are excluded because 10GBASE-R cannot negotiate pause, so enabling it there would force it.

## 7. LEDs, reset button, SYS LED and fan

- **Port LEDs worked "by accident".** Every RAM boot had run U-Boot's `rtk network on` first, which programs the LED block; OpenWrt never touched it. A flash boot would have left the LEDs dark. Reading the LED registers before and after `rtk network on` gave the stock values, which became the DTS `led_set` configuration. The test reset those registers to power-on values before booting, and OpenWrt then reproduced the stock LED behavior.
- **Reset button.** GPIO 5 reported press and release, tested with the factory-reset handler replaced by a logger.
- **SYS LED.** It blinked forever because nothing turned off the chip's hardware blink mode. Driving GPIO 0 as OpenWrt's status LED, as on the sibling Horaco board, gives fast blink, slow blink, then solid.
- **Fan.** The shared vendor table lists an ADT7476 for this profile, so a DTS node and driver were added. The owner noted this variant has a plain 2-pin fan. The first probe hung U-Boot because I²C needs `rtk network on`. The repeated probe found no device at any ADT7476 address, against a working control on the SFP EEPROM bus, and the node was removed.

## 8. Flashing

The build gained LuCI after adding the `luci` feed and `cgi-io` from the `packages` feed; the first build failed on the missing `cgi-io`. OpenWrt's sibling LG-SWTGW3C8F supplied the install route and image recipe. The live firmware partition matched the programmer dump's backup before anything was written. `sysupgrade` from the RAM-booted initramfs wrote the image, and stock U-Boot booted it with its normal `boota` ([install](openwrt.md#installing)).

- **Unreachable after flashing.** A sysupgrade from an initramfs does not keep its configuration, so the switch came up on `192.168.1.1`. The address was set over the console.
- **First flash boot received nothing on `lan1`.** Compared with a working boot, the SerDes 2 registers that hold RX calibration results looked uncalibrated: TGR_STD_1 reg 0 `000c` against `100d` (RX link), and ANA_SPD regs 3/0x13/0x18/0x1e `5f5f`/`027f`/`be48`/`07f8` against `4a5f`/`0264`/`3e48`/`87f8`. A boot after `rtk network on` worked. A plain `reboot`, and then a cold power-on, also worked, so U-Boot's initialization is not required. The first-boot failure is unexplained.
- The owner suggested putting `rtk network on` into `bootcmd`. It was kept in reserve because the cold boot worked without it, and because it would not help upstream users.

## 9. Polishing the image

After the install, the image gained the defaults and UI the owner asked for: EEE and flow-control advertisement on the copper ports, LuCI settings for EEE, flow control and the STP protocol, the negotiated state next to Link Speed in the Devices tab, a Status -> Ports page, and the `lldpd`, `luci-app-lldpd` and `ustp` packages. LLDP stays off until the user enables it.

- The first status table sat in the device dialog and lost its labels on a phone; it became the Ports page and Devices-tab columns, reviewed with screenshots in Chrome after the shared headless browser could not render LuCI views.
- `ustp` was found to run RSTP by default once STP is enabled. A small BPDU capture tool confirmed version-2 RST BPDUs on `lan1`.
- The first update attempt ran `sysupgrade` with `nohup ... &` over SSH. It died with the session and the switch never rebooted; uptime gave it away. Running it in the foreground worked, with settings kept.

## 9. Lessons

- Check the SDK, OpenWrt's sibling boards and the datasheet before probing; then probe once to confirm this board matches. The owner set this rule after several blind experiments that a reference answered.
- When a feature works in a RAM boot, ask whether U-Boot set it up. LEDs and PHY reachability both depended on `rtk network on`.
- Compare against stock, not against the bootloader. The U-Boot SerDes bisection looked rigorous but compared the wrong baseline.
- Treat vendor board tables as shared across variants. The ADT7476 entry and the RTL8261BE on MAC 24 were both absent on this board.
- Never assume a runtime network change sticks under netifd, and never cable two switch ports together with an uplink connected.
- Record mistakes where they happen. The [multi-model review](board-evidence-review.md) kept original reviewer notes next to their corrections, which made later reconciliation possible.
