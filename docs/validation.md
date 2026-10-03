# Validation ledger

This is a sanitized summary of observations from the 2026-10-01 through 2026-10-03 investigation. Original endpoint logs, local identifiers, absolute paths, raw disassembly, and captures are not public artifacts. These observations do not describe another machine or a later driver release.

**Latest state: private acquisition remains quarantined.** The corrected observer
passed two passive checks, then its private campaign stopped during the third
capture on unmatched reports. The earlier complete campaign below is a separate
experiment. See the [latest campaign report](qualification/private-campaign-2026-10-03-quarantine.md)
and the [findings and execution catalog](validation-execution-catalog.md).

| Item | Evidence level | Result |
|---|---|---|
| mt76 TSF/RX/TX paths | Static source | Identified at pinned revision |
| MediaTek Windows register path | Static binary | Dispatcher, USB/firmware paths, response handling identified |
| Qualcomm private host getters | Live, original local harness | Meaningful scalar results returned |
| Qualcomm TSF request | Live, original local harness | IOCTL accepted; empty timestamp result |
| Qualcomm standard timestamp APIs | Live, Python and native C | Return code 23, no valid capabilities/tuple |
| Cached beacon timestamps | Live | AP Timestamp field and Windows host receive timestamp accessible |
| FTM | Live, exact-build experiment | Six same-target operations had firmware responses, successful WDI completions, and successful callback target results; no independent RF capture |
| ETW report capture | Live, original local harness | One elevated capture succeeded; trace header reported zero lost events/buffers |
| Firmware report delivery/order | Live, bounded series | Twelve matching reports; eleven logs after userspace completion observation and one before; firmware sampling/completion instant unknown |
| Repeated TSF capture | Live, public wrapper at c960dcc | Twelve reads over 14.39 s, zero trace loss, successful cleanup; driver version/hash and final Up state preserved |
| SoC latch refresh | Live, exact-build experiment | Three capture actions refreshed the SoC field; subsequent reads reused it; simultaneous counter latching unproven |
| Guarded idle/workload acquisition | Live, new controller | 12/12 captures, 138/138 requests, zero reported trace loss; 18 capture refreshes and 108 eligible cached-read reuses; all 14 observer sessions cleaned up |
| Corrected controller-query observer | Live, passive | Two zero-request captures passed; loss counters zero and cleanup succeeded |
| Corrected-observer private repeat | Live, quarantined | 33 action-3 requests issued; two complete bundles contain 24 observations; third capture rejected, mixed/workload phases not reached |
| Unmatched-report postmortem | Saved ETL replay | Nine command groups plus two unassigned report/timer/delay groups; WMI dispatch precedes each extra group; origin unknown |
| Unmatched-report counter changes | Saved ETL replay | Both extra groups change the SoC value cached across the preceding nine reads; changed values do not establish freshness or simultaneous sampling |
| Pre-ETW memory log | Exact-build static | 2 MiB text ring and copy/file consumers identified; userspace retrieval, concurrency and latency remain unqualified |
| Passive follow-up after cleanup repair | Live, zero private requests | One 30-second observation passed; 111 health/connection records each, zero timing events/loss, normal observer stop and unchanged quarantine |
| Scan attribution lead | Saved ETL context | START_SCAN logged about 28.6 ms before first unmatched TSF report; temporal overlap, not causal attribution |
| Controlled scan comparison | Live, three calls and failed four-second profile | Quiet baseline then two TSF reports per call; final diagnostic tail observed scan completion at about six seconds; no private requests, no clock qualification |
| Post-quarantine evidence draining | Offline regression plus passive live check | Tail persistence and failure cases validated synthetically; normal shutdown passed one passive live run; no private campaign requalification |
| FTM result aggregation | Static binary and saved-trace replay | Post-filter selection model matches count, RTT and auxiliary field in 10/10 callbacks; empty-array selection explains two zero-count results |
| Adapter restart/reassociation | Live, one targeted restart | Same profile recovered automatically; Up observed after 7.18 s; pre/post captures and one nonempty FTM result succeeded; no continuity claim during the gap |
| Raw-register safety | Unvalidated | No qualified Windows memory-type/address target |
| Arbitrary hardware RX/TX stamps | Unvalidated | No complete interface demonstrated |
| Absolute/relative timing accuracy | Unvalidated | No independent reference or qualified local TSF/QPC samples |

