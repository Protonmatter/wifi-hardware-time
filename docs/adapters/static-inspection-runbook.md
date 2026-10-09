# Repeatable static inspection

Use this workflow to inspect vendor files without launching their installers or contacting a device. Preview shows the intended operation. Apply writes a private evidence directory, and an unchanged repeat validates the prior receipt. The outputs support byte identity and interface analysis; they do not establish live timing acquisition or clock accuracy.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__static-inspection-runbook.md).
<!-- /research-history -->

## Contents

- [Preconditions](#preconditions)
- [Operations](#operations)
- [Preview and apply](#preview-and-apply)
- [Package extraction sequence](#package-extraction-sequence)
- [Validation and failures](#validation-and-failures)
- [Refresh documentation](#refresh-documentation)

## Preconditions

- Windows PowerShell **7.4+**, Python **3.11+**, and the repository's existing
  `pefile` dependency. PowerShell 5.1 can parse the sources but cannot run the
  managed-metadata operations.
- Read permission on locally owned input files. Administrator privileges are
  unnecessary. The wrapper makes no network calls or device requests.
- A pre-existing output parent, normally ignored `artifacts/`. Input and output
  cannot contain one another. Reparse-point paths are rejected by the wrapper.
- Use standard local drive paths. UNC and extended/device namespace forms are
  rejected; existing filesystem paths are resolved consistently before comparing
  input/output ancestry, including short-name aliases.
- A reviewed SHA-256 for binary-format operations. A hash identifies bytes;
  publisher authenticity and entitlement are separate questions.
- 7-Zip is used separately for ZIP/7z/MSI cabinet extraction. Never substitute
  an installer's `/extract` switch, because that executes vendor code.

## Operations

Entry point:
[Invoke-QualcommStaticInspection.ps1](../../research/adapters/Invoke-QualcommStaticInspection.ps1).

| Operation | Input | Result |
|---|---|---|
| `Files` | A file or bounded directory | Relative file names, lengths, hashes and PE metadata |
| `QikInventory` | Decoded `block-NNNN-type-N.bin` directory | XML-to-payload association and PE metadata; rejects partial/unmapped files |
| `QccExtract` | Supported managed QIK wrapper | New block files and a validated container index |
| `QpstExtract` | Inspected QPST wrapper layout | BIN/103 and InstallShield v3 member decoding, including `members/QPST.msi` |
| `MsiTables` | MSI/MSM database | Read-only File/Registry/component metadata; unavailable optional tables are explicit |
| `TypeLibrary` | Extracted `.tlb` | COM interface metadata, with registration disabled |

`QccExtract`, `QpstExtract`, `MsiTables` and `TypeLibrary` require
`-ExpectedSha256`. QCC/InstallShield are **bounded supported formats**, not
universal installer extractors. Package decoding parameters remain in memory;
do not print or publish them. Raw extraction output remains private.

## Preview and apply

```powershell
$inputFile = 'C:/OwnedPackages/QXDM.4.0.450.2.Windows-x86.exe'
$expected = '<reviewed-64-character-sha256>'
$out = './artifacts/qxdm-static-new-run'

# Preview: no output directory is created.
./research/adapters/Invoke-QualcommStaticInspection.ps1 `
  -Operation QccExtract -InputPath $inputFile -ExpectedSha256 $expected `
  -OutputDirectory $out

# Apply: decode files and create receipt.json.
./research/adapters/Invoke-QualcommStaticInspection.ps1 `
  -Operation QccExtract -InputPath $inputFile -ExpectedSha256 $expected `
  -OutputDirectory $out -Apply

# Validate the decoded payload association in a separate directory.
./research/adapters/Invoke-QualcommStaticInspection.ps1 `
  -Operation QikInventory -InputPath "$out/blocks" `
  -OutputDirectory './artifacts/qxdm-inventory-new-run' -Apply
```

Use an absolute `-Python` executable path when multiple Python installations exist.
Status is JSON on stdout. The receipt records input hashes, tool hashes and every
output file hash. Do not commit receipts containing vendor contents or local paths.

## Package extraction sequence

1. Verify the three downloaded archive hashes against the
   [source evidence](qualcomm-archive-transport-findings.md#scope-and-provenance).
2. List each outer archive with `7z l -slt`; confirm member paths before extraction.
   Extract to a new private directory with `7z x -o<new-directory> <archive>`.
3. For QPST, use `QpstExtract` on the wrapper, then `MsiTables` on `members/QPST.msi`.
   Use 7-Zip to extract its `Data1.cab`, then the cabinet members. Match cabinet
   member keys and sizes to the MSI File table before interpreting names.
4. For QXDM, use `QccExtract` then `QikInventory`. Inspect declared embedded package
   members through the same operations, using their recorded hashes and fresh
   output directories. Keep parent-to-child provenance; do not equate wrapper
   version, enclosed application version and component version.
5. Use `Files` on the relevant installed Qualcomm directory for a fresh snapshot.
   Compare current hashes and CLR flags with earlier records before carrying
   version or architecture assumptions forward.
6. For managed methods, use the file-only metadata/IL tools identified in the
   [vendor inspection recipe](qualcomm-software-center-timing-leads.md#reproduction-and-validation-limits).
   Never load a vendor assembly merely to inspect its metadata.
7. For QPST native functions, use the exact-hash
   [TraceAtlasQuts.java](../../research/adapters/ghidra/TraceAtlasQuts.java) after
   importing the 496 server into a separate Ghidra project. Pass one new private
   output directory for preview and add `--apply` to create the trace files.
   Whole-program analysis completeness remains separate.

The initial experiment retained its original helpers under ignored artifacts.
Promoted tools add gates and receipts; their source identity differs from those
historical helpers. Reproduction results must identify which version actually ran.

## Validation and failures

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -p test_static_inspection.py -v
python -m unittest discover -s tests -p test_qik_inventory.py -v
```

- Exit **0**: preview, completed inspection or verified `Unchanged` repeat.
- Exit **1**: invalid input, worker failure, changed input/output or conflicting receipt.
- `-WhatIf` with `-Apply` remains nonmutating.
- A failed apply can retain partial files and `failure.json`; it has no completed
  receipt. Do not reuse it as evidence of a complete extraction.
- Existing output is never silently overwritten. Correct the cause and select
  a new output directory. A different script hash also requires a new snapshot.
- Rollback: inspect and remove only the output directory you selected. No driver,
  service, registry, WLAN profile or system-clock rollback is needed.
- Do not infer safety of a live call from successful static extraction.

## Refresh documentation

```powershell
python research/evidence/sync_workflow_diagrams.py --write
./research/evidence/Update-ResearchKnowledge.ps1 -Apply
python research/evidence/sync_workflow_diagrams.py --check
python research/evidence/build_knowledge_index.py --check
```

The [script catalog](../../catalog/scripts.json) records ownership, risk, validation
and rollback. Review the [research skill](../../skills/qualcomm-timing-research/SKILL.md)
and [current findings](../knowledge/current-findings.md) before selecting a live task.
