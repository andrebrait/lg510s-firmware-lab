# Offline validation and UART adapter — 2026-10-29

## Result

The actual OpenWrt reference userspace boots on an emulated big-endian MIPS Malta with 128 MiB RAM. Procd, ubus, netifd and Dropbear start; key-authenticated SSH and native OpenWrt DHCP acquisition work. The existing Linux management prototype also runs there, but has a confirmed IPv4 byte-order defect. This is useful software evidence, not LG510S hardware support or permission to boot/flash a switch.

No physical switch was contacted or changed by these tests. In particular, there was no reboot, flash write, register write or configuration change on either switch.

| Check | Observed result |
|---|---|
| Actual target binaries under QEMU user mode | BusyBox arithmetic and 1 MiB SHA-256 vector, ethtool, Dropbear and ip-full loopback query passed |
| Linux prototype unit assertions | 216 passed natively and 216 passed on emulated MIPS after correcting a test-only 32-bit portability error |
| Existing native namespace integration suite | 9/10 groups passed; `t_vlan` failed waiting for a DHCP lease |
| Existing namespace suite with MIPS binaries under QEMU user mode | 3/10 groups passed; significant netlink/ioctl translation limitations make this unsuitable as a complete networking acceptance gate |
| Actual userspace on full-system Malta | Boot, procd/ubus/netifd/Dropbear startup, SSH and native netifd DHCP passed at 128 MiB |
| Management prototype in full-system Malta | Completed: 34 checks passed, 3 checks failed, all three concerning IPv4 configuration/representation |
| Native reference image integrity/layout | CRCs, native metadata, package/driver requirements, kernel/DTB payload comparison and nominal 128 MiB segment bounds passed; image remains reference-only |
| Reference DTB schema validation | 43 errors and 16 unmatched-binding warnings; not schema-clean |
| Existing research-tool regression suite | 14/14 passed; synthetic tests, not additional hardware or QEMU coverage |

An all-checks-green result is not claimed. No browser-rendering, physical forwarding/offload, real PHY, SerDes or SFP test is implied.

## Inputs and isolation

Tests ran on the existing dedicated Debian 13 build VM, (`rtlp-build`), not on a switch. QEMU is Debian `10.0.13`. New packages were validation prerequisites; no VM reboot or unrelated host change was performed.

The native firmware inputs remain:

- OpenWrt source commit `19483fa9075686e7a627c777e09c0a24163c8323`.
- Reference profile `sirivision_sr-st3408f`, `realtek/rtl930x`, not an LG510S profile.
- Native initramfs image SHA-256 `adca7ddfe2aac2df0ff4340a0f015074c6a215107be198100924332381a41ad1`.
- The actual embedded reference archive is 7,758,336 bytes, SHA-256 `930404615b12eb0bc897e292b81f15401a3719977e873cc5c12e1d39b5b4d102`.

The reusable management code was checked at RTLPlayground commit `03b4b91` (`feat/linux-userland`). It is still a prototype, not packaged into the reference firmware. Its daemon, CLI client and existing tests were cross-built with the already-built OpenWrt GCC 14.4.0 MIPS toolchain and target libmnl. The only source correction was to its test result reporter; production application code was not fixed or changed.

All source work happened in task-specific linked worktrees. VM copies are:

```text
/srv/.lg510s-validation_worktrees/validate/offline-confidence
/srv/.rtlp-qemu-validation_worktrees/validate/qemu-linux-userland
```

Generated kernels, downloaded files, reports, cookie jars and ephemeral SSH keys remain under ignored `scratch/`. No vendor dump, extracted vendor binary, real device configuration or private key is committed.

## MIPS userspace checks

`qemu-mips -cpu 24Kc -L <actual-root-realtek>` executed the actual target BusyBox, ethtool 7.2, Dropbear 2026.94 and ip-full 7.3.0 binaries. The BusyBox SHA-256 result for a 1 MiB all-byte-value vector matched the native host: `fbbab289f7f94b25736c58be46a994c441fd02552cc6022352e3d86d2fab7c83`.

