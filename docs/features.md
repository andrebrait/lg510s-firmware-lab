# Enabled vendor feature inventory

Observed on LG510S-4T2XS firmware 1.1.1.34 through its `home_main.menuTree`, 65 enabled HTML pages and page GET responses on 2026-10-28. These are exposed controls and data, not functional validation of every protocol. Hidden endpoints and binary strings are not counted as working features by themselves.

| Area | Exposed features |
|---|---|
| Status | System/loader/firmware identity, uptime, CPU/memory use, front-panel links, port counters, MAC table |
| Network | Management VLAN/IP (static or DHCP), DNS, time/SNTP, timezone, DST rules |
| Ports | Four 10GBASE-T and two SFP+ ports; names, admin state, speed/duplex, configured/negotiated flow control, EEE |
| Frame size | Global jumbo size, observed 1522; advertised range 1518–10000 |
| Aggregation | Eight LAG groups, static/LACP, port assignment, system/port priority and timeout, hash selection |
| VLAN | Creation/naming, VLAN configuration, membership, per-port mode/PVID/acceptable frame types/ingress filtering/TPID/uplink settings |
| MAC/security | Static and filtered MAC entries; port MAC limits, sticky mode and violation actions; protected ports |
| Storm/mirror | Broadcast/unknown multicast/unknown unicast limits; four mirror sessions with ingress/egress sources |
| Spanning tree | STP/RSTP/MSTP, global and port parameters, MST instances/ports, statistics |
| Ring/loop | ERPS property/instance pages (GET advertised instance range 0–0), loopback detection and resume controls |
| LLDP | Global/per-port operation, timers, local/neighbor data, statistics, packet-overload view, LLDP-MED policy/port controls |
| Multicast | Unknown multicast actions, DMAC/DIP forwarding selection, groups/router ports, IGMP snooping and querier configuration |
| DHCP protection | Snooping/trusted ports/rate settings and IP/MAC binding table |
| QoS | CoS/DSCP trust and remarking, eight queues, strict/weighted scheduling, CoS/DSCP maps, ingress/egress limits |
| Diagnostics | Ping, copper cable test, SFP module/DDM information |
| Management | Accounts, HTTP/SNMP service controls, firmware/config transfers over HTTP or TFTP, two image slots, save/restore/backup |
| SNMP | Views, groups, communities, users, engine ID, trap events and notification settings |

TCP 22/23/443 were initially closed. That was service state/UI exposure, not proof that SSH/Telnet/HTTPS code was absent. SSH binaries, keys, configuration and native AAA handlers were subsequently found and SSH login was demonstrated.

## Comparison baseline and limits

RTLPlayground upstream `main` at 7ca4d2c already has port/VLAN/MTU configuration, counters, isolation, mirroring, four LAGs/LACP, RSTP, IGMP snooping, bandwidth/storm controls, EEE, LLDP transmission, SFP diagnostics, NTP/DNS/syslog and web config/firmware operations. Its integration branch carries additional unmerged work such as LLDP receive and SNMP. See upstream source rather than the old README for newly merged RSTP functionality.

Several software gaps have open PRs: MSTP (#453), loop detection (#456), DHCP snooping (#532), ACL (#520), QoS (#617/#618/#628), SNMP (#615) and the LLDP series. These references mean logicog/RTLPlayground PRs, not this repository.

The LG510S hardware has six 10G ports; RTL8372/RTL8373 have fewer 10G SerDes and their integrated copper PHYs are 2.5G-class. That port arrangement cannot be enabled by an RTLPlayground GUI change. Do not confuse the hardware's integrated PHY speed with possible external-PHY support on other RTLPlayground boards.

MSTP, ERPS, LLDP-MED, querier support, account management, TLS or SNMPv3 must not be labeled fundamentally impossible merely because RTLPlayground has not implemented them. Hardware resources, CPU budget and driver support need individual evidence. Earlier conversational claims about absolute LAG/mirror limits and SNMPv3 impossibility were not verified and are not adopted here.

The separate `rtl930x-firmware` project targets this same rebadged board using OpenWrt-derived kernel/PHY support plus a lean userland. The owner's current goal is open firmware for this family, not mandatory shared code or upstreaming a platform seam into RTLPlayground.
