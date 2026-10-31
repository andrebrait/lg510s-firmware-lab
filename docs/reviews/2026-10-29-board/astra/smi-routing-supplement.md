## Post-seal reconciliation — encoded SMI versus effective routing

The port table should label its field **encoded SMI selector / configured PHY address**, not an observed MDIO bus or Linux bus number. TE1..TE4 encode selector0 and addresses0..3. No live controller readback or physical routing test was performed.

Targeted additional native disassembly supplies a consumer beyond the formatter:

- `rtcore:_hwp_port_parse` at `.text+0x132f0..0x13300` copies row byte+3 into the parsed PHY-address array. The lack of a byte+2 read in that parser does not establish that the field is unused elsewhere.
- `rtk:_rtl9300_smiAddr_init` at `.text+0x250f8..0x25120` reads each parsed PHY address and calls `_rtl9300_port_phyAddr_set`, skipping ff. At `0x250a8..0x250dc` it separately retrieves the original MAC-indexed port-descriptor pointer, explicitly loads **byte+2** (`0x250c4: lbu s1,2(t8)`), skips ff, and passes that value to `_rtl9300_port_smiSel_set`.
- `_rtl9300_port_smiSel_set` at `0x24604..0x24674` validates selector<4, selects register enum373 for MAC<16 or enum374 for MAC16..27, indexes the per-MAC field table at `.rodata+0x690`, and calls `reg_field_write` with the supplied selector. `rtl9300_init` references `_rtl9300_smiAddr_init` at relocation offsets `0x254c8/0x254cc/0x255d4`.

Thus selector0 is **statically requested routing configuration**, not merely a printed label; successful programming, live selector state, controller-pin wiring and Linux MDIO bus numbering remain unverified. Candidate wording should be “vendor SMI selector0; configured PHY addresses0..3,” not an unconditional “MDIO bus0.” MAC, PHY-address and SerDes-lane numbers are unchanged.

GPIO distinctions retained: MDO/OE getter normalization is not TX-disable drive policy; a LOS getter returning1 on raw-low does not by itself prove electrical LOS assertion or Linux `GPIO_ACTIVE_LOW`. No Linux GPIO or SerDes polarity translation is approved here.

Executed: targeted static disassembly and relocation inspection only, saved under `scratch/`; no device or firmware execution, tests or mutations. Blind notes unchanged.
