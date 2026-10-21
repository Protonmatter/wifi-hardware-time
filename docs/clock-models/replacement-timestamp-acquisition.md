# Replacement timestamp acquisition: Gate 1 evidence and next decision

No replacement currently qualifies the existing Windows/Qualcomm system for
plus or minus 10 microseconds relative to AP TSF. The most defensible route
for that system is a supported fresh hardware-counter/QPC capture, with a
separately verified relation to AP TSF and an instrumented AP reference.
If a separate research platform is acceptable, a source-controlled Linux
ath9k/TSF implementation has the strongest directly relevant published precedent.
These are conditional engineering recommendations, not acquired capabilities.

Assessment date: 2026-10-21. Repository baseline and PR #15 head:
`df0c532907f6bdf8406255a53d4405588c6ab1d1`; PR was open and draft when checked.
This assessment used repository files and current public documentation/source.
No adapter query, vendor tool, packet transmission, AP command, driver loading,
trace capture, clock adjustment or live experiment was performed.

## Preserve the existing claim

The [feasibility evaluator](microsecond-feasibility.md) and its five baseline
candidates remain unchanged. The default profile remains plus or minus 10 us,
`ap_tsf`, idle and load, one adapter/driver/host. Existing settled median
half-widths around 133-164 us and the approximately 127 us acquisition floor
remain conditional uncertainty estimates. No independent absolute accuracy
claim follows. The 200 ppm prior, screening policy and jump allowance stay intact.

Gate 1 requires a known event read point, bounded QPC pairing, fresh acquisition
and event attribution. Local TSF, AP TSF, a free-running NIC counter and QPC
are distinct until measured relationships establish otherwise. A new AP or NIC
also changes the qualification scope; it cannot qualify the existing adapter.

## Option assessment

The status column describes evidence available for this assessment. Potential
means the mechanism could supply the required information after qualification.
None of these rows passes Gate 1 on the retained Windows target.

| Method | Gate 1 potential | Current status and decisive missing evidence |
|---|---|---|
| Windows driver-side hardware/QPC cross timestamp | Direct fit for counter capture: known read, driver QPC bracket, current sample and request/interface identity | API contract exists; target queries failed. Need successful exact-build tuples, freshness/read semantics, clock identity and AP relation, full idle/load tails and invalidation rules |
| NDIS hardware packet timestamps + cross timestamps | Adds attributable RX/TX frame events to the counter mapping | Neither capability qualified on target. Need active flags, real raw timestamps and packet IDs, RF placement/retry/aggregation contract and same-domain cross capture |
| Qualcomm/OEM supported TSF capture or driver extension | Direct TSF latch or owned management/RX event can remove diagnostic delivery delay from the sampling uncertainty | No accessible supported interface demonstrated. Need exact producer/ABI, units, read point, live hardware identity, bounded QPC pairing, freshness, owned copy, loss and epoch contract |
| AP-side TSF read or packet hardware timestamps | Strong AP reference and endpoint of a matched exchange | Does not independently pair the Windows client with QPC. Need AP TSF-to-reference mapping plus a qualified client path or separate hardware bridge |
| Linux ath9k TSF/PHC with controlled AP and station | Directly relevant published TSF hardware-clock implementation | Credible alternate platform, not a Windows fix. Need pinned build/hardware, contemporary port, actual RF placement, counter-to-host brackets and independent qualification |
| Intel Linux iwlwifi PTP | Documented source for NIC/host correlation and event timestamp infrastructure | Counter is GP2; firmware synchronized-time path is capability-dependent. Need exact NIC/firmware and GP2-to-AP-TSF/event mapping; Linux system time is not Windows QPC |
| SDR/FPGA MAC with hardware RX/TX latch and common reference | Can design known RF point and shared hardware event capture | Engineering project with accessible implementation, calibrated RF/cable delay, clock/epoch IDs and host mapping still required; generic SDR/TSFT presence is insufficient |
| Ethernet PHC/common pulse bridge | Can provide independent reference and hardware-to-host mapping | Ethernet PHC does not identify Wi-Fi AP TSF. Need an actual AP-TSF-to-PHC/common-event relation and a qualified Windows QPC bridge |
| Cached BSS, aggregate RTT, software send/receive, generic GPIO output | Incomplete under current contracts | Cached age/read point, absent raw exchange times, queue/interrupt delay or absent latch identity prevents a bound. More averaging or finer output resolution does not repair these gaps |

## Windows hardware timestamp APIs

