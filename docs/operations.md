# Operation log and API notes — 2026-10-28

## Device roles

- Production unit: carries the lab's uplink; it was never changed.
- Spare unit: used for all experiments; source of the programmer dump.
- Separate RTL8373 switches running RTLPlayground are on the same network. Do not flash the LG510S firmware onto them.

No credentials belong in this repository. Ask the owner for the current credentials or prompt interactively. Password changes in running configuration may revert on reboot unless explicitly saved.

## Vendor CGI protocol

The observed server reports Hydra/0.1.8; the extracted web server binary is `boa`. Do not assume those banners are distinct services. UI: Backbone.js plus `cgi/get.cgi?cmd=...` and `cgi/set.cgi?cmd=...`.

Login flow:

1. GET `home_login` for the RSA modulus.
2. Encrypt the password using RSA PKCS#1 v1.5, exponent 65537, then base64.
3. POST `home_loginAuth` with username and encrypted password.
4. GET `home_loginStatus` until `data.status` is `ok`; stop on the first explicit failure.
5. Keep the session cookie private and scoped to this unit.

The wire JSON is unusual: Backbone passes a form-encoded string as an object key. The envelope is a JSON object with one key `_ds=1&<urlencoded fields>&_de=1` and value `{}`. Fields must be URL-encoded, including `+`, `/`, `=` in base64.

Useful observed GET commands:

| Commands | Data |
|---|---|
| `home_main`, `sys_sysinfo` | Model/menu, firmware, hostname and addresses |
| `sys_line` | Management services exposed by the UI (only HTTP and SNMP were listed) |
| `aaa_login`, `aaa_loginAuth` | Existing authentication lists and line bindings, even though AAA pages are hidden from the normal menu |
| `lldp_prop`, `lldp_port`, `lldp_neighbor`, `lldp_statistic` | Discovery configuration, neighbours and counters |
| `port_port`, `port_eee`, `port_jumbo`, `port_cnt` | Port configuration/status, global jumbo size and counters |
| `vlan_conf`, `vlan_port`, `lag_mgmt`, `lag_lacp` | VLAN and aggregation state |
| `stp_global`, `stp_msti`, `qos_prop`, `qos_queue` | STP/MSTP and QoS configuration |
| `file_upStatus` with `fileType=running` | Running-configuration upload result |

GET naming alone does not establish that an arbitrary undocumented endpoint is harmless. Do not bulk-call every entry in `url.js`; many are disabled features or require parameters. The original survey fetched the 65 enabled menu pages and their known GET data.

### Configuration uploads

- Multipart POST `/cgi/httpuploadruncfg.cgi`, field `fileName`: applies a running configuration.
- `/cgi/httprestorecfg.cgi`: startup configuration; do not substitute it during an experiment.
- Other form fields used by the normal page: `fileType=running`, `cfg_action=upgrade`, `method=http`.
- Header required by observed fragments: `SYSTEM CONFIG FILE ::= BEGIN`, followed by the model/version comment header.
- A `200` response/`status: success` does **not** prove the intended command or section was applied. Always read back the specific configuration.
- Saving to flash is a separate operation; not automated in the toolkit.

## SSH enablement: verified workflow

The firmware already has SSH and Telnet binaries, keys and inetd configuration. Their absence from the menu did not mean they were compiled out. Earlier claims that SSH binaries were missing were disproved by extraction.

