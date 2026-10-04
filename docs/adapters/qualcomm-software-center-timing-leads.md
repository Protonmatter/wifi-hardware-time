# Qualcomm Software Center files: useful timing leads and missing runtime

The installed WLAN test assembly contains inherited WCN7850 RTT methods and concrete QMSL response-field names. That helps identify the next interface to inspect. It does not yet supply a usable clock: required runtime assemblies are missing from the searched locations, returned buffer semantics remain incomplete, and no vendor method or hardware command was executed.

## Contents

- [What was inspected](#what-was-inspected)
- [What the timing methods expose](#what-the-timing-methods-expose)
- [Other ranging and spectral code](#other-ranging-and-spectral-code)
- [Runtime and architecture gaps](#runtime-and-architecture-gaps)
- [How this helps the clock implementation](#how-this-helps-the-clock-implementation)
- [Reproduction and validation limits](#reproduction-and-validation-limits)

## What was inspected

Snapshot: 2026-10-03. This pass reads locally installed files obtained through
Qualcomm Software Center and its package cache. It does not install software,
load a vendor assembly, activate a license, change a driver or access the NIC.

**Terms:** QDART is Qualcomm's test-tool suite; QSPR is its sequence/test framework;
QMSL supplies library calls; QUTS supplies tool/device connectivity. An assembly
is a .NET program/library file. IL is its intermediate code, inspected here as
data. A DUT is a device under test. RTT is round-trip time. An ABI defines the
calling and buffer contract between components.

**FTM terminology:** the QDART/QMSL `FTM_*` API prefix denotes factory test mode.
It must not be equated with IEEE 802.11 Fine Timing Measurement merely because
the abbreviation matches. Ranging-specific methods require their own evidence.
Qualcomm also expands FTM as factory test mode in its public
[RF test report glossary](https://docs.qualcomm.com/bundle/publicresource/80-WL730-71_REV_AC_QCC730_FM01_1_WLAN_xPA_DVT_Test_Report.pdf).
That other-platform glossary is terminology context, not a contract for this NIC.

| File or package | Local finding |
|---|---|
| `QC.CTE.WLANTestSuite.dll` | Assembly `2.0.81.1`, package `WLAN_QSPR_Subsystem.2.0.00081.1` |
| `WLAN_QSPR_Subsystem.2.0.00081.1.Windows-x86.exe` | Present in the Qualcomm installer package cache; not executed in this pass |
| `Help_SBSYWLAN.chm`, `QDART_Base.chm` | Present; hashes match the earlier side investigation; fresh HTML extraction did not succeed here |
| `PRODUCT_BUNDLE_WIN_WLAN.json` | Historical sample bundle lists QMSL FastConnect, QSPR, QUTS and related tools; not proof of current installation or a version lockfile |
| WLAN test trees and TILIB assemblies | Present under the vendor installation; test/configuration presence does not establish an operational timing backend |

The WLAN assembly SHA-256 is
`5f906f7e7e0ffc1ca5655e384566aae5f50b91e62bc37cfad96f7ebb0ce8bef6`.
The cached WLAN installer SHA-256 is
`093df61fef59aba5a12e61760e5aae1748c8506d31626b52c3a831aeffd17cb8`.
Hashes identify inspected files; they do not prove loaded firmware compatibility.

## What the timing methods expose

Metadata establishes this inheritance chain:

```text
DUT_WCN7850
  -> DUT_QC6490
  -> DUT_QC6390
  -> DUT_IPQ807x
  -> DUT_QC6180
  -> DutCommon
```

`DUT_QC6180` implements both methods below. No intervening declaration of either
method was found in that chain. The base `DutCommon` versions throw an
unimplemented-function exception. This establishes inherited implementation,
not successful WCN7850 device selection or firmware execution.

| Method | Observed IL behavior | Qualification limit |
|---|---|---|
| `DUT_QC6180.RttInfo` | Uses `FTM_WLAN_TLV2_Create16` selector 358, supplies `rtt_info_Read` and `rtt_info_Write`, completes the request, reads `rtt_Size`, allocates a four-byte result array and retrieves `rtt_Data` through QMSL | The separately reported size is not proof of buffer capacity, valid bytes, timestamp layout or units |
| `WlanDutWrapper.WlanRttInfo` | Initializes outputs, delegates through `IWlanDut.RttInfo`, and catches exceptions | This is a managed wrapper, not a new kernel/userspace export contract |
| `DUT_QC6180.q5_getRtt` | Uses `FTM_WLAN_TLV2_CreateQ5` selector 20043 with PHY and packet-type arguments; retrieves packet ID, bandwidth code, GI, MCS, NSS, RTT and status | The inspected RTT conversion is `UInt16`; packet ID and status convert to bytes. No four absolute event times or epoch are established |
| `WlanDutWrapper.Q5_GetRtt` | Initializes outputs and delegates through `IWlanDut.q5_getRtt` | Return handling does not demonstrate fresh hardware completion or exact packet association |

GI is guard interval, MCS is modulation/coding selection, and NSS is spatial-stream
count. These radio parameters can provide context, but do not define the RTT
counter's clock domain or physical reference point.

Selectors 358 and 20043 are **QMSL builder inputs**, not established Windows
IOCTLs or firmware WMI event/command IDs. Do not send them through the previously
qualified TSF interface. The missing QMSL implementation must establish how they
are serialized, transported and interpreted.

The `RttInfo` body also returns true after its calls; the inspected body does not
independently prove response completeness or validate the declared size against
the four-byte managed array. Callee behavior may include additional validation
or exceptions, but that implementation is not available in the inspected files.
This is an unresolved contract, not a demonstrated overflow or working raw export.

## Other ranging and spectral code

The assembly contains explicitly ranging-oriented `MccRTT` and `RTTUtilities`
methods for 11mc/11az results. Selected method-body inspection found:

- LOWI command construction using an Android-style `shell lowi_test` invocation
  and `/data/` paths. This is a different execution path from the laptop's
  existing Windows callback.
- Parsers for distance statistics, yields, base delays, per-bandwidth delay terms
  and diagnostic logs from initiator/responder roles.
- No recovered absolute four-event timestamp output in those inspected methods.
  Parser names and string matches are not a complete call-graph search.

A timing-name metadata search also inspected all 32 DLLs in the installed WLAN
`BIN` directory. Several matches belong to external laboratory instruments or
ordinary utility code. For example, the inspected
`QSPRWCNUtility.StringManipulation.AppendTimeStamp` method uses `DateTime.Now`
and string formatting. Its name does not identify a hardware timestamp read.
This bounded name search cannot exclude interfaces with unrelated names.

The side investigation separately documents inherited spectral/FFT acquisition
and device-specific ADC capture methods. Those are useful for transport research,
but this pass does not rerun their full implementation analysis. Spectral capture,
radio calibration and ranging are separate capabilities. None establishes a
hardware-to-QPC relationship or safe simultaneous operation with normal Wi-Fi.

## Runtime and architecture gaps

The assembly targets **.NET Framework 4.7.2**, has PE machine `I386`, and CLR flags
`ILOnly, Requires32Bit`. Its intended managed host must therefore be 32-bit.
That does not establish complete runtime/driver compatibility on Windows ARM64.

Fresh dependency search covered both Program Files Qualcomm roots, the system
drive's Qualcomm directory and `.NET` GAC_32/GAC_MSIL caches:

| Dependency | Referenced version | Bounded search result |
|---|---|---|
| `QC.QMSLFastConnect` | `6.1.364.1` | No matching assembly found |
| `QTMDotNetKernelInterface` | `5.1309.8481.20772` | No matching assembly found |
| `QC.TILib.InterfaceDefinitions` | `2.0.91.1` | Candidate `2.0.92.1` present; binding compatibility not validated |
| `QC.TILib.LibraryManager` | `2.0.91.1` | Candidate `2.0.92.1` present; binding compatibility not validated |

Filename searches also did not find `QTMInterface.dll` or
`QMSL_WLAN_Transport.dll` in those roots. The inspected installer cache contains
the WLAN subsystem, shared files, test utilities and help packages, but no package
named for the missing QMSL FastConnect, QSPR core or QUTS runtime. This is not an
exhaustive disk search and does not establish account entitlement or the cause
of a failed installation. A QUTS logs directory alone is not runtime evidence.

## How this helps the clock implementation

These files make the next work more specific:

1. Obtain the legitimate matching QMSL FastConnect runtime, QSPR dependency and
   intended transport through the vendor's supported installation/access path.
   Inspect them as files before loading or connecting them.
2. Trace the two RTT methods through those components to the actual request and
   response ABI. Resolve buffer allocation, response length, completion, errors,
   timeout/cancellation and whether the operations alter test/firmware state.
3. Establish whether returned values correspond to the production driver's
   pre-aggregation FTM records, another firmware test protocol, or a different
   measurement. Matching names are insufficient to join these paths.
4. Qualify fields and lifetime against the [owned-response requirements](../ftm/ftm-ingress-to-owned-response.md).
   Keep an opaque diagnostic export separate from a timestamp whose units,
   event, identity, validity and epoch are established.

The vendor files are a useful new lead, not a completed bridge from the RX/FTM
producer to userspace. They do not justify switching the live adapter into test
mode, running calibration or lifting the existing campaign quarantine.

## Reproduction and validation limits

Metadata, IL and dependency inspection reused the side project's file-only tools:

- `Inspect-DotNetAssembly.ps1`: hash
  `9e27c96d61635b611dea1e16f9e7b291125472594b4c1c1782743063427c44b0`.
- `Inspect-ManagedIL.ps1`: hash
  `403dbd7007fa75baa9d74696fb7c8e4895b5cdc3eb4ea0faa72bdd3dcec7139c`.
- `Find-AssemblyDependencies.ps1`: hash
  `558eb158d130f3e79d670f315f3b85e78002ae9a69eda0fa8a448ced7a22ef15`.

The side checkout reported revision `f903d3e225c2c37db44a4348962335ed991b2153`
with pre-existing local changes, including the IL tool. Its commit alone is not
the source identity of this inspection; the file hashes above pin the tools used.
No side-project source was changed by this pass.

From a workspace containing both repositories, the focused file-only recipe is:

```powershell
$dll = 'C:\Qualcomm\WCN\ProdTests\BIN\QC.CTE.WLANTestSuite.dll'
./wifi-spectral-research/tools/managed/Inspect-DotNetAssembly.ps1 `
  -Path $dll -MethodPattern '^\.ctor$|^(RttInfo|q5_getRtt)$'
./wifi-spectral-research/tools/managed/Inspect-ManagedIL.ps1 `
  -Path $dll -TypePattern '(WlanDutWrapper|DUT_QC6180)$' `
  -MethodPattern '^(WlanRttInfo|RttInfo|Q5_GetRtt|q5_getRtt)$'
```

PowerShell 7.4+ and read permission are required; no elevation or runtime loading
is needed. The tools emit stdout, exit 0 for completed inspection and 1 for an
inspection error. Keep outputs local; the IL tool can reveal proprietary code.
This pass additionally retained decoded string operands privately to identify
response-field names. There is no device rollback because no device state changed.

Local receipts and the inspection manifest are under ignored
`artifacts/VendorClockInspection/`. Fresh CHM extraction was attempted but produced
no pages; the available standalone `7za` also rejected that archive format.
Help-content claims from the earlier side report were not independently reread
here. The main findings above come from fresh assembly metadata and IL inspection.

No vendor method, installer, live acquisition, calibration, test-mode change or
clock adjustment was executed. Runtime availability, live response contents,
firmware identity and timing accuracy remain unqualified.
