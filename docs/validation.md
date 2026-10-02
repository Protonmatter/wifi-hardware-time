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
| FTM | Capability observation | Initiator supported; current AP advertised responder support; no exchange tested |
| ETW report capture | Live, original local harness | One elevated capture succeeded; trace header reported zero lost events/buffers |
| Firmware report delivery/order | Live, one observation | Matching-vdev report logged 552.9 us after observed IOCTL completion; firmware sampling/completion instant unknown |
| Repeated TSF capture | Prepared; not executed | A subsequent 12-read elevation was canceled; offline analyzer tests are not repeatability evidence |
| Raw-register safety | Unvalidated | No qualified Windows memory-type/address target |
| Arbitrary hardware RX/TX stamps | Unvalidated | No complete interface demonstrated |
| Absolute/relative timing accuracy | Unvalidated | No independent reference or qualified local TSF/QPC samples |

The public packaging adds explicit interface selection and preview-by-default behavior. Offline checks and local discovery/preview can validate packaging; they do not replace the original hardware evidence. Hosted CI never accesses a wireless adapter and does not contain proprietary driver fixtures.

The public ETL decoder and analyzer were also checked against the saved single-read trace without publishing that trace. Their repeated-series behavior is tested with synthetic inputs. The public elevated wrapper and optional capability collection remain untested in an elevated live run. No independent reference, raw-register read, hardware RX/TX packet stamp, or FTM exchange was qualified by these updates.

## Qualification requirements

1. Pin hardware ID, architecture, complete driver hash, firmware revision when available, and source revision.
2. Separate request acceptance, firmware acknowledgement, report delivery, and userspace decoding.
3. Retain clock identity, epoch, units, event reference point, and host timing bounds.
4. Test cancellation, disconnect, reset, suspend/resume, out-of-order completions, and wraps on dedicated test hardware.
5. Characterize aggregation/retry effects and any changes caused by requesting TX status.
6. Use a qualified independent reference and state the metric, sample count, conditions, and uncertainty before claiming accuracy.

An interface being Up at the end is not continuous proof of no transient disruption. A successful IOCTL is not a hardware timestamp. An FTM advertisement is not a ranging result. Public-driver source can establish a possible register target without establishing the Windows diagnostic address-space translation.
