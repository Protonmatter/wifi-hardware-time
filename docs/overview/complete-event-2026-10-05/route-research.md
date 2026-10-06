# Complete-event export: which avenues remain useful?

The strongest native-Windows route still requires a supported event-return facility or instrumentation inside the valid producer lifetime. Packet filters and tracing can only return data their observation point actually receives. Source-accessible Linux offers a practical alternative development path, but the inspected stock ath12k trace/test interfaces do not already provide a generic original WMI-event export for this task.

## Contents

- [Decision table](#decision-table)
- [What primary sources add](#what-primary-sources-add)
- [What would change the decision](#what-would-change-the-decision)

## Decision table

| Avenue | What it offers | Missing prerequisite / limitation | Decision |
|---|---|---|---|
| Supported Qualcomm/OEM event export | Native producer knowledge and possibly an existing return path | Matching package/interface, exact device binding, original bytes and lifetime contract | Highest-value external dependency; inspect supplied package before execution |
| Instrumented Windows producer | Copy at the selected WMI or HIF boundary; retain original event and host observations | Driver source or supported extension/callback, WDK/build/signing and a controlled deployment target | Preferred native implementation once integration exists |
| Existing private return paths | Fixed test return, QUTS owned bytes, ART2/packet-log leads | No qualified complete timing producer; some routes alter state or have publication gaps | Keep operation-specific evidence; no speculative sends or campaign restart |
| NDIS filter / packet capture | Receive indications, packet context and any timestamps actually supplied by the miniport | Private WMI event is not demonstrated in that interface | Useful observation/comparison path; cannot reconstruct omitted metadata |
| Existing ETW/WPP instrumentation | Driver-emitted records with host trace timing | Exact callsite must emit the needed bytes; provider flags do not insert new source copies | Revisit only after locating a complete-payload logging site |
| Documented Windows cross timestamps | Adapter-supplied hardware/host relationship | Working capability/operation on the actual adapter | Retain separate diagnostic lane; do not infer hardware absence from a missing private OID branch |
| Source-accessible ath12k/mt76 backend | Ability to place a reviewed copy in the actual producer | Compatible physical hardware/OS, source/build/firmware qualification and live tests | Strong alternative when such a test target is available; no platform switch in this run |
| Debugger breakpoint / arbitrary kernel read | Can inspect selected execution state | Pauses/perturbs timing; a pointer read does not solve publication or lifetime | Not a clock-acquisition implementation or accuracy experiment |

## What primary sources add

### Windows packet and tracing boundaries

An NDIS filter receives the `NET_BUFFER_LIST` objects indicated by an underlying
driver. Its retention rights depend on the receive flags, and some cases require
copying before returning. That is a useful owned-packet pattern, but does not
establish visibility into a private firmware control message before reduction.
The last sentence is an inference from the documented observation point and our
exact-driver trace, not a claim that all vendor extensions are impossible.
[Microsoft filter contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/receiving-data-in-a-filter-driver).

NDIS hardware timestamps must be supplied by the miniport through packet
metadata. A later filter cannot establish a radio timestamp merely by adding a
host counter reading. [Packet timestamp attachment](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/attaching-timestamps-to-packets).

WPP requires instrumentation in the emitting component. Enabling a provider can
activate existing instrumentation; it does not supply an arbitrary new payload
copy point. Delivery delay is separate from the meaning of the producer's trace
time. [WPP overview](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/wpp-software-tracing).

The supported Windows cross-timestamp API remains a separate way to request a
hardware/host relationship. NDIS answers timestamp-capability OIDs from miniport
capability information, so absence of a private OID handler is not a hardware
support verdict. [Cross-timestamp API](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-captureinterfacehardwarecrosstimestamp),
[capability handling](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-capability).

### Pinned Linux comparison

The comparison uses Linux commit `67f0943b394d920b6c142aad8c6af94340342ae7`,
resolved from upstream on 2026-10-05. It is architecture/source evidence, not the
schema of the installed Qualcomm Windows firmware.

- `ath12k_wmi_op_rx` removes the WMI header before dispatch. Its diagnostic-event
  case reaches `ath12k_wmi_diag_event`; the latter copies the remaining payload
  through `trace_ath12k_wmi_diag`.
- That trace declaration retains device/driver strings and binary data. It is
  specific to that dispatched diagnostic event, not a generic capture of every
  original WMI envelope. Its readable print format does not print the full bytes.
- `WMI_PDEV_UTF_EVENTID` takes a separate test-event path. The unsegmented return
  allocates a netlink event and copies payload bytes, but selects a radio in test
  mode. The test-mode start operation requires the hardware state to be OFF.
  This is not an ordinary connected-Wi-Fi TSF getter.

Sources: pinned
[wmi.c](https://github.com/torvalds/linux/blob/67f0943b394d920b6c142aad8c6af94340342ae7/drivers/net/wireless/ath/ath12k/wmi.c),
[trace.h](https://github.com/torvalds/linux/blob/67f0943b394d920b6c142aad8c6af94340342ae7/drivers/net/wireless/ath/ath12k/trace.h),
[testmode.c](https://github.com/torvalds/linux/blob/67f0943b394d920b6c142aad8c6af94340342ae7/drivers/net/wireless/ath/ath12k/testmode.c).

A future instrumented Linux backend could use a purpose-built event trace before
header removal, with explicit bounds, loss and continuity. Kernel event formats
describe binary fields, and the ring buffer has a defined publication design.
Neither fact guarantees an arbitrary driver tracepoint contains the needed event.
[Event formats](https://docs.kernel.org/trace/events.html),
[ring-buffer publication](https://docs.kernel.org/trace/ring-buffer-design.html).

### Lifetime is a separate engineering requirement

Windows rundown protection can deny new accesses while waiting for existing
protected accesses to finish. It does not serialize payload writers/readers or
prove device DMA has stopped. A producer-owned callback integration must use
appropriate lifecycle and publication mechanisms together.
[Rundown protection](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/run-down-protection).

Similarly, cancellation is not automatically a join: `WdfDpcCancel` waits only
when requested, while `WdfWorkItemFlush` concerns one work item, not every callback
or firmware command. Those distinctions guide the exact-driver shutdown trace.
[DPC cancellation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfdpc/nf-wdfdpc-wdfdpccancel),
[work-item completion](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfworkitem/nf-wdfworkitem-wdfworkitemflush).

## What would change the decision

- A matching vendor package exposing a complete event and an attributable endpoint.
- A supported extension callback or instrumented driver build at the selected boundary.
- A compatible physical Linux target with a reviewed producer-copy implementation.
- A newly located logging callsite that actually preserves the required bytes.

Without one of those changes, additional byte-broker tests or repeated negative
discovery cannot create the missing hardware connection. The executable next
slice is the [shutdown/ownership audit](engineering-plan.md), with bounded scope
and an explicit report if an indirect call or external integration remains open.