[CaptureInterfaceHardwareCrossTimestamp](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-captureinterfacehardwarecrosstimestamp)
returns a driver-provided NIC/QPC tuple. The
[structure](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_crosstimestamp)
contains `SystemTimestamp1`, `HardwareClockTimestamp`, `SystemTimestamp2`.
The [NDIS OID contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-get-crosstimestamp)
requires QPC, current raw hardware clock, QPC, in that order. A genuinely
more accurate paired capture may report equal QPC endpoints. Equality is not
evidence of zero physical capture error. These contracts make the mechanism
promising; neither API availability nor successful DLL loading proves NIC support.

For an ordinary ordered tuple, the midpoint's conditional acquisition half-width
in microseconds is exactly `(QPC2 - QPC1) * 1,000,000 / (2 * QPC_frequency)`.
The bound assumes the actual fresh counter read occurs inside the bracket.
It excludes undocumented sampling delay, counter quantization, clock mapping,
AP synchronization, rate error, age, epoch changes and reference uncertainty.
A 20 us bracket would consume the entire 10 us half-width target before those
other terms. A useful acquisition allocation therefore needs to be smaller.

The [supported capabilities API](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getinterfacesupportedtimestampcapabilities)
and active configuration must identify the selected interface. Preserve nominal
frequency, SDK/OS target, driver hash, firmware identity or explicit unknown,
status codes and all raw tuples. Do not assume the returned hardware clock is
TSF or AP TSF. A matching frequency or a good affine fit cannot prove that identity.

The repository's [Windows follow-up](../windows-timestamps/windows-timestamp-path-followup.md)
retains error 23 and ABI checks. The later
[rejection-origin analysis](../windows-timestamps/ndis-rejection-origin-analysis.md)
retains INVALID_OID completion evidence but does not identify the first rejecting
layer. The inspected missing-capability-cache branches instead return
NOT_SUPPORTED. Thus the result is unqualified on this build, not a general
claim that Qualcomm hardware cannot timestamp. Repeating the unchanged query
does not resolve the origin; an OEM/Microsoft explanation or changed exact-build
evidence would discriminate. No live query was repeated in this work.

