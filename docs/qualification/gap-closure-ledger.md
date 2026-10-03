# Qualification gap closure ledger

Updated 2026-10-03, America/New_York. This ledger distinguishes an answered
research question from a passing acquisition profile or enabled clock capability.
The private campaign remains quarantined.

Follow-up: [timing boundaries](timing-boundary-investigation-2026-10-03.md)
narrows reset/crash ring consumers, reproduces a double-copy counterexample and
locates RX PPDU diagnostic fields. The [lifecycle cases](lifecycle-qualification-preparation.md)
are preparation only, as requested. None promotes a hardware clock capability.

| Gap | Current disposition | Evidence / next prerequisite |
|---|---|---|
| Can ordinary host activity produce additional TSF reports without our private request? | Operational pattern reproduced | Three controlled documented scan calls, each with a quiet baseline, one scan command and two TSF/SoC report groups; [results](scan-tsf-results-2026-10-03.md) |
| Why did the four-second scan-completion check fail? | Late completion directly observed in the final diagnostic run | Driver COMPLETED logs at about 6.025 s; both WLAN clients notified at about 6.027 s. Earlier runs ended before their completion could be measured |
| Has the scan comparison passed its original acceptance profile? | No | All three trials remain failed against four seconds; any changed deadline needs a separately declared experiment |
| Native-source provenance across checkout | Corrected and regression-tested | LF attributes restore exact qualified source bytes; selected native binaries unchanged |
| Normal observer cleanup | Observed again | Three owned trace/client/observer cleanups; no forced termination; trace absence and wrapper exit checked |
| Unique firmware request/report identity | Open | Operational scan association does not supply a firmware transaction ID; keep unassigned reports out of private-request evidence bundles |
| Freshness / simultaneous TSF and SoC capture | Open | Changed SoC values also occur around scans; neither an increment nor an action name proves a simultaneous latch |
| Hardware-to-QPC sampling relationship | Open | Need a qualified fresh bracket or documented hardware cross timestamp; regression and log receipt times are insufficient |
| Live memory-ring getter and consistent copying | Open; unsafe inference ruled out in a finite model | Direct consumers narrowed to reset/crash/recovery; two of ten schedules defeat equal-copy/stable-position checks without writer exclusion. Safe userspace reachability and publication semantics remain missing |
| Raw absolute FTM events | Open | Internal response comparison uses a request-context byte, not a qualified unique exchange/epoch token; absolute export, units and reference points remain missing |
| Arbitrary RX/TX packet timestamps | Open; RX diagnostic fields located | Descriptor +0x60/+0x68 are labeled high/low PPDU words. Live validity, units, packet identity and export remain unqualified; no new TX result |
| Host API one/four-reader overhead and basic thread invariants | Measured on current host | Downstream contention measurements: 150,000 timed reads; per-reader monotonicity/identity/integer conversion passed. Provisional p99 targets are 5 us / 250 us; separate acceptance testing remains pending |
| Shared cross-process clock identity | Open | Current SDK deliberately scopes identity to one clock instance in its owning process |
| Reset, suspend and roaming | Latest phase is preparation only | Separate cases and collector requirements are documented; prior single restart remains historical evidence |
| Calibrated/sub-millisecond synchronization | Equipment and semantics prerequisites unmet | No second controlled node or independent characterized reference; no qualified hardware/host conversion yet |
| Hosted CI | Merged baselines passed; follow-up had only local validation at report review | Check any later CI against the exact published revision; old CI does not validate this follow-up |

Published scan/tooling revision `fdcc22f80ad173a2f4f2844c0f6b666794fda54a`
passed [hosted CI](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37121148165).
The later timing-boundary package passed 149 local tests with owned fixtures
(146 plus three skips without them). Its own publication/CI must be checked
separately; neither CI nor those offline tests qualifies hardware.

## Downstream rules supported by the new result

- Do not infer a private capture action from a changed SoC value. Scan-associated
  reports changed it without a private TSF request from the harness.
- Do not treat a successful private getter as owning the next report merely by
  sequence. Ordinary scan activity introduces another operational context.
- Preserve observation origin as unknown or diagnostic when association is not
  established. The existing private evidence contract is not silently widened to
  admit unassigned reports; raw diagnostics are not clock-conversion inputs.
- Do not mark the failed scan profile passing by retrospectively increasing its
  deadline. The six-second measurement is evidence for designing a future profile.
- Keep QPC application reads independent of scan completion, ETW delivery and
  hardware requests. Measured call latency is not a synchronization-error bound.

## Work that current equipment cannot establish

Sub-millisecond accuracy needs both a qualified time-transfer/acquisition path
and comparison against a second controlled node or a characterized independent
reference. A rough AP distance estimate, synthetic offset estimator, local QPC
benchmark or additional same-machine TSF reads cannot substitute for that test.

The next hardware-interface work should target a narrow, reviewable producer-to-
userspace return path with explicit record completion and clock identity. A driver
change or firmware cooperation would be a separate engineering project; the
existing dump paths are not a safe polling API and no blind register or kernel
memory access is justified by these findings.