The first ip-full probe used a nonexistent `/usr/sbin/ip` path. After inspecting installed paths, the check used the actual `/usr/libexec/ip-full`. This was a probe-path error, not a target binary failure.

The prototype's original port-logic test reporter accepted `long` values. On the 32-bit target, that truncated its 64-bit advertised-link-mode masks and failed compilation under `-Werror`. The backed-up [test-only patch](../patches/rtlplayground-03b4b91-portlogic-test-width.patch) changes the reporter to `uint64_t` and `PRIx64`, preserving the original assertions rather than weakening warnings or expectations. The focused red-to-green proof was the failing cross-build followed by all 216 assertions passing on MIPS and native Linux.

The four assertion groups are link codes (35), MIB mapping (56), port logic (81) and FDB behavior (44). The FDB test intentionally exercises error handling with mocked netlink dumps; it does not prove hardware FDB operation.

### User-mode networking limit

Running the existing namespace integration suite with QEMU user-mode MIPS binaries passed `t_cli`, `t_http_hostile` and `t_smoke`. The other seven groups failed. This is not a list of seven confirmed application defects.

An isolated control reproduced the emulator limitation without the application:

- Target ip-full under `qemu-mips` could read loopback state, but creating a bridge returned `RTNETLINK answers: Not a socket`.
- Native iproute2 created the same kind of bridge in the same isolated host namespace.
- Actual target ip-full created a bridge successfully under the full-system MIPS kernel.

User-mode syscall translation is therefore not an acceptable substitute for full-system networking tests here. QEMU also reported the wrong virtual-link speed in that mode. The full-system checks below report the expected 10G virtual-link codes.

## Full-system boot of the exact userspace

A dedicated emulator-only Linux 6.18.55 kernel was built from the cached source tarball already verified by the OpenWrt source lock. Tarball SHA-256:

```text
f410638061a165c12f42ab871d2f3fcd525515359b5faeee80969cff84524df9
```

This is a vanilla Malta kernel, not the Realtek kernel or its driver stack. It embeds the reference archive directly. Extracting `.init.ramfs` from `usr/initramfs_data.o` reproduced the original archive byte for byte and with the same SHA-256 above; a different root filesystem was not silently substituted.

Final test-kernel evidence:

| Item | Value |
|---|---|
| CPU / ABI | QEMU 24Kc, ELF32 big-endian MIPS32r2 / O32 |
| RAM | 128 MiB configured |
| Page size | 4 KiB, matching the real reference kernel and userspace ELF load alignment |
| Kernel release | `6.18.55-qemu-validation` |
| Kernel ELF SHA-256 | `9cd7eb02ee17b54b309e71298552e37ff8fa0169bc83f12db7af4db551ef3d6a` |
| Resolved config SHA-256 | `2d38cd64ad19b524eca1abcaa148fade73b558448cc7c7965ce8c039a312fb9b` |

[`tools/qemu-kernel.sh`](../tools/qemu-kernel.sh) records the build configuration. It refuses an existing output directory and asserts required architecture/network selections before building. It intentionally has no Realtek hardware model or destructive reset/clean fallback. Kernel timestamps and absolute build paths mean these recorded hashes are one build's evidence, not a bit-for-bit reproducibility claim.

Boot observations:

- `/etc/openwrt_release` reports the actual `r0-19483fa`, `realtek/rtl930x`, `mips_24kc` userspace.
- PID 1 is procd; ubusd, netifd and Dropbear run.
- The root and writable filesystems are RAM-backed. No persistent guest disk or physical flash is attached.
- An emulator-only public key was provisioned in RAM; SSH authenticated through a VM-loopback-only forwarded port with the guest host key pinned from its console output. No shared password, real SSH identity or host-key-check bypass was used.
- Native UCI/netifd DHCP configuration on emulated `eth0` acquired `10.0.2.15/24`, gateway/DHCP server `10.0.2.2` and DNS `10.0.2.3`. These are QEMU's private user-network services, not the lab network or a switch.

