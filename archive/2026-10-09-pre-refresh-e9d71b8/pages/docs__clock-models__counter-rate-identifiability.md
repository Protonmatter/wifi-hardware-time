# TSF versus SoC: what the reported increments can identify

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__clock-models__counter-rate-identifiability.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Similar-looking counter rates do not prove two values share a clock or were sampled together. This analysis checks which rate relationships the saved data can distinguish. Several conditional explanations remain possible, so a good mathematical fit cannot decide the physical sampling mechanism or provide a calibrated conversion error bound.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QUTS and QXDM expose distinct hardware-origin, interpolated and host-delivery times. Owned bytes do not establish fresh hardware-to-QPC sampling or an accuracy bound. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

**Key terms:** Identifiability asks whether the available observations distinguish competing explanations. A conditional result is true only if its assumptions hold. Residual error measures fit to data, not error against an independent reference. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

This is an offline extension of the [pairing investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/clock-relationship-investigation.md),
using the same six mixed capture bundles and only their 18 action-4 observations.
No new acquisition or clock conversion is implied. The starting published research
revision is `dd4a92a7988ab848f4672fdb045e71c099ccf809`; the extension is a subsequent
working-tree change until separately committed.

## Question and method

The reported TSF-minus-SoC value varies within each run. Does that distinguish
different counter rates from unequal sampling positions? Test both counters
against the same assumed request-start to report-log host windows, using exact
rational constraints for `H = a*C+b`. Each counter has its own offset. Intersect
their feasible slope intervals to test whether one common raw-counter rate can
explain both under those assumptions.

This additionally assumes the raw counters use the same unit scale. It does not
assume a shared origin or simultaneous reads. The windows remain unproven hardware
sampling brackets. Failure would reject a conjunction of assumptions, not reveal
which one failed; success does not validate any of them.

## Results

| Run | Reported TSF-minus-SoC span (raw units) | Endpoint increment ratio minus one (ppm) | Common rate still feasible? |
|---|---:|---:|---|
| idle-mixed-1 | 193 | -7.971482 | Yes |
| idle-mixed-2 | 194 | -7.744055 | Yes |
| idle-mixed-3 | 186 | -7.676688 | Yes |
| workload-mixed-1 | 177 | -7.315998 | Yes |
| workload-mixed-2 | 178 | -7.313947 | Yes |
| workload-mixed-3 | 176 | -7.265960 | Yes |

The displayed ppm values are `(delta_TSF / delta_SoC - 1) * 1e6` across the first
and last selected reports, not calibrated oscillator-rate errors. With three
observations per run, they also do not establish a stable distribution.

**All six runs remain compatible with a common rate and different offsets** under
the assumed host windows. Thus the approximately 7.3–8.0 ppm difference in reported
increments cannot, by itself, distinguish oscillator differences, synchronization
adjustments or variable sampling skew. Conversely, common-rate feasibility is not
proof of a shared oscillator. Even a constant reported difference would not prove
simultaneity, because a constant acquisition bias is invisible to this fit.

The nominal fixed 10-QPC-ticks-per-raw-tick model fails for TSF as well as SoC in
every mixed run under the same window assumptions. Affine models remain feasible
for both. That narrows future hypotheses without producing an application mapping.

## Reproduce

```powershell
python research/clock_models/analyze_clock_pairing_hypothesis.py artifacts/QualcommCampaign-<id>/idle-mixed-1/evidence.json --compare-counters
python -m unittest discover -s tests -p test_clock_pairing_hypothesis.py -v
```

The existing default SoC-only CLI behavior is preserved. The new option validates
the complete bundle first and returns exact rational slope intersections and
reported increment ratios. Conversion and simultaneous-sampling qualification
remain false and external uncertainty remains null. Existing size and exit-code
limits apply. No output file is written by the CLI.

Three new synthetic regressions cover nonconstant paired differences with a
feasible common rate, incompatible conditional rates, and malformed/stale inputs.
All eight pairing tests pass. The CLI was then run against all six complete saved
bundles; the full local suite passes 72 tests with the owned driver fixture.
Independent review found no actionable defect in the interval-intersection math.

## Practical consequence

A future sampling experiment must constrain differential acquisition skew more
tightly and establish event identity/clock units. Extending the observation span
alone is insufficient if resynchronization or sampling bias can change during it.
Do not use these ppm values as holdover uncertainty or as a rate correction in
`userspace-clock`. Keep event-time acquisition, counter rate and clock offset as
separate quantities until the missing semantics are measured or documented.
