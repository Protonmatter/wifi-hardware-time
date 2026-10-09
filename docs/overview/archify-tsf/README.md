# Persistent TSF diagrams

These seven rendered Archify views explain the sampler layers, acquisition workflow, request lifecycle, time sources, timestamp sequence, clock algorithm and live/offline adapter boundary. The layers describe the sampler implementation tested in the 2026-10-08 smoke. The algorithm view additionally reflects the reviewed rounding-inclusive uncertainty and settlement-v2 overlap policy. They do not establish physical timing accuracy or online admission.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Maintained reading guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../../research-history/README.md) · [Timeline](../../research-history/timeline.md) · [Previous version](../../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__archify-tsf__README.md).
<!-- /research-history -->

| View | Rendered preview | Editable specification |
|---|---|---|
| System layers | [SVG](previews/layers.svg) | [layers.json](layers.json) |
| Acquisition workflow | [SVG](previews/workflow.svg) | [workflow.json](workflow.json) |
| Request lifecycle | [SVG](previews/lifecycle.svg) | [lifecycle.json](lifecycle.json) |
| Time source and QPC relationship | [SVG](previews/time-source.svg) | [time-source.json](time-source.json) |
| Timestamp sequence and availability | [SVG](previews/timestamps.svg) | [timestamps.json](timestamps.json) |
| Clock algorithm and settlement | [SVG](previews/algorithm.svg) | [algorithm.json](algorithm.json) |
| Live and offline adapters | [SVG](previews/adapters.svg) | [adapters.json](adapters.json) |

## Rendered views

These images render directly in GitHub and Markdown viewers. They require no JavaScript, iframe, external font or diagram plugin. Select an image to inspect it at full size. The editable JSON remains the source of truth.

### Persistent TSF: system layers

![Persistent TSF: system layers](previews/layers.svg)

**Ownership**

- The controller owns campaign exclusion and unfinished-run protection.
- The worker owns device, event, OVERLAPPED and buffers until completion.

**Evidence boundary**

- These views describe the sampler measured on 2026-10-08; the result summary identifies its source hashes.
- Recorded acquisition reaches the clock models through offline screening. Online admission is later work.

### Persistent acquisition: guarded workflow

![Persistent acquisition: guarded workflow](previews/workflow.svg)

**Cadence**

- Persistent mode requests one-second spacing by default; 0.5 s is the minimum.
- Report waits, identity checks and processing remain in achieved request gaps.

**Long waits**

- Heartbeat and observer pumping continue while waiting for a slot.
- Identity checks use a 30-second monotonic timer; stalled-owner lease is 60 seconds.

### Sampler lifecycle: completion is the release boundary

![Sampler lifecycle: completion is the release boundary](previews/lifecycle.svg)

**Sticky failure**

- A deadline or cancellation attempt fails the run even if completion later succeeds.
- ERROR_NOT_FOUND, WAIT_TIMEOUT and ERROR_IO_INCOMPLETE do not prove terminal completion.

**Owned resources**

- Finite polls are at most 50 ms. Pending operation lifetime can be indefinite.
- No close, exception or disconnect may release unresolved buffers, event or device.

### Time sources: TSF observation and QPC relationship

![Time sources: TSF observation and QPC relationship](previews/time-source.svg)

**What the clock means**

- The result estimates the station TSF at an application event QPC.
- QPC frequency converts host ticks; TSF values are interpreted in microseconds.

**Keep the events separate**

- I/O completion is not a firmware sampling fence. Report delivery is not the original report timestamp.
- Capture-inside-window, rate and continuity are assumptions. No UTC or measured station-to-AP accuracy is established.

### Timestamp sequence: sampling, completion and availability

![Timestamp sequence: sampling, completion and availability](previews/timestamps.svg)

**Availability rule**

- A = max(D, C, U + one QPC tick). D is receipt of the delay record completing the group.
- This is the existing replay boundary; later queueing, IPC and ingestion latency are not added.

**Ordering is illustrative**

- The drawing separates events and is not a measured timeline.
- Terminal I/O and diagnostic report delivery may occur in another order. The controller retains its report wait.

### Clock algorithm: preserve event, bound now, settle later

![Clock algorithm: preserve event, bound now, settle later](previews/algorithm.svg)

**Causal model**