[NDIS packet timestamp attachment](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/attaching-timestamps-to-packets)
provides a separate contract for raw hardware event timestamps and delay
correction. A counter cross timestamp alone does not enable it.
[Winsock timestamping](https://learn.microsoft.com/en-us/windows/win32/winsock/winsock-timestamping)
documents UDP RX control messages and TX retrieval by unique timestamp ID,
including unavailable/dropped results and socket/system configuration.
Require direction-appropriate active flags and a qualified Wi-Fi event point:
first attempt, final retry, acknowledgement and aggregated subframes are not
interchangeable. Retain every failed/missing attempt; do not reuse timed-out IDs
within the session. No timestamp configuration change or UDP test is authorized
by this document.

Moving from WDI to WiFiCx is not evidence of this capture capability. Microsoft's
[WiFiCx low-latency guidance](https://learn.microsoft.com/en-us/windows-hardware/drivers/netcx/wificx-low-latency-connection-quality)
explicitly allows cached BSS information for TSF synchronization during join,
with synchronization completed later. That operational guidance supplies no
microsecond application-facing TSF/QPC bound. The actual driver still needs the
qualified capture and clock-domain contract above.

## Qualcomm interfaces: what would actually change the answer

The strongest Windows path is driver-owner support for a fresh TSF/QPC latch or
a supported extension at the real timing producer. The
[route decision](../evidence/hardware-route-decision-2026-10-06.md) already
separates these from blocked QMSL/QUTS transport and deferred nested IHV controls.
No new proprietary evidence was supplied here. Do not infer a FastConnect
capability from Linux/mobile family names, installed diagnostic software or a
successful fixed-byte device-service control.

The [management producer investigation](../adapters/qualcomm-management-timing-producer.md)
has more information than the cached BSS pair: a schema-matched management block
with link/packet-counter fields, global timestamp, receive duration and an
MPDU-end HWMLO timestamp. Its pinned public Qualcomm reference does not establish
active firmware population or a shared TSF/QPC domain. The main TSF low word and
subsequently read high word also need rollover/atomicity evidence. Preserve all
fields and validity bits before callback cleanup; a wrapper copy alone does
not own its pointees.

The [normal RX export boundary](../adapters/qualcomm-rx-export-boundary.md)
locates descriptor data before packet-prefix removal. PPDU words at relative
`+0x60/+0x68` (full-prefix `+0x68/+0x70`) are an integration lead, not a getter.
Require units, counter width/domain, PPDU first-MPDU validity, retry/aggregation
identity and an owned record tied to the same event. Recording callback-entry
QPC only measures host delivery unless the hardware-event-to-callback delay
has a justified upper bound.

A public historical
[Qualcomm-derived TSF-plus implementation](https://coral.googlesource.com/linux-imx/+/refs/tags/3-1/drivers/net/wireless/qcacld-2.0/CORE/HDD/src/wlan_hdd_tsf.c)
illustrates TSF capture, GPIO interrupt host-time acquisition and paired updates.
Its IRQ handler reads host monotonic time; that is not a hardware latch into QPC.
The code includes a 100 us deviation tolerance and invalid-pair recovery logic,
so its presence is no proof of a worst-case 10 us bound. It is a different OS,
chip family/build and transport. Actual pin routing, capture edge, interrupt
latency bound and supported Windows exposure would all need evidence.
The inspected Windows
[IHV GPIO branch](../adapters/ihv-query-producer-map.md#the-gpio-path-is-an-output-command)
submits GPIO output; it does not expose a TSF capture latch. IHV execution
remains deferred. QMSL `FTM_*` factory-test names are not raw ranging timestamps.

Ask the driver owner for a package/ABI bound to the exact adapter, driver and
running firmware, documenting: capture edge/read point; clock units/width/domain
and AP synchronization; original event/token/link identity; hardware-to-QPC
capture bounds; freshness/age; rollover/reset/roam behavior; owned export/loss;
initialization/state effects; bounded cancellation and teardown. For FTM,
request per-exchange raw t1-t4 with domains, units, validity and token pairing.
The [Windows FTM response](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/wdi-tlv-ftm-response)
exposes aggregated RTT/statistics, which cannot reconstruct four raw event times
or identify offset independently of path delay.

## AP-side acquisition and alternative hardware

An AP TSF value obtained over SSH, a controller API or a queued firmware request
does not pair that AP read with the client QPC. The delivery round trip can be
logged but its midpoint is not an established symmetry bound. Use an AP-side
hardware event record with sequence/exchange ID, link/BSSID, TSF epoch, raw
counter, units, exact RX/TX position and validity; pair the same event at the
client using qualified hardware timestamps. A calibrated two-way exchange or
common hardware event can then address propagation/asymmetry. A second receiver
must itself have a stated reference uncertainty; seeing the same beacon alone
does not make it an independent clock reference.

[Radiotap TSFT](https://radiotap.org/fields/TSFT.html) defines a receive timestamp
at the MPDU's first bit at the MAC, in microseconds. The separate
[timestamp field](https://radiotap.org/fields/timestamp.html) carries units,
sampling position and an accuracy-known flag. Require the actual driver to
populate those semantics and verify the reference point. A PCAP file timestamp
can be host delivery time. Missing accuracy cannot be interpreted as zero.
Similarly, a driver `get_tsf` callback can sleep and is not inherently a hardware
cross timestamp, per the
[mac80211 interface](https://kernel.org/doc/html/next/driver-api/80211/mac80211.html).

The [Chen/Yang ATC 2021 study](https://www.usenix.org/conference/atc21/presentation/chen)
reports microsecond-level Wi-Fi timing using controlled configurations and
calibration, including a TSF-emulated hardware PTP clock. The
[companion source](https://github.com/zlab-pub/wifi-ptp/tree/2d45217058dbba429dcbc4517c83a601a39efac5)
targets modified ath9k on Linux 4.19.37 and AR9300+ cards. Its
[patch](https://github.com/zlab-pub/wifi-ptp/blob/2d45217058dbba429dcbc4517c83a601a39efac5/ath9k.diff)
reads TSF and exposes a PHC/timecounter. This is concrete feasibility precedent,
not a contemporary supported package or proof for arbitrary cards. Port/review
the exact driver and timestamp placement, preserve raw TSF and PHC adjustment
history, and validate against an independent reference. Do not simply load an
old kernel patch on a production endpoint.

Current Intel
[iwlwifi PTP source](https://github.com/torvalds/linux/blob/7455ba7b4d6d869e337db063c466033cf9392fb5/drivers/net/wireless/intel/iwlwifi/mvm/ptp.c)
contains a GP2-based PHC, software frequency/offset adjustment and a
`SYNCED_TIME`-gated firmware `READ_BOTH` path. Otherwise it uses a repeated
software sampling loop. This inspected implementation serves `CLOCK_REALTIME`
and does not supply system monotonic-raw time. It must not be described as a
generic AP-synchronized TSF or an available Windows QPC bridge. Confirm actual
NIC/firmware capability and establish GP2/event/AP relationships before choosing it.

The inspected
[openwifi driver](https://github.com/open-sdr/openwifi/blob/466cd3155483a6b31fbd1237cec2a55fbc394834/driver/sdr.c)
publishes RX `mactime` with `RX_FLAG_MACTIME_START`, but reads TSF low/high
registers separately. Its beacon path assigns the timestamp in software and
retains TODOs for hardware insertion/queue/timing. These details prevent treating
the generic AP beacon timestamp as a calibrated TX instant without examining
the matching FPGA image and proving its behavior. SDR/FPGA remains promising
when the actual MAC latches the needed event, rather than software composing it.

[Linux PHC infrastructure](https://docs.kernel.org/driver-api/ptp.html) supports
external timestamp events and periodic signals on capable hardware; actual pins
and capabilities are device-specific. A shared pulse measured by both an AP TSF
latch and an independent counter can isolate the reference error. An Ethernet
PHC on the Windows host can help only if its QPC relationship and the AP's
TSF-to-PHC relationship are both bounded. GNSS PPS by itself measures an external
epoch; it does not reveal AP TSF or establish a Windows interrupt latency bound.
No specific purchasable hardware or accessible laptop timing pin is assumed.

## Recommended sequence and evidence that would reopen Gate 1

1. Keep the current Windows conditional clock as the available result. Seek a
   supported OEM/Qualcomm hardware/QPC or TSF/QPC interface and explanation of
   the failed standard path. Prefer this over additional unqualified diagnostic
   polling: only an identified capture point changes the uncertainty floor.
2. Prepare an instrumented AP reference in the design, with known TSF event
   placement and its own error budget. A raw AP counter read is insufficient.
   Use a hardware common event or matched hardware exchange; establish the
   client-to-QPC link independently. Do not adjust either system clock.
3. If vendor support is unavailable and platform replacement is acceptable,
   select a separate Linux ath9k TSF/PHC prototype as the best evidenced route
   for proving the mechanism. Intel GP2/PHC and FPGA MACs are alternatives with
   distinct mapping or implementation work. This selection needs a new scoped
   physical qualification; none was performed here.
4. Review retained records before authorizing any experiment. For every Gate 1
   property require an exact source, statement, build/scope and original record.
   Then predeclare Gate 2 allocations and a finite idle/load campaign preserving
   every attempt, gap and tail. Pass Gate 3 only against the named independent
   reference. Reopening Gate 1 is not proof of the 10 us objective.

Pairing is only part of the budget. Retain all six terms in the existing
evaluator and account explicitly for AP/local-clock transfer in event placement
or reference uncertainty without double counting. For illustration, keeping a
2 us rate/age allocation under a 200 ppm rate bound permits at most 10 ms age
before other errors; this is arithmetic, not a measured refresh capability.
Epoch changes must invalidate mappings. Neither minimum-bracket selection nor
averaging establishes bounded tails, and no residual fit justifies narrowing
the existing prior.

## Offline evidence intake

[cross_timestamp_intake.py](../../research/clock_models/cross_timestamp_intake.py)
audits saved Windows raw-counter/QPC tuples. It uses only Python's standard
library and local read-only files. It requires no elevation, network, device,
vendor binary, new dependency or system configuration. The program writes its
JSON report to stdout and errors to stderr. It does not call the feasibility
evaluator, produce a `candidates` array, fit a clock, infer continuity, or
qualify a capture path.

The input schema is `wht/cross-timestamp-intake-v1`:

| Field | Required content |
|---|---|
| `provenance` | `synthetic` or `retained_capture`; declaration is not authenticated |
| `scope` | Nonempty `adapter`, `driver_sha256` (64 lowercase hex), `firmware`, `os_build`, `host`, `clock_domain`; use `unknown` when unresolved, and pseudonyms for endpoint identity |
| `qpc_frequency_hz` | Positive integer for this one host/session scope |
| `pairing_limit_us` | Predeclared positive integer 1-10 for bracket half-width alone; it is not the total error budget |
| `references` | Name-to-object map with relative local `path` and full lowercase `sha256`; hashes bind files, not the truth of statements |
| `claims` | All four Gate 1 names, each with `basis` (`unknown`, `documented`, `measured`), a nonempty `statement` and unique named `references`; established claims need references; pairing and freshness require measured basis for review readiness |
| `attempt_accounting` | `idle` and `load` objects, each with collector-declared `issued` (nonnegative integer or explicit `null` if unknown) and a verified source `reference` supporting that denominator |
| `attempts` | All successful and failed requests; each has `condition` (`idle`/`load`), `epoch`, `attempt_id`, evidence `reference`, DWORD `status`; status 0 requires nonzero uint64 `qpc_before`, `hardware_ticks`, `qpc_after` in order |

One manifest describes one interface/build/clock domain/QPC frequency. Separate
scopes belong in separate manifests. `(epoch, attempt_id)` must be unique across
conditions. Epochs are declared by the source; the auditor does not infer reset,
counter wrap, frequency changes or live-versus-replay identity from numeric trends.
Preserve collector/build/configuration, capabilities, epoch rules and event locators
in the referenced source/claim dossier. Review must match each normalized tuple
to its original bytes; the auditor does not parse arbitrary source formats.
The CLI report includes `manifest_sha256`, calculated from the exact input bytes,
so the reviewed assertions and normalized rows can be tied back to one manifest.
Hashes still do not authenticate capture provenance or semantic correctness.

QPC arithmetic uses exact rational numbers even above `2**53`. Output widths
are objects with integer numerator/denominator in microseconds. Failed requests
remain counted but their output buffers are not interpreted. All successful
brackets remain in the report, including over-limit tails. No admission or
statistical filtering occurs. Unknown claims, absent idle/load successes,
capture failures and wide brackets are review blockers. Supplied-row counts are
compared with the collector-declared issued totals: an unknown total or a deficit
blocks review readiness, and a total smaller than the supplied records is rejected
as contradictory. Reports preserve `issued` and `unrepresented` counts; unknown
counts stay null. The auditor cannot detect a false collector total, substituted
records or omissions from the original source itself. Review must verify the
source denominator independently. Equal QPC endpoints
require separate capture-error evidence outside this ordinary-bracket auditor;
they do not automatically pass as a zero-error pair.

Examples, from the repository root:

```powershell
python -m research.clock_models.cross_timestamp_intake --help
python -m research.clock_models.cross_timestamp_intake tests/fixtures/cross_timestamp_intake/manifest.json
python -m unittest discover -s tests -p test_cross_timestamp_intake.py -v
```

The checked-in fixture is explicitly synthetic and exits 2. For real intake,
place the manifest and approved source evidence together in private/ignored
storage and pass that manifest path. Absolute paths, parent traversal, alternate
data-stream syntax, external links/junctions, hash mismatches, duplicate JSON
keys, non-finite constants, overflowing JSON numbers (including in unused fields)
and malformed tuple values are rejected. Symlink loops produce a normal error
exit, including on Python versions that raise `RuntimeError` for them. Hash checks
assume a quiescent local bundle, not an adversarial concurrent filesystem writer.
Do not place proprietary traces, private binaries, endpoint identifiers or secrets
in public Git.

Exit codes: 0 means structurally ready for semantic review; 2 means valid intake
with unresolved blockers; 1 means invalid/unreadable input. Every report retains
`gate1_qualified: false` and `physical_bound_proven: false`, including exit 0.
The existing feasibility evaluator's boolean input interface remains a separate
trusted-evidence entry point. This auditor cannot authenticate hardware behavior
or protect an operator who bypasses review and writes those booleans manually.

Rollback: remove the added auditor, tests, synthetic fixture and this assessment,
revert only the added navigation lines, then regenerate the knowledge index.
There is no runtime provider integration or endpoint change to roll back.
The fixture's source text is pinned to LF in `.gitattributes` so its hash is
portable. The documentation-link test now normalizes parent segments before
checking existence: at this Windows checkout depth an unnormalized archive link
exceeded 260 characters even though the resolved file exists. This changes only
offline validation and leaves archive content intact.

## Source and qualification limits

External source revisions were checked on 2026-10-21: Intel PTP file change
`7455ba7b4d6d869e337db063c466033cf9392fb5` (2026-07-16), wifi-ptp head
`2d45217058dbba429dcbc4517c83a601a39efac5` (2024-07-01), openwifi driver change
`466cd3155483a6b31fbd1237cec2a55fbc394834` (2026-08-06). Dates identify source
revisions, not installed hardware/firmware. Historical Qualcomm-derived TSF-plus
source is pinned to its linked tag and is illustrative only. Public documentation
availability, source review, software tests, real acquisition and independent
accuracy qualification are separate evidence levels.
