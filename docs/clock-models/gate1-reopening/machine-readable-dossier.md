# Machine-readable Gate 1 dossier and offline validator

The version 1 dossier records the [work package](README.md) in JSON and checks
saved assertions, source integrity and arithmetic. It does not accept Gate 1,
Gate 2 or physical accuracy. No adapter, AP, driver, vendor runtime or network
API is called. It does not send the OEM request or authorize an experiment.

The package remains `WHT-G1-2026-10-22`, revision 1. The input format is
`wht/gate1-dossier-v1`; the report is `wht/gate1-dossier-report-v1`.
The [JSON Schema](../../../research/clock_models/gate1_dossier.schema.json)
defines required fields, closed objects, types and ranges. The
[validator](../../../research/clock_models/gate1_dossier.py) additionally checks
cross-field rules. A generic JSON Schema pass alone does not perform those checks.

## Run against saved files

From the repository root, using Python 3.11 or later:

```powershell
python -m research.clock_models.gate1_dossier --schema
python -m research.clock_models.gate1_dossier tests/fixtures/gate1_dossier/complete-synthetic.json
python -m research.clock_models.gate1_dossier tests/fixtures/gate1_dossier/incomplete-synthetic.json
python -m research.clock_models.gate1_dossier tests/fixtures/gate1_dossier/adversarial-synthetic.json
python -m unittest discover -s tests -p test_gate1_dossier.py -v
```

The tool writes a JSON report to stdout, errors to stderr and no files. Redirect
stdout to an approved private location if saving a report. Do not publish private
paths, identifiers, source material or reports in public Git. No special privileges
are required beyond read access to the saved bundle. There are no new dependencies.

| Exit | Meaning |
|---|---|
| 0 | Supplied assertions are consistent for the selected stage; synthetic input reports `synthetic_consistency_only` |
| 2 | Well-formed input has consistency blockers; command-line usage errors also use argparse's exit 2 |
| 1 | Malformed/unreadable dossier, invalid review metadata, contradictory ledger/capture structure, unsafe source path or hash mismatch |

Every successful report includes `gate1_qualified: false`, `gate2_qualified: false`,
`physical_bound_proven: false` and `experiment_authorized: false`. The schema does
not accept input overrides for these flags. `semantic_review_ready` is true only
for consistent `retained_evidence` declarations. It means ready for human semantic
review at the declared stage, including checking whether the provenance claim is
true. It is not a decision to accept the dossier or conduct an operation.
`gate1_reviews_complete` reports whether all four supplied labels are `met`;
even a synthetic example can have complete labels without qualifying anything.

## Dossier contents and stage rules

All top-level fields are required. Use JSON `null` for allowed unknown values;
do not substitute zero, an empty string or a guessed bound. Unknowns in required
scope/plan/review assertions block consistency. Unmeasured interface and Gate 2
budget bounds can remain null at this preparation stage and are reported as such.

| Field | Content and checks |
|---|---|
| `provenance`, `stage` | `synthetic` or `retained_evidence`; `contract_review` or `candidate_evidence_review` |
| `scope` | Adapter, driver SHA-256, actual firmware, OS, host/boot, AP/epoch, link, counter domain/epoch, C/R/H clock IDs and QPC frequency; reference clock IDs cannot alias C |
| `references` | 1-256 local source IDs, each with relative `path`, lowercase SHA-256 and `kind`: `synthetic`, `retained_evidence` or `documentation` |
| `vendor_answers` | All Q01-Q13, with status `established`, `unsupported`, `unknown` or justified `not_applicable` |
| `dossier_reviews` | All D01-D08, with status `met`, `not_met` or `unknown` |
| `gate1_reviews` | G1-R/P/F/A, with status `met`, `not_met` or `unknown`; these remain human declarations |
| `interfaces` | Fixed I-CQ, I-CA, I-AR, I-HR and I-HQ directions, status, nullable bound, citations and independence declaration |
| `plan` | Finite request/duration/concurrency/cadence/call/cancel/close/return limits, idle/load definitions, operation, state effects, stop/rollback/operator, selected request-ledger layer, publication mode, model freeze policy and collector/policy artifact references |
| `budget` | Fixed proposed ceilings, separate nullable actual bounds and term-specific source/justification records |
| `ledger_snapshots` | Immutable as-of totals per condition/session/epoch/layer, source citations and separate timeout/loss/invalid counters |
| `comparisons` | Attributed event labels, source locators, raw ticks, capture brackets, availability/cutoff/return/deadline, extra capture/hidden-age bounds and admission/rejection reason |

