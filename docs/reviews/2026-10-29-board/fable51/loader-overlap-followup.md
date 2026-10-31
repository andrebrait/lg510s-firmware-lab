# Focused loader follow-up

Scope: static read/disassembly only; no image execution, builds, switch access, mutations or safe-load-address recommendation. Blind notes and final-review.md left unchanged. This continuation runs on openai-codex/gpt-6.1-sol; do not count it as another independent Fable analysis. A provider refusal/error notice preceded this continuation; no missing result is treated as evidence.

## Exact offsets

All file offsets refer to parts/uboot.bin. Main-stage address translation independently recovered from command records: file = address - 0x83f00000 + 0x5030. Function names below are inferred from consumers/control flow; this raw binary has no symbols.

| Item | Command record file offset | Handler/address | Handler file offset |
|---|---:|---:|---:|
| boota | 0xd0ec8 | 0x83f02858 | 0x7888 |
| bootm | 0xd0ef8 | 0x83f03394 | 0x83c4 |
| tftpboot | 0xd10d8 | 0x83f05530 | 0xa560 |
| netboot_common | - | 0x83f05254 | 0xa284 |
| genimg_get_format | - | 0x83f08c1c | 0xdc4c |
| genimg_get_image | - | 0x83f08c24 | 0xdc54 |
| bootm_load_os | - | 0x83f02bf0 | 0x7c20 |
| LZMA wrapper | - | 0x83f0f738 | 0x14768 |
| LzmaDecode | - | 0x83f0f608 | 0x14638 |

Each command record is 6 big-endian words: name,maxargs,repeatable,handler,usage,help.
boota: 83fc0524 00000001 00000000 83f02858 83fc052c 83fc11e4
bootm: 83fc0070 00000010 00000001 83f03394 83fc0674 83fc0698
tftpboot: 83fc1700 00000003 00000000 83f05530 83fc170c 83fc1738

boota 0x83f02868 obtains partition 5 offset, adds 0xb4000000 at 0x83f02870, reads 64-byte header, validates hcrc, checks compressed size+64 against partition size, then memcpy destination 0x81000000 at 0x83f028dc..0x83f028e8. At 0x83f028f0 it finds command bootm; only a NULL result emits bootm-command-not-supported. At 0x83f0290c..0x83f02934 it invokes that table handler with argc=2 and argv={bootm,0x81000000}. This proves the staging address, without interpreting header word +0.

tftpboot handler 0x83f05530: move a1,a0; li a0,3; j 0x83f05254; nop. Static TFTP protocol wrapper only, not exercised network functionality.

genimg_get_format 0x83f08c1c: jr ra; li v0,1. The next function 0x83f08c24: jr ra; move v0,a0 is genimg_get_image identity, NOT image_get_magic (correction to prior report terminology). bootm_start 0x83f02e98 calls identity then 0x83f02eac calls format; 0x83f02eb8 compares result to 1 and 0x83f02edc calls hcrc checker. No word +0 magic comparison in this path. Retain description as unchecked ih_magic slot = 0x83800000; withdraw staging-address inference for that word.

## Output-size handling

bootm_load_os selects LZMA for comp=3 at 0x83f02c54; delay slot 0x83f02c58 sets t8=0x00800000. 0x83f02d20 stores that nominal 8 MiB at sp+16 and 0x83f02d30 calls wrapper with (load,&length,payload,payload_len).

Wrapper 0x83f0f738 never loads through the callers length pointer: it preserves it in s2 at 0x83f0f75c and only stores a result at 0x83f0f81c. Instead:
- 0x83f0f788..0x83f0f7b0 assembles LZMA-alone bytes src+5..12 as little-endian output-size low/high words.
- 0x83f0f7b4..0x83f0f7c8 accepts high word 0, or the all-ones unknown-size sentinel; otherwise returns error 1.
- 0x83f0f7d4 stores low word as local sp+56.
- 0x83f0f804..0x83f0f814 passes output, &local_length, src+13 and source-length pointer into LzmaDecode, finish mode 0.
- LzmaDecode 0x83f0f638 reads that local output bound into s5 and 0x83f0f698 assigns it to decoder dictionary-buffer size; 0x83f0f818..0x83f0f81c writes processed length back.

Thus 8 MiB is NOT an effective LZMA output cap. Known-size streams use their own declared 32-bit output size as destination bound, with no RAM-capacity or caller-limit check in the wrapper. Stock declares 11336112 bytes (>8 MiB), consistent with this trace. Unknown-size sentinel yields 0xffffffff as the destination bound, not a safe RAM bound. No firmware execution was used to establish this.

## Overlap check and caller outcome

Legacy type-2 setup at 0x83f02fd4..0x83f02fe4 sets image_start=header+64 and image_len=ih_size; 0x83f03084..0x83f03098 sets blob_end=header+64+ih_size and load=ih_load; 0x83f0315c sets blob_start=header. hcrc/dcrc validation precedes decompression (dcrc controlled by verify; 0x83f0890c returns true if unset, false only for first char n).

bootm_load_os ABI at entry:
a0=blob_start; a1=blob_end; a2=payload_start; a3=payload_len; stack+16=load; stack+20=comp (word); stack+24=type; stack+28=&load_end; stack+32=boot_progress.
Its saved registers: s5=blob_start, s7=blob_end, s3=payload_start (later repurposed as XIP flag), s0=load, s1=&load_end, s6=boot_progress.

1. 0x83f02d30 calls decoder BEFORE any overlap check. Failure at 0x83f02d38..0x83f02d5c prints LZMA error and returns -1; caller 0x83f03490..0x83f034f4 calls reset.
2. Success computes load_end=load+decoded_size at 0x83f02d60..0x83f02d6c, flushes/cache handling, then checks overlap at 0x83f02dbc..0x83f02dd8:
   return -2 iff load < blob_end AND blob_start < load_end (unless XIP flag bypasses).
   This is post-write detection, not preflight protection.
3. do_bootm 0x83f0349c branches to -2 handling. At 0x83f034a4 it checks legacy_hdr_valid (images+0x44); at 0x83f034b0 it checks copied legacy header type (images+0x22) against 4. Valid legacy type !=4 jumps via 0x83f034b4/its delay slot directly to 0x83f03524. No warning, failure return or reset. Type4 prints the multi-component warning and also continues. Nonlegacy case prints error and resets. Type2 then passes standalone(type1) test at 0x83f03528, reaches OS handler dispatch at 0x83f035b4..0x83f0362c, i.e. ordinary boot continuation.

For parent-supplied reference ranges, boota input starts at 0x81000040, output is [0x80100000,0x812f86b6). These address ranges overlap. The decoder can overwrite unread compressed input: there is neither preflight overlap rejection nor an effective 8 MiB LZMA bound. The post-decode overlap result would be -2 and is ignored for the reference legacy single-kernel type2 header. Whether this particular stream actually overwrites bytes before the decoder consumes them depends on consumption/write progression, not address overlap alone; no execution or certainty of corruption is claimed. A decode error would reset; successful decode plus overlap would continue. No output checksum after decompression was identified in this path.

ELF+BSS end 0x8143beec is parent evidence, not independently parsed here. The traced loader bounds use decoded payload length, not ELF BSS extent; these checks do not establish BSS safety. No safe load/staging address is inferred.

Preserved traces: uboot_boota.dis, uboot_bootm.dis, uboot_getkernel.dis, uboot_hdrcheck.dis, uboot_lzma.dis, uboot_cmdtable.txt. A Python env-key-existence probe initially hit UnicodeDecodeError on trailing erased bytes; corrected by stopping at the double-NUL terminator. No variables outside the allowlist were printed.
