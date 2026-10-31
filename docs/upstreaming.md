# Upstreaming

The board support, the `switchdev-config` package and the LuCI changes are prepared as five pull requests. Each branch is rebased on the upstream head named below, and every commit carries `Assisted-by: Claude:claude-opus-5-5` before `Signed-off-by`, as the OpenWrt AI policy requires.

| PR | Repository | Branch | Base | Commits |
|---|---|---|---|---|
| 1 | `openwrt/openwrt` | `lg510s-4t2xs` | `main` `feb8ac5` | `realtek: rtl930x: add Lianguo LG510S-4T2XS` |
| 2 | `openwrt/packages` | `switchdev-config` | `master` `87849fccd` | `switchdev-config: add new package` |
| 3 | `openwrt/luci` | `luci-network-eee-pause-stp` | `master` `5599f42b0e` | EEE option, flow-control advertisement option, STP protocol option |
| 4 | `openwrt/luci` | `luci-ethtool-port-status` | `master` `5599f42b0e` | `getEthtoolStatus` RPC method, Devices-tab columns, Status -> Ports page |
| 5 | `openwrt/luci` | `luci-app-switchdev` | `master` `5599f42b0e` | `luci-app-switchdev: add application` |

PRs 1 to 4 are independent. PR 5 needs PR 2: open it as a draft and mark it ready once `switchdev-config` is merged.

The upstream board patch differs from [`openwrt/0001`](../openwrt/0001-realtek-rtl930x-add-Lianguo-LG510S-4T2XS.patch) in this repository. It has none of this build's first-boot defaults (port EEE and pause, LLDP, SNMP, HTTPS, DHCP management), and its DTS follows current upstream style: `ethernet-phy-package`, `SWITCH_PORT_LED`/`SWITCH_PORT_SFP` and `-gpios` property names.

## Before submitting

1. Stock web upgrade: install `factory.bix` through the stock firmware's upgrade page on a unit still running stock firmware. If it works, add that route to the commit message.
2. Build each branch once more against the then-current upstream head.

The board uses Lianguo as the primary name, from the model number on the tested unit, and lists GoodTop, Horaco, HRUI, MokerLink and Sodola as `DEVICE_ALT0` to `DEVICE_ALT4`.

## Signing and pushing

LuCI and packages CI reject unsigned commits. The signed branches are in local worktrees under `~/git/.openwrt_worktrees/`, `~/git/.packages_worktrees/` and `~/git/.luci_worktrees/`, with the same branch names as above. Their trees are identical to the build-host branches, and `git log --format=%G?` shows `G` for every commit.

They were made by applying the build-host commits with `git am` (or `git rebase --force-rebase --gpg-sign` for OpenWrt) on top of the upstream base, with `commit.gpgsign` set. Author, date, message and trailers are unchanged. To push one:

```sh
git -C ~/git/.luci_worktrees/<branch> push <your fork> <branch>
```

The local repositories are shallow clones of the upstream base. If a push is refused for missing history, run `git fetch --unshallow` against upstream first.

## Pull request text

The OpenWrt projects close pull requests that look autonomously generated, and they ask for descriptions written by the contributor. The notes below are facts to draw on, not text to paste.

**PR 1, board support.** Hardware and installation are in the commit message. Points to mention: no lane polarity overrides are needed (tested on lan1 and lan2, which cover both patterns, matching openwrt/openwrt#26090), the port LED setup reproducing stock, and that only the TFTP and sysupgrade route was tested.

**PR 2, `switchdev-config`.** What it configures (static FDB entries, mirroring, ingress policing, egress shaping), that every rule uses `skip_sw`, and the test on the LG510S-4T2XS where all four rule types showed as offloaded. Mention `net/tcfilter` and the overlap described below. Fill in the template's AI checkbox.

**PR 3, network device options.** netifd already supports `eee`, `pause` and `stp_proto`; LuCI had no fields for them. `pause` advertises and leaves the result to autonegotiation, unlike `rxpause`/`txpause`.

**PR 4, ethtool status.** One RPC method with validated device names, used by two views. Screenshots of the Devices tab and the Ports page help here. openwrt/luci#9165 also touches ethtool JSON output; check it before submitting.

**PR 5, `luci-app-switchdev`.** Depends on PR 2. Screenshots of the three pages.

The LuCI template asks for the OpenWrt version, LuCI version and browser used for testing. The views were tested on the LG510S-4T2XS with OpenWrt `19483fa` and the LuCI commits before the rebase; take the versions from the LuCI footer of the build that is tested last.

## `switchdev-config` and `net/tcfilter`

`net/tcfilter` (maintainer Mark Abe, added 2026-09-07) installs raw `tc filter add dev <device> ingress pref <pref> <spec>` lines from UCI. It tracks what it installed, so it can remove the filters again, and it re-applies them from hotplug when a device reappears. Only ingress filters are supported, and the match and action are entered verbatim as tc syntax.

How the four `switchdev-config` rule types map onto it:

| Rule type | Mechanism | Fits `tcfilter` |
|---|---|---|
| Ingress rate limit | `flower` with `police`, `skip_sw` | Yes, as a raw spec |
| Mirroring of received traffic | `matchall` with `mirred egress mirror`, ingress | Yes, as a raw spec |
| Mirroring of sent traffic | Same filter on egress | No: needs egress filters |
| Egress rate limit | TBF root qdisc | No: a qdisc, not a filter |
| Static FDB entry | `bridge fdb add ... static` | No: not tc |

Extending `tcfilter` would mean adding a `direction` option and generating its rules from `luci-app-switchdev` for mirroring and policing. FDB entries and egress shaping would still need a separate home, so the features would be split across two packages and two configuration files.

Decision: keep `switchdev-config` as one package and state the overlap in PR 2. The point to make there: `tcfilter` is a generic front-end for raw ingress filters, while `switchdev-config` offers four fixed, validated rule types for a LuCI application, and only ingress policing and received-traffic mirroring could be expressed in `tcfilter` today.