Each review has `basis` (`contract`, `static`, `measurement`, `synthetic` or
`unknown`), `statement`, `reviewer`, ISO `reviewed_on`, `citations`, `owner` and
`open_action`. Known statuses require citations, reviewer and date. Unresolved
statuses require an owner and action. Citations contain `reference` and `locator`
(for example a page/field or JSON pointer). The tool verifies reference existence
and bytes; a human verifies that the locator exists and supports the statement.

Contract review requires the Q/D decisions, pinned scope, reference design and
bounded plan, but permits unknown G1 reviews and empty measurement/ledger arrays.
Candidate review additionally requires four met G1 labels, declared measurement
bases for G1-P/F and at least one consistently admitted comparison plus a request
ledger for each condition. Every `measurement` review basis and `measured`
interface requires a cited `retained_evidence` source. In a retained candidate
dossier, each comparison and ledger snapshot must also cite retained evidence;
documentation may supplement those citations but cannot replace the records.
Synthetic examples may use synthetic review bases and documented interfaces. Changing
only the top provenance label cannot remove synthetic-source/basis blockers.
Relabeling every field cannot authenticate the underlying evidence either.

The minimum comparison count is a consistency prerequisite, not an accuracy,
coverage or continuous-service acceptance criterion. The [acceptance criteria](acceptance-criteria.md)
still require original records, read-point/units/width/rollover/lifetime semantics,
cross-layer request/event attribution, supported access, applicable bounds and
independent human review. No default run limits or live collector are provided.

## Exact timing and budget arithmetic

QPC/raw counter values and bounds are integers; booleans, floats, zero QPC/raw
values, negative values and values beyond unsigned 64-bit are rejected. Bounds
are nonnegative integer nanoseconds; limits/frequency/rate are positive integers
when known. The ordinary-bracket format does not represent zero raw counter
values or an atomic paired latch: those require a separately reviewed contract.
JSON consumers must preserve integers above 2^53; JavaScript `Number` round trips
can corrupt evidence. All shipped fixtures exercise large QPC values.

The validator calculates conservative integer ceilings using exact rational math:

```text
half_ns = ceil((upper - lower) * 1e9 / (2 * QPC_frequency))
pairing_ns = half_ns + extra_capture_error_ns
distance_ticks = max(abs(event - lower), abs(event - upper))
age_ns = distance_ticks * 1e9 / QPC_frequency + hidden_age_bound_ns
rate_error_ns = ceil(age_ns * rate_bound_ppm / 1e6)
```

Hidden age is an additional bound beyond the stated capture bracket. The source
contract must justify that interpretation and avoid omitting or double-counting
the same subterm. This distance is to the event being estimated, not delivery
delay. Unknown extra capture/hidden age/rate, equal bracket endpoints, epoch
mismatch, missing ledger or pairing/rate over the proposed ceilings block an
asserted admission. A deliberately rejected record stays visible with its reason
and computed issues. Duplicate event IDs and contradictory capture order are
malformed even for rejected rows.

Immediate mode requires availability no later than evidence cutoff, and cutoff
no later than event. Settled mode allows later observations but requires cutoff
at/after event, cutoff no later than return, return by the declared deadline,
and deadline within the plan's maximum return latency. Both modes require return
and deadline at/after event. A static model requires training frozen by both
event and cutoff; adaptive mode instead records a frozen policy hash and no
static freeze timestamp. Reference values must be declared excluded from the
candidate model. Actual adaptive update provenance and hidden tuning inputs
still require source review.