The kernel intentionally has no loadable modules, so startup reports missing module folders for its `-qemu-validation` release. Board-generation/environment warnings are also expected because RTL930x userspace is running on Malta. `nft list ruleset` failed on this generic test kernel; firewall functionality is not accepted by this run.

Two earlier harness attempts failed and were not counted as target boot passes: the downloaded regular Malta kernel ignored the external initramfs; then Malta's default 16 KiB pages could not execute the reference's 4 KiB-aligned ELF files (`error -22`). Embedding the exact archive and selecting the matching page size resolved those harness issues. A missing `/proc/device-tree/model` guard was replaced with the actual `/proc/cpuinfo` Malta identity.

The unused official Malta snapshot inputs were downloaded and checksum-verified before the dedicated kernel build. Its source was `795f369b181cd128962fa8f60a03eaf0ac8afac6`, also Linux 6.18.55, but it was not the kernel used for the passing boot described above.

## Full-system management tests

[`tools/qemu-guest-check.py`](../tools/qemu-guest-check.py) reuses the prototype's existing ownership-aware namespace setup/teardown. It refuses a machine that does not identify as Malta or the wrong reference userspace. Six veth front-panel ports and isolated peers exercise the actual cross-built daemon and CLI client. The control connection is independent of the virtual management VLAN, allowing isolation tests without losing the test harness.

The completed report contains **34 passes and 3 failures**, with `complete: true`, `all_passed: false`, and a nonzero exit status. Passing behavior includes:

- Untagged forwarding; six virtual 10G link codes; down/up transitions; MTU applied to the kernel netdev.
- Password hashing and HTTP login; bad-password refusal; unauthenticated API refusal; gzip asset integrity; malformed port/path rejection; real JSON endpoints and hostname mutation.
- Tagged/untagged VLAN forwarding, cross-VLAN isolation, management VLAN movement and isolation of the previous VLAN.
- Kernel-learned MAC/VLAN/port decoded through the MIPS FDB path.
- Configuration upload, no plaintext password in the stored file, session invalidation on restart, and hostname/VLAN persistence across daemon restart in the RAM-backed test filesystem.

The prototype does not have a CLI `save` command. An initial harness attempt used one incorrectly; the completed test uses the existing authenticated `POST /config` multipart upload contract. That earlier unknown-command result is not an application defect.

### Confirmed IPv4 byte-order defect

All three failures concern the existing prototype's IPv4 handling:

1. `netmask 255.255.255.0` is rejected with `the netmask must be a run of one bits` on MIPS.
2. CLI address/prefix configuration does not produce the requested kernel state.
3. The address and mask are rendered incorrectly through the JSON API.

The shared parser constructs addresses using `uip_ipaddr()` / `HTONS`. `uip-conf.h` selects `LITTLE_ENDIAN`; the legacy uIP constants and libc endian names are not interchangeable. The parser's include environment selects a byte swap that is wrong on this big-endian target. This is independent of QEMU's user-mode netlink limitation.

The focused [IPv4 storage check](../tools/uip-byteorder-check.c), compiled with the shared parser's include environment, proves the actual bytes:

| Build | Address requested | Address stored | Mask stored |
|---|---|---|---|
| Native x86-64 | `192.0.2.10` | `192.0.2.10` | `255.255.255.0` |
| MIPS big-endian | `192.0.2.10` | `0.192.10.2` | `255.255.0.255` |

The native check exits 0; the MIPS check exits 1. No product fix was applied under this validation request.

After recording the failed CLI path, the remaining independent tests establish their address through the kernel explicitly. The report still fails. IPv4 CLI correctness or IPv4 configuration persistence is **not** inferred from successful hostname/VLAN persistence.

### Native namespace failure retained

The unmodified native integration suite passed nine groups but `t_vlan` failed its ten-second DHCP acquisition expectation. Its captured output includes a lease ACK, while the last CLI sample still reported `0.0.0.0 (static)`. The precise timing/lease-application mechanism was not isolated here. The failure was neither hidden nor re-pinned with a looser assertion.

Native OpenWrt netifd's successful DHCP test is a separate result, not a fix for that older prototype path.

## Device tree, image and layout checks

