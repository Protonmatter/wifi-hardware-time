# Wi-Fi Hardware Time in Archify Studio

> **Archive — not current operating instructions.** Historical documentation at [da4f55e48a36](https://github.com/Protonmatter/wifi-hardware-time/commit/da4f55e48a368f59ed68ee4427013a83b5c06070). Relative links are rebased for reading. [Exact original bytes](../originals/docs__overview__archify-studio__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

This ten-view evidence atlas uses [Archify Studio redesign](https://github.com/Protonmatter/archify-studio-redesign) to connect the persistent sampler, conditional clock models and remaining hardware gates to exact source excerpts. Every component and relationship has an evidence state and source citation. The portable HTML includes search, a source inspector, open questions, Paper/Ink themes and SVG export; the previews below render without JavaScript.

The atlas describes research revision `e9d71b84365122ff2640e240b20fc1dbb834388a`, including the October 8 corrections. Its renderer is pinned to `59225b55d66a922f26b5d57fa49eae5415be6b22`. [manifest.json](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/manifest.json) records both revisions, the editable model hash and the exact selected source hashes. The existing [seven upstream Archify views](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-tsf/README.md) remain separate maintained diagrams.

## Open the interactive atlas

**[Interactive atlas — index.html](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/index.html)** includes all ten diagrams, source snapshots, search, evidence inspection and exports in one portable file; its current byte size and digest are recorded in the manifest. No installation, online dependency or local server is required to use the saved file.

On GitHub, open the file above, select **Download raw file**, then open the saved `index.html` in a browser. GitHub displays HTML source in its repository viewer; the README itself does not execute this application. For direct viewing inside GitHub, use the SVG previews below. GitHub Pages hosting is not configured by this change.

The HTML and SVG artifacts preserve Archify's embedded MIT copyright and permission notice. That notice applies to the included renderer; it does not select a distribution license for the rest of this repository. The atlas embeds only the 16 selected public authored sources listed in the manifest. It makes no automatic network requests and contains no telemetry or private captures.

## Read the diagrams

| View | Question | Preview |
|---|---|---|
| System overview | How do observations reach a conditional timestamp? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/overview.svg) |
| Evidence and next gates | What do tests, a live smoke and replay each establish? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/qualification.svg) |
| Acquisition | Who owns admission, scheduling and retained evidence? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/acquisition.svg) |
| I/O lifetime | When can an operation release its resources? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/lifecycle.svg) |
| Adapter boundary | What do injected tests and a live backend share? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/adapters.svg) |
| Time domains | How do station TSF, QPC and AP/UTC relate? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/time-domains.svg) |
| Availability | How do L, U, C, D and A differ? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/availability.svg) |
| Producer gaps | Which byte-return and timing connections remain open? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/producer-routes.svg) |
| Causal estimate | Why check the frozen model before incorporating a sample? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/causal.svg) |
| Two-phase time | How is an event preserved while settlement narrows its interval? | [SVG](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/settlement.svg) |

### System overview

![System overview](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/overview.svg)

### Evidence and next gates

![Evidence and next gates](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/qualification.svg)

### Acquisition

![Acquisition](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/acquisition.svg)

### I/O lifetime

![I/O lifetime](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/lifecycle.svg)

### Adapter boundary

![Adapter boundary](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/adapters.svg)

### Time domains

![Time domains](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/time-domains.svg)

### Availability

![Availability](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/availability.svg)

### Producer gaps

![Producer gaps](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/producer-routes.svg)

### Causal estimate

![Causal estimate](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/causal.svg)

### Two-phase time

![Two-phase time](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/previews/settlement.svg)

## Evidence limits

Observed, software-tested, static, documented and unresolved are separate claims. Every arrow describes the cited relationship; an animated arrow is not observed traffic. The selected public text contains no private captures or vendor binary material. Studio embeds complete selected source files, so the source allowlist must be reviewed whenever it changes.

The retained smoke summary is 139 recorded requests, 138 offline-screened samples, 92.862589% conditional tracking coverage and 297/297 settled event-grid points. These are the corrected offline results of the original capture. The atlas performs no new acquisition and does not promote those measurements to causal online admission, physical AP/UTC accuracy, firmware-drain qualification or a production clock service. Original measurement source pins remain in the cited reports.

The packet format calls these source files **snapshots**. Byte comparison against the declared research Git blobs is additional provenance evidence; it does not prove that the code ran on hardware. The original source hashes and evidence status are independent of diagram geometry.

## Build a portable atlas

Requires Python 3.11+, Node.js 22+, and an accessible checkout of the pinned Studio repository. The build uses its existing standard-library tools and adds no dependency to this research repository. No elevation, adapter access, telemetry, network service or vendor execution is needed. Obtain the repositories separately, then run locally.

