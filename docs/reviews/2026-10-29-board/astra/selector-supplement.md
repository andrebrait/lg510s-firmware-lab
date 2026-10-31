## Post-seal supplement — newly authorized selector keys

After Main explicitly expanded the safe environment allowlist to include `idType` and `boardid`, I inspected only those keys and the original allowlisted keys. The sealed `blind-notes.md` was not changed. This supplement supersedes the earlier final-report limitation that saved selector values were not inspected.

Executed probe: exact NUL-delimited key matching in saved BDINFO bytes `uboot.bin[0xe0004:0xf0000]`, with separate selector matching in the compiled loader region before `0xe0000`. No complete environment or non-allowlisted values were emitted.

| Selector / boot field | Saved BDINFO result | Compiled loader selector result |
|---|---|---|
| `idType` | Absent | Absent |
| `boardid` | Absent | Absent |
| `boardmodel` | `RTL9303_8264B_2XGE` at `0xe0014` | Same at `0xc7d16` |
| `bootargs` | Absent | Not re-examined in this supplement |
| `bootcmd` | `boota` at `0xe0032` | Not re-examined in this supplement |
| `bootdelay` | `1` at `0xe0040` | Not re-examined in this supplement |
| `baudrate` | `115200` at `0xe0004` | Not re-examined in this supplement |

**Refined static conclusion:** with the compiled forced selector disabled (rtcore `.data+0x764` discriminator2), the saved environment takes the name-selection branch: missing `idType` leaves discriminator0, then `ioal_param_hwpIdKey_get` reads `boardmodel` (`.text+0x18684` branches to `0x1873c`, then `0x18748..0x18758`). `hwp_identifier_cmp` compares that exact name, selecting profile `0x008de842`. There is no saved numeric override in this dump.

Finding1 therefore becomes a completeness correction to document the actual precedence and the absence of numeric override, not an unresolved saved-selector conflict. Forced selection remains a code capability; live state or loader modification of the environment was not observed. No change to any port/PHY/SerDes/GPIO finding or no-boot/no-flash verdict.

Not checked: live runtime profile, device environment changes, or boot behavior.
Risk: the saved default selection is now substantially better established, but static evidence still does not certify live hardware state.