The public packaging adds explicit interface selection and preview-by-default behavior. Offline checks and local discovery/preview can validate packaging; they do not replace the original hardware evidence. Hosted CI never accesses a wireless adapter and does not contain proprietary driver fixtures.

The [guarded campaign](qualification/acquisition-campaign-2026-10-02-results.md)
completed after a successful elevation retry. Its real-time log-to-reader delivery
was typically about 1.6 seconds and exceeded two seconds for four observations.
This qualifies bounded experimental acquisition in the tested conditions, not a
low-latency hardware clock API, atomic sampling, calibrated accuracy or forced
failure/drain behavior. The final adapter remained Up on the same driver hash.

The decoder and analyzers were checked offline against saved live traces without publishing those traces. The public 12-read wrapper and optional capability collection completed an elevated run at `c960dcc`. A later live rerun of the published `e7da355` latch/FTM wrappers reproduced the latch behavior but exposed a remaining FTM validation gap: one result had successful API/target status and a matching BSSID, but zero measurements and RTT -1. The offline decoder rejected it while the native helper accepted it.

The native helper now requires a nonzero measurement count. A new bounded live run observed three nonempty results, then rejected another zero-measurement result and stopped before a fifth request, with trace cleanup and Wi-Fi Up. An offline C regression covers the zero-measurement counterexample and preserves signed RTT handling when measurements exist. This validates result completeness, not accuracy.

A subsequent offline investigation traced the empty-array selection and the origin of the callback's raw variance field. The latter matches a calculation involving the array means, so it is not qualified as statistical variance or timing uncertainty. It also traced the zero-filled TSF command tail and the report handler's 32-bit difference callback. See [result provenance](ftm-result-provenance.md) for RVAs, replay evidence, and limits; this follow-up did not repeat a hardware experiment.

Two local cancellation probes received `ERROR_CANCELLED` callbacks and normal follow-up API requests completed. Firmware/WDI work was also observed after cancellation; the internal Windows path calls nonabortive `RpcAsyncCancelCall`. Client completion cancellation is not evidence of immediate RF cessation. One follow-up response was empty despite success status, so cancellation recovery is not universally qualified.

One subsequent host-driven adapter restart recovered automatically without the prepared fallback reconnect. TSF and SoC endpoint values advanced, but no samples cover the restart gap; association can resynchronize timing. The post-restart FTM result matched the prior observed AP and contained four measurements. This does not qualify a firmware power cycle, fallback failure paths, cancellation during reset, or roaming. Standard timestamp queries still failed after restart.

Five additional FTM RTT estimates ranged from -1.353 to 3.694 ns. Conditional on a rough same-AP distance estimate, these did not pass a distance sanity check. No measured separation or independent clock reference was available, so no calibration or accuracy bound is claimed. See [experiment results](experiments.md#observed-results).

## Qualification requirements

1. Pin hardware ID, architecture, complete driver hash, firmware revision when available, and source revision.
2. Separate request acceptance, firmware acknowledgement, report delivery, and userspace decoding.
3. Retain clock identity, epoch, units, event reference point, and host timing bounds.
4. Test cancellation, disconnect, reset, suspend/resume, out-of-order completions, and wraps on dedicated test hardware.
5. Characterize aggregation/retry effects and any changes caused by requesting TX status.
6. Use a qualified independent reference and state the metric, sample count, conditions, and uncertainty before claiming accuracy.

An interface being Up at the end is not continuous proof of no transient disruption. A successful IOCTL is not a hardware timestamp. An FTM advertisement is not a ranging result. Public-driver source can establish a possible register target without establishing the Windows diagnostic address-space translation.
