# UniFi controller adoption — research, 2026-11-20

Can the LG510S-4T2XS, running this repository's OpenWrt image, be adopted and managed by a UniFi Network controller as if it were a UniFi switch? This note collects the evidence: existing device-side implementations of the UniFi inform protocol, the protocol itself, what a real UniFi switch sends and receives, which UniFi model fits this board, and how each controller-side switch feature would map onto the components already in this image. Nothing here has been run against a controller or on the switch. Controller account management is out of scope.

Primary evidence was read from source code, from the UniFi Network Application 10.6.109 package and from Ubiquiti's own switch firmware, downloaded from Ubiquiti's public firmware catalog. Claims taken from a secondary source are attributed; claims that could not be checked against a primary source are marked **UNVERIFIED**.

## Summary

Feasible. The protocol is well documented by several independent, recently active projects, two of which already make OpenWrt devices adoptable (as access points, not switches), and one of which emulates UniFi switches against a real controller. Ubiquiti's own Realtek RTL930x switch firmware is unencrypted, is LEDE 17.01-based, and contains the complete list of switch configuration keys the device side must understand.

The five most useful resources, in order:

1. **[antoniocosta/unifi-openwrt](https://github.com/antoniocosta/unifi-openwrt)** (Go, GPL-2.0, active): an OpenWrt package that adopts an OpenWrt AP into UniFi Network 10.6, with a `system_cfg` → UCI translator, rollback on failure, an "unhandled keys" ledger, and a refusal to apply Ubiquiti firmware. Closest in shape to what this board needs; its translator would need a switch section.
2. **[yesrab/openUF](https://github.com/yesrab/openUF)** `PROTOCOL-VALIDATION.md` (Lua, GPL-3.0, active): the most thorough validation log against a live controller, including the AES-GCM provisioning gate, both adoption paths, the per-port VLAN `switch.*` keys and the `port_table` contract, read from the decompiled controller.
3. **[jamesbraid/unifi-emu](https://github.com/jamesbraid/unifi-emu)** (Go, MIT, active): emulates UniFi APs, **switches** and gateways for controller integration tests; ships per-model profiles (including `US6XG150`, `USL8A`, `USWED76`) and `capability_bits.json`, a dictionary of every capability bitmap the controller tests, including `switch_caps` and per-port `speed_caps`.
4. **Ubiquiti's USW-Aggregation firmware 7.5.15** (`USL8A`, platform `US.rtl930x`): the same SoC family as this board. Its plaintext initramfs holds `mcad` (the inform agent), `syswrapper.sh`, `mca-dump`, and in `ubntbox` the full `switch.*` configuration key set.
5. **[jda/pixiedust](https://github.com/jda/pixiedust)** (Go, MIT): decrypts inform captures; its `unifi-fresh-usw.pcap` is a real USW-Pro-24 adoption with the switch's complete inform payload and the controller's `system_cfg`. It is the only real switch-side capture found.

Recommended model to impersonate: **`US6XG150` (US-XG-6PoE)**, the only UniFi model whose registered port layout is exactly four copper ports plus two SFP+ ports. **`USWED76` (USW-Pro-XG-8-PoE)**, a Realtek RTL9313 + RTL8264B switch, is the fallback if the controller's Broadcom-classified model turns out to behave differently. Both need testing.

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

## Risks and unknowns

- **Controller changes.** Obfuscated class names, capability gates and adoption details change between controller builds. Both AP projects track a specific Network version and keep "unhandled" ledgers for this reason. Expect maintenance on each controller release.
- **Model identity.** Impersonating `US6XG150` means the controller's UI, firmware offers, topology pictures and support data describe a Broadcom PoE switch. Upgrade offers must be answered without applying them, or the nightly auto-upgrade keeps retrying.
- **Device authenticity.** No evidence was found that Network 10.6 verifies device hardware or a device certificate before adoption: openUF and unifi-openwrt adopt OpenWrt APs on 10.6, and unifi-emu adopts software-only switches. Fields like `anon_id` and `hash_id` are not checked as far as those projects found. Whether UniFi OS consoles or a future release add a signed device identity is **UNVERIFIED**; it would end all of these projects at once.
- **Terms.** Ubiquiti's terms of service and EULA were not reviewed; **UNVERIFIED** whether they restrict using the controller with non-Ubiquiti devices. Keep Ubiquiti names and images out of the package, and do not distribute Ubiquiti binaries or controller files.
- **Hardware unknowns carried from this image**: VLAN isolation, LAG and IGMP snooping are untested on this board; storm control is not supported by the driver.

## Recommended starting point

1. Read [unifi-openwrt `docs/internals.md`](https://github.com/antoniocosta/unifi-openwrt/blob/8e87294191/docs/internals.md) and its `internal/inform`, `internal/device` and `internal/translate` packages for the client and translator structure; then [openUF `PROTOCOL-VALIDATION.md`](https://github.com/yesrab/openUF/blob/3da571983b/PROTOCOL-VALIDATION.md) for the GCM gate, adoption, `switch.*` and `port_table`. Licences: GPL-2.0 and GPL-3.0; unifi-emu and pixiedust are MIT.
2. Run unifi-emu against a test controller with `SIM_MODELS=US6XG150` and with `USWED76`, then decrypt the traffic with pixiedust. This gives the exact `mgmt_cfg`/`system_cfg` the controller sends to each candidate and shows how the UI renders a six-port switch, before any code runs on the switch.
3. Click through every switch setting on that emulated device (port profile, native VLAN, tagged VLANs, disable, speed, LAG, mirror, STP, storm control, rate limit, LLDP-MED) and diff `system_cfg` after each, as openUF did for VLANs. That diff is the translator's specification.
4. If a real Realtek UniFi switch is available (USW-Aggregation or USW-Pro-XG-8-PoE), capture from it: `mca-dump` and `mca-dump -g` over SSH, `cat /tmp/system.cfg` (path **UNVERIFIED**; find the running config), and a pcap of a fresh adoption with its authkey recovered by pixiedust. That is ground truth for `port_table`, `switch_caps` and `speed_caps` on 10G Realtek hardware.
5. Only then write the agent, starting with inform, L3 adoption, read-only `port_table` and `apply '0'`, and add translator sections one feature at a time, each claimed only after it is tested on the switch.
