# OpenWrt on the LG510S-4T2XS

## Status — 2026-10-31

OpenWrt with LuCI is installed on the spare unit's flash and boots from it without a console. Every on-board feature that could be tested without extra parts works:

| Area | Result |
|---|---|
| Copper TE1–TE4 | Link and IPv4 traffic at 10G on each port; TE1 also at 5G, 2.5G, 1G and 100M full duplex |
| SFP+ TE5/TE6 | Presence, module EEPROM, and a 10G link with traffic over a passive DAC between the two cages |
| Port LEDs | Stock behavior: green at 10G, orange below, solid on link, blinking on activity; SFP+ LEDs lit only with a live link partner |
| SYS LED | Fast blink (hardware), slow blink (OpenWrt booting), solid when running |
| Reset button | Press and release reported to `/etc/rc.button/reset` |
| Boot | Stock U-Boot `boota` from flash, on reboot and on a cold power-on; LAN reachable about 25 s after kernel start |
| Web UI | LuCI over HTTP on the management address, with EEE, flow-control and STP-protocol settings, negotiated state in the Devices tab and a Status -> Ports page |
| Bundled services | `lldpd` with `luci-app-lldpd` and `snmpd` with `luci-app-snmpd` (both off until enabled), `ustp` (RSTP when STP is enabled on a bridge), HTTPS for LuCI (`luci-ssl`), bonding (`kmod-bonding`), `ip-bridge` and `tc-full` |
| Switch features | Network -> Switch features: hardware MAC address table with static entries, port mirroring and per-port ingress/egress rate limits, applied by `switchdev-config` and offloaded to the switch (tested 2026-10-31 on unused ports) |
| Update | `sysupgrade` keeping settings: on 2026-10-31 the image `618843aa…` replaced the installed one; address, STP, LLDP and per-port EEE/flow-control settings survived, and no hand-copied LuCI files remained in the overlay |

