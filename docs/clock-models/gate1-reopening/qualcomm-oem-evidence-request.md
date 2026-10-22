# Qualcomm/OEM evidence request: fresh timing capture on Windows

Please provide the interface contract and retained evidence needed to determine
whether the recorded Qualcomm Windows platform can expose a fresh, attributable
hardware event with bounded pairing to QPC. This is a documentation and evidence
request. It does not ask support personnel to execute a new experiment, enable
diagnostics, change device state or disclose material through public Git.

Request ID: `WHT-G1-2026-10-22`, revision 1. Intended technical owners: OEM WLAN
support, Qualcomm Windows miniport/firmware engineering and the owner of any
supported timing extension. No recipient address or delivery authorization is
implied. Return the request ID and the applicable product/build scope with the reply.

## Objective and recorded context

The objective is plus or minus 10 us relative to the associated AP TSF, under
idle and load, with a qualified relationship to Windows QPC. A nominally
microsecond-resolution counter or aggregate RTT is insufficient. We need a known
event read point, bounded pairing, freshness and attribution for that same event.

The public investigation records FastConnect 7800, ARM64 Windows build
`26200.9457`, `qcwlanhmt8380.sys` version `1.0.4374.1300`, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
These are historical evidence pins, not a fresh machine inventory. A packaged
firmware hash does not identify the running firmware. Please identify whether
your response applies to this exact scope or to a different supported package.

Retained Windows capability and direct cross-timestamp queries returned error
23 without usable capability data or a tuple. Later completion evidence contains
INVALID_OID, but its first originating layer remains unresolved. Please do not
interpret this as a general finding that the hardware lacks timestamp support.
[Windows evidence](../../windows-timestamps/windows-timestamp-path-followup.md) and
[rejection-origin analysis](../../windows-timestamps/ndis-rejection-origin-analysis.md).

## Required answers

For every row, respond `established`, `unsupported`, `unknown` or `not applicable`.
Supply a reason for the latter three. An established answer must cite a document
section, source revision/line or retained record locator, its SHA-256, the owner,
date, exact applicable builds and whether it is a contract, static finding or
measurement. Do not replace an unknown bound with zero or a typical value.

| ID | Question / requested evidence | Required response detail |
|---|---|---|
| Q01 | Exact platform and applicability | Device/revision, bus/topology, OS/SDK/architecture, driver/package hashes, running firmware identity or explicit unknown, supported power/MLO/link configurations, host-boot and firmware-epoch identifiers; distinguish package contents from what executed |
| Q02 | Supported entry route | Public NDIS route or OEM-supported API/extension, package and ABI revision, entitlement/privileges, exact target binding, capability discovery, input/output lengths, status values and a supported build/sign/install/rollback contract if a new driver is needed; no guessed selector or generic kernel-memory access |
| Q03 | Standard timestamp failure and capabilities | Supported/active timestamp flags and cross support on applicable builds, origin of the retained error if known, and any documented corrected build; distinguish unsupported, disabled, filtered and failed queries; identify the first rejecting component only with evidence |
| Q04 | Clock and event definition | Raw units, width, scale/quantization, read/latch instant, rollover/atomicity, validity bits, local TSF versus HWMLO/SoC/PPDU/other clock, link identity, AP-TSF relationship and its uncertainty; do not infer a common domain from equal rates |
| Q05 | Hardware-to-QPC pairing | How the actual current hardware sample is related to QPC; driver pre/post capture or a real paired latch, QPC frequency, deterministic capture-delay/placement limits and applicability under load; equal QPC endpoints still require a nonzero or justified capture-error bound, not a zero-error assumption |
| Q06 | Freshness and age | Whether a request acquires a new event or returns a cache, exact sample-versus-delivery timestamps, maximum hidden age, sequence/token evidence, stale detection, expiry and power-save behavior; command completion or report receipt is not the sample instant |
| Q07 | Same-event attribution | Original request/exchange token and namespace, interface/vdev/link, clock epoch, sequence/PPDU/frame identity, duplicate/wrap/retry/aggregation rules, unsolicited/late returns and live-versus-playback provenance; host ticket IDs alone do not prove firmware attribution |
| Q08 | Owned event export | Original wire span and normalized sizes, required payload fields, callback/pointee lifetimes, copy point, synchronization/coherency, truncation and maximum message size; specify how a complete application-owned record survives callback return |
| Q09 | Completeness and loss | Retained issued-request totals and snapshot cutoff for idle/load; reconcile disjoint confirmed success/failure/cancellation plus unresolved counts, with host timeouts separate; record collector/driver/firmware loss, missing/invalid/foreign/duplicate records and source-request/event cardinality; distinguish export loss from request failure |
| Q10 | Lifecycle and state effects | Supported initialization, concurrency, rate limits, finite operation/cancel/close deadlines, confirmation of terminal completion/cancellation, callback rundown, firmware-drain evidence, failure recovery and cleanup failure behavior; a host timeout/cancel request is not source completion; list logging, scan, traffic, reset, factory-test and clock effects explicitly |
| Q11 | AP and packet semantics | How local counter observations relate to the selected AP TSF, reference-point differences and their correction/error, roam/MLO changes, and the precise RF event for packet timestamps; if FTM is proposed, provide raw per-exchange t1-t4 with separate domains, units, validity and matching IDs rather than only RTT |
| Q12 | Bounds and retained verification | A complete uncertainty derivation with deterministic versus statistical meaning, idle/load conditions, full attempts and tails, independent reference provenance and uncertainty, and all exclusions; a regression residual, median or percentile is not an upper bound |
| Q13 | Transfer and reviewable next action | Approved private delivery location, restrictions, manifest of filenames/hashes/source locators and known/synthetic/live/playback labels; identify a supported candidate operation for later review without executing it; if none exists, return a precise unsupported/unknown disposition and dependency owner |

## Preferred technical response

The first preference is a supported fresh hardware/QPC or TSF/QPC capture with
an explicit AP relationship. A driver-owner extension at a valid RX/management
producer is a separate candidate, not permission to instrument the installed driver.
The [route decision](../../evidence/hardware-route-decision-2026-10-06.md) and
[management producer findings](../../adapters/qualcomm-management-timing-producer.md)
identify existing static leads and ownership limits. They are not executable APIs.

For the standard Windows route, align the reply with Microsoft's
[cross-timestamp contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-get-crosstimestamp)
and [returned structure](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_crosstimestamp).
A successful tuple would qualify only its own sampling mechanism, subject to
the required evidence; it would not automatically qualify arbitrary packet events,
AP synchronization or UTC. If this route is unavailable, please say which exact
prerequisite is missing rather than recommending unbounded private-command probing.

Where retained records exist, include original integer values and source locators
for all attempts, including failures. Preserve raw bytes and unrounded counters;
keep decoded/converted values in a separate view. Explain every missing-value
sentinel and counter reset. Label manufactured examples synthetic. Do not transmit
secrets, credentials, unrelated endpoint identifiers or unlicensed material.

## Reply and disposition template

Return a response document containing: request/revision ID; responding organization
and technical owner; applicability; Q01-Q13 table with status, exact statement,
source/hash/locator and open action; attachment manifest; restrictions; and a
dated review decision. Actual names/contact details can remain in the private
dossier. A public response can contain only approved authored conclusions and hashes.

The evaluation will use the [acceptance criteria](acceptance-criteria.md). Unknowns
remain blocking. An offline-complete reply can make a dossier ready for experiment
review; it cannot establish fresh live pairing, change `physical_bound_proven`,
or authorize deployment/acquisition. No alternate driver package, collector or
firmware command is to be run as a consequence of this request alone.
