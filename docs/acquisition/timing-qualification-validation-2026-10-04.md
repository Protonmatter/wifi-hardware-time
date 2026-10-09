# Timing qualification: live query results and remaining dependencies

A fresh, bounded Windows query run returned no timestamp capabilities or hardware-to-host sample. Wi-Fi remained Up on the same exact driver. All 206 offline tests passed, but firmware sampling, live buffer publication and synchronization accuracy remain unqualified. At this report's initial validation checkpoint, hosted CI covered the preceding committed revision. Current publication and review status are tracked in the [gap ledger](../overview/gap-closure-ledger.md).

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__acquisition__timing-qualification-validation-2026-10-04.md).
<!-- /research-history -->

## Contents

- [Live result](#live-result)
- [Requested qualification status](#requested-qualification-status)
- [Software validation](#software-validation)
- [Hosted CI and publication](#hosted-ci-and-publication)
- [Evidence and reproduction](#evidence-and-reproduction)
- [Terms](#terms)

## Live result

Observation completed at `2026-10-04T06:42:33.9953326Z`.

- Selected the unique **Up physical Qualcomm interface**. Discovery also found
  disconnected/absent entries using the same driver; matching the driver name
  alone did not uniquely select the active target.
- Checked the exact interface identity, driver version and driver-file hash
  before queries and after completion.
- Built the existing ARM64 native probe from its current source using installed
  MSVC 14.44.35207 and Windows SDK 10.0.26100.0, with warnings treated as errors.
- Issued each of the following documented read-only queries once, in a separate
  child with a ten-second deadline. All children exited normally.
- Used a non-elevated token. No private command, trace session, marker provider,
  explicit scan, adapter restart, firmware/mode change or clock adjustment.

| Query | Return code | Returned timing/capability values |
|---|---:|---|
| `GetInterfaceSupportedTimestampCapabilities` | 23 | None |
| `GetInterfaceActiveTimestampCapabilities` | 23 | None |
| `CaptureInterfaceHardwareCrossTimestamp` | 23 | None |

The helper's process exit 0 means query execution and its own cleanup completed;
it does not turn the recorded API errors into successful timestamp retrieval.
Failed output buffers were not interpreted as timestamps.

The result is **no usable cross timestamp from this run**. It is not a finding
that the hardware lacks timestamp support. Microsoft documents
`ERROR_NOT_SUPPORTED` for a non-timestamp-aware adapter's supported-capability
query; this run returned a different error. No trace was collected to attribute
the originating rejection layer. See the [capability API](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getinterfacesupportedtimestampcapabilities),
[cross-timestamp API](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-captureinterfacehardwarecrosstimestamp)
and [earlier rejection analysis](../windows-timestamps/ndis-rejection-origin-analysis.md).

Post-check: the same interface remained **Up**, with driver **1.0.4374.1300**.
Driver SHA-256 remained
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
The inspected packaged firmware SHA-256 remained
`74f2ffde049d523cba7bc7660f4d9806110bbe1d1ecac9565f50028652a861f3`;
that package hash is not verification of the running firmware image.

## Requested qualification status

| Requested claim | Disposition | Evidence still needed |
|---|---|---|
| Actual candidate firmware timing-field contents | Not validated | A complete management event containing its frame, original header and optional timing block from an identified producer |
| Exact sampling instants | Not validated | Producer implementation or an independently characterized acquisition mechanism tying each field to a physical event |
| Split-word correction | Not validated | The actual producer's high/low-word rollover algorithm and qualified boundary cases; reference comments alone are insufficient |
| Live copy/publication safety | Not validated | An implemented driver/vendor return path with demonstrated input lifetime, synchronization, commit, overflow, teardown and cancellation behavior |
| Hardware-to-QPC conversion | Not validated; live documented query failed | A successful fresh sampling bracket or independently justified relationship between the identified clocks |
| Synchronization accuracy | Not validated | Qualified acquisition plus controlled peers and an independent comparison with characterized uncertainty |

The [producer investigation](../adapters/qualcomm-management-timing-producer.md)
locates candidate fields and the callback cleanup boundary. It does not export
those fields. Existing historical TSF diagnostics contain some counter values,
but cannot reconstruct omitted fields or the corresponding original frame.

The [C exporter](../evidence/owned-timestamp-export-prototype.md) accepts synthetic
records only and requires external serialization. Its software-copy tests do
not exercise a kernel callback, concurrent driver-buffer reuse or firmware DMA.
No synthetic result was promoted to a live qualification claim.

The last user-provided equipment status remains no second controlled node and
no independent timing reference. A roughly estimated AP distance or
uncharacterized NTP agreement does not supply that missing accuracy evidence.

A fresh filename search across five existing Qualcomm/GAC roots again found
no matching `QC.QMSLFastConnect.dll`, `QTMDotNetKernelInterface.dll`,
`QTMInterface.dll` or `QMSL_WLAN_Transport.dll`. This bounded absence result does
not cover every possible installation directory or establish vendor entitlement.
See [the vendor-interface investigation](../adapters/qualcomm-software-center-timing-leads.md).

## Software validation

- `python -m compileall -q research tests`: passed.
- `python -B -m unittest discover -s tests -v`: **206 passed, no skips**, with
  the owned Qualcomm, WiFiCx and WLAN service images configured and an initialized
  ARM64 MSVC environment for the native harness.
- `Test-TimestampExport.ps1 -Architecture x64`: native synthetic exporter checks
  passed under x64 compilation/execution on this workstation.
- Documentation and publication checks are separate from firmware qualification.

The existing test-first work on the inspector covers the management-event
history exclusion and allocation-flag offsets. This follow-up adds no hardware
provider, firmware decoder, timestamp conversion or new live API implementation.

## Hosted CI and publication

The live GitHub check found:

- Branch: `investigate-packet-export`.
- Local HEAD and remote branch HEAD:
  `a87fd034d537c9a1a863969e8ea4c4b3b13d9ec9`.
- [Offline checks run 37139298473](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37139298473):
  completed successfully; both `protocol` and `windows-syntax` passed.
- No pull request was returned for this head branch at the time of the check.
- New inspectors, evidence readers, the synthetic exporter, tests and research
  notes are still local changes. The successful run above does not cover them.

The pending workflow already adds the synthetic native contract to Linux and
Windows jobs. Hosted testing requires a commit containing the complete source,
tests, documentation and workflow changes, followed by a normal branch push.
Rerunning the old SHA would not validate the local edits. Hosted jobs also lack
the proprietary owned-image fixtures and cannot qualify this laptop's hardware.

The user's repository instructions require an explicit commit/push request.
No new commit, push, workflow dispatch or merge was performed in this validation
pass. Publication approval is a separate step from the results recorded here.

## Evidence and reproduction

The maintained query source is
[`ndis_query_probe.c`](../../research/windows_timestamps/ndis_query_probe.c).
This run reused `Get-ExactAdapter` and `Invoke-BoundedChild` extracted from the
owned [V2 wrapper](../../research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1)
without executing that wrapper's trace/elevation body.

Private local evidence is in ignored
`artifacts/QualificationValidation-cbbca9b10f724342b2d18c7b3bdf9f89/`:

- `validate_documented_queries.ps1`: actual bounded execution script; parsed
  before use, with exact-target checks and post-check in `finally`.
- `build-manifest.json`, `build.txt`: source, helper, compiler and executable
  identities and build output.
- `query-*.stdout.txt`, `query-*.stderr.txt`, `query-*.process.json`: API return
  codes, process completion and raw local identity information.
- `adapter-check.json`: before/after status, identity consistency and operation scope.
- `full-tests.txt`: current offline suite result.

The private wrapper has a selected local artifact directory and is an execution
record, not a newly supported public acquisition launcher. Source and binaries
must be checked again before any repeat run. Old launch manifests using paths
from before the repository reorganization were not reused.

| Build input/output | SHA-256 |
|---|---|
| Current probe source | `ee9adfa33159f3c73eb55842fba1c923cfbb37f6118df2974811e607b774d4a4` |
| ARM64 probe executable | `5e08163c50e3eb76ca552e7ca417cd67177af3a90edc9d6f035bd01829034bf0` |
| Maintained V2 wrapper | `b238f7388146913c6ec637576a3478a34871f0758b19373885ac1f7941227322` |
| Local execution script | `7cc7b2b9c0b0447829509eb228f36506b7c6211066d0cd9e51d5f987595f7023` |

No device configuration rollback is needed. Local evidence can be archived;
no proprietary binary, capture payload or endpoint identifier belongs in the
public commit. The private TSF campaign remains quarantined.

## Terms

- **QPC:** Windows's high-resolution interval counter.
- **Cross timestamp:** a hardware counter sample associated with host-clock samples.
- **Publication:** making a complete owned record visible to a consumer; distinct
  from publishing source to GitHub.
- **Split word:** storing a wide counter in separate high and low parts whose
  sampling/rollover behavior must be established.
- **Qualification:** evidence for a precise claim under stated conditions.

See the [glossary](../glossary.md) for other terminology.
