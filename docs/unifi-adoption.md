# UniFi controller adoption — research, 2026-11-20

Can the LG510S-4T2XS, running this repository's OpenWrt image, be adopted and managed by a UniFi Network controller as if it were a UniFi switch? This note collects the evidence: existing device-side implementations of the UniFi inform protocol, the protocol itself, what a real UniFi switch sends and receives, which UniFi model fits this board, and how each controller-side switch feature would map onto the components already in this image. Nothing here has been run on the switch. An emulated device was adopted by a local UniFi Network 10.6.109 controller; see [Lab validation](#lab-validation-2026-11-20). Controller account management is out of scope.

Primary evidence was read from source code, from the UniFi Network Application 10.6.109 package and from Ubiquiti's own switch firmware, downloaded from Ubiquiti's public firmware catalog. Claims taken from a secondary source are attributed; claims that could not be checked against a primary source are marked **UNVERIFIED**.

## Summary

Feasible. The protocol is well documented by several independent, recently active projects, two of which already make OpenWrt devices adoptable (as access points, not switches), and one of which emulates UniFi switches against a real controller. Ubiquiti's own Realtek RTL930x switch firmware is unencrypted, is LEDE 17.01-based, and contains the complete list of switch configuration keys the device side must understand.

The five most useful resources, in order:

