# Retained validation-source archive

This archive preserves older authored scripts as historical evidence, not as tools to run today. Some predate current safety and result checks. Each text snapshot has recorded hashes and transformations; use the maintained research folders for current commands and the linked reports to understand what the historical experiments actually demonstrated.

**Key terms:** A source snapshot is a saved code version. Hashes identify exact bytes. Redaction removes private details; a redacted snapshot may explain an experiment without being an executable reproduction. See the [glossary](../../glossary.md).

This archive contains **36 authored source snapshots** retained from local testing,
validation and analysis. It is historical evidence, not an additional set of
supported executable entry points. Every source is stored with a final `.txt`
extension so normal Python discovery, PowerShell checks and native builds do not
execute/import/compile it.

Do not rename these files and run them as current tools. Some send private requests
implicitly, have unbounded cancellation drains, restart an adapter, or predate
the current result-validation rules. Current commands are in the
[execution catalog](../../overview/validation-execution-catalog.md).

## Provenance and transformations

[manifest.json](manifest.json) records original-byte SHA-256, original size,
archived-byte SHA-256, normalization, redactions, and any normalized-equivalent
maintained source. Source labels are relative logical locations, not private
machine paths. All snapshots are UTF-8 without BOM and use LF line endings;
they are not generally byte-identical to the original Windows files.

Six sources needed explicit transformations: personal workspace/Python paths,
local interface-index defaults/examples, or an instruction-byte signature in a
historical guard were replaced by named placeholders. Those copies are not
executable reproductions. The original hashes remain evidence pointers, not
authentication or an execution claim. Build/API constants, driver/DLL hashes,
provider GUIDs and clearly synthetic test selectors were retained.

The third-party `cnss2-qmi-reference.c` is listed as excluded. No vendor binary,
firmware, raw disassembly, ETL, packet data, profile snapshot, identity JSON or
kernel/request-pointer output is included. Those materials remain local.

## Execution status is separate from retention

The latest passive qualification runner and campaign launcher are tied to their
actual runs by the published qualification/quarantine reports and local launch
receipts. Other snapshots support earlier documented work, but the existence of
a source file alone does not prove it was executed, compiled into a particular
binary, or passed a hardware experiment. Use the report's stated revision and
validation scope rather than treating all historical sources as interchangeable.

Some shell/Python snippets were executed interactively and did not exist as saved
script files. Their operations are recorded in the execution catalog and promoted
offline tools. A reconstructed command recipe is labeled as such; it is not an
invented original script or a claim of byte-for-byte replay.

## Known archival hazards

- Early `private_getter.py` and `latch_probe.py` can enter an unbounded overlapped
  cancellation drain. Do not run them to bypass current admission/quarantine.
- Early FTM helpers predate the explicit execution gate and measurement-count
  checks. Earlier zero-count acceptance is a historical defect, not qualification.
- Capture and launcher scripts can execute when invoked. The reset harness is
  disruptive and its recovery helper persists private profile/interface data.
- Topology and callback tools write private identifiers or possible request
  pointers. Publishing source does not authorize publishing their outputs.
- Historical tests can require a locally owned driver fixture and local paths.
  They are not added to CI by this archive.

The normal test suite checks the archived-byte hashes and containment. It does
not execute these historical files or certify their historical behavior.
