# Gate 1 reopening acceptance criteria

Use this checklist to reject incomplete evidence and distinguish preparation
from qualification. The current disposition is blocked: no new vendor reply,
fresh capture, independent AP reference or physical uncertainty budget was
obtained for this package. No criterion below is marked met by writing it down.

Acceptance ID: `WHT-G1-AC-1`, [package revision 1](README.md). The claim remains
plus or minus 10 us against `ap_tsf`, idle and load, for a pinned scope. The
existing [feasibility gates](../microsecond-feasibility.md) remain authoritative;
this document adds review requirements, not an alternate path around them.

## Dossier review: offline work that can be accepted now

For each ID record `met`, `not met` or `unknown`, a source/hash/locator, reviewer,
date and outstanding owner/action. An unfilled entry is unknown and blocking.
The reviewer checks evidence semantics; a response label or source hash alone
cannot establish the asserted capability.

| ID | Acceptance rule | Required evidence / request cross-reference |
|---|---|---|
| D01 | Exact applicable target is identified; historical and current identities are not conflated | Q01; adapter/revision, driver hash, OS/SDK/architecture, actual firmware/boot identity or explicit blocking unknown, AP/link and power/MLO scope |
| D02 | One supported candidate route and accessible technical owner exist | Q02-Q03; ABI/package/access contract and capability/error disposition; unsupported current builds stay unsupported/unqualified until changed evidence |
| D03 | Field-level read-point, domain, validity and lifetime contract is complete | Q04, Q07-Q08, Q11; precise event definition, units/width, atomicity/rollover, token namespaces, owned copy and original record extent |
| D04 | Pairing/freshness limits are stated with evidence and explicit unknowns | Q05-Q06, Q12; maximum capture error, source age, QPC relationship and scope under idle/load; typical/median values are insufficient |
| D05 | Completeness and lifecycle can be reviewed without assuming process exit proves drain | Q09-Q10; snapshot-reconciled issued/terminal/unresolved counts, separate host timeout and export-loss metrics, bounded cancel/close, rundown and cleanup-failure behavior |
| D06 | Independent reference has a complete interface and uncertainty design | Q11-Q12 and I-AR/I-HR/I-HQ in the [reference design](ap-reference-design.md); actual physical access/support and every proposed allocation remain explicit dependencies |
| D07 | Proposed operation and private handling are bounded and reviewable | Q10, Q13; all future-run fields below filled, source restrictions, rollback, private manifest and no secrets/public proprietary material |
| D08 | Qualification flags and old evidence remain protected | No changes to the existing baseline candidates, model policy, uncertainty prior, retained-run denominators, quarantine or `physical_bound_proven` |

D01-D08 can establish only that a dossier is ready for experiment review.
With missing physical interfaces or unknown pairing/reference bounds, record the
specific block; do not use a successful synthetic fixture or offline unit test
as the missing measurement.

## Gate 1: four independent properties for one capture path

All four requirements must concern the same identified event, build, domain and
epoch. Different records proving different pieces cannot be combined without a
bounded, attributed relationship. Static documentation can define the contract;
freshness and actual pairing require retained live evidence from an operation
that was separately authorized. No such operation is authorized here.

| ID / Gate 1 property | Pass condition for future evidence | Reject / block examples |
|---|---|---|
| G1-R: known read point | Vendor/producer contract and actual records identify the captured physical/counter event, units/width, validity, atomicity and all placement/correction uncertainty | Completion time substituted for sampling; guessed PPDU word units; low/high concatenation without rollover rules |
| G1-P: bounded QPC pairing | Actual current hardware read is contained in a justified driver-side QPC bracket or a qualified latch, with complete per-sample pairing error at or below the proposed 2 us ceiling under both conditions | Application call/return brackets around an unknown cache; ISR timestamp without delay bound; equal QPC endpoints interpreted as zero error; residual fit used as a bound |
| G1-F: fresh acquisition | Source-acquisition and availability evidence, sequence/token rules and hidden-age limit show the admitted event is new and within the approved expiry at use | Cache age unknown; timestamp unchanged/changed without an attribution proof; arrival time relabeled capture time; replay cannot be distinguished |
| G1-A: correct attribution | Original event/request identity is mapped to the selected interface/link, counter and firmware epoch; original bytes and complete owned export support it, with loss/duplicates/late events accounted | Host-only ticket assumed to be firmware token; foreign, duplicate or wrapped ID matched to the next request; temporary pointees retained past cleanup |

The 2 us pairing ceiling is a proposed allocation for this work package, not a
changed evaluator default or an observed capability. The simple bracket half-width
is `(QPC2-QPC1)*1,000,000/(2*QPC_frequency)`; extra capture uncertainty must also
fit. Equal endpoints need a separate qualified paired-capture analysis; the
existing ordinary-bracket auditor intentionally blocks them for further review.