1. **[antoniocosta/unifi-openwrt](https://github.com/antoniocosta/unifi-openwrt)** (Go, GPL-2.0, active): an OpenWrt package that adopts an OpenWrt AP into UniFi Network 10.6, with a `system_cfg` → UCI translator, rollback on failure, an "unhandled keys" ledger, and a refusal to apply Ubiquiti firmware. Closest in shape to what this board needs; its translator would need a switch section.
2. **[yesrab/openUF](https://github.com/yesrab/openUF)** `PROTOCOL-VALIDATION.md` (Lua, GPL-3.0, active): the most thorough validation log against a live controller, including the AES-GCM provisioning gate, both adoption paths, the per-port VLAN `switch.*` keys and the `port_table` contract, read from the decompiled controller.
3. **[jamesbraid/unifi-emu](https://github.com/jamesbraid/unifi-emu)** (Go, MIT, active): emulates UniFi APs, **switches** and gateways for controller integration tests; ships per-model profiles (including `US6XG150`, `USL8A`, `USWED76`) and `capability_bits.json`, a dictionary of every capability bitmap the controller tests, including `switch_caps` and per-port `speed_caps`.
4. **Ubiquiti's USW-Aggregation firmware 7.5.15** (`USL8A`, platform `US.rtl930x`): the same SoC family as this board. Its plaintext initramfs holds `mcad` (the inform agent), `syswrapper.sh`, `mca-dump`, and in `ubntbox` the full `switch.*` configuration key set.
5. **[jda/pixiedust](https://github.com/jda/pixiedust)** (Go, MIT): decrypts inform captures; its `unifi-fresh-usw.pcap` is a real USW-Pro-24 adoption with the switch's complete inform payload and the controller's `system_cfg`. It is the only real switch-side capture found.

Recommended model to impersonate: **`US6XG150` (US-XG-6PoE)**, the only UniFi model whose registered port layout is exactly four copper ports plus two SFP+ ports. **`USWED76` (USW-Pro-XG-8-PoE)**, a Realtek RTL9313 + RTL8264B switch, is the fallback. `US6XG150` was adopted in the lab: the controller provisioned six ports named `Port 1`-`Port 4`, `SFP+ 1`, `SFP+ 2`, and sent the port, VLAN, LAG, mirror, STP, isolation, storm-control and rate-limit settings as `switch.*` keys. Which features the controller offers depends on the capability bits the device reports, not on the model.

Another survey of the same question, written for the RTL837x 8051 port of RTLPlayground, is in that repository at `doc/unifi-protocol-research.md`. It found the switch-emulation projects listed last in the table below.

## Projects

Last activity is the latest push date reported by the GitHub API on 2026-11-20.

| Project | Language, licence | Last activity | Emulates | Reaches | Switch payloads |
|---|---|---|---|---|---|
| [antoniocosta/unifi-openwrt](https://github.com/antoniocosta/unifi-openwrt) | Go, GPL-2.0 | 2026-11-20 | AP on OpenWrt (default `U7PG2`) | Discovery, SSH and inform adoption, full provisioning, stats, mesh, locate; tested on Network 10.6 | `port_table`/`if_table` for an AP's own LAN ports only |
| [yesrab/openUF](https://github.com/yesrab/openUF) | Lua, GPL-3.0 | 2026-11-18 | AP on OpenWrt (`U6IW` and others) | L2 discovery, SSH and L3 adoption, provisioning, stats, locate, mesh; validated on UCG Ultra, Network 10.6 | Per-port VLAN (`switch.*`) for the AP's built-in switch; README says "no gateway or switch emulation, by design" |
| [jonasevcik/openUF](https://github.com/jonasevcik/openUF) | Lua, MIT | 2026-10-30 | Upstream of yesrab/openUF | As above | As above |
| [trueserve/openUF](https://github.com/trueserve/openUF) | Lua, no licence file | 2017-01-06 | Original openUF | Historical | No |
| [jamesbraid/unifi-emu](https://github.com/jamesbraid/unifi-emu) | Go, MIT | 2026-11-19 | AP, switch, gateway (software only) | Discovery, adoption to connected, faked upgrade | Yes: minimal `port_table` and `ethernet_table` per model profile |
| [JohnKiller/TNBU](https://github.com/JohnKiller/TNBU) | C#, AGPL-3.0 | 2026-08-13 | Controller (GUI), MitM proxy, device simulator | Its own controller adopts real APs and a real USW-Pro-48-PoE; simulator reaches `setparam` | Yes, controller side: generates `switch.*` `system_cfg` (`TNBU.Core/Models/DeviceConfiguration/CfgSwitch*.cs`) |
| [lucavb/open-unifi](https://github.com/lucavb/open-unifi) | Go, MIT | 2026-11-19 | Controller | Adopts a real `U7PG2`; bytecode-cited protocol docs, including UDP 10001 discovery | No |
| [jda/pixiedust](https://github.com/jda/pixiedust) | Go, MIT | 2026-08-12 | Capture decoder | Decrypts captures, recovers authkeys from adoption traffic | Real USW capture included |
| [dmke/inform-inspect](https://github.com/dmke/inform-inspect) | Go, MIT | 2026-11-18 | Packet inspector | Decode only | n/a |
| [ZAP-Quebec/unifi-inform](https://github.com/ZAP-Quebec/unifi-inform) | Go, MIT | 2017-05-12 | Library | Codec | No |
| [ZAP-Quebec/unifi-fake-device](https://github.com/ZAP-Quebec/unifi-fake-device) | none (README only), MIT | 2017-05-02 | Monitoring inform client | README only | No |
| [rbradley0/ubnt_inform](https://github.com/rbradley0/ubnt_inform) | Python, MIT | 2021-12-20 | Client/server experiments | Work in progress | No |
| [damienheiser/ripugw](https://github.com/damienheiser/ripugw) | Go, NOASSERTION | 2023-03-07 | Gateway on pfSense | Not assessed | No |
| [fxkr/unifi-protocol-reverse-engineering](https://github.com/fxkr/unifi-protocol-reverse-engineering) | Docs | 2015-03-23 | — | Original header/CBC description | No |
| [MartinDejmal/unifi-simulator](https://github.com/MartinDejmal/unifi-simulator) | Python, no licence file | 2026-10-16 | Switch (`US8`, `US24PRO2`) fed from MikroTik RouterOS, and `UGW3` | Adoption to connected on Network 10.6.106; `port_table`, `mac_table` and `lldp_table` accepted (its `docs/validation.md`) | Yes, read-only: never applies controller config |
| [konstruktor1/unifi-stubd](https://github.com/konstruktor1/unifi-stubd) | Go, no licence file | 2026-10-31 | A Linux bridge (or FreeBSD) presented as a `US8` | Discovery, inform, optional SSH shim for `set-adopt`; detailed `docs/en/protocol-notes.md`; reports 10.5.67 | Yes, read-only |
| [benklop/unifi-tlsg](https://github.com/benklop/unifi-tlsg) | Python, no licence file | 2026-07-26 | TP-Link TL-SG2424 presented as a `US24`, via an inform proxy | Applies VLAN and port config over the TP-Link SSH CLI; README says it needs lab validation | Parses `port.N.*` keys, which disagrees with the `switch.port.N.*` keys captured below |
| [ArmedGuy/unifiction](https://github.com/ArmedGuy/unifiction) | Go, no licence file | 2020-09-27 | SNMP or Cisco switches via L3 adoption | Reports config as applied without applying it | Old; same idea |
| [jeffreykog/unifi-inform-protocol](https://github.com/jeffreykog/unifi-inform-protocol) | Docs | 2020-05-18 | — | Header, flags incl. GCM and snappy | No |
| [mcrute/ubntmfi](https://github.com/mcrute/ubntmfi) | Python, BSD-3-Clause | 2017-08-16 | mFi controller | Early protocol notes (`inform_protocol.md`) | No |
| [nitefood/python-ubnt-discovery](https://github.com/nitefood/python-ubnt-discovery), [maxried/udpr](https://github.com/maxried/udpr) | Python, MIT | 2022, 2018 | UDP 10001 discovery | Discovery client / TLV decoder | No |
| [patricegautier/unifiZabbix](https://github.com/patricegautier/unifiZabbix) | Shell | 2026-10-11 | — | Monitoring via `mca-dump` over SSH | Consumes real `mca-dump` output |

No project was found that makes a non-Ubiquiti **switch** adoptable as a UniFi switch. A Wireshark dissector, "UniPi" and a Ubiquiti-provided simulator were searched for and not found.

## Protocol reference

### Inform packet

The device POSTs a binary frame to `http://<controller>:8080/inform` and the controller answers in the same format. Header, 40 bytes, big-endian ([unifi-openwrt `internal/inform/packet.go`](https://github.com/antoniocosta/unifi-openwrt/blob/8e87294191/internal/inform/packet.go) lines 3–22; [TNBU `InformPacket.cs`](https://github.com/JohnKiller/TNBU/blob/ba2c22f4bd/TNBU.Core/Models/InformPacket.cs) lines 15–60; [fxkr README](https://github.com/fxkr/unifi-protocol-reverse-engineering/blob/0566e8e1dd/README.md) line 54):

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | Magic `TNBU` |
| 4 | 4 | Packet version; devices send 0, the controller does not check it |
| 8 | 6 | Device MAC; must equal the payload's `mac` or the controller answers HTTP 400 |
| 14 | 2 | Flags: `0x01` encrypted, `0x02` zlib, `0x04` snappy, `0x08` AES-GCM |
| 16 | 16 | IV, also the 16-byte GCM nonce |
| 32 | 4 | Data version, must be 1 |
| 36 | 4 | Payload length, including the 16-byte GCM tag |

- **Encryption.** AES-128-CBC with PKCS#7, or AES-128-GCM with a 16-byte nonce and the whole 40-byte header as additional data. The key is the hex-decoded 32-digit `authkey`. Before adoption it is the factory key `ba86f2bbe107c7c57eb5f2690775c712`, MD5 of `ubnt` ([TNBU `InformPacket.cs`](https://github.com/JohnKiller/TNBU/blob/ba2c22f4bd/TNBU.Core/Models/InformPacket.cs) line 16). Compression is zlib before encryption; snappy is legacy ([jeffreykog README](https://github.com/jeffreykog/unifi-inform-protocol/blob/63d75a085c/README.md) lines 61–74).
- **GCM is mandatory for provisioning.** On Network 10.4.57 the controller will not provision a device until it has received a genuinely GCM-encrypted inform; the `x_aes_gcm` flag is set only from the wire flag, and a GCM→CBC downgrade is rejected afterwards. A device stuck here shows a new `cfgversion` on every cycle and "Adopting" forever ([openUF `PROTOCOL-VALIDATION.md`](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 529–565). The pixiedust USW capture shows the controller sending `use_aes_gcm=true` in `mgmt_cfg`.
- **Inform URL.** The reported `inform_url` must have an IP-literal host; a host name is rejected with `invalid inform_ip` ([unifi-emu `docs/PROTOCOL.md`](https://github.com/jamesbraid/unifi-emu/blob/a538889cce/docs/PROTOCOL.md) "Three things that trip up an implementer"). HTTP 404 with an empty body to a pending device is normal.
- **Cadence.** Keep informing; the controller can only answer the device's next inform. `noop` carries `interval`; after a `cmd` the device informs again immediately ([openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 606–638).

### Adoption

Both paths are seen on Network 10.6 and a device should support both ([unifi-openwrt `docs/internals.md`](https://github.com/antoniocosta/unifi-openwrt/blob/8e87294191/docs/internals.md) "Adoption"; [openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 566–605):

1. **L3, inform only.** The device is configured with the controller's inform URL and informs with the factory key, `default: true`, `state: 1`. After the operator clicks Adopt, a `setparam` delivers `mgmt_cfg` with `authkey=…`, `cfgversion=…`, `use_aes_gcm=true`, `inform_url=…`, `mgmt_url=…`, `stun_url=…`. The controller logs "discovered via L3 inform, skip SSH adoption". Accept a key from `mgmt_cfg` only while still on the factory key.
2. **L2, SSH.** For a device found by broadcast discovery, the controller SSHes in as `ubnt`/`ubnt` (or the site's device credentials once set) and runs `syswrapper.sh set-adopt <inform-url> <authkey>`. Its SSH client offers only RSA host keys (`ssh-rsa`, `rsa-sha2-*`). unifi-openwrt answers with a dedicated SSH responder on a separate port advertised in the inform's `sshd_port`; openUF adds a locked-down `ubnt` account to Dropbear and had to register its forced shell in `/etc/shells`.

Some builds deliver the key with `{"_type":"cmd","cmd":"set-adopt","key":…,"uri":…}` instead ([unifi-emu](https://github.com/jamesbraid/unifi-emu/blob/a538889cce/docs/PROTOCOL.md) "The two key-delivery channels").

`mgmt_cfg` and `system_cfg` are newline-separated `key=value` strings, not JSON. `mgmt_url` is the controller's web UI link, not an inform URL; treating it as one loses the controller ([openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 600–604).

### Replies

Per openUF's reading of `InformServlet` (10.4.57): `noop`, `setparam`, `cmd`, `upgrade`, `reboot`, `setdefault` ([openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 606–638). unifi-emu also describes a `setstate` reply carrying `port_table`/`port_overrides`; openUF's servlet reading does not list it. **UNVERIFIED** which is right for USW on 10.6; capture it.

| Reply | Meaning for this agent |
|---|---|
| `setparam` | `mgmt_cfg` (key, cfgversion, GCM, inform URL) and `system_cfg` (the whole device configuration) |
| `cmd` `set-locate` / `unset-locate` | Blink an LED |
| `reboot` | Reboot (`reboot_type` soft) |
| `setdefault` | Operator clicked Remove: forget the controller and return to pending. Do **not** factory-reset OpenWrt |
| `upgrade` | `version`, `md5sum`, `url` of a Ubiquiti image. **Never apply it**: report the offered version so the controller stops offering it nightly (both unifi-openwrt and openUF do this) |

`cmd` strings seen for switches in Ubiquiti's `mcad`/`swctrl` (port restart, PoE power-cycle, clear counters) were not mapped to their wire names; **UNVERIFIED**.

### Discovery (optional)

UDP 10001 broadcast with a 4-byte header (`version`, `command`, `length`) and TLVs: MAC (1), MAC+IP (2), firmware (3), uptime (10), hostname (11), platform (12), sequence (18), source MAC (19), model (21), short version (22), default-state (23) ([unifi-emu `docs/PROTOCOL.md`](https://github.com/jamesbraid/unifi-emu/blob/a538889cce/docs/PROTOCOL.md) "L2 discovery packet"; [open-unifi `docs/PROTOCOL-discovery.md`](https://github.com/lucavb/open-unifi/blob/c1d8ebc604/docs/PROTOCOL-discovery.md) lines 130–150; [TNBU `Docs/DiscoveryType.md`](https://github.com/JohnKiller/TNBU/blob/ba2c22f4bd/Docs/DiscoveryType.md)). The discovery path decides the adoption method: broadcast-discovered devices get SSH adoption. A device configured with an inform URL needs no discovery at all.

## Switch payload and model mapping

### What a real UniFi switch reports

From the decrypted inform in [pixiedust `unifi-fresh-usw.pcap`](https://github.com/jda/pixiedust/blob/a4356227df/unifi-fresh-usw.pcap) (USW-Pro-24, `US24PRO2`, firmware 4.3.22, decoded with pixiedust on 2026-11-20):

- Top level: `architecture`, `board_rev`, `bootrom_version`, `cfgversion`, `default`, `fw_caps`, `hw_caps`, `general_temperature`, `has_fan`, `has_temperature`, `overheating`, `gateway_ip`, `gateway_mac`, `hostname`, `ip`, `netmask`, `mac`, `serial`, `model`, `model_display`, `version`, `kernel_version`, `uptime`, `time`, `inform_url`, `stp_priority`, `switch_caps`, `sys_stats`, `system-stats`, `if_table`, `port_table`, `uplink`, `satisfaction`, `total_max_power`.
- `switch_caps`: `{"feature_caps":1023,"max_aggregate_sessions":6,"max_l3_intf":64,"max_mirror_sessions":1,"max_reserved_routes":62,"max_static_routes":2}`.
- `sys_stats`: `loadavg_1/5/15`, `mem_total`, `mem_used`, `mem_buffer`; `system-stats`: `cpu`, `mem`, `uptime` as strings.
- `port_table[]` per port: `port_idx`, `media` (`GE`, `SFP+`), `up`, `enable`, `speed`, `full_duplex`, `autoneg`, `flowctrl_rx`, `flowctrl_tx`, `jumbo`, `is_uplink`, `speed_caps`, `poe_caps`, `port_poe`, `stp_state` (`forwarding`, `disabled`, …), `stp_pathcost`, `dot1x_mode`, `dot1x_status`, `satisfaction`, `rx/tx_bytes`, `rx/tx_packets`, `rx/tx_errors`, `rx/tx_dropped`, `rx/tx_broadcast`, `rx/tx_multicast`, a nested `lldp_table` (`lldp_chassis_id`, `lldp_port_id`, `lldp_system_name`) and a `mac_table` (`mac`, `ip`, `vlan`, `age`, `uptime`, `static`). SFP+ ports add `sfp_found`.

Ubiquiti's current RTL930x agent (`bin/mcad` in USW-Aggregation 7.5.15) additionally names `lacp_state`, `aggregate_num_ports`, `lag_member`, `port_caps`, `stp_role`, `stp_edge_port`, `sfp_vendor`, `sfp_part`, `sfp_serial`, `sfp_temperature`, `sfp_txpower`, `sfp_rxpower`, `mac_table_count`, `fan_level` and `general_temperature` among its JSON keys (strings extracted from the binary; field placement **UNVERIFIED**).

Bit values the controller tests, from [unifi-emu `capability_bits.json`](https://github.com/jamesbraid/unifi-emu/blob/a538889cce/capability_bits.json) (read from controller 10.4.57):

- `port_table[].speed_caps`: 10H `1`, 10F `2`, 100H `4`, 100F `8`, 1000H `16`, 1000F `32`, 2.5G `64`, 5G `128`, 10G `256`, autoneg `1048576`, FEC `2097152`. The captured USW sent `1048623` (autoneg, 10–1000) on copper and `1048928` (autoneg, 1G/2.5G/10G) on SFP+. For this board: copper `1049064` (autoneg, 100F, 1000F, 2.5G, 5G, 10G), SFP+ `288` or `1048864` (1G and 10G), **UNVERIFIED** what the UI does with each.
- `switch_caps.feature_caps`: L3 routing `1`, 802.1X `2`, port isolation `4`, storm control `8`, LLDP-MED `16`, egress rate limit `32`, STP `64`, DHCP snooping `128`, IGMP snooping `256`, port security `512`, LACP `8192`, FEC `65536`, bridge VLAN filter `262144`, jumbo `524288`, keepalive loop protection `1048576`, and higher bits for EtherLighting, MC-LAG, BGP, stacking, VRRP, OOB port, PTP.
- `switch_caps.stp_caps`: BPDU guard `1`, auto edge `2`, port cost `8`. `port_table[].port_caps`: EEE `1`.

The rule both AP projects learned the hard way applies here: claim only what the agent can carry out. A claimed bit makes the controller emit configuration and show controls; an unimplemented claim becomes a silently broken feature ([openUF `REVERSE-ENGINEERING.md`](https://github.com/yesrab/openUF/blob/3da571983b/REVERSE-ENGINEERING.md) "Aim and ground rules"; [unifi-emu](https://github.com/jamesbraid/unifi-emu/blob/a538889cce/docs/PROTOCOL.md) "Capability bitmaps").

### Where the controller defines models

Read from UniFi Network Application **10.6.109** (`v10.6.109+atag-10.6.109-36013`, the Debian package listed by `https://fw-update.ubnt.com/api/firmware-latest?filter=eq~~product~~unifi-controller&filter=eq~~channel~~release` on 2026-11-20):

- **Model enum** `com.ubnt.i.g.a.XCfthFC` in `usr/lib/unifi/lib/internal/internal-dependencies.jar` (obfuscated name, changes per build). Each constant carries device type, capability set, chipset, system ID, port count and Ethernet class. Disassembled with `javap -c -p`. `ace.jar` is only a launcher; the classes and their case-colliding package names must be read on a case-sensitive filesystem or straight from the zip ([openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 437–491).
- **Product database** `usr/lib/unifi/dl/uidb/uidb.json` (on UniFi OS: `/data/unifi-core/uidb.json`, referenced from `com.ubnt.service.br.JLudBrawuIVqu`): per SKU, `unifi.network.model`, `numberOfPorts`, `ports` (`standard` = RJ45, `plus` = SFP+, `sfp` = SFP), front-panel `diagram`, `features.poe`, `deviceCapabilities`. It is data shipped with the controller, so a modified copy is conceivable, but it is overwritten on upgrade and the enum in the jar is not; patching the controller is not a maintainable route.

Candidates, from both sources:

| UniFi model | `model` | Ports in uidb | Enum: chipset, ports, class | Fit for 4x 10GBASE-T + 2x SFP+ |
|---|---|---|---|---|
| US-XG-6PoE | `US6XG150` | `standard` 1–4, `plus` 5–6; diagram `01 02 03 04 __ 05 06`; PoE | BROADCOM, 6, GIGABIT_ETHERNET; sysid `0xeb23` | **Exact layout.** Advertises PoE the board lacks; report `poe_caps 0` |
| USW-Pro-XG-8-PoE | `USWED76` | `standard` 8, `plus` 9–10; PoE | REALTEK, 10, TEN_GIGABIT_ETHERNET; sysid `0xed76` | Same PHY (RTL8264B) and SoC family (RTL9313); report ports 5–8 absent or down |
| USW-Aggregation | `USL8A` | `plus` 8 | REALTEK, 8, GIGABIT_ETHERNET; sysid `0xed2d` | Same SoC (RTL9303, [`rtl9303_ubnt_usw-aggregation.dts`](https://github.com/openwrt/openwrt/blob/main/target/linux/realtek/dts/rtl9303_ubnt_usw-aggregation.dts) in OpenWrt), but all SFP+ |
| USW-Flex-XG | `USFXG` | `standard` 5 | MARVELL, 5, GIGABIT_ETHERNET | No SFP+ |
| USW-Enterprise-8-PoE | `US68P` | `standard` 8, `sfp` 9–10 | MARVELL, 10 | 1G SFP |

`US6XG150` firmware is still in Ubiquiti's catalog at 7.6.11, so the controller will keep offering upgrades. Whether the controller changes behaviour on `chipset` (feature gating, config dialect) is **UNVERIFIED**; the `system_cfg` key set captured from a Broadcom-era USW and the key set parsed by the Realtek firmware overlap in every key this note maps.

What happens when the reported `port_table` has fewer ports than the registry: on an AP, openUF observed that `switch.port.N` inventory entries follow the registry count while the Ports view and per-port settings follow the reported `port_table` ([openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 932–1006). For a USW this is **UNVERIFIED**, which matters only for the `USWED76` fallback.

## Config provisioning format

`system_cfg` is a flat `section.N.key=value` file. The switch section, as sent to the captured USW-Pro-24 (pixiedust capture) and as generated by TNBU's controller ([`CfgSwitch.cs`](https://github.com/JohnKiller/TNBU/blob/ba2c22f4bd/TNBU.Core/Models/DeviceConfiguration/CfgSwitch.cs), [`CfgSwitchEntry.cs`](https://github.com/JohnKiller/TNBU/blob/ba2c22f4bd/TNBU.Core/Models/DeviceConfiguration/CfgSwitchEntry.cs), [`CfgSwitchVLAN.cs`](https://github.com/JohnKiller/TNBU/blob/ba2c22f4bd/TNBU.Core/Models/DeviceConfiguration/CfgSwitchVLAN.cs)):

```text
switch.managementvlan=1
switch.jumboframes=disabled
switch.mtu=9216
switch.stp.status=enabled
switch.stp.version=rstp
switch.stp.priority=32768
switch.dhcp_snoop.status=enabled
switch.dot1x.status=disabled
switch.vlan.status=enabled
switch.vlan.1.id=1
switch.vlan.1.mode=untagged
switch.vlan.1.status=enabled
switch.vlan.2.id=10
switch.vlan.2.mode=tagged
switch.vlan.2.status=enabled
switch.port.1.name=Port 1
switch.port.1.opmode=switch          # switch | aggregate | mirror
switch.port.1.stp.port_mode=enabled
switch.port.1.lldpmed.opmode=enabled
switch.port.1.port-security=disabled
switch.port.1.keepalive=disabled
switch.port.2.pvid=10                # native VLAN override
switch.vlan.1.port.2.mode=tagged     # untagged | tagged | exclude
switch.vlan.2.port.2.mode=untagged
switch.port.3.lag=1                  # with opmode=aggregate
switch.port.4.status=disabled        # port disabled
```

`switch.vlan.M` is a slot; `.id` is the VLAN ID. Membership is expressed per port (`pvid`) and in a per-VLAN, per-port matrix; the matrix is authoritative, and an absent per-port key means "default" ([openUF](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) lines 932–1006, mapped by diffing five controller states).

The complete set the Realtek USW firmware understands was extracted from `bin/ubntbox` in the USW-Aggregation 7.5.15 image (`https://fw-download.ubnt.com/data/unifi-firmware/127c-USL8A-7.5.15-dc23f38c-6be7-470e-ac36-fe6ec832275c.bin`; header `UBNTUS.rtl930x.v7.5.15+17146`; uImage at `0x9ea3a`, LZMA kernel with an XZ-compressed cpio initramfs). Per port: `status`, `name`, `opmode`, `speed`, `duplex`, `autoneg`, `flowctrl`, `eee`, `fec`, `mtu`, `pvid`, `ingressfilter`, `isolation`, `lag`, `mirror_port`, `egress_rate_limit_kbps`, `stormctrl.{status,type,bcast,mcast,ucast}`, `stp.{port_mode,cost,edge,bpdu_guard,root_guard,loopback_detection}`, `lldp.opmode`, `lldpmed.*`, `dot1x.*`, `port-security*`, `keepalive`, `link_debounce`, `qos`, `dscp`, `acl.*`, `poe`, `mclag`. Global: `switch.lag.%d.lacp`, `switch.igmp_snooping.*`, `switch.multicast.*`, `switch.lldp.*`, `switch.qos.*`, `switch.acl.*`, `switch.dhcp_guard.*`, `switch.radius.*`, `switch.routing_interface.*`, `switch.ptp.*`, `switch.mclag.*`, `switch.oob.*`, `switch.etherlight.*`. Exact value vocabularies beyond those in the capture are **UNVERIFIED** until captured from a controller.

The same image confirms the device-side architecture: `mcad` (aliased as `mca-ctrl`, `mca-cli-op`, `inform-collector`), `mca-dump` (a shell wrapper around `mca-ctrl -t dump`, the reference for the inform payload), `syswrapper.sh`, `swctrl`, `ubntconf`, `ubus`/`ubusd`, Linux 3.18.24 with Realtek SDK modules (`rtk.ko`, `rtdrv.ko`, `l2g_stp.ko`, `l2g_lldp.ko`), and the build path `FW_uap_multi/lede1701.usw_rtk_93xx`, i.e. a LEDE 17.01 base. The default per-board configurations are `usr/etc/default-<sysid>.cfg`.

No Ubiquiti GPL source archive for USW firmware was found; a 2016 request for a UAP GPL archive was answered that Ubiquiti had none ([LKML thread](https://lkml.iu.edu/hypermail/linux/kernel/1611.3/00525.html)). The firmware binaries themselves are downloadable from the catalog. Read them for interoperability facts only; do not copy their code.

## Mapping to this firmware

The image is upstream OpenWrt `main` with the board in tree (openwrt/openwrt#26346, `058f001086`), the bridge device `switch` with `lan1`–`lan6`, bridge VLAN filtering, and the components listed in [OpenWrt on the LG510S-4T2XS](openwrt.md). Rolling snapshot feeds are disabled and there is no package manager, so the agent must be a vendored package built into the image, like `switchdev-config` (openwrt/packages#31070). The table maps each controller feature to the component that would carry it. "Gap" means nothing in the image does it today; the agent should then leave the capability bit unclaimed.

| UniFi feature | `system_cfg` / payload | Component in this image | State |
|---|---|---|---|
| Adoption, inform, keys | `mgmt_cfg` | New agent package | Gap: the work |
| Identity, uptime, load, memory | `sys_stats`, `system-stats`, `uptime` | `ubus call system info`, `/proc` | Available |
| Temperatures | `general_temperature`, `has_temperature`, `overheating` | `thermal_zone0` and RTL8264B hwmon, as used by the Ports page patches | Available |
| Port enable/disable | `switch.port.N.status` | netifd device / link state | Partial: no clear persistent per-port disable ([feature gap](openwrt-feature-gap.md)) |
| Port name | `switch.port.N.name` | none; `ip link set … alias` at runtime | Gap for persistence |
| Speed, duplex, autoneg | `switch.port.N.{speed,duplex,autoneg}` | netifd `config device` options, as set by LuCI | Available; tested 10G to 100M on TE1 |
| Flow control | `switch.port.N.flowctrl`, `flowctrl_rx/tx` | netifd `pause` (advertisement only, deliberately not `rxpause`/`txpause`); status via `getEthtoolStatus` (openwrt/luci#9178) or `ethtool -a` | Available |
| EEE | `switch.port.N.eee`, `port_caps` EEE | netifd `eee`; copper only | Available |
| Jumbo frames, MTU | `switch.jumboframes`, `switch.mtu`, `port.N.mtu` | netifd `mtu` | Available; only 1522 exercised |
| Networks/VLANs, native VLAN, tagged/untagged/blocked | `switch.vlan.*`, `switch.port.N.pvid`, `switch.vlan.M.port.N.mode` | UCI `bridge-vlan` sections on device `switch`, port lists with `:t`, `:u*`; offloaded by `port_vlan_add` | Available; VLAN isolation untested; OpenWrt #25993 (VID 0 leak) was open on 2026-10-19 |
| Management VLAN and IP | `switch.managementvlan`, `netconf.*`, `dhcpc.*` | `lan` on `switch.1`, DHCP by default | Available, **risky**: a network reload once made a unit unreachable until power-cycled ([known issues](openwrt.md#known-issues-and-cautions)); apply with a rollback timer |
| STP/RSTP, bridge priority | `switch.stp.{status,version,priority}`, `stp_priority` | `ustp`, UCI `stp`, `stp_proto`, `priority`; hardware via `port_stp_state_set` | Available (RSTP tested) |
| Per-port STP mode, cost, edge | `switch.port.N.stp.{port_mode,cost,edge}` | ustp/bridge port options | Partial: per-port UCI support in `ustp` **UNVERIFIED** |
| BPDU guard, root guard, loop detection | `stp.bpdu_guard`, `stp.root_guard`, `keepalive` | none | Gap |
| STP state and cost per port | `stp_state`, `stp_pathcost` | `bridge -j link` / rtnetlink | Available (kernel bridge state; `ustp` has no ubus status) |
| Link aggregation, LACP | `opmode=aggregate`, `switch.port.N.lag`, `switch.lag.N.lacp` | netifd bonding device, `kmod-bonding`; offload `port_lag_join` | Partial: untested; a bond inside the VLAN bridge changes the `bridge-vlan` port list |
| Port mirroring | `opmode=mirror`, `switch.port.N.mirror_port` | `switchdev-config` `config mirror` (`list source`, `direction`, `target`), tc matchall/mirred `skip_sw` | Available, offloaded |
| Egress rate limit | `switch.port.N.egress_rate_limit_kbps` | `switchdev-config` `config ratelimit` `egress` (Mbit/s; convert from kbit/s) | Available, offloaded |
| Static MAC entries | (UniFi feature and key **UNVERIFIED**) | `switchdev-config` `config fdb` | Available |
| MAC table per port | `port_table[].mac_table` | `bridge -j fdb show` (switch `self` entries, as on the MAC table page), ARP for IPs | Available |
| Port isolation | `switch.port.N.isolation` | bridge port `isolated` flag (driver supports `BR_ISOLATED`) | Partial: no UCI option; agent would set it at runtime |
| IGMP snooping, querier | `switch.igmp_snooping.*`, `switch.multicast.*` | bridge `igmp_snooping`, `multicast_querier`; offload `port_mdb_add` | Available, untested |
| Storm control | `switch.port.N.stormctrl.*` | none; no RTL930x driver support | Gap |
| LLDP, neighbours | `switch.lldp.*`, `port.N.lldp.opmode`, `lldp_table` | `lldpd` (UCI `/etc/config/lldpd`), neighbours from `lldpcli -f json show neighbors` | Available; off by default |
| LLDP-MED | `switch.lldpmed.*`, `port.N.lldpmed.*` | `lldpd` supports it | Partial |
| Port counters | `rx/tx_bytes`, packets, errors, dropped, broadcast, multicast | rtnetlink stats64 (`get_stats64`), `ethtool -S` MIB | Available; broadcast/multicast split **UNVERIFIED** for this driver |
| Link, speed, media | `up`, `speed`, `full_duplex`, `media`, `speed_caps` | `ethtool` / `getEthtoolStatus`, sysfs | Available |
| SFP+ module info | `sfp_found`, `sfp_*` | `ethtool -m lan5` | Partial: untested with a DOM module |
| Uplink port | `is_uplink`, `uplink` | Port where the default gateway's MAC is learned (FDB), as openUF does | Available |
| Locate | `cmd set-locate` | SYS LED (`gpio-leds`, `/sys/class/leds`) with a timer trigger | Available |
| Reboot | `_type reboot` | `reboot` | Available |
| Firmware upgrade | `_type upgrade` | **Never apply.** OpenWrt is updated by sysupgrade with this repository's images | By design |
| Remove / forget | `_type setdefault` | Agent state reset to pending; no OpenWrt reset | Agent |
| NTP, timezone, remote syslog | `ntpclient.*`, `system.timezone`, `syslog.remote.*` | UCI `system` | Available |
| SNMP | `snmp.*` (**UNVERIFIED** key names) | `snmpd` | Available; off by default |
| 802.1X, port security, DHCP snooping/guard, ACL, QoS/DSCP, L3 routing, PoE | various | none (PoE: no hardware) | Gap; do not claim |

Bits to claim at first, given the table: STP `64`, IGMP snooping `256`, egress rate limit `32`, bridge VLAN filter `262144`, jumbo `524288`, and port isolation `4` and LACP `8192` once implemented and tested; EEE in `port_caps` on copper ports; `poe_caps 0`. Values that real USWs send but whose effect is unknown should be learned from a capture, not guessed.

## Shape of the package

A procd service, `unifi-agent` or similar, with:

- **UCI** `/etc/config/unifi`: `enabled`, `inform_url` (IP literal), `model` (default `US6XG150`), `apply` (log-only first, as unifi-openwrt does), and state kept outside `/etc/config` (authkey, `cfgversion`, adopted flag) in a mode-600 file that sysupgrade keeps.
- **Inform client**: HTTP POST, AES-128-GCM/CBC, zlib, JSON. `libmbedtls` is already in the image for `libustream-mbedtls` and implements both modes; `libubox` (`blobmsg_json`, `uloop`) is in base; `zlib` is one package more. A small C or ucode daemon over these adds the least to the 12 MiB firmware partition; a Go binary (unifi-openwrt) or Lua with `lua-openssl` (openUF) works but costs more flash. Measure before choosing.
- **Translator**: `system_cfg` → UCI changes on `network` (`bridge-vlan`, `device`, bonding), `switchdev`, `lldpd`, `system`, `snmpd`, then `reload_config`. Apply as one transaction with a rollback timer that restores the last good configuration if the controller is not reachable afterwards; the management address is the dangerous part. Record every key it does not handle in an "unhandled" ledger (unifi-openwrt, openUF), so a new controller version shows up as a list of new keys.
- **Collector**: `port_table` from rtnetlink/ethtool netlink (link, speed, counters, pause, EEE), `bridge` (FDB, STP state, VLANs), `lldpcli` JSON, hwmon/thermal, `ubus call system info`.
- **Adoption**: L3 inform only to start, with the controller address set in UCI. This needs no `ubnt` account and no SSH changes. Broadcast discovery and the SSH path can follow; if added, prefer unifi-openwrt's separate single-command SSH responder over a second Dropbear login on port 22.

## Lab validation, 2026-11-20

An emulated `US6XG150` was adopted by a local controller and its provisioning was captured. Nothing ran on the switch, and no real Ubiquiti device was involved.

Setup, all on one workstation under Docker, on a private Docker network so that discovery could not reach any production controller:

- Controller: `ghcr.io/jamesbraid/unifi-network:seeded` (UniFi Network Application 10.6.109, first-run wizard already completed, empty site).
- Device: [jamesbraid/unifi-emu](https://github.com/jamesbraid/unifi-emu) at `a538889`, run as `-model US6XG150` and adopted through the controller API. Two local, unpublished hooks were added: one writes every decrypted controller reply and every outgoing inform to files, and one merges extra top-level fields into the inform payload.
- Changes were made through the controller's classic REST API (`rest/networkconf`, `rest/device/<id>` with `port_overrides`, `cmd/devmgr`), and the `system_cfg` received after each change was diffed against the previous one.

### Adoption

- The first inform was answered with HTTP 404 (pending). After the adopt request, the controller sent `setparam` with a `mgmt_cfg` containing `authkey`, `cfgversion`, `use_aes_gcm=true`, `mgmt_url`, `stun_url`, `led_enabled`, `report_crash` and `capability=notif,fastapply-bg,notif-assoc-stat`. The device was connected about 20 seconds after its first inform.
- The next `setparam` carried the full `system_cfg` (86 lines with default settings), plus `cfgversion` and `blocked_sta`. Besides `switch.*` it contains `unifi.*`, `system.*`, `users.*` (a device admin account with an MD5-crypt password hash), `netconf.*`, `dhcpc.*`, `resolv.*`, `route.*`, `sshd.*`, `ntpclient.*`, `vlan.status=disabled` and `bridge.status=disabled`. The agent should apply only the sections it maps, and should not create the `users.*` account.
- The controller listed the device with six ports: `Port 1`-`Port 4` (media `GE`, `speed_caps` 1048623) and `SFP+ 1`, `SFP+ 2` (media `SFP+`, `speed_caps` 1048864). The port names came from the controller, not from the emulator profile, which names them `Port 5` and `Port 6`.

### Capability bits decide what the controller offers

With only `fw_caps` reported, the controller refused STP, jumbo frames and flow control (`api.err.SpanningTreeChangeNotAllowed`, `api.err.JumboFrameChangeNotAllowed`, `api.err.FlowControlChangeNotAllowed`) and left out the egress rate limit, even for a `US6XG150`. After re-adopting with this extra inform field, the controller stored it and provisioned STP keys on every port by default:

```json
"switch_caps": {"feature_caps": 532844, "vlan_caps": 7, "stp_caps": 11,
                "max_mirror_sessions": 1, "max_aggregate_sessions": 3}
```

`feature_caps` 532844 sets `PORT_ISOLATION` (4), `STORM_CONTROL` (8), `EGRESS_RATE_LIMIT` (32), `STP` (64), `IGMP_SNOOPING` (256), `LACP` (8192) and `JUMBO` (524288), with the bit values from unifi-emu's `capability_bits.json`. `stp_caps` 11 is `BPDU_GUARD`, `AUTO_EDGE` and `PORT_COST`. Jumbo frames and flow control were still refused on the device even with the `JUMBO` bit set. In 10.6 they are site-wide settings (see [Site-wide switch settings](#site-wide-switch-settings)). The agent must report only capabilities it can apply. Clear `STORM_CONTROL` while the driver lacks it.

### Captured switch configuration

The `switch.*` section after these changes:

- Two VLAN-only networks, 10 and 20.
- Port 2: native VLAN 10, no tagged VLANs, isolation, STP off, mirrored by port 6.
- Ports 3 and 4: a LAG with native VLAN 1 and VLANs 10 and 20 tagged.
- Port 5: forced 10G full duplex, a 500 Mbit/s egress limit and a broadcast storm limit.
- STP priority 4096.

`switch.wevent.*` lines are left out of the block:

```text
switch.power_source.status=disabled
switch.managementvlan=1
switch.jumboframes=disabled
switch.mtu=9216
switch.stp.version=rstp
switch.stp.priority=4096
switch.stp.status=enabled
switch.vlan.1.id=1
switch.vlan.1.mode=untagged
switch.vlan.1.status=enabled
switch.vlan.2.id=10
switch.vlan.2.mode=tagged
switch.vlan.2.status=enabled
switch.vlan.3.id=20
switch.vlan.3.mode=tagged
switch.vlan.3.status=enabled
switch.routing_enabled=false
switch.port.1.name=Port 1
switch.port.1.stp.port_mode=enabled
switch.port.1.stp.edge=auto
switch.port.1.stp.bpdu_guard=disabled
switch.port.1.opmode=switch
switch.port.2.name=access-v10
switch.port.2.stp.port_mode=disabled
switch.port.2.opmode=switch
switch.port.2.pvid=10
switch.port.2.isolation=enabled
switch.vlan.1.port.2.mode=exclude
switch.vlan.2.port.2.mode=untagged
switch.vlan.3.port.2.mode=exclude
switch.port.3.name=lag-3-4
switch.port.3.stp.port_mode=enabled
switch.port.3.stp.edge=auto
switch.port.3.stp.bpdu_guard=disabled
switch.port.3.opmode=aggregate
switch.port.3.lag=1
switch.vlan.1.port.3.mode=untagged
switch.vlan.2.port.3.mode=tagged
switch.vlan.3.port.3.mode=tagged
switch.port.4.name=Port 4
switch.port.4.stp.port_mode=enabled
switch.port.4.stp.edge=auto
switch.port.4.stp.bpdu_guard=disabled
switch.port.4.opmode=aggregate
switch.port.4.lag=1
switch.vlan.1.port.4.mode=untagged
switch.vlan.2.port.4.mode=tagged
switch.vlan.3.port.4.mode=tagged
switch.port.5.name=fixed-10g
switch.port.5.stormctrl.status=enabled
switch.port.5.stormctrl.type=rate
switch.port.5.stormctrl.bcast=100
switch.port.5.autoneg=disabled
switch.port.5.duplex=enabled
switch.port.5.speed=10000
switch.port.5.ld_mode=disabled
switch.port.5.stp.port_mode=enabled
switch.port.5.stp.edge=auto
switch.port.5.stp.bpdu_guard=disabled
switch.port.5.egress_rate_limit_kbps=500000
switch.port.5.opmode=switch
switch.port.6.name=mirror
switch.port.6.stp.port_mode=enabled
switch.port.6.stp.edge=auto
switch.port.6.stp.bpdu_guard=disabled
switch.port.6.opmode=mirror
switch.port.6.mirror_port=2
```

Observations:

- `switch.vlan.M` is a slot number, and `.id` is the VLAN ID. Ports without a VLAN override get no `switch.vlan.M.port.N.mode` lines and no `pvid`, so an absent key means the default membership. That default is presumably native VLAN 1 with every VLAN tagged, the controller's "auto" setting, but this is **UNVERIFIED**.
- A port that had been overridden to native VLAN 10 with all tagged VLANs blocked became `pvid=10`, with `untagged` in VLAN 10 and `exclude` in every other VLAN.
- A LAG is `opmode=aggregate` plus `lag=<n>` on each member. The REST call needs `aggregate_members`. No `switch.lag.<n>.lacp` key was sent, so whether the LAG should run LACP or be static is not stated in this capture.
- A forced speed is `autoneg=disabled`, `duplex=enabled`, `speed=10000`, `ld_mode=disabled`.
- Storm control is `stormctrl.status=enabled`, `stormctrl.type=rate` and `stormctrl.bcast=<rate>`. The egress limit is `egress_rate_limit_kbps=<kbps>`.
- A port is disabled (`switch.port.N.status=disabled`) only when its override has `forward: "disabled"` together with an empty `native_networkconf_id` and `tagged_vlan_mgmt: "block_all"`. `forward: "disabled"` alone produced no key.
- The port name is `switch.port.N.name`. The firmware's UCI has nowhere to store it today, so it is a gap.

### Site-wide switch settings

Several switch settings live in site settings, not on the device: `rest/setting/global_switch` and `rest/setting/igmp_snooping`. They apply to every switch on the site.

| Site setting | Keys sent |
|---|---|
| `global_switch.jumboframe_enabled` | `switch.jumboframes=enabled`. `switch.mtu=9216` is always sent. |
| `global_switch.flowctrl_enabled` | `switch.port.N.flowctrl=enabled` on every port. A per-port `flow_control_enabled: false` removes that port's line. |
| `global_switch.stp_version` | `switch.stp.version` (`stp` or `rstp`). The priority (`switch.stp.priority`) is per device. |
| `global_switch.dhcp_snoop` (default on) | `switch.dhcp_snoop.status=enabled`, with `DHCP_SNOOPING` set. |
| `global_switch.dot1x_portctrl_enabled`, `radiusprofile_id`, `dot1x_fallback_networkconf_id` | `switch.dot1x.status=enabled`, `switch.dot1x.dynvlan`, `switch.dot1x.guest_vlan=<vid>`, `switch.radius.{auth,acct}.N.{ip,port,secret}`, and `switch.port.N.dot1x.mode=force_authorized` on every port. The RADIUS secret is sent in plain text. |
| `global_switch.link_debounce` | `switch.port.N.link_debounce=<ms>` on every port, with `feature_caps2` `LINK_DEBOUNCE` (1) set. |
| `igmp_snooping` (`enabled`, `network_ids`, `switches`, querier fields) | Per VLAN slot: `switch.vlan.M.igmp_snooping=true`, `igmp_fastleave`, `igmp_maxresponse=10`, `igmp_mcrtrexpiretime=180`, `igmp_groupmembership=260`, `igmp_supression`, `igmp_querier_status`, `igmp_querier`. Globally: `switch.multicast.forward_unk_mcast_router_ports`, `switch.multicast.flood_known_protocols`. Setting `igmp_snooping` on the network document alone sent nothing. |
| Network `dhcpguard_enabled`, `dhcpd_ip_1`, `dhcpd_ip_2` | `switch.dhcp_guard.N.{server,vlan,status}`, one entry per trusted server. |

### Keys gated by further capability bits

A second emulated `US6XG150` reported more capability bits:
- `feature_caps` 71115774, which adds `DOT1X`, `LLDP_MED`, `DHCP_SNOOPING`, `PORT_SECURITY`, `FORWARD_ERROR_CORRECTION`, `BRIDGE_VLAN_FILTER`, `KEEPALIVE_LOOP_PROTECTION`, `WEVENT_SNOOPING` and `IGMP_SNOOPING_ADVANCED`.
- `feature_caps2` 1, `storm_control_caps` 1 and `igmp_snoop_caps` 15.
- `port_caps` 1 (`EEE`) on every port.

With those set, the controller also sent these keys, which it had left out for the first device:

```text
switch.port.N.eee=enabled|disabled                  # port_caps EEE
switch.port.N.keepalive=enabled|disabled            # KEEPALIVE_LOOP_PROTECTION
switch.port.N.port-security=enabled|disabled        # PORT_SECURITY
switch.port.N.port-security.mac.K=<mac>
switch.port.N.lldpmed.opmode=enabled|disabled       # LLDP_MED
switch.port.N.lldpmed.topology_notify=enabled|disabled
switch.port.N.link_debounce=<ms>                    # feature_caps2 LINK_DEBOUNCE
switch.port.N.stormctrl.type=level                  # storm_control_caps IN_PERCENTAGE
switch.port.N.stormctrl.{bcast,mcast,ucast}=<percent>
switch.port.N.dot1x.mode=force_authorized|mac_based|...   # DOT1X
switch.port.N.dot1x.idle_timeout=<s>
```

Without `IN_PERCENTAGE`, a `level` storm-control override was sent as `type=rate`, with 100 for each traffic type that had no rate set. A `voice_networkconf_id` produced no key.

### How the controller builds the configuration

- The controller's REST field schemas are in `api/fields/*.json` inside `lib/internal/internal-dependencies.jar`. They list every field with a validating regular expression. `Device.json` defines `port_overrides`: `forward` is `all|native|customize|disabled`, `op_mode` is `switch|mirror|aggregate|routed|routed_aggregate`, `speed` runs from 10 to 100000, and storm-control rates and levels have fixed ranges. `PortConf.json` (port profiles), `NetworkConf.json` and `Setting.json` are alongside it. This is the most direct reference for what the controller can ask for.
- Port profiles are flattened. Assigning a `portconf_id` to a port, or editing the profile later, sends the profile's settings as that port's ordinary `switch.port.N.*` and VLAN keys. The device never sees a profile.
- A VLAN that no port carries is dropped from `switch.vlan.*`, and the slot numbers of the remaining VLANs can change. The agent must key VLANs by `.id`, never by slot.
- A device `PUT` with `port_overrides` replaces the whole list. Ports left out return to defaults.
- The fields the controller reads from a reported `port_table` entry are listed in one class's constant pool. They include `port_idx`, `up`, `speed`, `autoneg`, `full_duplex`, `media`, `name`, `is_uplink`, `stp_state`, `mirror_port_idx`, `lag_idx`, `aggregate_members`, `port_security_*` and `sfp_*` (vendor, part, serial, temperature, tx/rx power). In 10.6.109 that class is `com/ubnt/i/b/t/UQKIrjV`; the name is obfuscated and changes between builds.

### Reporting a different port layout under a borrowed model

A third emulated device informed as `US8` (eight gigabit ports in the controller's registry), but reported the LG510S layout in `port_table`: four `GE` ports and two `SFP+` ports, with 10G speeds and 10G `speed_caps`. unifi-emu's per-device `ports` setting and unifi-stubd's per-device profiles do the same thing. Results:

- The controller's device record and port list followed the reported `port_table`: six ports, `SFP+` media on ports 5 and 6, and 10G link speeds.
- `system_cfg` still followed the registry and listed eight ports. The names came from the controller (`Port 5`, `Port 6`). The reported names were ignored.
- A forced 10G speed on port 5 of the `US8` was accepted and sent (`switch.port.5.speed=10000`). The controller did not check it against the model.
- An override on port 7, which does not exist on the device, was accepted and sent.

So a borrowed model with a different port count works. The agent must ignore `switch.port.N` entries beyond its physical ports. `US6XG150` needs no such handling, because its registry layout is the LG510S layout.

### PoE

`US6XG150` is a PoE switch in the controller's registry, and the LG510S has no PoE. A fourth emulated `US6XG150` reported `poe_caps: 0` and `port_poe: false` on every port. The other devices reported `poe_caps: 7` on ports 1-4.

- The controller adopted it normally and stored `poe_caps: 0` on every port. It raised no alarm, no event and no log line about the mismatch, and the device was not marked unsupported or incompatible.
- No PoE key reached `system_cfg` on either device, not even after a `poe_mode` override of `off` or `auto`. The only power-related key sent was `switch.power_source.status=disabled`. The controller's config generator has the strings `switch.poe`, `power_budget` and `power_source_ctrl`, so PoE configuration probably also depends on a power budget that the emulator does not report. This is **UNVERIFIED**.
- The web UI hides PoE for that device. Compared with a `US6XG150` that reports `poe_caps: 7`:
  - The Port Manager has no PoE Mode column and no PoE legend, and the PoE filter reads "None (6)".
  - The per-port settings panel has no PoE selector. The PoE device offers Off, PoE+ and 24V Passive there.
  - The model name still reads "US XG 6 PoE" everywhere.

So the agent should report `poe_caps: 0` and `port_poe: false` on every port, report no power budget, and ignore any `switch.poe*` or `switch.port.N.poe*` key it receives.

### Link speeds and SFP+ modules

A fifth emulated `US6XG150` reported the following ports, each with `poe_caps: 0`:

| Port | Reported link | Reported `speed_caps` |
|---|---|---|
| 1-4 | up at 10000, 2500, 5000 and 1000 Mbit/s | 1049064: 100M, 1G, 2.5G, 5G and 10G full duplex, plus bit 1048576 |
| 5 (SFP+) | up at 10000, autonegotiation off | 1048864: 1G and 10G |
| 6 (SFP+) | down | 1048864: 1G and 10G |

`speed_caps` 1048576 is present on every real profile; its meaning was not identified. Port 5 reported a module with these fields:

```json
"sfp_found": true, "sfp_eeprom": true, "sfp_rxfault": false, "sfp_txfault": false,
"sfp_vendor": "FS", "sfp_part": "SFP-10GSR-85", "sfp_rev": "A",
"sfp_serial": "F2030812345", "sfp_compliance": "10G Base-SR",
"sfp_temperature": "38.50", "sfp_voltage": "3.30", "sfp_current": "6.20",
"sfp_txpower": "-2.10", "sfp_rxpower": "-3.40"
```

Port 6 reported a module with `sfp_rxfault: true`. The field names and types (booleans, and strings for every measurement) come from the controller's port model class. The value formats and units are a guess, and the UI accepted them.

What the web UI showed:

- **Speeds.** The Port Manager showed 10 GbE, 2.5 GbE, 5 GbE and GbE on ports 1-4, each with its own colour and legend entry, and 10 GbE on port 5. The Link Speed filter counted them. The down port showed "Auto".
- **Speed choices.** With autonegotiation off, the speed list held exactly the speeds in `speed_caps`. Copper ports offered 10 GbE, 5 GbE, 2.5 GbE, GbE and 100 MbE, all full duplex. The SFP+ port offered 10 GbE and GbE. The agent's `speed_caps` therefore decide what an admin can pick, so they must match what the RTL8264B and the SFP+ cages actually support.
- **SFP tab.** Each module's vendor, serial, part number, compliance, temperature (`38.5℃`) and output power (`-2.1 dBm`) were shown. The power fields are therefore read as dBm. The agent can fill these from `ethtool -m` on the SFP ports.
- **Faults.** `sfp_rxfault: true` raised a critical "Port 6: Receive SFP Signal Loss" alert, gave port 6 an anomaly score of 70, and put a warning icon on the device. Report a fault only when the module really asserts LOS.

### Firmware upgrades

All three emulated devices reported firmware 7.4.1.16850 and were marked `upgradable` to 7.6.11.17272. A manual upgrade sent:

```json
{"_type": "upgrade", "version": "7.6.11.17272", "md5sum": "...",
 "url": "https://fw-download.ubnt.com/data/unifi-firmware/<id>-US8-7.6.11-<uuid>.bin"}
```

The agent must never download or apply this file. If it ignores the message, the controller keeps offering the upgrade, and the site's nightly auto-upgrade (`mgmt.auto_upgrade`, on by default) retries it. Reporting a version at or above the controller's latest for the impersonated model probably avoids the offer, but this was not tested.

### Commands

- Locate arrives as `{"_type": "cmd", "cmd": "set-locate", ...}` on the next inform. Turning it off was not captured.
- Restart arrives as `{"_type": "reboot", "reboot_type": "soft", ...}`.
- Between changes the controller answers `noop` with `interval: 10`.

## Risks and unknowns

- **Controller changes.** Obfuscated class names, capability gates and adoption details change between controller builds. Both AP projects track a specific Network version and keep "unhandled" ledgers for this reason. Expect maintenance on each controller release.
- **Model identity.** Impersonating `US6XG150` means the controller's UI, firmware offers, topology pictures and support data describe a Broadcom PoE switch. Upgrade offers must be answered without applying them, or the nightly auto-upgrade keeps retrying.
- **Device authenticity.** No evidence was found that Network 10.6 verifies device hardware or a device certificate before adoption: openUF and unifi-openwrt adopt OpenWrt APs on 10.6, and unifi-emu adopts software-only switches. Fields like `anon_id` and `hash_id` are not checked as far as those projects found. Whether UniFi OS consoles or a future release add a signed device identity is **UNVERIFIED**; it would end all of these projects at once.
- **Terms.** Ubiquiti's terms of service and EULA were not reviewed; **UNVERIFIED** whether they restrict using the controller with non-Ubiquiti devices. Keep Ubiquiti names and images out of the package, and do not distribute Ubiquiti binaries or controller files.
- **Hardware unknowns carried from this image**: VLAN isolation, LAG and IGMP snooping are untested on this board; storm control is not supported by the driver.

## Recommended starting point

1. Read [unifi-openwrt `docs/internals.md`](https://github.com/antoniocosta/unifi-openwrt/blob/8e87294191/docs/internals.md) and its `internal/inform`, `internal/device` and `internal/translate` packages for the client and translator structure; then [openUF `PROTOCOL-VALIDATION.md`](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) for the GCM gate, adoption, `switch.*` and `port_table`. Licences: GPL-2.0 and GPL-3.0; unifi-emu and pixiedust are MIT.
2. Done for `US6XG150`, and for a borrowed `US8` with the LG510S port layout; see [Lab validation](#lab-validation-2026-11-20). Still open: LACP versus static LAG (no `lacp` key was ever sent), the voice VLAN, how the reported version affects upgrade offers, and a run as `USWED76`.
3. Write the translator against the captured keys, with each still-open item treated as unknown until it is captured.
4. If a real Realtek UniFi switch is available (USW-Aggregation or USW-Pro-XG-8-PoE), capture from it: `mca-dump` and `mca-dump -g` over SSH, `cat /tmp/system.cfg` (path **UNVERIFIED**; find the running config), and a pcap of a fresh adoption with its authkey recovered by pixiedust. That is ground truth for `port_table`, `switch_caps` and `speed_caps` on 10G Realtek hardware.
5. Only then write the agent, starting with inform, L3 adoption, read-only `port_table` and `apply '0'`, and add translator sections one feature at a time, each claimed only after it is tested on the switch.
