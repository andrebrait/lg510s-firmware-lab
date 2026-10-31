# Independent LG510S core-evidence review

## Verdict and provenance

**The six-port allocation and SFP GPIO/I2C numbers in the pinned documents are confirmed as static vendor configuration. No conflicting core mapping was found. They do not establish active HAL selection, physical continuity, or permission to boot/flash.**

- Requested seat: Gemini4Argon retry. Runtime identifier exposed by this session's harness: **`google-antigravity/gemini-4-argon`**. No substitution notice is visible. Provider-internal model identity is not independently attestable from the available tools; do not describe this as a separately verified provider attestation.
- Checkout: `<worktrees>/review/board-evidence-argon-retry`, observed HEAD `6f7d67b`.
- Blind notes: `scratch/blind-notes.md`, 11170 bytes, SHA-256 **`e62419dcf6377bf02fff20429a6da53af0b5fe043ffd82e931d93f8239df1152`**. Saved and hashed before the first reads of all four pinned documents. Tool order records the seal, then the document reads. No peer outputs were read.
- Raw modules under `~/lg510s-dump/modsqfs/lib/modules/3.18.24/`: `extra/board_conf.ko` SHA-256 `027521d79363a0cbe9ac84c2ee64e2424cbea511bc2e5bfcb895a03715510d70`; `kernel/drivers/net/switch/rtcore/rtcore.ko` SHA-256 `d81ba50d4e9058d1633281400809204ed0db7d5b168586d9f803769c53eee5c4`; supporting `extra/ski.ko` SHA-256 `ab5244c2058ef8b6ab04ccf0cc5370b8a068ab931c7a063f2d26ede0a69b9cfb`.
- Independently decoded ELF32 big-endian headers, sections, symbol indices and in-place REL addends using Python's standard library. Cross-checked native MIPS readelf/objdump via the expressly supplied transport helper and existing analysis VM toolchain. Modules were never loaded/executed. Retained native evidence: `scratch/{board_conf,rtcore,ski}-disassembly.txt`; decoder/probes: `scratch/inspect_elf.py`, `elf_probe.py`, `profiles.py`, `selector-details.py`.
- First full dump hash matched the supplied hash. Other dump copies were not rehashed. Read `rootfs/etc/rc`; printed only allowed environment values. Two initial inline Python quoting attempts failed with SyntaxError and were corrected; native binutils worked in this seat.

## Independent mapping and proof

All numbers below are **static**, conditional on selecting profile ID `9300034` (`0x008de842`). SDK unit is zero throughout.

| CLI/user port | SDK switch/MAC port | Vendor media | Static SerDes lane association* |
|---|---:|---|---:|
| TE1 / 1 | 0 | Copper | 2 |
| TE2 / 2 | 8 | Copper | 3 |
| TE3 / 3 | 16 | Copper | 4 |
| TE4 / 4 | 20 | Copper | 5 |
| TE5 / 5 | 25 | Fiber | 7 |
| TE6 / 6 | 26 | Fiber | 8 |

*Lane association is recovered from the stock SDK descriptor/parser, not a measured live mode or verified replacement-driver setup. PHY MDIO addresses and lane polarity are not established here.

Proof anchors:

1. `rtcore.ko`: `.data` file base `0x301e0`; hardware-profile list slot `.data+0x824` has `R_MIPS_32`, **symbol #7 = .data**, `S=0`, in-place `A=0x33dc`. Target header name at `+0x33e0` is exactly `RTL9303_8264B_2XGE`; ID at `+0x340c` is `0x008de842`. Profile switch pointer at `+0x3418` is symbol #7 plus `0x3434`.
2. `board_conf.ko`: `.data` file base `0x8980`; record `.data+0x160` has that ID. Relocations at `+0x164/+0x168` bind **symbol #145** `portConf_9303M4XC2XF` and **#312** `fiberConf_9303M4XC2XF`, both addend zero. `.text+0x318..328` obtains ID from `hwp_myHwProfile+0x30`; `board_conf_get` at `+0xd04` searches/caches the matching boardMap record.
3. `.rodata` file base `0x2c90`; port table `.rodata+0x1f00`, stride 32, six rows then sentinel. Row offsets: type `+0`, user `+4`, SDK unit `+8`, SDK port `+12`, media `+16`. Native formatter `.text+0x910..9c4` establishes these roles; `ski.ko:board_conf_port_get`, `.text+0x70e10..70e5c`, independently looks up the unit/port pair. Raw SDK-port words are **0,8,16,20,25,26**, not PHY addresses.
4. SDK switch descriptor `.data+0x3434` has 20-byte port entries at `+0x14`. It also includes MAC24 and MAC27; those are **not extra front-panel ports in board_conf**. In particular, do not assign TE5 to MAC24 by blindly taking the fifth SDK row. `_hwp_port_parse` `.text+0x12f68..12f94` establishes stride/terminator.
5. `_hwp_serdes_parse` `.text+0x13ec0..13f48` reads two-byte descriptors from switch `+0x515`; `.text+0x14004` reads each port's word `+4` as their index. Bytes at `.data+0x3949` are `02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff`. Indices 0..7 map MAC0/8/16/20/24/25/26/27 to lanes2/3/4/5/6/7/8/9. Attribute bytes `72/71/70/08` were not promoted to mode/polarity claims.

### SFP records and meanings

| Cage label | Logical port | I2C device | Path | EEPROM | SCK / SDA | MDO/detect | LOS | TX-disable |
|---|---:|---:|---|---|---|---:|---:|---:|
| TE5 | 4 | 0 | software GPIO | `0x50` | INT8 / INT9 | INT14 | INT13 | INT15 |
| TE6 | 5 | 1 | software GPIO | `0x50` | INT8 / INT10 | INT17 | INT16 | INT18 |

These are vendor internal GPIO numbers, not package pins or Linux global GPIO numbers. I2C devices **0/1 are not hardware controllers 0/1**. The shared clock is configuration evidence, not a continuity measurement.

- `fiberConf` `.rodata+0x387c` has count2, detection pointer through symbol #176 to `+0x38f0`, optical pointer through #335 to `+0x3888`.
- Optical rows, stride52: `4,0,2,0x50,0,20,1,1,0,8,9,0,0` and `5,1,2,0x50,0,20,1,1,0,8,10,0,0`. Interface **2** means software GPIO; 0/1 mean hardware controllers, established by formatter `.text+0x1308..154c`. Delay20 has no established unit. `ski:board_fiber_optical_init` `+0x72478..72494` passes row+4 to the driver. `rtcore:r9300_i2c_dev_init` `+0x5958..5988` actually dispatches interface2 to `drv_software_i2c_init`, corroborating the formatter interpretation.
- Detection rows have logical ports4/5, presence selector1=`OE`, media-change selector0=`None`, OE/LOS enabled flags1. **Those flags do not mean a module is currently inserted or LOS asserted.** OE reads the MDO input, not the TX-disable output; avoid interpreting the acronym as a driveable output-enable.
- Detection relocations at `.rodata+0x3904/3908/3920/3924` use **symbol #227**, `boardGpio_930x`, `S=.data+0x670`; addends `0x50c/0x4b0/0x620/0x5c4`. These equal **92×(14/13/17/16)+4**. The `+4` skips the table entry ID and points at the unit/bank/pin descriptor. For example `0x670+0x50c=0xb7c`; treating `0x50c` as absolute or omitting `+4` is wrong.
- The file's GPIO entries are initially ID-only, not fully initialized wiring records. ID9300034 jump slot `.rodata+0x480c` reaches `.text+0x1a8c`, selects the 32 internal entries, then reaches `.text+0x2684..2738`. Helper0x15d0 installs MDO14/17; helper0x1724 LOS13/16; helper0x1878 TX_DIS15/18. MDO/LOS are inputs, default1; TX_DIS outputs default0, with descriptor marker1.
- More polarity semantics are recoverable than the docs currently record: `ski:board_fiber_oeStatus_get` `+0x77158..77184` and `board_fiber_losStatus_get` `+0x7727c..772a4` return1 for raw low with these descriptors. But the monitor at `+0x76edc..76f20` / `+0x77040..7704c` enables reception on LOS raw low and disables it otherwise. Thus **API losStatus=1 is not evidence that electrical loss is asserted**. Physical polarity/inversion and cage continuity still require validation. TX_DIS name/marker/default are consistent with high-disable, but its downstream actuation semantics were not fully traced.

