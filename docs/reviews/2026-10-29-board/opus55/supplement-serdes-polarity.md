# Supplement / correction — Opus 5.5 seat (written after the sealed review; blind notes and final-review.md left unchanged)

## Correction: the SerDes byte also carries static TX/RX polarity
My sealed claims "no polarity field in the serdes descriptor" and "no board-specific SerDes polarity anywhere" are **WRONG**. The second byte of each 2-byte SerDes entry is {mode in the upper bits, polarity in bits 1..0}.

### Evidence

**1. Raw bytes.** rtcore `.data+0x3949` (= swDescp `0x3434` + 1301) holds `02 72 03 71 04 72 05 71 06 70 07 08 08 08 09 08 ff`.

**2. Consumer.** rtk `dal_longan_construct_macConfig_init` (`.text 0x132a8c`), which is entry 4 of `constructEntry_930x`. It loops over SerDes 0..23, takes `p = sdsID2SerdesDescp[sds]` and reads `ctl = p[1]`. Arguments to `hal_sds_field_write` are (unit, sds, page, reg, bit, bit, val):

| Condition | Writes (page.reg bit = value) | Code location |
|---|---|---|
| `ctl & 0x2` set | 6.2 bit13 = 1, then 0.0 bit9 = 1 | `0x132bc4` `andi 0x2`; set path at `0x132ae4` |
| `ctl & 0x2` clear | 6.2 bit13 = 0, then 0.0 bit9 = 0 | `0x132bd4..0x132c04` |
| `ctl & 0x1` set | 6.2 bit14 = 1, then 0.0 bit8 = 1 | `0x132c28` `andi 0x1`; set path at `0x132b44..0x132b70` |
| `ctl & 0x1` clear | 6.2 bit14 = 0, then 0.0 bit8 = 0 | `0x132c38..0x132c70` |

**3. Semantics.**
- rtk `phy_9300_polar_get` reads SerDes page 6 reg 2:
  - `0x1dad0`: `ext v0,t8,13,1`, stored to `out+4`.
  - `0x1dad4`: `ext t8,t8,14,1`, stored to `out+0`.
- `dal_phy_polar_set` (`0x15dcf4..0x15dd20`) logs `.rodata.str1.4+0x10c88` "unit=%u, port=%u, polar tx:%d rx:%d". Its `tx` comes from struct `+0` and its `rx` from struct `+4`.
- Therefore:
  - bit14 / `ctl` bit0 = TX polarity
  - bit13 / `ctl` bit1 = RX polarity
- The meaning of the paired page0/reg0 bits 8 (TX) and 9 (RX) is not established; I only know they are written alongside.

**4. Mode masking.** This is consistent with the mode checks I already cited, which mask the low bits off the mode:
- `_switch_sdsMode_convert`: `& 0xfc` compared with `0x70`.
- `dal_longan_sds_init`: `& 0xfc`/`& 0xdc`.

## Corrected static vendor values (SDK enum/bit values, not Linux GPIO/DT flags)

| MAC | SerDes | Byte | Mode family | TX invert (bit0) | RX invert (bit1) |
|---|---|---|---|---|---|
| 0 | 2 | `0x72` | `0x70` | 0 | **1** |
| 8 | 3 | `0x71` | `0x70` | **1** | 0 |
| 16 | 4 | `0x72` | `0x70` | 0 | **1** |
| 20 | 5 | `0x71` | `0x70` | **1** | 0 |
| 24 (not exposed) | 6 | `0x70` | `0x70` | 0 | 0 |
| 25 (TE5) | 7 | `0x08` | `0x08` | 0 | 0 |
| 26 (TE6) | 8 | `0x08` | `0x08` | 0 | 0 |
| 27 (not exposed) | 9 | `0x08` | `0x08` | 0 | 0 |

- The alternating `0x72`/`0x71` pattern that I previously called "unknown" is this polarity.
- The mode-family names are still not recovered: `0x70` maps to `rt_serdesMode` 28 (USXGMII-like); `0x08` is 10G-fiber class.
- This is what the vendor firmware programs on the RTL9303-side SerDes. It is not proof of PCB routing, and it says nothing about RTL8264B-side settings.
- The `conf_rtl9300_cust_board_list` finding (always NULL, no per-board tx/rx-cali override) still stands. It is a separate mechanism from this polarity.

## Retained qualifications
- **Module presence ("OE" in the vendor dump, labelled `MDO_FX`):**
  - GPIO14 (TE5 / lport4) and GPIO17 (TE6 / lport5), inputs.
  - The cage binding is consumer-proven: `detectConf` → `boardGpio_930x` entries 14/17 → ski `board_fiber_oeStatus_get`, which reads status = (pin == 0).
  - LOS is GPIO13/16, bound the same way.
- **TX_DISABLE is a separate output and is not part of the "OE" path:**
  - GPIO15/18, set OUT with default 0 and the active-high flag, only by `board_gpio_init`.
  - Nothing imports or consumes it afterwards.
  - Pairing GPIO15 with TE5 and GPIO18 with TE6 rests only on the `_FX_0`/`_FX_1` label suffixes: **[INFERENCE]**, not a consumer binding.
- **GPIO18 pinmux:** the `GPIO_SEL_CTRL` bit10 (`GPIO18_USBLED_SEL`) clear still applies to GPIO18.

## Superseded lines in my sealed outputs
- **`blind-notes.md`:**
  - "NO polarity field exists in this SDK's serdes descriptor"
  - "No evidence of inverted polarity anywhere in firmware"
  - "Why SDS2/4=0x72 vs SDS3/5=0x71: unknown"
- **`final-review.md`:**
  - "SerDes descriptor has no polarity field…"
  - New-facts bullet "absence of any board-specific SerDes configuration"
  - Unknown-list item "SerDes polarity"
  - Correction #4 should add the per-lane TX/RX invert bits above.
