# Live packet capture, driver observation and elevation

A bounded capture on FastConnect returned 589 packets in Ethernet format with
host timestamp options. This establishes a usable traffic-observation baseline,
not a radio clock export. The administrator launch for a paired kernel trace was
canceled before execution. Its outcome is recorded separately, and the repeatable
collector now records privilege context and command cleanup explicitly.

## Contents

- [What ran and what it established](#what-ran-and-what-it-established)
- [How packet and code observations relate](#how-packet-and-code-observations-relate)
- [Elevation record](#elevation-record)
- [Repeat the bounded experiment](#repeat-the-bounded-experiment)
- [Validation and remaining work](#validation-and-remaining-work)
- [Terms](#terms)

## What ran and what it established

Observation date: 2026-10-04 local time. The exact adapter was FastConnect 7800,
driver `1.0.4374.1300`, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
The before/after checks found the same interface and PnP identity, **Up**, with
the same running driver hash and version.

| Observation | Supported interpretation |
|---|---|
| Wireshark/dumpcap 4.6.6 and Npcap were already installed | No installer or capture-driver change was needed |
| Normal-mode link types: `EN10MB` and `DOCSIS`; selected `EN10MB` | Captured Ethernet-format packets; no raw 802.11 or radiotap in this experiment |
| 589 packets across 9.841175800 seconds of packet timestamps | Successful bounded acquisition; the requested stop timer was ten seconds |
| 509 IPv4, 75 IPv6, 5 ARP packets | Ordinary network traffic is visible through the capture interface |
| 128-byte snapshot limit; capture file approximately 78 kB | Large frames are intentionally truncated; protocol-analysis “short” indications do not establish malformed original traffic |
| dumpcap reported 589 received / 0 dropped, including its reported subcounters | No capture-layer loss reported for this run; not proof that every over-the-air frame reached the host |
| Timestamp options: `host`, `host_hiprec_unsynced`, `host_lowprec` | Only host timestamp sources were advertised by this installed capture path |
| pcapng stores one-billion ticks per second | Nanosecond **representation resolution**, not demonstrated nanosecond accuracy or a hardware clock origin |
| Kernel trace was not started | No live CPU-call, interrupt, private-IOCTL or packet-to-function attribution from this run |

The capture used no promiscuous or monitor mode, injected no test packets and
sent no private firmware commands. A 128-byte limit can still retain application
data, addresses and names. The packet file, endpoint identity, command logs and
all raw analysis remain in ignored private artifacts. Public notes contain only
the aggregate findings above.

## How packet and code observations relate

```text
Wi-Fi hardware and firmware
          |
          v
Qualcomm / Windows receive and send paths
          |                          |
          | packet delivery          | sampled CPU / DPC / interrupt activity
          v                          v
Npcap -> dumpcap -> pcapng      Windows WPR -> ETL trace
          |                          |
          | observed this run        | NOT collected this run
          v                          v
Packet bytes + host time       Module addresses + execution evidence
                                     |
                                     | exact image + address mapping required
                                     v
                              Ghidra code inspection
```

- **Solid arrows** show different observation paths, not a demonstrated one-to-one
  match between an individual packet and a function call.
- A packet capture does not record kernel function arguments, firmware commands,
  register values or all system calls.
- The prepared WPR profile requests process/module information, CPU samples,
  deferred procedure calls and interrupts. Its samples are not an exhaustive
  call trace, and a sample near packet arrival is not sufficient event identity.
- Ghidra supplies static interpretation for addresses in a matching image. It
  does not make the current file-only decompilation a live debugger session.
- Neither capture-file resolution nor an ETW/QPC event time establishes the
  radio's sampling instant. Hardware-to-QPC correlation remains independent.

See the primary [dumpcap options](https://www.wireshark.org/docs/man-pages/dumpcap.html)
and Microsoft's [system tracing keyword definitions](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/keyword--in-systemprovider-)
for the capture and WPR mechanisms.

## Elevation record

The user authorized Wireshark/Npcap installation and use, monitoring, and normal
administrator launches, and requested an explicit record of elevation.

| Step | Privilege / outcome |
|---|---|
| Initial shell and profile preview | Non-elevated; no UAC request |
| Paired-capture launch | `Start-Process -Verb RunAs`, hidden child requested; normal UAC elevation expected |
| Windows launch result | Reported “The operation was canceled by the user.” No child PID or capture receipt was produced. The actual prompt interaction was not independently observed. |
| First non-elevated preflight | The tool version query ran, but the original Windows PowerShell subprocess helper did not retain its exit code. The collector rejected the unknown result before capture. |
| Corrected packet-only run | Non-elevated; Npcap's existing access policy allowed capture; every child returned zero and exited |
| Kernel trace start/stop | Prepared and profile-validated, not executed; administrator privilege still required |
| Offline parsing, Ghidra and checks | Non-elevated; no UAC launch |

The subprocess helper now owns a `Diagnostics.Process` from startup and retains
short-lived exit status. It records each child's command, actual administrator
token state, expected administrator requirement, QPC bracket, timeout and cleanup.
`ElevationOrigin` is caller-declared provenance; it does not prove that a UAC
prompt appeared. The verified `is_elevated` field is separate. No UAC settings or
security controls were changed.

Private receipts are under
`artifacts/wlanlib-alternatives-20261004/`: the launch result in
`live-path-prep/elevation-launch-01.json`, failed preflight in `packets-only-01`,
and successful packet acquisition in `packets-only-02`. Preserve failed attempts
alongside successful evidence; do not overwrite or silently relabel them.

## Repeat the bounded experiment

Use [Observe-WifiDataPath.ps1](../../research/acquisition/Observe-WifiDataPath.ps1)
with its adjacent [wifi-path.wprp](../../research/acquisition/wifi-path.wprp).

**Prerequisites**

- Windows PowerShell 5.1+, Windows WPR, installed Wireshark/Npcap.
- Exactly one Up FastConnect 7800 on the pinned driver/version. Mismatch stops
  execution; this is not a generic adapter benchmark.
- A new private output directory. Keep it out of public Git.
- An administrator shell for the paired kernel trace. Packet-only access depends
  on the Npcap installation policy; this run's permission does not guarantee it on
  another machine.

```powershell
# Identity/profile preview; does not start a trace or capture.
./research/acquisition/Observe-WifiDataPath.ps1

# Existing Npcap permissions only. No kernel trace or automatic elevation.
./research/acquisition/Observe-WifiDataPath.ps1 -Execute -PacketsOnly `
  -OutputDirectory C:/PrivateEvidence/wifi-packets-01

# Run from a normally elevated administrator shell.
./research/acquisition/Observe-WifiDataPath.ps1 -Execute `
  -OutputDirectory C:/PrivateEvidence/wifi-paired-01 `
  -ElevationOrigin ExistingAdministrator
```

- `Seconds`: 5–15, default 10. Packet capture also stops at 10,000 packets or
  approximately 8 MiB. Kernel buffers are configured for 32 MiB in memory.
- `WiresharkDirectory`: explicit installed-tool directory when different.
- `ElevationOrigin`: `ExistingAdministrator` or `RunAs`; declare the actual
  launch method. A non-elevated run records `NonElevated` instead.
- **Outputs:** `result.json`, identity snapshots, exact executed source/profile,
  tool hashes/signature results, per-command output and `packets.pcapng`.
  A successful paired run additionally writes `cpu.etl`.
- **Exit codes:** 0 = preview/acquisition completed; 1 = blocked/failed. Neither
  code certifies timestamp meaning, trace coverage or synchronization accuracy.
- **Cleanup:** normal completion waits for dumpcap and stops its unique WPR
  instance. Failures attempt cancellation of only that instance. After an
  external interruption, use `wpr -cancel -instancename <result.json instance>`
  from an administrator shell. Do not cancel another collector's session.

## Validation and remaining work

- PowerShell parser and `wpr -profiles` accepted the script/profile.
- [Offline subprocess regressions](../../tests/Test-WifiPathHelpers.ps1) cover a
  short-lived successful exit, nonzero exit, timeout/owned-child termination,
  privilege-receipt persistence and unsafe argument rejection. They never invoke
  the collector body or open an adapter. The Windows CI job includes these tests.
- The packet-only live result and before/after identity checks are recorded above.
- Actual paired WPR start, stack coverage, trace loss, stop/cancel behavior and
  address-to-driver-function attribution remain **not live validated**.
- The next paired run should examine trace health and module identity before
  interpreting any stack. Exact per-packet association requires additional
  identifiers or targeted supported instrumentation; time proximity is not enough.
- No TSF/FTM export, hardware-to-QPC conversion, calibrated accuracy or
  synchronization capability is promoted by this capture.

## Terms

- **UAC:** Windows User Account Control, including the normal administrator prompt.
- **pcapng:** a packet file with interface metadata and packet timestamps.
- **Npcap:** the installed Windows packet-capture driver/library.
- **WPR / ETL:** Windows Performance Recorder / its event trace file.
- **DPC:** deferred procedure call, kernel work scheduled after an interrupt or
  another high-priority operation.
- **QPC:** QueryPerformanceCounter, Windows's high-resolution host counter.
- **RVA:** address relative to the loaded module's image base; used to map a
  verified live module address to the exact binary inspected in Ghidra.
