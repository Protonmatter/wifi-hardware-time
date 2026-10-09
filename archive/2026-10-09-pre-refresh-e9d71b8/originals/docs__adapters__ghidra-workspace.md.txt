# Ghidra workspace for Qualcomm timing paths

Ghidra makes the recovered driver paths easier to inspect as linked assembly, bytes and approximate C. This workspace labels the management-event and packet-log paths in one exact ARM64 driver build. It is an offline research aid: the labels and decompiler output do not prove that a path ran, that a buffer is safe to read, or that a timestamp has a qualified clock relationship.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Scope and prerequisites](#scope-and-prerequisites)
- [Create the private project](#create-the-private-project)
- [Open and navigate](#open-and-navigate)
- [What to examine first](#what-to-examine-first)
- [Validation and failure handling](#validation-and-failure-handling)
- [Limits and cleanup](#limits-and-cleanup)
- [Glossary](#glossary)

## Scope and prerequisites

- Tool: [Ghidra 12.1.4](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build), portable installation.
- Runtime: 64-bit Java Development Kit (JDK) 21. The tested Windows ARM64 setup uses an x64 JDK and Windows emulation, matching the package's x64 native decompiler. The **driver target remains ARM64**.
- Exact input: owned `qcwlanhmt8380.sys`, version `1.0.4374.1300`, SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Language: `AARCH64:LE:64:v8A`; compiler specification: `windows`; preferred image base: `0x140000000`.
- Authored script: [AnnotateQualcommTiming.java](../../research/adapters/ghidra/AnnotateQualcommTiming.java).
- Permissions: normal user file access. No administrator elevation, device access or kernel debugger is needed.
- Store project databases, logs and decompilation output under ignored `artifacts/ghidra/`. They contain proprietary code and local paths.

The [version-specific getting-started guide](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/GhidraDocs/GettingStarted.md)
describes this release's requirements. Do not substitute a newer release's Java requirement.

## Create the private project

Run from the repository root after extracting verified Ghidra and JDK packages.
Supply your actual paths; the driver is read as a file, never loaded or executed.
Use a fresh project name and report directory for each independent analysis.

```powershell
$ErrorActionPreference = 'Stop'
$ghidraRoot = 'C:/Tools/ghidra_12.1.4_PUBLIC'
$jdkRoot = 'C:/Tools/jdk-21'
$driverFile = 'C:/OwnedDrivers/qcwlanhmt8380.sys'
$repoRoot = (Get-Location).Path
$projectName = 'QualcommTiming_1300'
$projectDir = Join-Path $repoRoot 'artifacts/ghidra/projects'
$reportDir = Join-Path $repoRoot 'artifacts/ghidra/reports/initial'
$expectedHash = 'ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'

if ((Get-FileHash -LiteralPath $driverFile -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'Different driver build: do not apply these annotations'
}
if ((Test-Path -LiteralPath "$projectDir/$projectName.gpr") -or
    (Test-Path -LiteralPath "$projectDir/$projectName.rep") -or
    (Test-Path -LiteralPath $reportDir)) {
    throw 'Choose a new project name and report directory'
}
New-Item -ItemType Directory -Path $projectDir, (Split-Path $reportDir) -Force | Out-Null
$savedJavaHome = $env:JAVA_HOME
$savedHeap = $env:GHIDRA_HEADLESS_MAXMEM
try {
    $env:JAVA_HOME = $jdkRoot
    $env:GHIDRA_HEADLESS_MAXMEM = '3G'
    & "$ghidraRoot/support/analyzeHeadless.bat" $projectDir $projectName `
        -import $driverFile -processor 'AARCH64:LE:64:v8A' -cspec windows `
        -scriptPath "$repoRoot/research/adapters/ghidra" `
        -postScript AnnotateQualcommTiming.java $reportDir `
        -analysisTimeoutPerFile 300 -max-cpu 4 `
        -log "$repoRoot/artifacts/ghidra/headless.log" `
        -scriptlog "$repoRoot/artifacts/ghidra/scripts.log"
    if ($LASTEXITCODE -ne 0) { throw 'Headless execution failed; inspect logs' }
    $receipt = Join-Path $reportDir 'receipt.tsv'
    if (-not (Test-Path -LiteralPath $receipt)) { throw 'No annotation receipt' }
    if (-not (Select-String -LiteralPath $receipt -Pattern '^failures\s+0$' -Quiet)) {
        throw 'Incomplete annotation/decompilation; inspect receipt'
    }
} finally {
    $env:JAVA_HOME = $savedJavaHome
    $env:GHIDRA_HEADLESS_MAXMEM = $savedHeap
}
```

The script independently checks the imported file hash, language, compiler and
image base. It adds `wht_` research labels, explanatory bookmarks and comments.
It keeps existing non-default function names and does not force new function
boundaries. Missing functions or failed selected decompilations are reported.

Two reference-only structure definitions appear under
`WiFiHardwareTime/ReferenceOnly`. One describes candidate management-header
offsets; the other describes the selected packet-log header layout. They are
**not applied to variables or function signatures**. In particular, the candidate
TSF names do not establish firmware field contents, units or atomic sampling.

## Open and navigate

1. Start `ghidraRun.bat` from the portable installation with that JDK available.
2. Open `artifacts/ghidra/projects/QualcommTiming_1300.gpr`.
3. Double-click `qcwlanhmt8380.sys` to open CodeBrowser. Keep the completed analysis
   rather than starting a duplicate import.
4. Open the **Decompiler**, **Bytes**, **Function Graph** and **Bookmarks** windows
   from CodeBrowser's Window menu. The listing shows ARM64 instructions; Bytes
   shows the imported file's mapped bytes, not current kernel memory.
5. Press **G** to go to a `wht_` label or an absolute address from the table below.
   Select an instruction to correlate assembly and decompiler output. Follow
   references to inspect callers; a computed indirect call may need manual
   table resolution.

RVA means an offset from the image base. For this project only:
`Ghidra address = 0x140000000 + RVA`. The running kernel may load the driver at
a different base. These addresses are not live pointers or callable APIs.

## What to examine first

| Start at | Ghidra address | Question to answer |
|---|---|---|
| `wht_management_rx` | `0x1401a8160` | Which header fields and frame bytes reach the compact metadata and downstream queue? |
| `wht_wmi_control_rx` | `0x140168ce0` | Where does callback ownership begin and end, and when is decoded storage cleaned up? |
| `wht_packetlog_offload_write` | `0x140220e90` | What is copied into the packet log, and can its producer be tied to a complete management event? |
| `wht_packetlog_reserve` | `0x140220b18` | Does the write cursor advance before the payload is fully copied? |
| `wht_packetlog_copy` | `0x1401ebbf8` | What protects readers from concurrent writers, wrap and teardown? |
| `wht_packetlog_result_envelope` | `0x140037e00` | Which bytes, counts and errors are passed toward application completion? |
| `wht_ihv_request` | `0x14012e4f0` | How does the selected dispatch result reach serialization and completion? |

Read the path in this order:

```text
Management event -> temporary decoded slots -> selected callback -> cleanup
                                               |
                                               +-> frame copy + reduced metadata
                                               +-> candidate timing block: not forwarded

Packet-log producer -> reserve space -> advance cursor -> copy payload
                            |
                            +-> reader -> result envelope -> IHV completion
                                ^
                                Complete-event identity and copy safety unresolved
```

Arrows describe selected static connections, not a measured runtime sequence.
The packet-log producer has not been connected to the complete management-event
tuple above. See [management ownership](qualcomm-management-timing-producer.md)
and [the packet-log return path](../memory-ring/packetlog-return-path.md).

The [producer follow-up](../memory-ring/packetlog-producer-trace.md) traces this
input back to an HTT packet-log message and documents a separate MLO offset-cache
lead. Its bounded cross-reference exporter operates in a separate project so
the original GUI workspace can remain open.

## Validation and failure handling

Local qualification on 2026-10-04 used the exact driver above. Import and analysis
completed with all 36 selected function entries found, 48 bookmarked locations,
two reference-only structures and 19 successful decompilation exports. A
different input hash and an existing output directory were each rejected in
separate headless runs. Both rejected runs still returned process exit code zero,
which is why the receipt and log checks are required.

The run also reported an unparsed Windows event resource at `0x14043c7d0`, no
matching private PDB and security-cookie decompiler substitutions. Selected
guarded indirect calls remain approximate in the C view. These limitations do
not prevent inspection of the named functions, but this is not a warning-free
or fully resolved analysis of the whole image.

- Check `receipt.tsv` for the exact hash, ARM64 language, Windows compiler and
  zero failures. A headless process exit code alone does not prove that a
  post-script succeeded.
- Check the headless log for analysis timeouts and decompiler failures. A
  completed pseudocode export still can contain warnings, inferred argument
  types or unresolved indirect calls. Inspect the ARM64 instructions before
  adopting a new finding.
- The private `*.c.txt` reports contain approximate C, not original vendor
  source. Keep them out of public Git.
- A hash mismatch rejects the script before annotations or report creation.
  An existing report directory is also rejected rather than overwritten.
- If interrupted, retain the logs and use a new report directory. Close the GUI
  before processing the same project in headless mode; do not delete lock files
  while either instance is running.
- Repository checks: `python -m unittest discover -s tests -p test_documentation_navigation.py -v`.
  Java compilation and native decompilation require this local Ghidra setup;
  the existing hosted Python/PowerShell workflow does not exercise them.

## Limits and cleanup

- Offline decompilation does not observe driver calls happening in real time.
- This workflow does not attach a kernel debugger, enable boot debugging, issue
  private requests, start packet logging or alter the network adapter.
- Host-driver analysis cannot directly observe execution on the Wi-Fi firmware
  processor. Live byte values need a separately controlled capture mechanism.
- Breakpoints would perturb execution and timing. They can help establish
  ownership/dataflow but cannot independently validate timing accuracy.
- No complete-event return, safe concurrent snapshot, fresh hardware/QPC sample
  or synchronization accuracy is qualified by this project.
- Rollback: close Ghidra and remove only the private project/output directory
  you created. The portable tool directories can also be removed after use.
  No driver or system-wide environment setting needs restoration.

## Glossary

- **Decompiler:** reconstructs approximate C from machine instructions; its
  variable names, types and control flow need review.
- **PDB:** a debug-symbol file that can supply original names and types. A
  matching private Qualcomm PDB was not available in this analysis.
- **RVA:** relative virtual address, an offset from a program's image base.
- **WMI:** here, Qualcomm's firmware/host WLAN messaging interface, not Windows
  Management Instrumentation.
- **IHV:** independent hardware vendor; Windows' vendor-specific control path.
- **TSF:** the Wi-Fi Timing Synchronization Function counter.
- **QPC:** Windows QueryPerformanceCounter, a host performance-counter clock.
- **Publication:** the point at which a writer makes a complete record available
  to a reader. Reserving space does not necessarily publish a complete record.
