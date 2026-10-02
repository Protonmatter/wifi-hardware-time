# Validation ledger

This is a sanitized summary of observations from the initial 2026-10-01/02 investigation. Original endpoint logs, local identifiers, absolute paths, raw disassembly, and captures are not public artifacts. These observations do not describe another machine or a later driver release.

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
| Raw-register safety | Unvalidated | No qualified Windows memory-type/address target |
| Arbitrary hardware RX/TX stamps | Unvalidated | No complete interface demonstrated |
| Absolute/relative timing accuracy | Unvalidated | No independent reference or qualified local TSF/QPC samples |

The public packaging adds explicit interface selection and preview-by-default behavior. Offline checks and local discovery/preview can validate packaging; they do not replace the original hardware evidence. Hosted CI never accesses a wireless adapter and does not contain proprietary driver fixtures.

The decoder and analyzers were checked offline against saved live traces without publishing those traces. The public 12-read wrapper and optional capability collection completed an elevated run at `c960dcc`. Local latch/FTM helpers subsequently completed live experiments; their public packaging adds path/CLI changes, shared action selection, and stricter FTM target-result checks. That repackaged version has offline tests/builds but has not been rerun in an elevated hardware experiment.

Five additional FTM RTT estimates ranged from -1.353 to 3.694 ns. Conditional on a rough same-AP distance estimate, these did not pass a distance sanity check. No measured separation or independent clock reference was available, so no calibration or accuracy bound is claimed. See [experiment results](experiments.md#observed-results).

## Qualification requirements

1. Pin hardware ID, architecture, complete driver hash, firmware revision when available, and source revision.
2. Separate request acceptance, firmware acknowledgement, report delivery, and userspace decoding.
3. Retain clock identity, epoch, units, event reference point, and host timing bounds.
4. Test cancellation, disconnect, reset, suspend/resume, out-of-order completions, and wraps on dedicated test hardware.
5. Characterize aggregation/retry effects and any changes caused by requesting TX status.
6. Use a qualified independent reference and state the metric, sample count, conditions, and uncertainty before claiming accuracy.

An interface being Up at the end is not continuous proof of no transient disruption. A successful IOCTL is not a hardware timestamp. An FTM advertisement is not a ranging result. Public-driver source can establish a possible register target without establishing the Windows diagnostic address-space translation.