`plan.artifact_references` contains required `collector_source`, `collector_build`,
`collector_config` and `policy` reference IDs. Each must resolve to a hash-verified
saved file; null is an explicit blocker. The policy artifact's verified SHA-256
must equal `plan.policy_sha256`. These pins apply to static and adaptive models.
They identify bytes for review, not proof that a collector used the pinned build,
configuration or policy. Reviewers still verify build/source correspondence,
runtime provenance, the declared freeze time and the absence of hidden tuning.

The six proposal terms remain 2000/2000/1000/1000/0/2000 ns (8000 ns plus 2000 ns
margin). Changing that proposal is rejected for this package revision. Supplied
actual bounds must fit each proposed ceiling and the 10000 ns target; known
terms require citations and justification, including zero epoch-change error.
Known pairing/rate terms cannot understate arithmetic from admitted comparisons.
Any unknown term keeps `actual_total_ns` null and `actual_within_target` false.
An arithmetic total within target does not establish a physical bound or a
complete, independent uncertainty budget. Interface bounds and subterm coverage
are not automatically combined or authenticated.

## Request accounting and integrity limits

At every supplied snapshot with known counts:

```text
issued = completed_success + completed_failure + confirmed_cancelled + unresolved
```

Snapshots must increase in QPC order for each condition/session/epoch/layer.
Issued/terminal/timeout/loss/rejection counters cannot decrease, including across
intervening null snapshots: each known value is compared with the last known
value for that counter and ledger key. Final timeout counts must be known.
Final unresolved
operations and unknown/nonzero export or firmware loss block consistency.
Duplicate/foreign/timing-invalid reason counters must be known; positive counts
remain visible without automatically rejecting a declared admitted-event scope.
Their correct rejection and relationship to original records still need review.
Earlier unresolved snapshots remain in the report when
a later completion resolves them; host timeouts remain separate overlapping
metrics. The matching ledger's final snapshot must cover a comparison's return,
and a zero-issued source ledger cannot support an asserted admitted comparison.
Final issued totals are summed across sessions only for the selected
`request_ledger_layer` when checking the per-condition request cap. Snapshots and
API/driver/firmware layers are not added together. Comparison counts are reported
separately; one request can produce several or no events.

This version checks aggregate arithmetic, not original per-request transitions,
cross-layer cardinality, cancellation confirmation, rundown, safe ownership
release or exact source denominators. It records duration/concurrency/cadence and
cleanup limits but cannot prove they were obeyed from aggregate snapshots.
Counter/ID reuse and hidden dropped records require original-record review.
It does not compute residuals, enforce a train/holdout split or implement the
Gate 3 reference guard. None of those can be inferred from exit 0.

The manifest must be an ordinary nonsymlink UTF-8 file, at most 4 MiB, with
unique object keys and finite numbers. Arrays are capped at 10000 entries each.
Sources must be ordinary local files inside the manifest's directory tree;
absolute paths, URLs, traversal and alternate data streams are rejected, as are
symlink/junction targets outside the tree. Files are hashed in streaming reads.
Internal source symlinks are allowed if their targets remain inside the bundle.
Use approved storage on a quiescent filesystem: concurrent replacement and
malicious filesystem races are outside this validator's integrity guarantee.
Source size/runtime are not capped; run only on approved local bundles.
Hashes prove byte identity, not authenticity, source completeness, hardware
behavior, units or reviewer truth. The embedded schema checker implements only
the shipped schema's closed subset and never retrieves remote schema resources.

All checked-in material is authored fiction. The complete fixture demonstrates
consistency with unknown physical budget terms; incomplete and adversarial
fixtures demonstrate blockers. No retained capture or vendor response was added.
The existing Windows tuple auditor and feasibility evaluator are unchanged;
there is no automatic dossier-to-evaluator conversion. Baseline Gate 1 remains
killed and the conditional sub-millisecond results retain their existing meaning.
The synthetic policy file and collector artifact references illustrate pinning;
they do not contain a functional collector or a qualified timing policy.

Rollback is removal of the new module/schema/test/fixtures and added documentation
links, followed by authored-index regeneration. There is no endpoint state to
restore. Publication, vendor contact and future hardware operations remain
separate actions.
