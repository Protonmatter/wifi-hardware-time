# Gate 1 reopening: offline work package

This package specifies the evidence and reference design needed to reconsider
microsecond-class acquisition on the recorded Windows/Qualcomm target. It
prepares a vendor request and an engineering review; it does not reopen Gate 1,
authorize an experiment, enable a provider or change the conditional clock results.

Package ID: `WHT-G1-2026-10-22`, revision 1. Prepared 2026-10-22 against merged
main `2bca0627fdd215608cb40a84216ad9d3a6bbef10` (PR #15). This is a source pin,
not evidence of the currently installed adapter, driver or running firmware.

## Deliverables and order of work

| Deliverable | Consumer | Required result |
|---|---|---|
| [Qualcomm/OEM evidence request](qualcomm-oem-evidence-request.md) | OEM support owner and Qualcomm driver/firmware engineering | A source-referenced answer to Q01-Q13, including explicit unknowns and unsupported operations |
| [AP-side reference design](ap-reference-design.md) | Measurement and Windows timing engineers | A reviewed independent reference chain, clock/event identities and a complete uncertainty ledger |
| [Acceptance criteria](acceptance-criteria.md) | Evidence reviewer and experiment approver | An evidence-linked decision for each criterion; unfilled or unsupported fields remain blocking |
| [Machine-readable dossier and validator](machine-readable-dossier.md) | Offline evidence preparer and reviewer | Versioned JSON, source/hash/locator reviews, cutoff and ledger checks, synthetic regressions; qualification flags remain false |

First review the [merged feasibility gates](../microsecond-feasibility.md) and
[replacement-path assessment](../replacement-timestamp-acquisition.md). Use the
request as a prepared document; no recipient address is assumed and nothing has
been sent. A vendor reply is evaluated offline before any operational request.

## Fixed boundaries

- Objective remains plus or minus 10 us relative to `ap_tsf`, under idle and load,
  for one explicitly pinned adapter/driver/firmware/host/AP scope. UTC, other
  stations and system-clock discipline are separate claims.
- All five baseline paths remain unqualified. The baseline still returns
  `killed_at_gate1_no_qualified_capture_path` and `physical_bound_proven: false`.
- Settled median half-widths around 133-164 us and the approximately 127 us floor
  remain conditional uncertainty estimates. Do not alter the 200 ppm prior,
  screening window or jump allowance to satisfy the new objective.
- The prior private campaign remains quarantined. Nested IHV controls, factory
  test, packet-log activation, reset, roam and suspend retain their existing
  deferred or preparation-only status. A document does not grant access to them.
- No hardware experiment, adapter query, AP command, vendor execution, deployment,
  trace capture, clock adjustment or radio/network timing acquisition is part of this work.

## Decisions and owners

These are review labels used only by this package, not new evaluator statuses.

| Review outcome | Meaning | Decision owner |
|---|---|---|
| Blocked | Evidence, supported access, a bound or an ownership/lifecycle rule is missing | Evidence reviewer records exact missing item and owner |
| Dossier ready for experiment review | Offline contract, reference design and proposed limits are coherent; no acquisition capability is asserted | Driver/OEM owner, reference engineer and evidence reviewer sign their respective sections |
| Candidate evidence ready for Gate 1 review | A separately authorized future acquisition has produced the complete attributed records and bounds | Evidence reviewer checks the original records and scope before a human gate decision |

Gate 1 needs actual evidence for its four capture properties. Paper readiness
does not establish freshness or physical pairing. Gate 2 reference/budget and
Gate 3 accuracy remain separate even if a capture path is eventually accepted.
The human user's explicit operational authorization is a separate final gate;
these role signoffs cannot substitute for it.

Publication mode is part of the future claim: immediate timestamps cannot use
later-arriving candidate observations, while settlement requires a declared
evidence cutoff and finite return deadline. Request ledgers also keep host
timeouts separate from confirmed source completion and unresolved ownership.
See the [acceptance criteria](acceptance-criteria.md) for the conservation rule,
intake limitations and authored counterexamples.

## Offline review procedure

1. Save vendor material in approved private storage. Record source hashes,
   access restrictions, applicability and the Q01-Q13 answer matrix. Do not place
   proprietary schemas, raw traces or binaries in public Git.
2. Map each claim to a precise source location and to the acceptance IDs. An
   attachment name, product feature name or successful getter alone is insufficient.
3. Complete the AP design interface records and budget ledger. Record all
   unknowns, including missing physical access and Windows reference-to-QPC support.
4. Record the review outcome, outstanding owner/action pairs and a dated decision
   dossier. If an operation is proposed later, complete every future-run limit
   before asking the user to authorize that exact operation.

For saved Windows NIC/QPC tuples, use the existing
[intake contract](../replacement-timestamp-acquisition.md#offline-evidence-intake).
The auditor only checks file/record structure and supplied assertions. Its exit 0
is not Gate 1 acceptance, and its flags must remain false. AP, reference and
exchange records use the [separate dossier format](machine-readable-dossier.md);
do not relabel them as Windows cross-timestamp tuples to fit the existing schema.

Rollback for the document package removes its documents and added navigation
lines, then regenerates the knowledge index. The dossier implementation has its
own [removal scope](machine-readable-dossier.md). There is no endpoint
or runtime state to restore. Commit, publication and sending the request are
separate actions from preparing it.
