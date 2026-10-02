# Sources and provenance

## Vendor downloads

- [ALFA AWUS036AXML specification](https://www.alfa.com.tw/products/awus036axml)
- [ALFA Windows Wi-Fi directory](https://files.alfa.com.tw/?dir=%5B1%5D%20WiFi%20USB%20adapter/AWUS036AXML/Windows/WiFi)
- [ALFA Linux directory](https://files.alfa.com.tw/?dir=%5B1%5D%20WiFi%20USB%20adapter/AWUS036AXML/Linux)

The Windows Qualcomm binary was read from an existing installation. This repository does not supply it. Artifact hashes and versions are identification evidence, not download authenticity guarantees or redistribution permission.

## Pinned source trees

- [mt76](https://github.com/openwrt/mt76/tree/be5ce7910521492d4a2e4ce7ee3843680a46c047): `be5ce7910521492d4a2e4ce7ee3843680a46c047`.
- [WiFi PTP](https://github.com/zlab-pub/wifi-ptp/tree/2d45217058dbba429dcbc4517c83a601a39efac5): `2d45217058dbba429dcbc4517c83a601a39efac5`.
- [mac80211 debugfs reference](https://github.com/torvalds/linux/blob/ce1e0223d8ad4211275c82a17ed6d43ab81e13d9/net/mac80211/debugfs_netdev.c): separate Linux snapshot, not a tested build pairing with mt76.
- [Qualcomm WMI firmware header](https://android.googlesource.com/kernel/msm/+/efc684e83e29f4a8d0dd0f6cde762c78897f769a/drivers/staging/fw-api/fw/wmi_unified.h): TSF action semantics; different firmware/source lineage.
- [ath12k WCN7850 PCI reference](https://android.googlesource.com/kernel/common/+/3a8a670eeeaa40d87bd38a587438952741980c18/drivers/net/wireless/ath/ath12k/pci.c): hardware-version register read; does not establish Windows QMI mapping.
- [WiFi PTP paper](https://www.usenix.org/conference/atc21/presentation/chen): performance claims belong to the studied configurations, not these unqualified backends.

## Microsoft API contracts

- [NDIS cross timestamps](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-get-crosstimestamp)
- [NBL timestamp attachment](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/nbltimestamp/nf-nbltimestamp-ndissetnbltimestampinfo)
- [Supported timestamp capabilities](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getinterfacesupportedtimestampcapabilities)
- [Hardware cross-timestamp query](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-captureinterfacehardwarecrosstimestamp)
- [WLAN BSS timestamp fields](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_bss_entry)
- [WDI FTM request](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-wdi-task-request-ftm)
- [IHV control](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanihvcontrol)

SDK structure layouts were checked locally against Windows SDK 10.0.26100.0. All third-party code and documents retain their own licensing; none is vendored in this repository.
