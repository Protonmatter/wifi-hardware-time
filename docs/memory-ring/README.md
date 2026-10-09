# Reading the driver's memory log

The driver keeps a circular diagnostic log before sending messages to Windows tracing. Inspection found internal copy and dump paths, but no safe live reading interface. An offline model also showed that matching copies need not contain finished records. These findings guide further research; they do not demonstrate live corruption or clock accuracy.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Maintained reading guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__memory-ring__README.md).
<!-- /research-history -->

A ring is a circular buffer that overwrites old entries. A getter is an interface that returns data to a caller. Static findings come from inspecting driver files; model results come from simulated operation order. See the [glossary](../glossary.md) for related terms.

| Read | Main result | Limit |
|---|---|---|
| [MLO cache and native symbol search](mlo-cache-and-symbol-search.md) | Reference schema matches selected cache stores; callback precedes update; identical public SYS located | No independent reader or matching PDB recovered; live timing and owned export remain unqualified |
| [Packet-log producer trace](packetlog-producer-trace.md) | HTT message, subscription and callback traced into the binary log; separate MLO offset-cache lead | No complete management-event schema, runtime binding or safe publication contract |
| [Packet-log return path](packetlog-return-path.md) | Binary packet-log copy connected to the IHV response bridge | Different buffer from the TSF diagnostic log; full-event contents, snapshot safety and live invocation remain unqualified |
| [Timing boundaries and copy model](timing-boundary-investigation-2026-10-03.md) | Consumers narrowed to diagnostic/recovery paths; receive timestamp fields located | No safe getter, live corruption measurement, complete-copy guarantee or packet timestamp export |
| [Unmatched reports and the original ring lead](unmatched-tsf-and-memory-log.md) | Extra reports changed cached values; a pre-tracing memory copy exists | Historical source-attribution lead, superseded by later scan and boundary work |
| [Passive validation and retrieval follow-up](../acquisition/passive-and-retrieval-validation-2026-10-03.md) | One passive live run passed; log-saving callers narrowed | No ring read or performance measurement |
| [Controlled scan results](../acquisition/scan-tsf-results-2026-10-03.md) | Extra reports recurred after three scans | All three trials failed the four-second completion profile |

The offline inspector and finite model are in
[research/memory_ring](../../research/memory_ring/). Private acquisition remains
quarantined. [Lifecycle testing](../acquisition/lifecycle-qualification-preparation.md)
is preparation only; these documents do not authorize reset, suspend, roaming or a diagnostic dump.
