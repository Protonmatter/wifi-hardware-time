# Collecting and qualifying clock reports

These documents explain how clock reports are collected, checked and rejected when their source is uncertain. An earlier campaign passed, but the later private campaign remains quarantined. Three scans reproduced extra reports and all missed their completion deadline. Passive collection success does not qualify accurate clock conversion or authorize another private run.

Start with the current results, then use the plans and historical reports for context. TSF is the Wi-Fi timing counter; quarantine means further private requests are blocked. See the [glossary](../glossary.md) for other terms.

| Question | Read | Evidence and limit |
|---|---|---|
| Why is private collection blocked? | [Quarantined campaign](private-campaign-2026-10-03-quarantine.md) | Live unmatched reports; rejected capture and retained quarantine |
| Can ordinary scans produce similar reports? | [Scan results](scan-tsf-results-2026-10-03.md) | Three observed patterns; all three failed the four-second profile |
| Does passive collection shut down cleanly? | [Passive validation](passive-and-retrieval-validation-2026-10-03.md) | One repaired live run; no private requests or safe ring getter |
| What should the research investigate next? | [Private acquisition plan](private-timing-acquisition-plan.md) | Proposed paths and requirements; no rearm authorization |
| What is prepared for connection or power changes? | [Lifecycle preparation](lifecycle-qualification-preparation.md) and [offline model](lifecycle-matrix.md) | Preparation only; no restart, suspend or roaming execution |
| Why do reports arrive slowly? | [Latency audit](private-acquisition-latency.md) | Saved-capture measurements and a proposed experiment |
| What did the original campaign establish? | [Completed campaign](acquisition-campaign-2026-10-02-results.md) | Historical collection success; no calibrated accuracy |
| How do the guarded procedures work? | [Campaign runbook](live-acquisition-campaign.md) and [experiment guide](experiments.md) | Reproduction details subject to the current quarantine |
| How were the observer and scans prepared? | [Observer qualification](observer-passive-qualification-2026-10-03.md) and [scan plan](scan-comparison-plan.md) | Earlier prerequisite checks and declared experiment bounds |

The maintained collectors, admission checks and offline analyzers are in
[research/acquisition](../../research/acquisition/). The [memory-ring investigation](../memory-ring/README.md)
covers possible alternate retrieval paths. The [qualification ledger](../overview/gap-closure-ledger.md)
keeps the current capability limits together.
