# Annex: LG510S vendor firmware versus RTLPlayground

This comparison is a **north star, not a requirements list, feature-parity commitment or first-release acceptance checklist** for our independent RTL930x firmware. It records capabilities worth considering, including ones beyond the RTL8372/RTL8373 hardware. Hardware bring-up and recovery still come first.

Survey date: **2026-10-28**. Vendor baseline: LG510S-4T2XS firmware **1.1.1.34**. RTLPlayground baseline: upstream `main` **7ca4d2c**, with unmerged work identified separately. PR numbers below refer to **logicog/RTLPlayground**, not this repository; their status is a dated snapshot, not a live tracker. The `feat/linux-userland` port implements only a subset of upstream RTLPlayground, as the [reassessment](project-reassessment.md) explains.

The vendor survey inspected enabled menu pages and their API data, not every feature's behavior on traffic. Later dump/SSH findings are incorporated below. **Not exposed**, **not implemented** and **hardware cannot support it** are different claims. An unverified hardware limit is not treated as an impossibility.

## Target switch

| Item | Observed value |
|---|---|
| Model | LG510S-4T2XS; one production unit, one spare unit for experiments |
| Firmware | 1.1.1.34, March 29, 2025; loader 1.0.0.2; UI lists two image slots, both showing 1.1.1.34 |
| Ports | TE1–TE4: 10GBASE-T copper with lower-speed modes; TE5–TE6: 10G SFP+ |
| Web stack | Realtek managed-switch UI, Backbone.js, `cgi/get.cgi?cmd=...` / `cgi/set.cgi?cmd=...`, RSA-wrapped login; HTTP banner Hydra/0.1.8 and extracted `boa` binary |
| OS | Dump confirms Linux 3.18.24, MIPS32r2 big-endian userspace and uClibc |
| Management access | Normal menu lists HTTP and SNMP. SSH/Telnet/HTTPS were initially closed; SSH was subsequently enabled and authenticated on the experimental unit. SSH reaches the vendor CLI, not a demonstrated Linux shell |
| Hardware | Dumped boot environment identifies `RTL9303_8264B_2XGE`, consistent with RTL9303 + quad RTL8264B + two SFP+ interfaces |

`url.js` and the extracted files contain additional hidden features. Their presence is not proof of operational support. Conversely, the absence of SSH from the menu did not mean its daemon was absent: extraction and successful login disproved that early inference.

## Status

| LG510S feature | RTLPlayground coverage |
|---|---|
| System information: model, serial, MAC, uptime, firmware/loader versions, sysObjID | main exposes hostname, IP, MAC, firmware/build date, temperature and flash size; not every vendor field |
| CPU and memory utilization | No equivalent OS utilization display on the 8051 firmware; that does not preclude suitable resource reporting in a Linux replacement |
| Front-panel view: link, speed and media | main: port strip |
| Port counters | main: Statistics and per-port details |
| MAC address table view | main |
| Local syslog view | Not identified in main; remote syslog transmission exists |

## Network and time

| LG510S feature | RTLPlayground coverage |
|---|---|
| Static/DHCP management IP and management VLAN | main |
| IPv6 management-address fields | Not implemented in the compared RTLPlayground management UI. Vendor API has IPv6 address fields, but configuring management IPv6 on this unit was not verified |
| DNS servers | main |
| SNTP client, configurable server port, timezone, EU/US/custom recurring or non-recurring DST | main: NTP, timezone and DST off/eu/us; not equivalent to every vendor time-setting option |
| Manual time setting | Not identified in the compared RTLPlayground controls |

## Ports

| LG510S feature | RTLPlayground coverage |
|---|---|
| Administrative enable and description | main |
| Speed and duplex | main |
| Copper ports supporting 2.5G/5G/10GBASE-T | **Integrated-PHY hardware difference:** RTL837x integrated copper PHYs are 2.5G-class. External 10G PHYs on other supported boards must be assessed separately; 10G copper is not universally impossible for every RTLPlayground board |
| Six 10G ports: four copper and two SFP+ | **SoC topology limit:** this six-port 10G arrangement exceeds RTL8372's two / RTL8373's one 10G SerDes interfaces; a GUI change cannot reproduce the RTL9303 board topology |
| Configurable flow control and operational state | PR #652 adds per-port control and richer status; existing CLI can report negotiated pause |
| EEE per port | main: status and toggle; richer advertised/link-partner details in PR #652 |
| Global jumbo frame size, range 1518–10000 | main: per-port MTU control, accepted CLI range 64–16383. Accepted values/readback do not independently prove effective wire-length semantics |
| Port security: MAC limits, violation action, sticky mode and rate limits | No equivalent complete feature identified in main. Per-port learn-limit hardware exists; complete implementation and enforcement need verification |
| Protected ports | main: port isolation, offering more general allowed-port sets |
| Storm control: broadcast, unknown multicast/unicast, pps/kbps and actions | main provides storm controls; PR #539 changes shared meter allocation. Exact vendor-action parity is not established |
| Four mirroring sessions with RX/TX sources | main provides mirroring. The exact hardware/session-count difference was not verified |
| Eight LAG groups, static/LACP, hash selection and LACP priorities/timeouts | main provides four groups, LACP and hash controls. Do not label eight groups an established SoC impossibility without checking the hardware limits |

## VLAN

