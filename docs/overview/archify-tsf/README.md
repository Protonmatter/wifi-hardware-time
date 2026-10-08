# Persistent TSF Archify specifications

These seven editable Archify specifications explain the sampler layers, acquisition workflow, request lifecycle, time sources, timestamp sequence, clock algorithm and live/offline adapter boundary. The diagrams describe the sampler implementation tested in the 2026-10-08 smoke. They do not establish physical timing accuracy or online admission.

| View | Editable specification |
|---|---|
| System layers | [layers.json](layers.json) |
| Acquisition workflow | [workflow.json](workflow.json) |
| Request lifecycle | [lifecycle.json](lifecycle.json) |
| Time source and QPC relationship | [time-source.json](time-source.json) |
| Timestamp sequence and availability | [timestamps.json](timestamps.json) |
| Clock algorithm and settlement | [algorithm.json](algorithm.json) |
| Live and offline adapters | [adapters.json](adapters.json) |

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

Each output is a standalone interactive HTML diagram. Keep generated HTML, screenshots and machine-local receipt paths in ignored `artifacts/`. Schema, artifact and real-browser checks are distinct from visual inspection. A successful finalizer does not verify the underlying physical assumptions.

The local diagram delivery passed all four gates for every view. Lifecycle and algorithm light desktop captures were additionally inspected. Publication specifications use portable ignored output paths; their hashes are in [manifest.json](manifest.json). At original creation the sampler was uncommitted, so Archify's committed-source gate was not used to misattribute new code to the base SHA. Source file hashes for the tested implementation accompany the [measurement summary](../../acquisition/persistent-tsf-smoke-2026-10-08.json).

## Related documentation

- [First live smoke result](../../acquisition/persistent-tsf-smoke-2026-10-08.md)
- [Sampler contract](../../acquisition/persistent-tsf-sampler.md)
- [Mathematics and assumptions](../../clock-models/tsf-mathematics.md)
- [Research, implementation and testing roadmap](../persistent-tsf-next-steps.md)
