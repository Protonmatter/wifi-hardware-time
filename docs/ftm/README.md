# Wi-Fi ranging results and raw timestamp limits

Can Wi-Fi ranging supply the four timestamps needed to compare clocks? Saved results and driver analysis explain aggregate ranging output and identify an earlier internal measurement buffer. No supported export of the four absolute event times is established. Successful ranging therefore does not qualify clock offset, timestamp accuracy, or general packet timing.

FTM (Fine Timing Measurement) is a Wi-Fi ranging exchange. RTT is round-trip time; an ACK is a frame acknowledging receipt. An aggregate combines several measurements into one result. See the [glossary](../glossary.md).

## Reports

| File | Question answered |
|---|---|
| [ftm-result-provenance.md](ftm-result-provenance.md) | Why can a successful callback contain zero measurements, and why is its variance field unqualified? |
| [ftm-raw-access-followup.md](ftm-raw-access-followup.md) | What exists before aggregation, and which export contract is still missing? |
| [ftm-notification-routing.md](ftm-notification-routing.md) | Do the inspected notification or completion routes carry that raw buffer? |

## Four-event model versus observed output

This simplified model identifies the times a full exchange needs. It does not claim the current callback exposes them. Source: [ftm-timestamp-path.mmd](diagrams/ftm-timestamp-path.mmd).

```mermaid
sequenceDiagram
  participant A as Responder / AP clock A
  participant B as Initiator / station clock B
  participant U as Userspace reader
  Note over A,B: Model: one matched FTM exchange.<br/>Negotiation omitted
  Note over A: t1: hardware departure time
  A->>B: FTM frame n
  Note over B: t2: hardware arrival time
  Note over B: t3: hardware ACK departure time
  B->>A: ACK: no t3 timestamp field
  Note over A: t4: hardware ACK arrival time
  A->>B: Later FTM frame: prior t1 / t4 and matching token
  Note over B: Full exchange needs local t2 / t3 and peer t1 / t4
  B-->>U: Observed API output: aggregate RTT, count, status, raw auxiliary fields
  Note over U: Not exposed: four individual timestamps or clock mapping
  Note over A,U: Model needs four valid times and rate correction.<br/>Delay asymmetry still limits offset estimation
```

Diagram key: solid arrows are modeled radio frames; the dashed arrow is the observed application result. Notes labeled **Model**, **Observed API output**, and **Not exposed** distinguish assumptions, findings, and limits without relying on color. Time labels belong to the local clock shown above each participant. Unequal delay in the two directions still limits clock-offset estimates even when all four times are available.

## Research tools

- [ftm_once.c](../../research/ftm/ftm_once.c) and [ftm_result.h](../../research/ftm/ftm_result.h): exact-build request and callback layout.
- [Capture-FtmOnce.ps1](../../research/ftm/Capture-FtmOnce.ps1): bounded ranging capture workflow.
- [decode_ftm_response.py](../../research/ftm/decode_ftm_response.py): aggregate callback decoding.
- [FtmDeltaLog.ps1](../../research/ftm/FtmDeltaLog.ps1) and [Export-FtmDeltaEvents.ps1](../../research/ftm/Export-FtmDeltaEvents.ps1): logged time-difference extraction.
- [analyze_ftm_deltas.py](../../research/ftm/analyze_ftm_deltas.py): saved delta analysis.
- [model_ftm_selection.py](../../research/ftm/model_ftm_selection.py): pure offline model of result selection and aggregation.

Live tool availability does not qualify raw timestamp access or ranging accuracy. Return to the [documentation index](../README.md).
