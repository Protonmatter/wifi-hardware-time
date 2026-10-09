# Corrections following the independent post-merge assessment

This follow-up starts from research merge `9ddc1c3586450d3a866b5486da945e95a83417fb`. It addresses reproduced evidence, lifecycle, replay and numerical edge cases while preserving historical capture files, original analysis JSON, the audited standalone probe, the 200-ppm mathematical prior and the 0.5-us integer-rounding allowance. It performs no live adapter, trace, elevation, network workload or system-clock operation.

## Acquisition and evidence

- A request is finalized only after terminal evidence processing and successful operation release. Later session failure does not rewrite that finalized request. Current-request failure still covers deadline, cancellation, terminal-evidence and resource-release errors.
- Native event/device close attempts have explicit bookkeeping. An ambiguous close is never retried by numeric handle. Unresolved private I/O retains buffers, OVERLAPPED storage, event and device ownership.
- A failed event wait remains a sticky session failure, but a safe nonblocking terminal-result query can establish completion. API misuse or an unresolved result does not authorize release, a new request or a worker kill.
- Quarantine writers use a bounded cross-process marker lock and durable merged causes. The lock is independent of admission and never clears quarantine. Worker snapshots are preserved even when marker publication must retry.
- Online early stopping retains its 100-request grace. Final success requires at least one request and an exact final own-loss ratio of no more than 1%; `own_loss_policy_passed` records the result in both sampler modes.
- Trace teardown retries only the exact owned session, with at most three five-second stop commands and attempt evidence. Failure retains quarantine/unfinished-run state. No wildcard stop or automatic rearm was introduced.

Additive request evidence includes `event_close_attempted` and `event_closed`. Old v1 receipts remain readable; new contradictory evidence rejects. A failed session can legitimately contain earlier successful requests.

## Versioned numerical policies

| Policy | Behavior |
|---|---|
| `wht/arrival-order-v2` | Causal replay processes availability first, uses capture order for equal-availability ties, and explicitly records skipped late historical captures. The provider ordering guard and elapsed denominators remain intact. |
| `wht/settlement-v2` | A complete true-before/true-after bracket may be narrowed with event-overlapping envelopes already available by the returned settlement cutoff. Overlap never supplies a bracket side. Results record contributing sequences. |
| `wht/sample-screen-v2` | A backward TSF observation between structurally eligible chronological candidates closes the segment. The cause is suspected discontinuity, not a proven reset. Subsequent samples cannot reopen it when tolerance grows; a new epoch requires an explicit decision. |
| `wht/clock-pairing-quantized-v2` | Counter bins and upper QPC endpoints are widened consistently. Equal integer counts can be valid within one bin; an unbounded affine slope ceiling is `null`, and an undefined endpoint increment ratio is `null`, never Infinity/NaN. |

For a suspected continuity break, causal invalidation occurs only once both compared observations are available. Missing evidence needed to establish that time rejects the replay. Retrospective/settled statistics on a pre-break prefix do not qualify the whole recording. Complete-recording analysis requires versioned clear continuity independently of its rejection fraction.

The actual settled-grid maximum is reported separately from the retrospective consecutive-pair maximum. The latter is not a universal cap on a nonadjacent first-available settlement. The overlap regression gives 1000.75001 us with the extra eligible envelope, rather than 1600.34999 us without it; neither number is a physical-accuracy claim.

## Reproducible headline publication

Current numerical summary blocks read one [versioned result source](postmerge-corrections-2026-10-08.json). The generator validates source schema, qualification, counts and required fields before writing any page. Historical result JSON is not rewritten.

```powershell
python research/evidence/sync_tsf_headlines.py --check
python research/evidence/sync_tsf_headlines.py --write
python research/evidence/sync_tsf_headlines.py --check
```

Default/`--check` is read-only and exits 1 on drift. `--write` updates only declared marker blocks, with UTF-8/LF output; unchanged repeats do nothing. Exit 0 means synchronized/written, 1 means drift or invalid input/I/O failure, and 2 means invalid CLI arguments. No permissions beyond reading/writing the checkout are required. Review the Git diff to roll back authored block changes. A malformed source or missing/duplicate marker fails before any page write.

Old October 4 context banners are explicitly historical. The original long implementation plan is labelled archival and links to maintained contracts. Current cross-device wording remains a research hypothesis requiring independent station/AP error bounds.

## Validation and remaining gates

The clean corrected source is `0f41db0175e3601e899c51143b46bb8b3df02135`. The [result comparison](postmerge-corrections-2026-10-08.json) replays that source and baseline `9ddc1c3` against the same hashed retained captures. Every input JSON/JSONL hash remained unchanged. The counted idle/load hour verdicts remain true, with explicit clear screen-v2 continuity. Request/accepted/rejected counts, tracking coverage and exact retrospective maxima are unchanged for all three captures; no late-history skip or continuity invalidation occurs in them.

| Retained run | Tracking coverage | Actual settled-grid maximum half-width | Settled grid points |
|---|---:|---:|---:|
| Idle hour | 78.632051394% | 894.669 us | 3,598 / 3,598 |
| Loaded hour | 72.349582965% | 766.954 us | 3,597 / 3,597 |
| Persistent idle smoke | 92.862588662% | 614.883 us | 297 / 297 |

Loaded-hour median/p90/p99 settled half-widths narrow from 325.406/463.915/585.591 to 324.908/463.139/585.340 us under the eligible-overlap policy. The maxima and waits remain unchanged. The SoC diagnostic intervals change under quantization-aware arithmetic, while all three retained runs still reject nominal SoC/QPC-domain compatibility. No shared-oscillator or physical accuracy qualification is inferred.

Fresh local Windows ARM64 Python 3.14.3 verification initially discovered 549 research tests: 512 passed, 37 skipped. A subsequent hosted index check exposed Python-version-dependent f-string source locations. The index now anchors literal fragments to their containing expression while preserving ordinary replacement-string and nested-expression locations. Two regressions cover this distinction; index generation agrees on Python 3.11.9, 3.13 and 3.14. Final suite and hosted counts are recorded on [the correction PR](https://github.com/Protonmatter/wifi-hardware-time/pull/8). The independently reviewed consumer port passed 103 tests and exact golden-v3 parity. Historical consumer v1/v2 fixtures remain unchanged; v2 regeneration against its original `498758f` source still matches. Stronger behavioral tests now reject the supplied in-memory unsafe margin mutations.

Every reproduced behavior receives a failing regression before its correction. Exact boundary containment tests exercise +/-200 ppm, fractional capture edges, both quantization widenings and overlapping events. In-memory mutations remove TSF widening or reduce the prior to 160 ppm; the strengthened behavioral tests must fail both unsafe variants without editing source.

Final validation includes full Windows/Linux offline suites, independent review, exact retained-input comparisons, generated-headline/index/diagram checks and downstream golden parity. Results and exact source pins are recorded in the linked result JSON and correction PR. Original measurements stay attached to their original builds; source fixes do not retroactively qualify hardware cleanup or failure paths.

Online admission still needs a justified delivery watermark or bound; no numeric claim about its effect on coverage is made here. Driver capture semantics, firmware drain, live cancellation/interruptions, AP/UTC accuracy and multi-device synchronization remain unqualified. Licence/vendor-material decisions are separate from these engineering corrections.