The untouched compiled Sirivision DTB was validated with `dtschema 2026.9` against the patched reference kernel's binding schemas. `dt-validate` returned 0 despite diagnostics, so the JSON diagnostics were inspected rather than treating exit status as success:

- 43 validation errors, including interrupt/timer/switch binding differences, legacy LED properties, serial/pinctrl node naming and SFP properties.
- 16 unmatched-binding warnings, including Realtek-specific nodes.
- Schema preprocessing also reported one ignored Hasivo schema and a missing type in a Realtek USB-Ethernet schema.

These are schema-conformance findings in the upstream reference artifacts, not 43 independently confirmed runtime driver bugs. They prevent a schema-clean claim. There is still no exact LG510S device tree to validate.

The actual image's CRCs, native digest/profile/source metadata, required packages/drivers and RTL8264B data passed the existing verifier again. LZMA output exactly matched the native kernel plus appended reference DTB.

Its expanded payload ends at physical `0x012f86b6`; the ELF load segment including BSS ends at `0x0143beec`. Both lie below a nominal 128 MiB ceiling. This does **not** establish a safe board loading/staging address: physical RAM and bootloader reservations remain unverified, the reference DT declares 512 MiB, its image magic differs from stock, and its port/GPIO wiring is not this board's wiring.

Subsequent [loader disassembly](board-evidence-review.md#loader-and-reference-image-hazard) adds a concrete risk: this output intersects stock `boota` staging at `0x81000000`, and the loader checks overlap only after decompression, permitting legacy single-kernel continuation. Its LZMA wrapper does not enforce the apparent 8 MiB caller bound. Exact unread-input corruption was not demonstrated; no safe loading address is established.

## Reproduction pointers

Run these on the isolated Linux build VM, not on a switch. The OpenWrt source/build location is:

```text
/srv/rtl930x-openwrt-build/.openwrt_worktrees/reference
```

On a fresh linked prototype worktree at `03b4b91`, apply the test-only patch before cross-building:

```sh
LAB=/srv/.lg510s-validation_worktrees/validate/offline-confidence
PROTOTYPE=/srv/.rtlp-qemu-validation_worktrees/validate/qemu-linux-userland
OW=/srv/rtl930x-openwrt-build/.openwrt_worktrees/reference
export STAGING_DIR="$OW/staging_dir/target-mips_24kc_musl"
export CROSS_COMPILE="$OW/staging_dir/toolchain-mips_24kc_gcc-14.4.0_musl/bin/mips-openwrt-linux-musl-"
export QEMU_LD_PREFIX="$OW/build_dir/target-mips_24kc_musl/root-realtek"
export QEMU_CPU=24Kc
git -C "$PROTOTYPE" apply "$LAB/patches/rtlplayground-03b4b91-portlogic-test-width.patch"
make -C "$PROTOTYPE/platform/linux" OUT=output/mips HOOKS=1 \
  CC="${CROSS_COMPILE}gcc -I$STAGING_DIR/usr/include -L$STAGING_DIR/usr/lib" bin html_min unit
```

The unit command executes MIPS binaries through the VM's `qemu-user-binfmt` registration. Direct `qemu-mips -L ...` execution was also exercised for the individual tests.

The emulator-kernel helper takes a verified Linux source directory, a **new** output directory and the existing reference `.cpio`. Export the already-built toolchain prefix as `CROSS_COMPILE` and the OpenWrt target staging path as `STAGING_DIR`; invoke `sh tools/qemu-kernel.sh <source> <new-output> <reference.cpio>`.

The actual passing emulator used:

```sh
qemu-system-mips -M malta -cpu 24Kc -m 128 -nographic -monitor none -no-reboot \
  -kernel "$LAB/scratch/malta-build-4k/vmlinux" \
  -qmp "unix:$LAB/scratch/malta-validation.qmp,server=on,wait=off" \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:22044-:22 \
  -device pcnet,netdev=net0 -device virtio-rng-pci \
  -append 'console=ttyS0,115200 loglevel=4'
```

`LAB` is the validation worktree path shown above. Provision an ephemeral public key in guest RAM, pin its server host key, and give the emulated NIC its test address before running:

```sh
python3 tools/qemu-guest-check.py <prototype-worktree> <ephemeral-private-key> \
  <pinned-guest-known-hosts> <new-report.json>
```

The driver uses only loopback port 22044 and reports known failures; it does not silently make a failing suite green. It uploads only cross-built prototype binaries, generated web assets and the existing fixture scripts into guest RAM. No firmware installation is performed.

For the separate native OpenWrt DHCP check, the following commands were issued only inside the disposable guest; `/etc/config/network` is RAM-backed there:

```sh
uci set network.qtest=interface
uci set network.qtest.device=eth0
uci set network.qtest.proto=dhcp
uci commit network
ubus call network reload
ifstatus qtest
```

The test waited for `up: true` and checked the actual lease address, prefix and route rather than counting command success as acquisition.


To reproduce the narrow IPv4 proof, compile `tools/uip-byteorder-check.c` with the prototype's real include paths (`platform/linux`, `platform/linux/output/mips`, repository root, `httpd`, `uip`), `-DRTLP_HOST_TEST -D_GNU_SOURCE -include platform/linux/sdcc_shim.h`, and the native or MIPS compiler. Run the MIPS result with `qemu-mips -cpu 24Kc -L <actual-root-realtek>`. Keep the parser's include environment; adding libc network headers before uIP changes these legacy macro definitions.

## UART purchase

A genuine **FTDI TTL-232R-3V3** cable provides documented **3.3 V UART logic**. Do not buy an RS-232 adapter or a 5 V logic cable. Individual jumper leads will be useful because the board's header/pad order is not established.

The FTDI cable's red VCC wire outputs **5 V even on the 3V3 model**. Leave VCC, RTS and CTS disconnected. After verifying the switch's UART signal voltage and pinout, use ground, adapter TX to switch RX and adapter RX to switch TX. If the board uses 1.8 V signalling, a matching adapter/level translator is needed; the flash chip's 3.3 V supply does not prove UART voltage. The board was later measured at 3.3 V and a 115200 session worked; see the [UART validation](uart-uboot-validation.md).

The owner's [Amazon link](https://amzn.eu/d/074quS0a) resolves to **DSD TECH SH-U09C5**, ASIN **B07WX2DSVB**. The [manufacturer specification](https://www.deshide.com/product-details_1663161.html) lists FT232RL with selectable **1.8/2.5/3.3/5 V UART logic** and selectable output VCC. It is suitable on specification: choose the measured board signal level and connect only GND/TX/RX after identifying the pads. Leave VCC disconnected. Unlike the fixed FTDI cable above, this adapter does not have an invariably 5 V output. The purchased unit worked at its 3.3 V setting on the measured 3.3 V console.

Sources:

- [FTDI product specification](https://ftdichip.com/products/ttl-232r-3v3/); manufacturer datasheet [mirror, section 4](https://cdn-shop.adafruit.com/datasheets/DS_TTL-232R_CABLES_V201.pdf). FTDI's direct pages returned HTTP 403 to the reader, so the manufacturer's PDF hosted by Adafruit supplied the full electrical table.
- [QEMU MIPS system models](https://www.qemu.org/docs/master/system/target-mips.html) and [user-mode semantics](https://www.qemu.org/docs/master/user/main.html).
- [OpenWrt's pinned Malta instructions](https://github.com/openwrt/openwrt/blob/19483fa9075686e7a627c777e09c0a24163c8323/target/linux/malta/README).
- [Native OpenWrt network configuration](https://openwrt.org/docs/guide-user/network/network_configuration).
- [Kernel device-tree validation](https://docs.kernel.org/devicetree/bindings/writing-schema.html).

The next software blocker is the prototype's IPv4 endian boundary. Physical board wiring, bootloader behavior, driver initialization, offload and programmer-based recovery remain unproven by QEMU.

After collecting evidence, the disposable emulator was stopped through its owned QMP socket and exited successfully. Its ephemeral client key pair and guest known-hosts file were removed. The build VM was left running; ignored build artifacts and diagnostic reports were retained for reproduction.
