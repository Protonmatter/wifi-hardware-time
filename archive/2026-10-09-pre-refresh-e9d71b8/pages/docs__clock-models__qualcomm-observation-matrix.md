# Offline observation quality: first downstream work package

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__clock-models__qualcomm-observation-matrix.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

This report evaluates how well saved Wi-Fi timing observations predict host timing, including samples withheld from model fitting. It compares simple baselines and more detailed models while retaining data-quality limits. Predictive success is useful for research, but it does not establish the hardware sampling instant, external accuracy or a qualified clock.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QUTS and QXDM expose distinct hardware-origin, interpolated and host-delivery times. Owned bytes do not establish fresh hardware-to-QPC sampling or an accuracy bound. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

**Key terms:** Held-out samples are excluded from fitting and used to test predictions. A baseline is a simpler comparison model. An observation timestamp may mark logging rather than the event being measured. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Contents

- [Admission results](#admission-results)
- [Held-out prediction](#held-out-prediction)
- [Reproduce locally](#reproduce-locally)
- [Follow-up live campaign](#follow-up-live-campaign)
- [Qualification beyond the completed campaign](#qualification-beyond-the-completed-campaign)
- [Immediate priority: qualify the installed Qualcomm NIC](#immediate-priority-qualify-the-installed-qualcomm-nic)

This pass analyzed saved captures only. It sent no new private IOCTL, FTM request,
register operation, WLAN change or clock adjustment.

## Admission results

The exporter and downstream validator admitted 12 observations from the saved
READ_VALUE run `WifiTime-6ee1b42080dc` and 11 observations from the saved mixed
READ_VALUE/QTIMER_CAPTURE run `WifiLatch-d714d8a90d79`. Both retain experimental
observation-only qualification, null hardware sampling interval and null external
uncertainty. The exported numeric bundles remain ignored local artifacts.

## Held-out prediction

The quality analyzer uses exact rational fitting centered on the first point to
avoid losing integer precision in large QPC values. It fits TSF against **host
report-log QPC**, not firmware sample time. Within-run fits use the first six
points only; all remaining points are held out. An endpoint-rate baseline uses
the first and last training points only.

| Evaluation | Held-out points | Affine maximum absolute error (raw TSF ticks) | Endpoint-rate baseline maximum |
|---|---:|---:|---:|
| READ_VALUE run | 6 | 96.0004 | 195.5744 |
| Mixed-action run | 5 | 67.3556 | 63.0978 |
| READ_VALUE-trained rate transferred to mixed-action run | 10 | 40.9463 | 48.4861 |

The transfer test fits rate using all 12 training-run points, then uses exactly
one observation at the beginning of the other run to establish a new offset.
It does not assume phase continuity across runs. Its remaining ten observations
are held out; this is rate-transfer evaluation, not clock synchronization.

The affine model is not uniformly better than the endpoint baseline. The last
value baseline is also reported in within-run output, but is weak for an advancing
counter. No practical advantage over ordinary host event timing has been proven.
The data comprise two short, nonrandomized historical runs; there is no load/power
matrix or independent reference. Raw ticks are not converted into an accuracy claim.

Saved userspace request brackets (start to completion observation) were
47.0/53.0/361.3 microseconds min/median/max for the 12-read run and
46.9/52.0/54.4 microseconds for the 11-request mixed run. These exclude process
startup, discovery, ETW collection/decoding and firmware report delivery; they
are not total collector cost or firmware execution latency. CPU/power overhead
and application timestamp-read latency remain unmeasured.

A synthetic constant-bias test produces zero residual while retaining null
external uncertainty. This deliberately demonstrates why a good fit cannot
identify sampling bias or supply a calibrated timing bound.

## Reproduce locally

```powershell
python research/evidence/export_clock_evidence.py artifacts/WifiTime-6ee1b42080dc artifacts/read-series-evidence-v1.json
python research/evidence/export_clock_evidence.py artifacts/WifiLatch-d714d8a90d79 artifacts/latch-series-evidence-v1.json
python research/clock_models/analyze_observation_quality.py artifacts/read-series-evidence-v1.json --train-count 6
python research/clock_models/analyze_observation_quality.py artifacts/latch-series-evidence-v1.json --train-count 6
python research/clock_models/analyze_observation_quality.py artifacts/latch-series-evidence-v1.json --rate-training-bundle artifacts/read-series-evidence-v1.json
```

Use fresh export filenames if they already exist. Export receipts change when
source provenance changes; the numerical results for these unchanged captures
should remain the same. The CLI validates the full v1 contract before analysis,
rejects mismatched QPC frequencies for rate transfer and retains unknown accuracy.
Exit codes: 0 for analysis, 1 for rejected input/I/O, 2 for invalid CLI usage.

## Follow-up live campaign

The subsequently completed [guarded campaign](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/acquisition-campaign-2026-10-02-results.md)
passed three idle and three workload repetitions of each approved sequence:
12 captures and 138 accepted observations. This extends the earlier offline
analysis above; the campaign report records the new latency/freshness limits.

## Qualification beyond the completed campaign

Define a consumer freshness/error target before interpreting the repeated
capture results as sufficient. Firmware association and externally established
drain behavior, plus the remaining disruptive lifecycle cases, still need
qualification before a resident hardware provider is justified.

## Immediate priority: qualify the installed Qualcomm NIC

The next hardware target is the existing FastConnect 7800, not a replacement
adapter. A fresh read-only baseline on 2026-10-02 confirmed Wi-Fi Up, driver
1.0.4374.1300, qcwlan Running and the same qualified full driver hash. Python and
the independently compiled SDK helper again returned 23 for supported and active
timestamp capabilities. The Python tool therefore did not request a cross timestamp
in this pass. These failures leave standard capability unknown.

Run the next campaign in this order:

1. Prepare live lifecycle observation and an explicit timeout/ambiguity quarantine
   path. Inspect adapter/build, association and trace health before and after each
   run. No more than one private timing request is outstanding.
2. Collect three idle runs of each existing approved sequence: bounded READ_VALUE
   and mixed READ_VALUE/QTIMER_CAPTURE, preserving current limits and cadence.
3. If all runs complete cleanly, collect three runs of each sequence under a
   specified reproducible local workload. Record request/report latency, missing
   and duplicate records, cached/fresh semantics, loss, relative rate and collection
   overhead. Do not modify WLAN profiles or generate unbounded network traffic.
4. Stop the campaign at an unexplained timeout, ambiguous/late report, trace loss,
   identity change or cleanup failure. Do not start another acquisition merely
   because a process or ETW session restarted; prove isolation/drain or keep the
   provider unavailable and investigate the trace offline.
5. Qualify non-disruptive collector stop/start and data expiry first. Adapter reset,
   suspend/resume, forced reassociation and roaming have separate recovery and
   authorization gates. One historical successful restart is not this matrix.
6. Produce a capability-by-capability qualification record for downstream use:
   raw TSF delivery, freshness, experimental relation to host time, standard
   cross timestamps and packet timestamps each retain their own evidence state.

Operational repeatability and failure handling can be tested with the current
adapter. Calibrated accuracy still requires an independent reference; a comparison
NIC is a diagnostic control, not a substitute for validating this Qualcomm device.
No new elevated capture or lifecycle experiment was performed by the baseline
refresh above.