Not tested: optical SFP+ modules and LOS under light, simultaneous traffic between switch ports, VLAN isolation, throughput and EEE power savings. The board has no fan controller (see [fan](#fan)).

The board definition is [`openwrt/0001-realtek-rtl930x-add-Lianguo-LG510S-4T2XS.patch`](../openwrt/0001-realtek-rtl930x-add-Lianguo-LG510S-4T2XS.patch) against OpenWrt `19483fa9075686e7a627c777e09c0a24163c8323`: one DTS, one image definition and this build's first-boot defaults, no kernel change. How the work got here, including the wrong turns, is in the [process log](process-log.md). What the vendor firmware offered and this image still lacks is mapped in the [feature gap](openwrt-feature-gap.md).

## Board facts used

| Item | Definition | Evidence |
|---|---|---|
| RAM | `memory@0` 128 MiB | Kernel reports `RTL9303 rev B (6487) SoC with 128 MB`; U-Boot RAM checks |
| Copper | `lan1`–`lan4` = ports 0/8/16/20, SerDes 2–5, USXGMII, Clause 45 PHYs 0–3 on SMI bus 0 | Dump plus live port and PHY-routing checks |
| Lane polarity | No overrides: the stock inversions on the MAC side (SerDes 2/4 RX, 3/5 TX) and on the PHY side (PHY 0/2 TX, 1/3 RX) cancel out | Without any polarity property, lan1 and lan2 each carried the uplink at 10G on 2026-10-31; they cover both inversion patterns (see [process log](process-log.md#5-the-data-path-that-linked-but-carried-nothing)) |
| SFP | `lan5`/`lan6` = ports 25/26, SerDes 7/8; presence 14/17 (active low), LOS 13/16, TX-disable 15/18 | Dump plus live presence and EEPROM checks |
| SFP I²C | SoC I²C master 1, SDA lines 0/1 | SDK register names: master 1 SCL = GPIO 8, SDA 0/1 = GPIO 9/10; the module EEPROM reads in Linux |
| Port LEDs | `led_set0`/`led_set1`, serial mode, active low, set 1 on the SFP+ ports, port 24 forced into the chain | Reproduces what stock programs (`0xbb00cc00`–`0xbb00cc44`); verified from power-on register values |
| SYS LED | `gpio-leds` on GPIO 0, active high, with `pinmux_disable_sys_led` | Datasheet: GPIO 0 is the system-LED pin when `SYS_LED_EN` is strapped |
| Reset button | GPIO 5, active low, `KEY_RESTART` | Vendor board configuration and a live press |
| Flash | Stock partition layout; only `firmware` (0x300000, 12 MiB) is writable | Live MTD map |

## Building

Build on the analysis VM in a dedicated OpenWrt worktree at `19483fa9075686e7a627c777e09c0a24163c8323`, as the non-root build user. LuCI needs the `luci` feed and `cgi-io` from the `packages` feed; the image was built with `luci` at `c1b79e84ba2b51b8df3ceb0dad1798f15c12a6dc` and `packages` at `76bf8b232b20a0e66870096d21203d666afbee46`. The nine `openwrt/luci-*.patch` files go on top of `feeds/luci` with `git am`. They add EEE and flow-control advertisement choices to Network -> Interfaces -> Devices -> Configure; a `luci.getEthtoolStatus` RPC method that returns ethtool's link, pause and EEE state; Flow Control and EEE columns with the negotiated state next to Link Speed in the Devices tab, with the advertisements in tooltips; and a read-only Status -> Ports page with one card per port showing link details and what flow control and EEE this switch and the link partner advertise, and the result. Stock LuCI can set neither netifd's `eee` nor its `pause` option and shows no negotiation state.

```sh
git am 0001-realtek-rtl930x-add-Lianguo-LG510S-4T2XS.patch
printf 'src-git packages https://git.openwrt.org/feed/packages.git\nsrc-git luci https://git.openwrt.org/project/luci.git\n' > feeds.conf
./scripts/feeds update packages luci
git -C feeds/luci am ../../luci-000*.patch  # nine patches
git am ../0002-switchdev-config-add-package.patch
./scripts/feeds install -p luci luci
./scripts/feeds install cgi-io luci-app-lldpd net-snmp luci-app-snmpd luci-ssl luci-app-switchdev luci-app-statistics collectd-mod-thermal collectd-mod-sensors
cat > .config <<'EOF'
CONFIG_TARGET_realtek=y
CONFIG_TARGET_realtek_rtl930x=y
CONFIG_TARGET_realtek_rtl930x_DEVICE_lianguo_lg510s-4t2xs=y
CONFIG_PACKAGE_luci=y
CONFIG_PACKAGE_cgi-io=y
CONFIG_PACKAGE_ethtool-full=y
CONFIG_PACKAGE_ip-full=y
CONFIG_PACKAGE_lldpd=y
CONFIG_PACKAGE_luci-app-lldpd=y
CONFIG_PACKAGE_ustp=y
CONFIG_PACKAGE_snmpd-ssl=y
CONFIG_PACKAGE_luci-app-snmpd=y
CONFIG_PACKAGE_luci-ssl=y
CONFIG_PACKAGE_kmod-bonding=y
CONFIG_PACKAGE_luci-app-switchdev=y
CONFIG_PACKAGE_luci-app-statistics=y
CONFIG_PACKAGE_collectd-mod-thermal=y
CONFIG_PACKAGE_collectd-mod-sensors=y
EOF
make defconfig
make -j"$(nproc)"
```

Outputs in `bin/targets/realtek/rtl930x/`: `…-initramfs-kernel.bin` (RAM boot), `…-squashfs-sysupgrade.bin` (6.55 MB with LuCI) and `…-squashfs-factory.bix`. All keep the stock uImage header value `0x83800000`.

## Installing

Prerequisites: the serial console ([`J5`, 3.3 V, 115200 8N1](uart-uboot-validation.md#console-hardware)), a TFTP server on the LAN, and a backup of the stock firmware partition.

1. Stop U-Boot with **Esc** during its one-second countdown.
2. Load the initramfs into RAM and boot it. Staging at `0x84000000` keeps the compressed image clear of the decompressed kernel:

   ```text
   rtk network on
   setenv ipaddr <switch address>
   setenv netmask <netmask>
   setenv serverip <TFTP server>
   tftpboot 84000000 <initramfs-kernel.bin>
   rtk network off
   bootm 84000000
   ```

   `setenv` without `saveenv` changes RAM only.
3. Back up stock from the running system: `cat /dev/mtd5 > /tmp/RUNTIME.bin` and copy it off the switch. On this unit its SHA-256 (`71a626ba…f2c2`) matched the `RUNTIME` slice of the programmer dump.
4. Fetch the sysupgrade image to `/tmp`, check it with `sysupgrade -T`, then write it with `sysupgrade -n /tmp/<sysupgrade.bin>`.
5. On the first flash boot the switch asks for an address by DHCP and uses `192.168.1.1/24` while it has none (see [management address](#known-issues-and-cautions)). A sysupgrade from an initramfs does not keep its configuration. This boot also takes about 100 s longer while JFFS2 formats the configuration area.
6. Set a root password in LuCI (System → Administration) or with `passwd`.

The vendor web upgrade with `factory.bix` works on this model. On 2026-10-31 two units on stock 1.1.1.34 were installed through the stock image page (`/cgi-bin/httpupload.cgi`, then `sys_reboot`); one stock firmware hung while rebooting and needed a power cycle. Both came up with DHCP, got their reserved addresses, and advertised `LG510S-4T2XS` over LLDP.

## Updating and recovering

- **Update:** copy a new sysupgrade image to the switch, check it with `sha256sum` and `sysupgrade -T`, then run `sysupgrade -v <image>` in the foreground over SSH, or use LuCI (System -> Backup / Flash Firmware). The configuration is kept unless `-n` is given. The SSH session ends with `Command failed: ubus call system sysupgrade ... (Connection failed)` when procd takes over; that is expected. Do not start it in the background with `nohup ... &`: it is killed when the SSH session closes and nothing is written.
- **Return to stock:** copy `RUNTIME.bin` to `/tmp` and run `mtd -f write /tmp/RUNTIME.bin firmware`, then `mtd verify /tmp/RUNTIME.bin firmware`.
- **If OpenWrt does not boot:** stop U-Boot, boot the initramfs as in step 2, and write either image from there.
- **Last resort:** write the verified programmer dump with the SPI clip.

Stock U-Boot needs no change: its default `bootcmd=boota` loads OpenWrt. Putting `rtk network on` into `bootcmd` was considered and is not needed.

## Known issues and cautions

- **First flash boot.** On the first boot after flashing, `lan1` linked but received nothing. Neither a later `reboot` nor a cold power-on reproduced it. The cause is not established; if it recurs, reboot and compare the SerDes RX calibration registers with the [captured values](process-log.md#8-flashing).
- **Bridging loops.** The default configuration bridges all six ports with no STP. Before connecting two switch ports to each other, disconnect every uplink, or remove one of them from `network.lan_vlan.ports` and reload. Removing a port only at runtime does not stick: netifd re-adds it when its link comes up. This caused a broadcast storm on the home LAN during the DAC test.
- **PHY soft reset.** Writing VEND1 `0x145` by hand leaves the RTL8264B in PMA low power and drops its host-side setup until the driver reinitializes it. Do not use it as a probe.
- **EEE and flow control.** Upstream OpenWrt advertises neither on this board (`Advertised pause frame use: No`, EEE disabled). The first-boot script `/etc/uci-defaults/05_lg510s_port_defaults` adds `config device` sections for `lan1`-`lan4` with `eee '1'` and `pause '1'`. Both only advertise: TE1 then negotiated `flow control rx/tx` and active EEE against a peer offering both, and a peer that doesn't leaves them off. netifd's `rxpause`/`txpause` options are deliberately not used: setting either disables pause autonegotiation and forces flow control. The SFP+ ports are left alone: 10GBASE-R has no autonegotiation, so pause there would be forced, and the driver reports EEE unsupported. The script also runs after a sysupgrade that keeps settings, so it skips any port that already has a `config device` section; a port turned off by hand stays off. To see the result, look at the Flow Control and EEE columns in Network -> Interfaces -> Devices, open Status -> Ports for details, or run `ethtool lan1`, `ethtool -a lan1` and `ethtool --show-eee lan1`.
- **Spanning tree.** `ustp` is in the image. With it installed, enabling STP on a bridge (Network -> Interfaces -> Devices -> Configure -> Advanced device options -> Enable STP, or `option stp '1'`) hands the bridge to `ustpd`, which runs RSTP unless `option stp_proto` says `stp` or `mstp`; the sixth LuCI patch adds that choice as "STP protocol". `option stp_kernel '1'` selects the kernel's legacy STP instead. STP is off by default. Checked on 2026-10-31 on the spare unit: with `stp '1'` and no protocol set, `/sys/class/net/switch/bridge/stp_state` was `2` (user-space STP) and `lan1` sent version-2, type-0x02 BPDUs (RSTP), captured with `tools/lab/bpdu.c`. Port states reach the switch hardware through the DSA driver's `port_stp_state_set`.
- **LLDP.** `lldpd` and `luci-app-lldpd` are in the image but off by default. `/etc/uci-defaults/06_lg510s_lldpd` disables the service unless `lldpd.config.enabled` is `1`, the option that Services -> LLDPd -> Enable service writes. Because that option is in a kept config file, the choice survives a sysupgrade; enabling the service only with `/etc/init.d/lldpd enable` does not. The same script sets `lldpd.config.lldp_description` to the model from `/tmp/sysinfo/model` without the vendor (`LG510S-4T2XS`), as stock advertises, instead of lldpd's `OpenWrt SNAPSHOT @ <hostname>`; it does so only while the option is unset, so a description set in LuCI is kept.
- **SNMP.** `snmpd` and `luci-app-snmpd` are in the image but off by default. Its package default says `enabled '1'`, so `/etc/uci-defaults/07_lg510s_snmpd` sets `snmpd.general.enabled` to `0` once and records that in `/etc/lg510s/snmpd-default-off`, a marker kept across sysupgrade (`/lib/upgrade/keep.d/lg510s`). Enabling SNMP in Services -> SNMP survives later updates. Change the default communities before enabling it.
- **HTTPS.** LuCI redirects HTTP to HTTPS by default (`uhttpd.main.redirect_https '1'`), set once by `/etc/uci-defaults/08_lg510s_https` with the marker `/etc/lg510s/https-redirect-default`, so turning the redirect off survives updates. The certificate is self-signed and generated on first boot; browsers warn until it is accepted or replaced.
- **Management address.** `/etc/uci-defaults/09_lg510s_mgmt` turns OpenWrt's untouched static default into a DHCP client (`proto 'dhcp'`, `retry '3'`), drops `ip6assign` and the ULA prefix, and sets `ipv6 '0'` on the `lan` device (`switch.1`), the option behind LuCI's Enable IPv6 checkbox. It runs once (marker `/etc/lg510s/mgmt-default`) and leaves any other configuration alone. While `lan` holds no lease, `/etc/udhcpc.user.d/lg510s-fallback` gives it `192.168.1.1/24` through netifd on each `leasefail`, so the lan firewall zone applies; a later lease replaces it. `retry` matters: with OpenWrt's default `-t 0` udhcpc retries forever and never reports `leasefail`. The bridge itself carries VLAN 1 tagged only and `eth0` is the CPU conduit, so neither needs IPv6 turned off. The fallback was tested on a throwaway interface; the full first boot is not yet tested. If the network already uses `192.168.1.1` and its DHCP server is down, the fallback address conflicts with it.
- **Network reload.** On 2026-10-31, setting `ipv6 '0'` on the `eth0`, `switch` and `switch.1` device sections and running `/etc/init.d/network reload` made the switch unreachable; the reload that restored the old configuration did not bring it back, and only a power cycle did. The cause is not known; LuCI's Save & Apply on device settings may trigger the same reload.
- **Temperatures.** The SoC sensor (`thermal_zone0`, `cpu-thermal`) and the four RTL8264B PHY sensors (hwmon, one per copper port) are read by two LuCI patches: Status -> Overview shows the CPU temperature, and Status -> Ports shows each port's temperature. The overview reads `/sys/devices/virtual/thermal/thermal_zone0/temp`, not the `/sys/class/thermal` symlink: rpcd checks file ACLs against the resolved path, so an ACL on the symlink is never matched. A DSA port has no `phydev` link in sysfs, so the RPC finds its PHY through the device tree `phy-handle`. SFP+ ports show the module's own temperature (`ethtool -m`, `module_temperature_measurement`) when the module has diagnostics; the passive DAC used in testing has none. `luci-app-statistics` with the thermal and sensors plugins graphs them under Statistics -> Graphs; `/etc/uci-defaults/10_lg510s_statistics` enables both plugins once. The graph history is kept in RAM and starts over after a reboot.
- **Switch features.** `switchdev-config` adds its rules with `skip_sw`: a rule the switch cannot offload fails and is logged (`logread | grep switchdev`) instead of running on the CPU. Ingress limits need `kmod-sched-flower` and `kmod-sched-act-police`, which the package pulls in. `tc -j` does not report a police rate, so the Rate limiting page shows the configured incoming limit next to the hardware state.

## Fan

No fan controller is fitted. Stock `board_conf` assigns this profile an ADT7476 at `0x2e` (bit-banged SCL GPIO 8, SDA GPIO 11), and `ski.ko` would set PWM 1–3 to manual mode at duty `0x4d`. That table is shared with board variants that have the chip. In U-Boot, after `rtk network on`, a software-I²C device on SCL 8/SDA 11 got no answer at `0x2c`, `0x2d` or `0x2e` (`FAIL (-1)`), while the same method on SDA 10 read the TE6 module EEPROM (`0x03`). The fan is a 2-pin fan without tachometer that runs from power, so the DTS declares nothing for it.