## Findings and document dispositions

**No incorrect core port or GPIO number was found.** The following are evidence completions, not evidence that the stock board runs another profile.

1. **Selection chain needs its conditional branches recorded** — `docs/board4-investigation.md:57-65`; related shorthand `docs/firmware.md:51`.
   `rtcore:hwp_probe` `+0x16e90..16ef4` consults the forced identifier before the environment. `ioal_param_hwpIdKey_get` `+0x18664..18758` uses `idType=integer`/`boardid`, otherwise `boardmodel`; `hwp_identifier_cmp` `+0x16890` compares by type. Static forced state `.data+0x764` is type2 (`Default None`), so no initial force is demonstrated. Runtime selector values/overrides were not inspected. **Smallest correction:** add those branches and explicitly condition the chain on the selected identifier. Existing line48's runtime-HAL disclaimer should remain. Consequence if omitted: a DTS author can mistake an environment string for proof of the active profile.

2. **Add recoverable static lane/GPIO semantics; retain physical unknowns** — `docs/board4-investigation.md:78,161`, `docs/project-reassessment.md:63`.
   The lane associations and input/default/API semantics above are derivable offline. Existing statements that they need board-specific validation remain true; they should distinguish *recoverable static association* from *unverified physical wiring, polarity and runtime state*. This is an evidence improvement, not a contradiction of the current safety warning. Do not substitute API return values directly into Linux GPIO polarity flags.

| File | Scoped verdict |
|---|---|
| `docs/board4-investigation.md` | Core allocations and SFP table confirmed; complete selection branches and add static lane/status semantics. Preserve no-boot gate. |
| `docs/firmware.md` | Expected profile string agrees with raw bytes; line51 describes an expected model, not a live selection or lane-count proof. Loader/layout outside this bounded verdict. |
| `docs/project-reassessment.md` | Hardware-validation requirement remains correct; annotate newly recoverable static facts. No need for a larger framework/rewrite. |
| `docs/offline-validation.md` | Hardware/non-hardware boundary at lines5-21 and236 is appropriate. Reported software failures were not rerun; numerical test claims and unrelated harness code are not independently accepted by this review. |

## Four-lens evidence and probes

- **Contract:** blind-first seal completed; only own ignored scratch plus expressly permitted private mutation directory written; no tracked edits, installs, builds, lint, formatters, firmware/device execution, commits, pushes or other agents.
- **Correctness/hostile inputs:** resolved section identity, symbol index, addend, stride, sentinel and descriptor alignment; distinguished static enable bits from live signal values and device IDs from controller IDs.
- **Test honesty:** performed four analysis-only corruptions of private module copies under `/var/tmp/agents/lg510s-argon-sf4n1hbq`. Removing descriptor+4 yielded `0xb78` and failed alignment; changing relocation symbol#227 to section symbol#6 yielded `0x50c` and failed descriptor-range/alignment; TE5 MAC25→24 failed the sealed mapping comparison; interface2→0 failed the software-path comparison. Baseline satisfied those guards. Results: `scratch/mutation-probes.json`. These probes demonstrate sensitivity of **my analysis checks**, not the repository's tests or hardware correctness; mapping expectations came from the blind extraction, so this is not independent corroboration of the board wiring.
- **Ponytail:** no product changes, dependency, compatibility layer or speculative DTS introduced. The useful follow-through is a small evidence-table/qualification update, not exhaustive loader/PHY reverse engineering.

## Candidate definition and remaining gates

An offline candidate may record six SDK ports0/8/16/20/25/26, copper/fiber split, software I2C clock8/data9/10, detect14/17, LOS13/16 and TX-disable15/18 as **provisional vendor-configured values**. Static lane associations2/3/4/5/7/8 can also enter evidence notes. Do not expose unused SDK MAC24/27 as cages, choose hardware I2C from device IDs0/1, or claim live polarity from status names.

Not checked: exhaustive PHY MDIO/reset/init, SerDes mode/polarity/calibration, loader/RAM/partitioning, external Linux bindings, claimed QEMU/test totals, physical forwarding, or device recovery. No boot/flash approval; active selection and electrical wiring remain the consequential risks.
