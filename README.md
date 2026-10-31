# LG510S-4T2XS firmware lab

OpenWrt for the Lianguo LG510S-4T2XS 10G managed switch and its rebadges, with LuCI pages that cover most of what the stock web interface offered. The repository also holds the research behind the port: how the board was mapped, what was tested on hardware, and the dead ends. The goal is that someone with a related board can follow the same process.

## Supported hardware

One board is sold under several brands and model names. What identifies it is the PCB marking `PCB-510S-4T2XS-V1_0_1-19676`, printed on the board inside the case.

| Brand | Model | Status |
|---|---|---|
| Lianguo | LG510S-4T2XS | Tested |
| GoodTop | LG510S-4T2XS | Tested; GoodTop sells the Lianguo unit under the same model number |
| Horaco | ZX510S-4T2XS | Reported to be the same board, not tested |
| HRUI | HR510S-4T2XS | Reported to be the same board, not tested |
| Sodola | SL510S-4T2XS | Reported to be the same board, not tested |
| MokerLink | 10G04210GSM | Reported to be the same board, not tested |

| Board | |
|---|---|
| PCB marking | `PCB-510S-4T2XS-V1_0_1-19676` |
| Stock firmware tested | 1.1.1.34 (loader 1.0.0.2) |
| SoC | Realtek RTL9303, 128 MiB RAM, 16 MiB SPI NOR |
| Ports | 4x 10GBASE-T (one RTL8264B quad PHY), 2x 10G SFP+ |
| Console | Header `J5` beside the SFP+ cages, 3.3 V, 115200 8N1 |

Three units have been installed and run this firmware. Before flashing a unit sold under another name, open it and check the PCB marking, or compare its stock firmware with the [firmware notes](docs/firmware.md). The upstream OpenWrt board support lists the other names as alternatives for the same image.

## Getting started

This takes about 30 minutes, plus build time if you build the image yourself. You need a switch on stock firmware 1.1.1.34 and a network with a DHCP server.

