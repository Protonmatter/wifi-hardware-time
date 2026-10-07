# Corrected observer: passive live qualification

Two passive checks confirmed that the rebuilt observer could start, report trace health and stop cleanly without sending private requests. They collected no clock reports, so they did not test active delivery or accuracy. This was a historical prerequisite check; the later private campaign still failed and remains quarantined.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The private campaign remains quarantined. The new QUTS client ownership finding does not establish firmware drain, report association or a new live acquisition. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

The observer reads diagnostics without requesting clock measurements in this test. ETW is Windows event tracing. A passive check tests the collector; it cannot prove that pending firmware reports have drained. See the [glossary](../glossary.md) for related terms.

Result: **passed**, 2026-10-03 America/New_York. The corrected observer was rebuilt,
selected at the campaign's existing executable path, and exercised through two
passive calls to the existing capture function. Both used an empty action list
and `smoke=True`; no private request was admitted or sent.

**Later status:** the [private repeat](private-campaign-2026-10-03-quarantine.md) failed and remains quarantined. The marker-removal statement below describes only these earlier passive checks.

## Build and selection

Source revision: `85cd217d6c413852c3d039643dc297b39ba35bf2`.
The ARM64 build used installed MSVC with `/W4 /WX /O2 /Brepro`. Observer, included
decoder, gate, controller, compiler and executable hashes were recorded locally.

Selected `artifacts/live_observer.exe` SHA-256:
`afc40361b7037213cf3315a1765205f65bc1e90ebabefb5293796b42e7e3e134`.

The prior executable was copied to the qualification directory before selection
and its backup hash was verified:
`ce9ae0bd97a5c555c296b159e5043ead9da59e9a03c3dabebf061cd2faced597`.

The selected hash matched the candidate before and after testing. Selection changed
only the local research collector executable, not a driver or firmware component.

## Live results

| Check | Passive pass 1 | Passive pass 2 |
|---|---:|---:|
| Ready protocol | controller-query/v1 | controller-query/v1 |
| Valid controller-health records | 17 | 17 |
| Connected-state observations | 17 | 17 |
| Lifecycle records | 0 | 0 |
| Private requests | 0 | 0 |
| TSF timing records | 0 | 0 |
| Controller query failures | 0 | 0 |
| EventsLost / LogBuffersLost / RealTimeBuffersLost | 0 / 0 / 0 | 0 / 0 / 0 |
| Offline header EventsLost / BuffersLost | 0 / 0 | 0 / 0 |
| Observer ProcessTrace / CloseTrace status | 0 / 0 | 0 / 0 |
| Offline ProcessTrace / CloseTrace status | 0 / 0 | 0 / 0 |
| Observer clean stop | Yes | Yes |
| Exact trace-session post-stop query | Not found | Not found |
| Total controller capture duration | 6.763 s | 6.638 s |

Both observer processes exited normally. No access-denied result was mistaken
for an absent session. Live/offline timing-record equality passed with both sets
empty, as required for passive testing; this does not test active timestamp delivery.

The adapter remained Up on driver 1.0.4374.1300 with the exact qualified SYS hash.
Interface identity, service state and association remained consistent. The test
owned the shared campaign marker to exclude concurrent campaign admission, then
removed only that unchanged owned marker after success. No active/quarantine
marker remained afterward.

## Evidence and operational consequence

Private receipt directory: `artifacts/ObserverQualification-a52d80148dd5`.
It retains build/selection and launch manifests, the passive-only runner, identity
snapshots, both traces, observer/decoder outputs, cleanup verification and the
successful `qualification.json`. Raw identifiers, traces and binaries stay ignored.

The corrected observer is selected at the existing campaign launch path. Its
passive readiness prerequisite is met for this host/build. Subsequent authorized
private campaigns must still run their own preflights, exact identity checks and
quarantine rules. The preserved old binary remains incompatible with the new gate;
restoring it is not a way to admit a private campaign.

## Limits

No lifecycle notification occurred. Registration initialized successfully, but
disconnect, roaming, reset and suspend/resume detection were not exercised. No
loss was injected, and the specific missing-session shutdown-race branch was not
instrumented. Active delivery, improved latency, firmware drain, timestamp
semantics and timing accuracy are not qualified by this passive success.

No 138-request campaign, automatic-report command, FTM request, statistics IOCTL,
register operation, WLAN-profile change or clock write was performed. No commit
or push was performed in this qualification pass.
