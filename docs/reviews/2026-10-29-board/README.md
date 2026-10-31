# Independent board-review evidence archive — 2026-10-29

This archive preserves independent analyses of the same firmware evidence at base commit `6f7d67b6fd378981874d354b512495b99c31d5bc`. Each completed reviewer derived its findings before reading the existing documentation, saved a blind note, then performed an adversarial document review. The parent checked the blind-file hashes and relevant transcript order.

**These are historical reviewer artifacts, not an authoritative device tree, an execution guide or boot/flash approval. Initial conclusions can be wrong. Read the supplements and the [consolidated adjudication](../../board-evidence-review.md) before using any claim. Multiple models reading one vendor configuration are not multiple physical observations.**

| Reviewer | Sealed blind-note SHA-256 | Records |
|---|---|---|
| Opus 5.5 | `b300d15bd72d655749ab0a8057107836776f02843eefe81f4c76bec045ce3e40` | [Blind](opus55/blind-notes.md), [initial review](opus55/final-review.md), [SerDes correction](opus55/supplement-serdes-polarity.md) |
| Fable 5.1 | `1cf9789fcdd7fc8b1696b6106ad621e5fcfce463f38299349cff1bcc555afadc` | [Blind](fable51/blind-notes.md), [initial review](fable51/final-review.md), [loader follow-up on GPT-6.1-Sol](fable51/loader-overlap-followup.md) |
| GPT-6 Astra | `c6f13976f083113e5730cdc6bf74242dba86c13005b75a543ee35328daed95b5` | [Blind](astra/blind-notes.md), [review and supplements](astra/final-review.md), [selector supplement](astra/selector-supplement.md), [SMI routing supplement](astra/smi-routing-supplement.md) |
| Grok 4.7 | `c6e5e70b08bbe3e848c997490372820ca0cc219c6d2110aea805f78929c687a8` | [Blind](grok47/blind-notes.md), [review with explicit corrections](grok47/final-review.md) |
| Gemini 4 Argon, fresh retry | `e62419dcf6377bf02fff20429a6da53af0b5fe043ffd82e931d93f8239df1152` | [Blind](argon-retry/blind-notes.md), [bounded core port/SFP review](argon-retry/final-review.md) |

Gemini's original request failed with a provider abort after three retries. A resumed continuation later disclosed GPT-6.1-Sol and unauthenticated inherited Gemini claims; its [provenance correction](argon-failed/provenance-sol-continuation.md) is preserved, but its hardware conclusions are not counted as Gemini evidence. A **fresh** retry on the pinned Gemini selector completed, exposing runtime label `google-antigravity/gemini-4-argon` with no substitution notice; the parent verified its separate blind-note hash and seal-before-docs transcript order. Model attribution is harness-level, not independent provider attestation. Its bounded core review does not independently review the full PHY/polarity/loader analysis.

Fable's loader continuation explicitly disclosed GPT-6.1-Sol and is not another Fable sample. Other post-seal supplements are follow-up analyses, not additional independent reviews.

**Retry contract deviation:** despite the parent's no-tests and own-scratch-only instruction, the fresh Gemini retry performed four analysis-only corruptions of temporary module copies under `/var/tmp/agents/`. Its report calls that location expressly permitted; that assertion is not supported by the parent contract. No vendor code was executed and no device was contacted. These probes are excluded from repository-test/hardware evidence; the independent static derivation and original files remain inspectable. Future binary-review dispatches should suppress the specialist's unrelated mutation-review default explicitly.

Corrections already established during reconciliation:

- Initial claims that SerDes polarity is absent (including Opus and Fable) are superseded by consumer decoding: packed control bytes contain TX/RX controls consumed by the vendor driver. Opus preserved an explicit correction supplement.
- Grok's initial OE/TX-disable conflation is corrected in its appended supplement. OE refers to module presence, and normalized LOS `1` means Normal in the CLI consumer, not asserted loss.
- Grok's initial SYSINFO interpretation is corrected: the exact relocation-indexed key is `bootmsg`, and the parsed field is copied into the global model structure. Duplicate local symbol names must not be resolved by name alone.
- The SMI byte is both printed and consumed by a separate driver initialization path. Describe an intended vendor selector, not a measured transaction or an automatically equivalent Linux bus number.
- All five completed seats reproduce the main OEM port allocation and SFP GPIO numbers; the fresh Gemini retry additionally recovers the same lane associations. The consolidated report grades direct bindings separately from label-inferred TX-disable pairing, and static configuration separately from physical/live validation.
- Fable's initial header-value/staging-address inference is withdrawn in its attributed loader follow-up: `boota` actually stages at `0x81000000`; `0x83800000` is an unchecked header value in the traced `bootm` path. That follow-up also establishes the ineffective LZMA caller bound and post-decompression overlap check, not a safe boot procedure.

No switch was accessed during these reviews. The archive contains text analyses only, screened before copying; it contains no raw firmware image, extracted vendor binary, device configuration, credential or private key. The original blind notes remain unchanged even where later analysis corrects them, except that local paths and lab addresses were later replaced with placeholders before publication. The hashes above refer to the sealed originals, so the Fable 5.1 and Grok 4.7 blind notes no longer match them.
