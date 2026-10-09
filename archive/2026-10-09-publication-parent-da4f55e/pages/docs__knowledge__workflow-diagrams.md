# Research workflow diagrams

> **Archive — not current operating instructions.** Historical documentation at [da4f55e48a36](https://github.com/Protonmatter/wifi-hardware-time/commit/da4f55e48a368f59ed68ee4427013a83b5c06070). Relative links are rebased for reading. [Exact original bytes](../originals/docs__knowledge__workflow-diagrams.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These diagrams show where timing values originate, where software copies them and which connections still need evidence. Follow the labeled arrows and legends: modeled radio behavior, observed historical paths and statically inspected client code are different kinds of evidence. The vendor-return diagram makes the unresolved adapter-to-QUTS connection explicit.

## Contents

- [Interactive Archify Studio HTML](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/index.html) and [SVG gallery/guide](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-studio/README.md): ten source-linked views covering acquisition, I/O ownership, clock models, evidence and open hardware gates. Download the HTML and open it locally for interactive use.
- [Persistent TSF Archify views](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/overview/archify-tsf/README.md): system layers, workflow, lifecycle, time sources, timestamp sequence, algorithms and live/offline adapters.
- [Packet path](#packet-path)
- [Private TSF reports](#private-tsf-reports)
- [Four-event FTM model](#four-event-ftm-model)
- [Uncertainty and rejection](#uncertainty-and-rejection)
- [Application adoption](#application-adoption)
- [Reports versus memory ring](#reports-versus-memory-ring)
- [FTM notification routing](#ftm-notification-routing)
- [FTM reduction](#ftm-reduction)
- [Vendor return candidates](#vendor-return-candidates)

## Packet path

Source: [packets-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/clock-models/diagrams/packets-timestamp-path.mmd).

```mermaid
flowchart TB
  subgraph TX["TRANSMIT: generic layered path, not qualified Qualcomm export"]
    direction TB
    A["1. Application asks to send<br/>Optional host counter timestamp"]
    B["2. Operating-system network queues"]
    C["3. Driver packet buffer<br/>Optional software timestamp metadata"]
    D["4. Host-to-adapter transfer<br/>PCIe, DMA or USB"]
    E["5. Adapter and firmware queues<br/>Channel wait, aggregation and retries"]
    F["6. Radio transmit reference point<br/>Candidate hardware TX timestamp"]
    A --> B --> C --> D --> E --> F
  end
  F ==>|802.11 frame: no universal hardware timestamp field| W["OVER THE AIR"]
  W ==> G
  subgraph RX["RECEIVE: generic layered path"]
    direction TB
    G["7. Radio receive reference point<br/>Candidate hardware RX timestamp"]
    H["8. Receive descriptor or firmware record<br/>Metadata beside the frame"]
    I["9. Host transfer and driver processing<br/>Decode, reorder and split aggregates"]
    J["10. Operating-system packet metadata<br/>Timestamp delivered only if supported"]
    K["11. Application receives data<br/>Host receive time is a different event"]
    G --> H --> I --> J --> K
  end
  L["Separate transmit status<br/>Completion time is not radio launch time"]
  M(["UNQUALIFIED on this Qualcomm path:<br/>General RX/TX export and exact radio reference points"])
  F -. "TX status or timestamp, if supported" .-> L
  L -. "match to packet and retry before use" .-> K
  C -. "missing qualification" .-> M
  H -. "missing qualification" .-> M
  I -. "UNPROVEN: adapter event to diagnostic protocol" .-> Q["Candidate QUTS diagnostic packet"]
  Q -->|Static client code: deserialize and allocate| O["Owned application byte array<br/>Clock and event meaning still required"]
  KEY["KEY: solid = modeled packet path or labeled static code<br/>Dotted = missing or conditional connection<br/>Host delivery time is not radio sampling time"]
  classDef gap fill:#fff2dd,stroke:#ac6b12,stroke-width:1.5px,color:#241b0e;
  classDef air fill:#e6eefc,stroke:#315b96,stroke-width:2px,color:#182844;
  classDef hw fill:#fbebeb,stroke:#b83232,stroke-width:1.5px,color:#300;
  class M,L,Q,KEY gap;
  class W air;
  class F,G hw;
```

## Private TSF reports

Source: [qualcomm-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/tsf/diagrams/qualcomm-timestamp-path.mmd).

```mermaid
flowchart TB
  subgraph REQ["1. REQUEST AND REPORTED COUNTERS: inspected control path"]
    direction TB
    A["Sampler records request-start QPC<br/>QPC is the host interval counter"]
    B["Observed: guarded QcomWifi request<br/>Exact driver hash required"]
    C["Observed: command 0x5012<br/>Action 3 READ or action 4 CAPTURE"]
    D(["Reported TSF and SoC values<br/>Sampling instant and pairing UNQUALIFIED"])
    A -->|issue request| B
    B -->|command dispatch| C
    C -->|request processed: sampling instant unknown| D
    B -. "IOCTL return: around 54 us median<br/>No counter tuple returned" .-> A
  end
  subgraph REP["2. ASYNCHRONOUS REPORT AND LOG DELIVERY"]
    direction TB
    E["Observed: firmware report 0x5005"]
    F["Driver logs the report<br/>ETW timestamp is host logging time"]
    G["ETW delivers the log to the reader<br/>About 1.6 seconds median delay"]
    H["Diagnostic record<br/>Keep action, identity, epoch and report age"]
    E -->|process event| F
    F -->|asynchronous stream| G
    G -->|parse and validate evidence| H
  end
  D ==>|report delivery| E
  A -. "request-start to report log:<br/>about 0.27 ms median" .-> F
  D -. "action behavior" .-> U(["Action 3: SoC cached or unknown<br/>Action 4: refreshed, simultaneous latch unproven"])
  H -. "qualification limit" .-> X(["No calibrated TSF-to-QPC conversion"])
  E -. "UNPROVEN producer association" .-> V["Separate candidate: QUTS binary payload<br/>Managed byte allocation located statically"]
  V --> Z["Keep DIAG / interpolated / QDSS / host time separate"]
  KEY["KEY: observed path describes historical captures<br/>Private campaign is currently QUARANTINED<br/>Dotted arrows mark unqualified relationships"]
  classDef gap fill:#fff2dd,stroke:#ac6b12,stroke-width:1.5px,color:#241b0e;
  classDef seen fill:#e8f5ed,stroke:#34704a,color:#193323;
  class D,U,X,V,Z,KEY gap;
  class B,C,E,F,G,H seen;
```

## Four-event FTM model

Source: [ftm-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/ftm/diagrams/ftm-timestamp-path.mmd).

```mermaid
sequenceDiagram
  participant A as Responder / AP clock A
  participant B as Initiator / station clock B
  participant U as Userspace reader
  Note over A,B: Model: one matched FTM exchange.<br/>Negotiation omitted
  Note over A: t1: hardware departure time
  A->>B: FTM action frame n
  Note over B: t2: hardware arrival time
  Note over B: t3: hardware ACK departure time
  B->>A: ACK: no t3 timestamp field
  Note over A: t4: hardware ACK arrival time
  A->>B: Later FTM frame: matched prior t1 / t4 and follow-up token
  Note over B: Full exchange needs local t2 / t3 and peer t1 / t4
  B-->>U: Observed API output: aggregate RTT, count, status, raw auxiliary fields
  Note over U: Current ranging callback: no four-time export or clock mapping
  Note over B,U: Separate lead: QXDM WLAN definitions and QUTS owned bytes.<br/>Connection to this exchange is UNPROVEN
  Note over A,U: Model needs four valid times and rate correction.<br/>Delay asymmetry still limits offset estimation
  Note over A,U: KEY: solid arrows model radio frames.<br/>Dashed arrow is observed aggregate delivery.<br/>Time flows downward within each separate clock
```

## Uncertainty and rejection

Source: [uncertainty-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/clock-models/diagrams/uncertainty-timestamp-path.mmd).

```mermaid
flowchart TB
  E["Radio event placement: UNKNOWN"] -->|error contribution| SUM["Combine every justified error bound"]
  A["Different delay in each direction: UNKNOWN"] -->|possible offset bias| SUM
  M["Hardware-to-host clock conversion: UNKNOWN"] -->|conversion error| SUM
  D["Age since a valid sample"] --> H["Error may grow while waiting for fresh data"]
  R["Remaining rate error: UNKNOWN"] --> H
  H -->|age-dependent error| SUM
  P["Arithmetic and API read error"] -->|software-verifiable contribution| SUM
  SUM --> G{"Are all required errors bounded
and within the stated target?"}
  G -->|No or unknown: current state| NO(["Keep conversion unavailable or experimental"])
  G -. "Yes, after independent validation" .-> OK(["Candidate for a scoped accuracy claim"])
  X["Wrong clock epoch, stale source or missing packet identity"] -->|reject| NO
  T["QXDM fallback, QUTS interpolation<br/>or missing QDSS timestamp sentinel"] -->|reject as a hardware sample| NO
  B["Owned bytes and 100 ns field units<br/>do not bound clock accuracy"] -. "separate evidence requirement" .-> M
  KEY["KEY: UNKNOWN means no justified bound yet<br/>Solid arrows show required reasoning or rejection<br/>Dotted arrows require additional qualification"]
  classDef unknown fill:#fff2dd,stroke:#ac6b12,color:#241b0e;
  class E,A,M,R,NO,T,B,KEY unknown;
```

## Application adoption

Source: [adoption-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/evidence/diagrams/adoption-timestamp-path.mmd).

```mermaid
flowchart TB
  Q["Implemented: host interval counter QPC"] -->|fast local read| FAST["Application asks for a timestamp"]
  FAST -->|available now| LOCAL["Host-only event record<br/>No synchronized-time claim"]
  REF(["Needed: controlled reference peer"]) -.-> RAW(["Needed: matched raw radio timestamps"])
  NIC(["Local TSF and FTM timer observations"]) -.-> REL(["Establish counter domains and sampling semantics"])
  REL -.-> RAW
  REL -.-> MAP(["Needed: fresh hardware-to-host mapping<br/>with qualified error bounds"])
  RAW -.-> EST(["Estimate relative clock offset and rate"])
  MAP -.-> EST
  EST -.-> SNAP(["Publish a model with identity, epoch and expiry"])
  SNAP -. "only after qualification" .-> FAST
  FAST -. "future qualified model" .-> OUT(["Logical reference-time record"])
  SNAP -. "monitor validity" .-> CHECK["Loss, reset, roam, stale data or unknown error"]
  NIC -. "source changes" .-> CHECK
  CHECK -->|required behavior| INVALID["Invalidate the affected model"]
  INVALID --> FALLBACK["Explicit host-only fallback<br/>or unavailable reference-time result"]
  FALLBACK --> FAST
  INVALID -. "reacquire raw evidence" .-> RAW
  INVALID -. "reestablish mapping" .-> MAP
  OUT -. "separate permission and reference gate" .-> OS(["Future: adjust the operating-system clock"])
  FTM["Current aggregate Wi-Fi ranging result"] --> DIAG["Diagnostics only: cannot supply clock offset"]
  V["Located: QUTS client allocates owned bytes"] --> CONTRACT{"Complete event identity, validity,<br/>clock domain, freshness and epoch?"}
  CONTRACT -->|No: current hardware state| DIAG
  CONTRACT -. "Yes: still needs live producer qualification" .-> RAW
  KEY["KEY: solid = implemented software or required decision<br/>Dotted = future qualified connection<br/>Local measurement, node sync and OS discipline have separate gates"]
  classDef existing fill:#e8f5ed,stroke:#34704a,color:#193323;
  classDef future fill:#fff2dd,stroke:#ac6b12,color:#241b0e;
  class Q,FAST,LOCAL,V existing;
  class REF,RAW,NIC,REL,MAP,EST,SNAP,OUT,OS future;
```

## Reports versus memory ring

Source: [report-vs-ring.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/memory-ring/diagrams/report-vs-ring.mmd).

```mermaid
flowchart TD
    RH[Static: firmware report handler] -->|formats counter words| LOG[Static: diagnostic logger and level gate]
    LOG -->|optional copy before output| RING[Static: circular memory log]
    LOG -->|selected output| ETW[Windows event tracing]
    RING -->|copy and transform| FILE[Static: diagnostic file path]
    RING -->|pointer and length| SPAN[Static: recent-span consumer]
    RH -->|stores low-word difference| DELTA[Per-interface TSF minus SoC]
  NEW["New static lead: QUTS owned diagnostic bytes<br/>Exact firmware-producer connection still UNPROVEN"]
  KEY["KEY: solid arrows describe the selected inspected path<br/>Dotted arrows mark missing or conditional relationships<br/>No new live acquisition is claimed"]
```

## FTM notification routing

Source: [notification-routing.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/ftm/diagrams/notification-routing.mmd).

```mermaid
flowchart LR
  B["Merged FTM buffer"] --> P["Parser 0x146ef0"]
  P --> R["Selected fields and RTT banks"]
  P -. "wake waiting task" .-> E(["Host signal: KeSetEvent<br/>request context +0x89f8"])
  R --> A["Aggregate builder 0x1462a0"]
  A --> S["Serializer 0x161c80"]
  S --> F["Common WDI sender: selector 0x89"]
  T["Synthetic test / SAR payload"] --> D["Device-service helper 0x137ca8"]
  D --> N["Common WDI sender: selector 0x85"]
  NEW["New static lead: QUTS owned diagnostic bytes<br/>Exact firmware-producer connection still UNPROVEN"]
  KEY["KEY: solid arrows describe the selected inspected path<br/>Dotted arrows mark missing or conditional relationships<br/>No new live acquisition is claimed"]
```

## FTM reduction

Source: [ftm-reduction.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/clock-models/diagrams/ftm-reduction.mmd).

```mermaid
flowchart LR
  F["Firmware OEM measurement payload"] --> P["64-byte per-record entry, tag 0x2b"]
  P --> D["+0x18 t3_del / +0x1c t4_del"]
  D --> S["Signed 32-bit modular difference"]
  S --> B["Two RTT storage banks"]
  B --> A["Filtering and mean selection"]
  A --> C["104-byte aggregate userspace result"]
  P -.-> U["+0x08..+0x17 opaque region not read by this loop"]
  U -.-> X["Absolute timestamp interpretation and extraction UNQUALIFIED"]
  NEW["New static lead: QUTS owned diagnostic bytes<br/>Exact firmware-producer connection still UNPROVEN"]
  KEY["KEY: solid arrows describe the selected inspected path<br/>Dotted arrows mark missing or conditional relationships<br/>No new live acquisition is claimed"]
```

## Vendor return candidates

Source: [vendor-return-paths.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/da4f55e48a368f59ed68ee4427013a83b5c06070/docs/adapters/diagrams/vendor-return-paths.mmd).

```mermaid
flowchart TB
  FW["1. Exact Wi-Fi timing producer<br/>Frame plus TSF / FTM / RX metadata"]
  LINK{"2. Proven connection to a<br/>diagnostic device and protocol?"}
  FW -. "Not yet demonstrated" .-> LINK
  LINK -. "Candidate only" .-> Q["3. QUTS DiagPacket<br/>Binary bytes plus optional identity and times"]
  Q -->|Static client implementation| OWN["4. Thrift reader allocates byte array<br/>Application owns these bytes"]
  OWN --> CHECK{"5. Complete, fresh, valid<br/>and attributable timing event?"}
  CHECK -->|No or ambiguous| REJECT["Retain diagnostic evidence<br/>Reject as a clock input"]
  CHECK -. "After live qualification" .-> RECORD["Scoped hardware observation"]
  RECORD -. "Separate fresh sampling contract" .-> QPC["Hardware-to-QPC relationship"]
  P["QPST QUTS references<br/>Connection bookkeeping located"] --> PONLY["Useful interface evidence<br/>No timestamp return demonstrated here"]
  X["QXDM WLAN definition data<br/>and byte-array accessor"] -. "Firmware/schema match required" .-> CHECK
  U["QUD USB request-owned buffers"] -. "Different transport from this PCI adapter" .-> LINK
  KEY["KEY: solid = located code or required validation<br/>Dotted = missing evidence connection<br/>Byte ownership does not establish clock accuracy"]
  classDef known fill:#e8f5ed,stroke:#34704a,color:#193323;
  classDef gap fill:#fff2dd,stroke:#ac6b12,color:#241b0e;
  class OWN,P,PONLY known;
  class LINK,CHECK,REJECT,QPC,KEY gap;
```
