# ALFA AWUS036AXML / MT7921AUN

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__adapters__axml.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Can the ALFA USB adapter provide useful hardware timing? Source inspection identifies a readable Wi-Fi timer and packet timestamp fields, but no complete standard timestamp export. Windows register access remains a static finding; no live request or physical timing accuracy was validated for this adapter.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

TSF (Timing Synchronization Function) is the Wi-Fi hardware timer. RX and TX mean receive and transmit; a PHC is a Precision Time Protocol hardware clock. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) for clock and driver terms.

## Contents

- [Acquired artifacts](#acquired-artifacts)
- [Linux source paths](#linux-source-paths)
- [Windows static result](#windows-static-result)
- [WiFi PTP reference](#wifi-ptp-reference)

## Acquired artifacts

ALFA's Windows Wi-Fi installer contained MediaTek WDI (Windows wireless-driver interface) driver version **1.0.0.119**, INF date **2023-09-13**, with x86 and x64 variants. No ARM64 variant was present. Embedded SYS/CAT signatures validated as Microsoft Windows Hardware Compatibility Publisher signatures; the outer installer was unsigned. No installer was executed.

The Linux download contained firmware and a tutorial, not mt76 source or a PTP driver. The separately inspected mt76 source is pinned in [sources](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/sources.md).

| Download | SHA-256 |
|---|---|
| `AWUS036AXMLsetup.exe` | `3e4cb4c09ad9668bdc511347ca970c1dd33900dad032e5c7d167edfe18bd79bf` |
| ALFA MT7921AU Linux archive | `8178d64fcad0d49060b1250fb1aae46972262bb92b424b7ee60b165944d2fabb` |
| Extracted x64 `mtkwl6eux.sys` | `a261b4d4c7307cb12907673a440498088cd6f3b42fc2bd273e4a13766fcbdbb8` |

## Linux source paths

| Location in pinned mt76 tree | Finding |
|---|---|
| `mt792x_core.c`, `mt792x_get_tsf` | Selects OMAC (the hardware MAC context), triggers capture, reads 64-bit TSF low/high words |
| `mt792x_core.c`, `mt792x_set_tsf` | Can overwrite the selected timer; keep clock ownership explicit |
| `mt7921/mac.c`, RX group 2 | 32-bit timestamp marked `RX_FLAG_MACTIME_START` |
| `mac80211.c` | Propagates timestamp to mac80211 metadata |
| `mt76_connac2_mac.h` | Defines 32-bit `MT_TXS4_TIMESTAMP` |
| `mt7921/mac.c`, `mt7921_mac_add_txs` | USB-reachable TX status with packet/WCID association |
| `mt76_connac_mac.c` | Requests host TX status for tracked packets; disables hardware A-MSDU for those packets |
| `mt792x_usb.c` / `usb.c` | Register operations use serialized USB control transfers with failure/retry behavior |

The tree does not implement an mt76 PHC or a standard way to return hardware packet timestamps to applications. RX capture metadata and TX descriptor definitions are useful starting points, not proof of a complete timing API.

Band-0 capture registers are `MT_LPON_UTTR0 = 0x820eb080`, `MT_LPON_UTTR1 = 0x820eb084`, and `MT_LPON_TCR(n) = 0x820eb0a8 + 4*n`. These are source-derived addresses, not a tested userspace register recipe. Capture-control writes, correct OMAC selection, locking, USB errors, and reset epochs matter.

Generic mac80211's TSF debugfs file is created for IBSS/mesh in the inspected upstream reference. The mt7921 modes do not advertise those interface types. Existing mt76 `regidx`/`regval` are privileged diagnostics with shared selector state, not an atomic TSF transaction.

Other important limits:

- A-MPDU subframes share timestamp metadata.
- Advertised radiotap units are microseconds; nanosecond formatting would not increase resolution.
- `mt792x_phy_get_nf()` returns zero in the inspected tree. Do not claim measured noise floor from that stub.
- Some airtime counters are reset by reads; independent register polling can disturb driver accounting.
- RF test mode changes normal operating/power behavior and belongs in a separate lab workflow.

## Windows static result

The x64 driver registers an A8000-named control device. An IOCTL is a control request sent to a driver. Its dispatcher accepts IOCTL `0x00170002` and private register operations `0xfffcf001` / `0xfffcf002`. High addresses route through firmware command `0xc0`; a response handler returns a register value to a pending request. This is static reconstruction only; no AXML Windows hardware request was tested.

Static inspection found no positive evidence of standard NDIS (Windows network-driver framework) timestamp or cross-timestamp support. Literal/import absence is not proof of capability absence. The bundled IHV DLL names a different control endpoint, so its integration cannot be assumed to work unchanged.

## WiFi PTP reference

`zlab-pub/wifi-ptp` implements a TSF-backed virtual PHC for ath9k/AR9300-class PCI hardware on an older kernel baseline. Its kernel/userspace components use a custom timestamp encoding and debugfs conversion, bypass some capability/configuration failures, and apply hardware-specific corrections. Study its clock-conversion ideas; do not transplant its contract or performance results to MT7921 USB.