Over-limit/stale/invalid records must remain visible and produce unavailable
results. A route with admission filtering can be considered only for its declared
admitted-event scope; it cannot claim continuous service from a few narrow
brackets. Report valid counts/issued counts and maximum unavailability by session
and condition. Any coverage, latency or continuous-service claim needs its own
predeclared numerical acceptance requirement; this package invents no such SLA.

G1-P and G1-F do not follow from D04 paperwork alone. Passing Gate 1 would support
the explicitly reviewed capture capability only. It would not qualify the AP
mapping, packet timestamp delivery, system-clock discipline or physical accuracy.

## Required future-run profile: no blanks before authorization

This is an operation-review form, not an executable campaign. Values are currently
unselected because the vendor route, rate limit and reference hardware are unknown.
Every field must have a concrete value and evidence owner before the user is
asked to authorize the exact run. No default polling rate, duration or side effect
is inferred from this document.

| Required field | What must be frozen before acquisition |
|---|---|
| Scope and source pins | Hardware/driver/actual firmware/host boot/AP/link, collector source/build/config hashes, reference identity/calibration, UTC versus monotonic labeling |
| Run identifiers and denominators | Distinct session/request IDs and true clock epochs; intended requests per condition, finite maximum requests and wall time, snapshot cutoff, disjoint terminal/unresolved accounting and pending-at-stop policy |
| Conditions | Operational idle definition; exact CPU/network/IO workload and maximum duty/rate; no traffic generation or workload changes without explicit approval; report conditions actually achieved |
| Acquisition and admission | Supported cadence/rate cap, concurrency, hard call deadlines, timestamp point, hidden sample age, event-to-capture propagation distance/expiry for the selected mode, proposed complete pairing ceiling, unknown/zero/duplicate/reorder rules and availability scope |
| Publication and evidence cutoff | Immediate or settled output, Q_i, evidence admission cutoff, actual consumer-visible return time and finite return deadline for either mode; immediate mode has no later-evidence allowance; retain provisional outcomes and all late/unavailable results |
| Independence and validation | I-AR/I-HR/I-HQ bindings and bounds; predeclared validation events, training/holdout split, frozen algorithm/policy and static-coefficient freeze or adaptive-update provenance; reference values/residuals excluded from candidate tuning |
| Stop and cleanup | Abort on identity/epoch mismatch, unbounded/stale pairing, loss-counter failure, unknown state effect, timeout/cancel failure or reference invalidity; finite cancel/close deadlines and unresolved-ownership handling |
| Permissions and rollback | Exact target, required privileges, all state effects, separately approved restart/reset/roam if ever needed, cleanup/readback, rollback and the responsible operator; no implicit fleet targeting |

There is no required minimum sample count that can turn a finite run into a
deterministic physical bound. The chosen counts/durations must support the
declared condition/availability coverage and preserve all tails. Contractual
or independently justified upper bounds and their applicability are still needed.
A deadline or failed cleanup must stop the run and invalidate affected outputs;
killing a process must not be reported as proof of firmware drain or buffer ownership release.

## Request conservation and unresolved operations

At each recorded snapshot cutoff, reconcile every issued request exactly once:

```text
issued = completed_success + completed_failure + confirmed_cancelled + unresolved
```

Use the original request/epoch key and the source's confirmed completion or
cancellation evidence. A host deadline expiring, cancellation being requested,
collector shutdown or process exit does not establish a terminal source outcome.
Such requests remain unresolved until evidence supports a terminal transition.
Host timeout/cancel-attempt counts are separate metrics and can overlap later
completion; do not add them to this partition. Preserve the earlier as-of
snapshot when late evidence arrives, with a later snapshot recording the change.
Never reuse an unresolved token for a new operation.

Reconcile at request-ledger level before normalizing timestamps. Exported-row
loss, firmware-event loss, duplicates, foreign records and timing-invalid results
have separate reason counters; they are not additional terminal request outcomes.
One source request can produce several events or no exported event, so record
cardinality and matching rules explicitly. Unknown source counts remain unknown.
Accounting does not prove drain, successful cancellation or safe ownership release.
Keep API-call, driver-operation and firmware-event ledgers separate, with explicit
cross-layer mappings. An API error return can be terminal for the API call while
the associated firmware operation remains unresolved; their status/counts must
not be substituted for one another.

The current Windows intake schema accepts actual completed API statuses and
their tuples, not an asynchronous request ledger. Do not invent a DWORD failure
status for a pending operation, substitute zero timestamps, or treat collector
timeout as source completion. Where the source really is one API request per
attempt, retain its issued total and leave missing/unresolved rows unrepresented,
which blocks intake; attach the ledger separately. Other cardinalities or private
asynchronous event routes require an explicitly reviewed normalization contract
or a future schema extension, not relabeling as the existing Windows API route.
A real API error return is retained with its actual status; it must not be
removed merely because a lower-layer operation remains unresolved. Even fully
represented API-call counts cannot close that separate ownership/lifecycle gap.