1. A running-config fragment containing only global `ip ssh` opened TCP port 22.
2. SSH identifies as OpenSSH 6.2 and offers old RSA/DSA host signatures. A per-host `HostKeyAlgorithms=+ssh-rsa` exception permits negotiation. Do not enable obsolete algorithms globally or disable fingerprint verification in a reusable client.
3. OpenSSH's transport reported successful authentication using `none`, but the vendor CLI immediately failed login. Forcing SSH password auth with an old Paramiko client did not fix this.
4. Read-only `aaa_login` showed `default` = local users. `aaa_loginAuth` showed Console/Telnet bound to it but SSH unbound.
5. The native AAA form uses `list_<line val>` fields. The observed line IDs are Console 0, Telnet 1, SSH 2, HTTP 3, HTTPS 4.
6. Applying the SSH binding through `set.cgi?cmd=aaa_loginAuth` succeeded; GET readback showed SSH = `default`.
7. An interactive SSH connection then displayed `Username:` and `Password:`. Entering the local user/password reached the `Switch#` prompt; `show version` returned loader 1.0.0.2 and firmware 1.1.1.34. This is the vendor CLI, not a Linux shell.

`show line lists` returned `Unknown command` despite related strings in the CLI library. Do not advertise it as a supported diagnostic.

### Failed attempt and side effects

A fragment containing `line ssh` followed by indented `login authentication default` reported success but changed the HTTP authentication binding while leaving SSH unbound. A `no ip http login authentication` fragment did not return the empty HTTP binding: the vendor returned `default`. A subsequent native AAA write correctly bound SSH; attempts to send an empty HTTP list still read back as `default`.

The initial HTTP field was empty; it now reads `default` (the same local-user authentication list). Web login remained functional with the existing credentials, and no passwords were changed. This runtime normalization was an unintended side effect, not a proven exact rollback. Nothing was saved to flash. Do not repeat the context-sensitive fragment approach or claim that every other raw field was unchanged.

Reusable tooling uses the native API and verifies that non-SSH bindings remain unchanged. If a fresh unit normalizes additional bindings, it stops and retains before/after snapshots for inspection rather than blindly writing again.

## LLDP interoperability

Observed on the production switch: enabling pfSense LLDP transmission was associated with stopped switch LLDP advertisements and an HTTP listener that accepted TCP but sent no response. The switch recovered after a power cycle with pfSense receive-only. No kernel crash trace or isolated trigger was captured.

pfSense's local System Description was roughly 282 ASCII bytes of FreeBSD build text. With a 7-octet `pfSense` description, the switch learned the firewall, kept advertising, and returned HTTP 200 for a 90-second test. Reintroducing the LAN IPv6 management address alongside IPv4 also worked. Both management TLVs use LAN interface index 2. Length is the leading hypothesis, not proven as the sole cause; do not deliberately replay the long description on the production uplink.

The pfSense package regenerates its service command on Save, losing a runtime description override. The temporary workaround keeps its GUI package disabled and starts a separately owned script:

- `/usr/local/etc/rc.d/zz-lldpd-local.sh`
- `/conf/lldpd-local.conf`
- daemon flags: `-l -S pfSense -I ixl1 -C ixl1 -m ixl1 -O /conf/lldpd-local.conf`
- startup port status: RX only; runtime transmission was later enabled explicitly for the controlled test.

`-m ixl1` selects the LAN IPv4/IPv6 management addresses rather than the unrelated WAN-side IPv4 address. The `-S` flag establishes the description at daemon launch. The custom files are not in pfSense's normal config.xml backup. No firewall reboot was tested.

Existing upstream report: https://redmine.pfsense.org/issues/17002 (283-octet System Description TLV captured by another reporter).
Fix PR: https://github.com/pfsense/FreeBSD-ports/pull/1468 (255-octet encoder limit preserving UTF-8 boundaries). Our evidence and the PR URL were posted on the existing Redmine issue. The fix was encoder-tested, not deployed to this firewall or switch.

## Host/tool limitations

Initially macOS allowed `/usr/bin/curl`/SSH but denied LAN access to Python/Chromium. Do not diagnose those host permission errors as a switch outage. Docker with host networking reached the switch; its normal network path did not. Permission prompts were subsequently addressed by the owner.

The scratch Expect script timed out even after SSH started presenting a login prompt. A direct interactive PTY session worked. Authentication examples intentionally use an interactive SSH command until reliable automation has been verified.
