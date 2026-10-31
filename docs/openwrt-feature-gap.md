# Vendor firmware features versus the OpenWrt image — 2026-10-31

This compares the [vendor feature inventory](features.md) (firmware 1.1.1.34) with the OpenWrt image described in [OpenWrt on the LG510S-4T2XS](openwrt.md). For each feature it separates three layers:

- **Hardware path:** whether the OpenWrt switch driver (`target/linux/realtek/files-6.18/drivers/net/dsa/rtl83xx` at OpenWrt `19483fa`) offloads it to the switch chip.
- **Configuration:** whether netifd/UCI can set it persistently.
- **LuCI:** whether the web interface shows or sets it.

Driver support is read from source unless the row says it was tested. "CLI" means it works from a shell with the named tool but has no persistent UCI setting or LuCI page.

## Present

| Vendor feature | OpenWrt image | Notes |
|---|---|---|
| Status: identity, uptime, CPU and memory | LuCI Status -> Overview | |
| Front-panel link state | Overview port boxes, Devices tab, Status -> Ports | Ports page and Devices-tab columns are our LuCI patches |
| Management IP, static or DHCP, management VLAN | netifd interfaces and bridge VLANs, LuCI | Tested: static IPv4 on `switch.1` |
| DNS, SNTP, timezone | LuCI System | DST follows the timezone |
| Speed and duplex | LuCI device options (autonegotiation off -> speed/duplex) | Tested 10G to 100M on TE1 |
| Flow control, configured and negotiated | LuCI device options plus Devices tab and Ports page | Our patches; advertisement on by default on copper |
| EEE | LuCI device options plus Devices tab and Ports page | Our patches; on by default on copper; SFP+ unsupported |
| Jumbo frames | Per-device MTU in LuCI | Driver allows frames up to 12288 bytes; only 1522 was exercised |
| VLAN membership, PVID, tagged/untagged | Bridge VLAN filtering in LuCI (Devices -> bridge -> Bridge VLAN filtering) | Offloaded (`port_vlan_add`); VLAN isolation not yet tested on this board |
| Spanning tree STP/RSTP | `ustp`, LuCI Enable STP and our protocol dropdown | Tested: RSTP BPDUs on `lan1`; port states offloaded (`port_stp_state_set`) |
| IGMP snooping and querier | LuCI bridge options | Offloaded (`port_mdb_add`); not tested |
| LLDP transmit/receive, timers, neighbour data | `lldpd` with `luci-app-lldpd` | Off by default; enabled and running on the spare unit |
| Ping | LuCI Network -> Diagnostics | Also traceroute and nslookup |
| Firmware upgrade over HTTP | LuCI System -> Backup / Flash Firmware, or `sysupgrade` | Tested over SSH |
| Configuration backup and restore | LuCI System -> Backup / Flash Firmware | |
| SSH | Dropbear | Key login tested |
| MAC address table, static entries | Network -> Switch features -> MAC address table (`luci-app-switchdev`) | Shows the switch's own table (`self` entries from `port_fdb_dump`); static entries tested offloaded |
| Port mirroring | Network -> Switch features -> Port mirroring | tc matchall/mirred, tested offloaded in both directions |
| Ingress/egress rate limits | Network -> Switch features -> Rate limiting | tc flower police and TBF, tested offloaded |
| SNMP | Services -> SNMP (`luci-app-snmpd`, `snmpd-ssl`) | Off by default; not exercised against a manager |
| HTTPS | LuCI over HTTPS (`luci-ssl`) | Self-signed certificate generated on first boot; HTTP redirects to HTTPS by default |

## Partial

| Vendor feature | Hardware path | Configuration | LuCI | What is missing |
|---|---|---|---|---|
| Port counters | MIB counters via `ethtool -S` | n/a | Overview tooltip shows RX/TX bytes only | Detailed per-port counters page |
| Link aggregation, static and LACP | `port_lag_join` offload, L2/L2+L3 hashes | netifd `bonding` device | LuCI "Bonding/Aggregation device" (`kmod-bonding` bundled) | Untested; L3+L4 hash is only partly handled by the driver |
| QoS queues and scheduling | ETS offload, fixed default DSCP and priority maps in the driver | None | None | Trust/remark settings and maps are not configurable |
| ACL-like filtering | tc flower offload (drop, trap, redirect, police, VLAN push/pop) | None | None | `tc`; no UCI or LuCI |
| Protected ports | `BR_ISOLATED` supported by the driver | Bridge port flag from CLI | None | Persistent setting and LuCI option |
| MSTP | `port_mst_state_set`, `vlan_msti_set` | `stp_proto 'mstp'` selects MSTP in `ustp` | Our protocol dropdown | No way to define MST instances or map VLANs to them |
| LLDP-MED | `lldpd` supports it | `/etc/config/lldpd` | Some options in `luci-app-lldpd` | Policy and per-port MED pages |
| SFP module and DDM information | OpenWrt SFP driver | n/a | None | `ethtool -m <port>` with a module inserted is untested; no LuCI view |
| Accounts | rpcd supports several LuCI logins | `/etc/config/rpcd` | None | Only `root` exists; no account page |
| Port name/description, administrative disable | n/a | Interfaces can be stopped; no per-port description | None | Port descriptions; a clear per-port enable/disable |
| Firmware/config transfer over TFTP | n/a | `tftp` from BusyBox if enabled | None | CLI only |

## Missing

| Vendor feature | State in OpenWrt |
|---|---|
| Storm control (broadcast, unknown multicast/unicast) | No support for RTL930x in the driver (only RTL838x register names in debugfs) |
| Port security: MAC limits, sticky MACs, violation actions | Not implemented |
| DHCP snooping, trusted ports, IP/MAC binding | Not implemented |
| Loopback detection | Not implemented; STP/RSTP is the available loop protection |
| ERPS ring protection | Not implemented |
| Unknown multicast action, DMAC/DIP forwarding choice | Not exposed |
| Copper cable test | The OpenWrt PHY driver implements cable testing for RTL8224 only; `ethtool --cable-test` on these RTL8264B ports reports "PHY driver does not support cable testing" (tested) |
| Two firmware image slots | The image uses one `firmware` partition; recovery is U-Boot TFTP plus the saved stock image |
| Spanning-tree statistics page | `ustp` exposes no status over ubus beyond configuration |

## Tracking

The remaining gaps are tracked as issues #1 to #18 in this repository.