## Gate 2 and Gate 3: separate acceptance, never inferred from Gate 1

For Gate 2, every existing term must have an applicable bound and source:
`event_placement_us`, `pairing_us`, `rate_error_times_age_us`, `asymmetry_us`,
`epoch_changes_us`, `reference_us`. The [proposed allocation](ap-reference-design.md#error-budget-proposal-and-reference-independence)
is 8 us total plus 2 us margin; actual terms are unknown and the baseline budget
does not pass. A zero term requires a justified non-applicability or fail-closed
argument, not a blank. Invalid epochs are rejected rather than assigned zero
physical jump error. Reference error includes all independent bridge/calibration
terms. Unsupported statistical-to-deterministic conversions or duplicate/omitted
subterms block the budget.
The zero epoch allocation needs evidence that every relevant transition is
detected before an affected result is admitted. An unobservable transition or a
stability heuristic cannot justify zero.

For future independent accuracy qualification, keep signed residuals and reference
uncertainty separate from model half-widths. With all earlier gates satisfied,
require `abs(A_hat(Q_i)-A_ref(Q_i)) + U_ref(Q_i) <= 10 us` for every admitted
validation event in each condition, and retain every excluded/unavailable event
in the denominator with its reason. Check the publication/evidence cutoff before
applying this guard. A settled result is labeled and evaluated at its declared
deadline; it cannot replace an immediate provisional/unavailable outcome or
hide a missed deadline. Count reference uncertainty once: it is
included in Gate 2 and in the comparison guard, not added twice to a single total.
This conservative guard is an additional human-review requirement; the current
evaluator accepts a flat residual array and does not enforce condition/session
coverage, holdout provenance or this guard automatically.

An offline evaluator pass remains consistency of supplied evidence, not physical
confirmation. Both existing software tools keep `physical_bound_proven: false`;
the intake auditor also always keeps `gate1_qualified: false`. No flags or trusted
boolean inputs are to be promoted automatically by a completed checklist.

## Intake, decision record and next handoff

Use only saved approved files for the existing intake tool. Its manifest needs
one pinned Windows scope, source hashes, four claim records, per-condition
`attempt_accounting` with source-referenced issued totals or explicit null, and
all successful/failed attempts. Unknown totals, missing records, over-limit
brackets or unresolved claims block readiness. Verify the original source
denominator and normalized-row locators manually; the auditor cannot authenticate
false totals or arbitrary vendor formats. AP/reference dossiers stay separate.
For this package, a future candidate manifest must set `pairing_limit_us` to 2
or a stricter value after reserving any additional capture error. That setting
screens bracket half-width only; human review must still check the complete
pairing error against G1-P. The checked-in synthetic example keeps its existing
illustrative limit and is not qualification evidence.

The final review record must name the package revision, source manifest/hash,
each D/G1 decision, actual scope and conditions, bounds and unknowns, references
to original attempts, publication cutoffs/return times, request-ledger snapshots,
unavailable/lost/foreign/duplicate counts, all reviewer
decisions and open owner/action pairs. State explicitly whether the outcome is
blocked, ready for experiment review, or candidate evidence ready for Gate 1 review.
Do not infer operational authorization from any of those labels.

Current handoff: send nothing and acquire nothing. Obtain reviewed vendor and
reference-interface evidence first; any future experiment requires a concrete
bounded plan and explicit user authorization. Existing conditional results and
the [baseline kill criterion](../microsecond-feasibility.md#gate-1-capture-path-with-a-known-read-point)
remain unchanged.

## Offline review counterexamples

These are authored logical examples, not captured data or timing qualification.
The tick values compare event/availability order only; they test no physical bound.
The remaining Gate 1 and reference requirements must still be proved separately.

| Example | Required review result |
|---|---|
| Event Q_i=100; a candidate observation was captured at 90 but admitted at 120 | Ineligible for immediate output at 100, even if its hindsight residual is small |
| Same observation; settled cutoff 130, consumer return 135, declared deadline 140 | Availability predicate can pass for settled output only; all other bounds/identities remain required and the immediate outcome is preserved |
| Same settled result returned at 145 with deadline 140 | Missed deadline; retain unavailable/late status, not an on-time accepted result |
| Event Q_i=100; a later observation is captured at 150 and delivered at 152 | Settled propagation must account for the 50-tick event-to-capture distance, not only the 2-tick delivery delay; eligibility also depends on the declared cutoff/deadline |
| Three API requests issued; one confirmed success and two host timeouts with no API return records | API partition is success=1, failure=0, cancelled=0, unresolved=2; API intake has two unrepresented attempts and remains blocked; firmware state is a separate ledger |
| One unresolved request later has confirmed failure | Later snapshot is success=1, failure=1, cancelled=0, unresolved=1; retain the earlier snapshot and timeout counters |