- Nominal TSF rate is 1,000,000 / QPC_Hz microseconds per tick; prior is +/-200 ppm.
- low(Q) = max(T - a*(U+1)) + a*Q; high(Q) = min(T+1 - b*L) + b*Q.
- Acquiring before a usable sample; stale when half-width plus 0.5 us reaches 1,000 us; conflicts latch invalid.

**Settlement and scope**

- A later available sample brackets the preserved event with an earlier sample.
- Intersect bracket envelopes and any overlap available by the settlement cutoff. Affine estimate additionally assumes constant rate.
- These are conditional offline replay results; numerical ingest is not online acquisition admission.

### Live and offline adapters: shared contract, different evidence

![Live and offline adapters: shared contract, different evidence](previews/adapters.svg)

**Live adapter**

- One device handle and fresh per-request buffers/event. At most one outstanding IOCTL.
- Requires exact profile, campaign guard, observer readiness and explicit execution.

**Offline adapter**

- The same core receives a fake kernel, identity validator, clock and controller.
- Tests establish software decisions and resource ownership; they do not establish firmware drain or accuracy.

## Render and verify

The optional renderer is [Archify](https://github.com/tt-a1i/archify), version 3.0.1, pinned to `73aaa0696e8f72c232ea710e6fa94fd953f3e773`. Its upstream license is MIT. No renderer/runtime code or new runtime dependency is vendored into this repository. Obtain that exact tool separately, then set its CLI path explicitly. From this repository root:

```powershell
$ArchifyCli = '<ARCHIFY_CHECKOUT>/archify/bin/archify.mjs'
$diagrams = Get-Content docs/overview/archify-tsf/manifest.json -Raw | ConvertFrom-Json
foreach ($diagram in $diagrams.diagrams) {
    $specification = 'docs/overview/archify-tsf/' + $diagram.slug + '.json'
    $output = 'artifacts/archify-tsf/' + $diagram.slug + '/' + $diagram.slug + '.html'
    node $ArchifyCli finalize $diagram.type $specification $output --quality showcase --json
    if ($LASTEXITCODE -ne 0) { throw ('Archify validation failed: ' + $diagram.slug) }
}
```

Each output is a standalone interactive HTML diagram. Keep interactive HTML, screenshots and machine-local receipt paths in ignored `artifacts/`. The compact script-free SVG previews under `previews/` are checked in for direct viewing. Schema, artifact and real-browser checks are distinct from visual inspection. A successful finalizer does not verify the underlying physical assumptions.

The original local interactive diagram delivery passed all four gates for every view. Lifecycle and algorithm light desktop captures were additionally inspected. Publication specifications use portable ignored output paths; their hashes are in [manifest.json](manifest.json). At original creation the sampler was uncommitted, so Archify's committed-source gate was not used to misattribute new code to the base SHA. Source file hashes for the tested implementation accompany the [measurement summary](../../acquisition/persistent-tsf-smoke-2026-10-08.json).

## Publish portable previews

From the repository root, use the same pinned external Archify checkout:

```powershell
python research/evidence/publish_archify_previews.py --write --archify-cli $ArchifyCli
python research/evidence/publish_archify_previews.py --check
python -m unittest discover -s tests -p test_archify_previews.py -v
```

Default/`--check` is read-only. `--write` verifies the renderer revision and specification hashes, regenerates all seven diagrams, runs Archify artifact/composition checks, materializes their classic light-theme paint, removes inactive keyboard/button semantics, and updates SVG/hash files only after all conversions succeed. It uses Python 3.11+, Node and the explicitly supplied Archify checkout; no browser, network call, elevation or installed plugin is needed. Exit 0 means success, 1 means validation/I/O/render failure, and 2 means invalid arguments. Review or revert the generated SVG and manifest diff to roll back a publication.

This exporter supports the classic semantic styles used by these specifications. It retains geometry, labels, evidence caveats and source digests; animations, focus controls and interactive theme changes remain in the optional HTML renderer. The committed previews have intrinsic dimensions and concrete paint so a Markdown image does not depend on its surrounding page CSS. CI checks preview presence, source/preview hashes, intrinsic size, embeds and absence of external or executable SVG content.

## Related documentation

- [First live smoke result](../../acquisition/persistent-tsf-smoke-2026-10-08.md)
- [Sampler contract](../../acquisition/persistent-tsf-sampler.md)
- [Mathematics and assumptions](../../clock-models/tsf-mathematics.md)
- [Research, implementation and testing roadmap](../persistent-tsf-next-steps.md)