Use a clean source checkout at the declared research revision when reproducing this edition. In particular, the atlas cites the original README; do not silently substitute the later README containing this navigation link. Run from the Wi-Fi research checkout, replacing the two explicit tool/source paths:

```powershell
$Studio = '<ARCHIFY_STUDIO_CHECKOUT>'
$SourceRoot = '<CLEAN_WIFI_CHECKOUT_AT_e9d71b84365122ff2640e240b20fc1dbb834388a>'
$Packet = Join-Path (Get-Location) 'artifacts/archify-studio/packet'
$Html = Join-Path (Get-Location) 'artifacts/archify-studio/index.html'

git -C $Studio rev-parse HEAD
git -C $SourceRoot rev-parse HEAD
python "$Studio/studio/tools/package_atlas.py" --model docs/overview/archify-studio/atlas-model.json --source-root $SourceRoot --out $Packet
if ($LASTEXITCODE -ne 0) { throw 'Atlas packaging failed' }
node "$Studio/studio/build.mjs" --atlas $Packet --out $Html
if ($LASTEXITCODE -ne 0) { throw 'Atlas build failed' }
python research/evidence/apply_studio_export_policy.py --html $Html --write
if ($LASTEXITCODE -ne 0) { throw 'Static export policy failed' }
```

Verify both printed revisions against [manifest.json](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/manifest.json) before building. An existing identical complete packet returns `unchanged`; a changed destination is refused, so choose a fresh packet directory for a new edition. Package/build success exits 0; invalid source/model or I/O/build failures are nonzero. The JSON model and packet are UTF-8, and original source bytes are retained with SHA-256 digests.

The pinned renderer receives one repository-local packaging correction from [static-export-policy.js](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/static-export-policy.js). It gives exported SVGs image semantics and strips inactive button labels, focus attributes and control state from every element, including nodes that were never selected. It also removes graph pointer-cursor and hover/focus highlighting rules from the export's cloned stylesheet. Interactive HTML controls and styling retain their behavior. The helper checks without writing by default, applies only with `--write`, and rejects unfamiliar or partial exporter patches before writing. Exit 0 means matched/applied, 1 means drift or invalid input/I/O, and 2 means invalid arguments. Rebuilding the pinned upstream HTML restores the pre-policy artifact. No new dependencies, permissions or hardware operations are needed.

Open the generated HTML directly in a browser. If an embedded browser blocks local file URLs, use the optional loopback-only preview and stop it with Ctrl+C:

```powershell
node "$Studio/studio/serve.mjs" --file $Html --port 43136
```

## Edit and validate

Edit [atlas-model.json](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/atlas-model.json), preserving source IDs and one-based citation bounds. Changes to claims require reviewing the underlying source and updating the source/revision manifest. Changing the source snapshot may require updating citation lines. Studio supports architecture/evidence graphs; these views are not claims of UML, BPMN or protocol conformance.

Use the pinned Studio checks and the research documentation checks:

```powershell
Push-Location $Studio
try { npm run check:all } finally { Pop-Location }
python research/evidence/build_knowledge_index.py --check
python research/evidence/sync_workflow_diagrams.py --check
python research/evidence/publish_archify_previews.py --check
python research/evidence/sync_tsf_headlines.py --check
python -m unittest discover -s tests -p test_documentation_navigation.py -v
python -m unittest discover -s tests -p test_workflow_diagrams.py -v
python -m unittest discover -s tests -p test_studio_previews.py -v
python research/evidence/apply_studio_export_policy.py --html docs/overview/archify-studio/index.html
```

The existing `publish_archify_previews.py` checks the separate seven-view upstream gallery. For this Studio atlas, rebuild the packet/HTML, apply the local export policy, open each view, and use **Export → Diagram as SVG** in Paper theme to refresh these ten SVG files. Preserve complete topology and the embedded MIT notice. Update the corresponding preview and HTML hashes/size in the manifest after intentional regeneration. The Studio regression tests verify all ten static previews, topology and manifest hashes, and exercise the export policy with Node.js when available. Check source hashes and source line bounds separately from actual browser interaction and visual inspection. Desktop and narrow layouts, keyboard access, source inspection and export need browser review; no blanket accessibility certification is implied.

## Rollback

This change adds documentation, an editable JSON model, the self-contained interactive HTML and script-free SVG previews. Roll back only this atlas directory, its README/gallery navigation links and the corresponding regenerated knowledge-index entries. The sampler, native boundary, clock models, thresholds and existing diagram sources are unchanged. Stop the optional local preview process when no longer needed; it is not installed as a service.