| LG510S feature | RTLPlayground coverage |
|---|---|
| VLAN creation/naming and tagged, untagged or forbidden membership | main supports VLAN creation/naming and membership; no equivalent forbidden membership state was identified |
| Per-port VLAN mode, PVID and ingress filtering | main has PVID and ingress controls; exact mode parity is not established |
| Acceptable frame types, TPID and uplink settings | Some overlap through RTLPlayground ingress controls; equivalent coverage of all vendor settings, particularly TPID/uplink, was not established |

## MAC address table

| LG510S feature | RTLPlayground coverage |
|---|---|
| Static MAC entries | No corresponding static-entry configuration identified in the surveyed main UI; the L2 table is programmable, so this is not inherently a hardware impossibility |
| Filtering/drop addresses | No corresponding complete control identified in main; implementation/hardware enforcement needs assessment |

## Spanning tree, rings and loops

| LG510S feature | RTLPlayground coverage |
|---|---|
| STP/RSTP, BPDU handling, timers and statistics | main includes the RSTP work merged as PR #444; exact option parity needs checking |
| MSTP instances and per-instance port settings | PR #453, described as supporting up to 15 instances |
| ERPS / G.8032 ring protection | Not implemented in the compared main; software/driver/CPU requirements need assessment, not an automatic SoC-impossibility label |
| Loopback detection with blocking and automatic resume | PR #456: RLDP |

## Discovery

| LG510S feature | RTLPlayground coverage |
|---|---|
| LLDP transmission, timers and per-port TX/RX controls | main has transmission; PRs #587–#605 cover related timing, receive and TLV work, not all merged capabilities |
| Neighbor table, local information and statistics | Parts covered by PRs #589, #593 and #595; not all are included in our integration branch |
| Vendor LLDP Packet View / overloading page | No equivalent identified; this page was not verified as a packet-capture facility |
| LLDP-MED network policies and port settings | Not implemented in the compared main; software gap rather than an established SoC limit |

## Multicast

| LG510S feature | RTLPlayground coverage |
|---|---|
| IGMP snooping, report suppression, per-VLAN timers and immediate leave | main has IPv4 IGMP snooping, but not equivalent coverage of all these controls. Its documented DIP/SIP forwarding path is not VLAN-aware; IPv6 MLD management is not implemented |
| IGMP querier | Not implemented in the compared main |
| Unknown-multicast action and DMAC/DIP forwarding selection | No equivalent complete management controls identified in main |
| Static multicast groups and router ports | Router-port API exists in main; no equivalent full group/router-port UI identified |

## Security and QoS

| LG510S feature | RTLPlayground coverage |
|---|---|
| Enable/disable management services, configure session timeout | main supports session timeout; no equivalent complete HTTP/SNMP service-management interface |
| DHCP snooping and IP/MAC binding (vendor IMPV/IPSG binding page) | PR #532 covers snooping/binding work; PR #520 adds ACL capability. Exact binding-enforcement parity was not verified |
| CoS/DSCP trust, mapping and remarking | PRs #617/#618 cover CoS/DSCP queue selection/mapping work; full remarking parity was not established |
| Eight queues, strict/weighted scheduling and CoS/DSCP maps | PR #628 covers queue limits and a per-port scheduler bit; this is not evidence of complete vendor scheduling/UI parity |
| Ingress/egress rate limits | main: Bandwidth |

## Diagnostics and management

| LG510S feature | RTLPlayground coverage |
|---|---|
| Ping | No corresponding CLI/UI function identified in the compared main |
| Copper cable test | main: CLI cable test; no equivalent web page |
| SFP DDM: temperature, voltage, bias, optical power and LOS | main provides SFP diagnostics; actual fields depend on the module |
| Multiple users and privilege levels | main uses one administrative password, not equivalent account/role management |
| Firmware upgrade over HTTP or TFTP; two image slots | main: HTTP upgrade; no equivalent exposed dual-image/TFTP workflow |
| Configuration save, backup and restore over HTTP or TFTP | main: HTTP configuration operations; no equivalent TFTP workflow |
| SNMP v1/v2c/v3 views, groups, communities, users, engine ID, traps and notifications | PR #615 adds read-only v2c. Full parity is absent; SNMPv3 cost requires measurement, not a claim of fundamental impossibility on the SoC |

## RTLPlayground advantages or additional areas to retain

| RTLPlayground feature | LG510S survey / relevance to our replacement |
|---|---|
| Per-port MTU | Vendor UI exposes one global jumbo setting |
| Arbitrary allowed-port isolation sets | Vendor ordinary UI exposes protected/unprotected ports |
| LED/GPIO and direct register/PHY/SerDes CLI access | Not exposed through the ordinary vendor web UI; guarded SDK diagnostic access exists, so this is not proof the vendor stack lacks the underlying functions |
| Health instrumentation | Useful model for diagnosability; not an exposed equivalent in the vendor survey |
| MACsec and 802.1X work | RTLPlayground PRs #718/#606 explore these areas. Vendor images contain additional hidden authentication components; absence from the enabled menu does not establish hardware absence or working support |

## How to use this annex

Treat each row as an item to evaluate when it becomes useful, not a promise to implement it. The RTL837x limits above do not constrain our RTL9303 replacement: its limits come from this board, the chosen open drivers and measured resource budgets. Preserve standard Linux behavior where it helps rather than emulating an 8051 interface solely for compatibility.

The detailed vendor inventory remains in [features.md](features.md); verified hardware/file findings are in [firmware.md](firmware.md). The recommended implementation order is in the [project reassessment](project-reassessment.md).