1. **Check the board.** Find your brand and model in the table above, and check the stock firmware version. For a model marked as not tested, open the case and confirm the PCB marking first.
2. **Get the image.** Build it as described in [Building](#building). Use the `...-squashfs-factory.bix` file for the first install.
3. **Back up the stock firmware.** In the stock web interface, save the firmware image and both configurations (running and startup) from the backup pages. Keep them: they are the way back to stock.
4. **Install.** Upload `factory.bix` on the stock firmware upgrade page and wait until it reports success, then reboot from the stock interface. If the switch does not come back within a few minutes, power-cycle it once; the image is already written.
5. **Wait for the first boot.** It takes a few minutes while the configuration area is formatted. Do not cut the power during this time. The SYS LED is solid when OpenWrt is running.
6. **Find the switch.** It asks your DHCP server for an address, so look for a new lease from the switch's MAC address, or reserve an address for that MAC beforehand. If no DHCP server answers, it uses `192.168.1.1/24`.
7. **Log in.** Open the address in a browser; HTTP redirects to HTTPS with a self-signed certificate. Log in as `root` with an empty password.
8. **Secure and name it.** Set a root password and add your SSH public key under System -> Administration. Set the hostname, timezone and NTP server under System -> System.
9. **Optional: give it a static address.** Under Network -> Interfaces -> lan, change the protocol to static. Apply it with a reboot rather than Save & Apply; see [known issues](docs/openwrt.md#known-issues-and-cautions).
10. **Optional: turn on services.** LLDP (Services -> LLDPd) and SNMP (Services -> SNMP) are off by default.

Later updates use the `...-squashfs-sysupgrade.bin` image and keep the configuration; see [Updating](#updating). If anything goes wrong, see [Recovery](#recovery).

## The 5x RJ45 variant

A related model with five 10G RJ45 ports, one SFP+ cage, a fan controller and a PWM fan has **not** been tested. The stock board table for this switch family already lists an RTL8261BE PHY on MAC 24 and an ADT7476 fan controller, neither of which is fitted on the LG510S-4T2XS, so the variant is probably that configuration.

Almost all of this work should carry over: the SoC, flash layout, LED setup, SFP wiring and LuCI pages are likely shared. What needs checking is the fifth copper port, the SFP+ cage that remains, and the fan controller. Using an LLM with this repository as context is a good way to do that port: the [process log](docs/process-log.md) and the [board facts](docs/openwrt.md#board-facts-used) show which evidence was needed and how each fact was confirmed. Do not flash an image built for the LG510S-4T2XS onto it.

## What works

Every port, the port LEDs, the system LED, the reset button and the SFP+ module EEPROMs work. Updates keep the configuration. The image adds the following to a plain OpenWrt build:

- EEE and flow-control advertisement, and the STP protocol choice, in Network -> Interfaces -> Devices.
- Negotiated flow-control and EEE state in the Devices tab, and a Status -> Ports page.
- Network -> Switch features: the switch's MAC address table with static entries, port mirroring, and per-port ingress and egress rate limits, all offloaded to the switch chip.
- LLDP (`lldpd`) and SNMP (`snmpd`), both off until enabled, RSTP (`ustp`), link aggregation (`kmod-bonding`) and HTTPS for LuCI.

See [OpenWrt on the LG510S-4T2XS](docs/openwrt.md) for the test results, and the [feature gap](docs/openwrt-feature-gap.md) for what the stock firmware did that this image does not do yet. Open features are tracked as issues.

This build changes a few defaults compared with upstream OpenWrt: the switch gets its address by DHCP and falls back to `192.168.1.1/24` while it has no lease, IPv6 is off, EEE and flow-control advertisement are on for the copper ports, HTTP redirects to HTTPS, and LLDP and SNMP start disabled. The first-boot scripts in the board patch set these once, so later changes survive updates.

## Building

The board patch applies to OpenWrt `19483fa9075686e7a627c777e09c0a24163c8323`. Build on Linux, as a normal user:

```sh
git clone https://git.openwrt.org/openwrt/openwrt.git
cd openwrt
git checkout 19483fa9075686e7a627c777e09c0a24163c8323
git am /path/to/this/repo/openwrt/0001-realtek-rtl930x-add-Lianguo-LG510S-4T2XS.patch
git am /path/to/this/repo/openwrt/0002-switchdev-config-add-package.patch
./scripts/feeds update packages luci
# The LuCI patches were made against the luci commit listed in docs/openwrt.md.
git -C feeds/luci am /path/to/this/repo/openwrt/luci-000*.patch
./scripts/feeds install -a
```

Then create `.config` as listed in [Building](docs/openwrt.md#building), run `make defconfig` and `make -j"$(nproc)"`. The images are in `bin/targets/realtek/rtl930x/`:

- `...-initramfs-kernel.bin`: boots from RAM, for installation and recovery.
- `...-squashfs-sysupgrade.bin`: the image to install and update with.
- `...-squashfs-factory.bix`: for the stock firmware's upgrade page.

## Installing

From stock firmware 1.1.1.34, the simplest route is the stock web interface. It was tested on two units on 2026-10-31:

1. Back up the stock image and both configurations on the stock backup pages, and keep them.
2. Upload `factory.bix` on the firmware upgrade page and wait until it reports success.
3. Reboot from the stock interface. On one of the two units the stock firmware hung while rebooting; a power cycle then booted OpenWrt, because the image was already written.
4. The first boot takes a few minutes while the configuration area is formatted. The switch then asks for an address by DHCP, as described in step 5 below.

The serial console route below also works, and is the way back if OpenWrt does not boot:

1. Connect to `J5` and power on the switch. Press **Esc** during U-Boot's one-second countdown.
2. Boot the initramfs image from TFTP:

   ```text
   rtk network on
   setenv ipaddr <switch IP>
   setenv netmask <netmask>
   setenv serverip <TFTP server IP>
   tftpboot 84000000 <initramfs-kernel.bin>
   rtk network off
   bootm 84000000
   ```

   `setenv` without `saveenv` changes nothing on flash.
3. Back up the stock firmware from the running OpenWrt: `cat /dev/mtd5 > /tmp/runtime.bin`, and copy it off the switch. Keep it; it is the way back to stock.
4. Copy the sysupgrade image to `/tmp` and install it: `sysupgrade -n /tmp/<sysupgrade.bin>`.
5. The switch then boots OpenWrt from flash and asks for an address by DHCP. Look for it in your DHCP server's lease list. Without a lease after about 10 s it uses `192.168.1.1/24` until one arrives. There is no root password. The first boot takes about 100 s longer while the configuration area is formatted. Set a password in LuCI (System -> Administration) or with `passwd`.

The stock bootloader is left unchanged.

## Updating

Copy a new sysupgrade image to the switch and check it with `sysupgrade -T <image>`. Then either upload it in LuCI (System -> Backup / Flash Firmware) or run `sysupgrade -v <image>` in the foreground over SSH. The configuration is kept.

Do not add `-n` unless you want to reset the configuration: the switch would come back with the default DHCP setup. Do not start sysupgrade in the background (`nohup ... &`): it stops when the SSH session closes and nothing is written.

## Recovery

- **Back to stock:** copy the saved `runtime.bin` to `/tmp`, run `mtd -f write /tmp/runtime.bin firmware`, then `mtd verify /tmp/runtime.bin firmware`, and reboot.
- **OpenWrt does not boot:** stop U-Boot and boot the initramfs image as in step 2 of Installing. From there, write either the sysupgrade image or `runtime.bin`.
- **U-Boot does not start:** write a full flash backup with an SPI programmer and a SOIC-8 clip. Make that backup before the first flash; [firmware notes](docs/firmware.md) describe how this one was read.

The [known issues](docs/openwrt.md#known-issues-and-cautions) include a bridging-loop warning that applies to any test with two switch ports connected to each other.

## Upstream

The board support, the `switchdev-config` package and the LuCI changes are being prepared for upstream OpenWrt, LuCI and the packages feed. Until they are merged, use the patches in [`openwrt/`](openwrt/). The branches and submission steps are in [Upstreaming](docs/upstreaming.md).

## Repository layout

| Path | Contents |
|---|---|
| `openwrt/` | Patches for OpenWrt, the packages feed and LuCI |
| `docs/openwrt.md` | Status, board facts, building, installing, known issues |
| `docs/process-log.md` | How the port was done, including mistakes |
| `docs/openwrt-feature-gap.md` | Stock features compared with this image |
| `docs/firmware.md`, `docs/board4-investigation.md`, `docs/uart-uboot-validation.md` | Stock firmware analysis and hardware checks |
| `docs/reviews/` | Independent model reviews of the board evidence |
| `tools/` | Stock firmware and configuration tools, lab helpers for the console, TFTP and MDIO |
| `tests/` | Tests for the Python tools (`python3 -m unittest discover -s tests -v`) |
| `patches/` | A patch for RTLPlayground |

The tools in `tools/` work with the stock firmware: `firmware.py` inspects and unpacks a flash dump, `switchctl.py` talks to the stock web interface, and `configfile.py` edits a stock configuration file. They were written for firmware 1.1.1.34; `switchctl.py` refuses to change settings on any other model or version.

## How this was made

Development was assisted by LLMs, mainly Claude, under human direction. Every hardware fact in the board definition was checked on the switch, and the docs record what was tested and what was not. Model output was checked against the hardware before it was trusted; the [process log](docs/process-log.md) records where it was wrong.

Nothing in this repository contains vendor firmware, extracted vendor files, or configuration and keys from a switch. Do not add them.

## License

Tools and tests are GPL-2.0-only, documentation is CC BY-SA 4.0, and the patches keep the license of the project they apply to. See [LICENSE](LICENSE).
