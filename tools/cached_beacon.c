#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wlanapi.h>
#include <objbase.h>
#include <stdio.h>
#include <stddef.h>
#include <string.h>

/* Read existing BSS cache only. Never scans, sends FTM, or prints network IDs. */
static int responder(const WLAN_BSS_LIST *list, const WLAN_BSS_ENTRY *entry)
{
    size_t base = (const unsigned char *)entry - (const unsigned char *)list;
    size_t pos = base + entry->ulIeOffset;
    size_t end = pos + entry->ulIeSize;
    const unsigned char *p = (const unsigned char *)list;
    if (pos < base || end < pos || end > list->dwTotalSize) return -1;
    while (pos + 2 <= end) {
        unsigned int id = p[pos], length = p[pos + 1];
        pos += 2;
        if (length > end - pos) return -1;
        /* Extended Capabilities bit 70: FTM responder. */
        if (id == 127 && length >= 9) return (p[pos + 8] & 0x40) ? 1 : 0;
        pos += length;
    }
    return pos == end ? 0 : -1;
}

int wmain(int argc, wchar_t **argv)
{
    GUID guid;
    HANDLE client = NULL;
    DWORD version = 0, size = 0, rc, bss_rc, i, matches = 0, responders = 0;
    WLAN_CONNECTION_ATTRIBUTES *connection = NULL;
    WLAN_BSS_LIST *list = NULL;
    WLAN_DEVICE_SERVICE_GUID_LIST *services = NULL;
    if (argc != 2 || FAILED(CLSIDFromString(argv[1], &guid))) return 2;
    rc = WlanOpenHandle(2, NULL, &version, &client);
    printf("{\"wlan_open_rc\":%lu", rc);
    if (rc) { puts("}"); return 0; }
    rc = WlanGetSupportedDeviceServices(client, &guid, &services);
    printf(",\"device_services_query_rc\":%lu", rc);
    if (!rc && services) printf(",\"device_services_count\":%lu", services->dwNumberOfItems);
    if (services) WlanFreeMemory(services);
    rc = WlanQueryInterface(client, &guid, wlan_intf_opcode_current_connection,
                           NULL, &size, (void **)&connection, NULL);
    printf(",\"current_connection_rc\":%lu", rc);
    if (rc || size < sizeof(*connection)) goto cleanup;
    printf(",\"connection_state\":%u", connection->isState);
    bss_rc = WlanGetNetworkBssList(client, &guid, NULL, dot11_BSS_type_any,
                                  FALSE, NULL, &list);
    printf(",\"bss_query_rc\":%lu", bss_rc);
    if (bss_rc) goto cleanup;
    if (list->dwTotalSize < offsetof(WLAN_BSS_LIST, wlanBssEntries) ||
        list->dwTotalSize > 16 * 1024 * 1024 ||
        list->dwNumberOfItems > (list->dwTotalSize - offsetof(WLAN_BSS_LIST, wlanBssEntries)) / sizeof(WLAN_BSS_ENTRY)) {
        printf(",\"invalid_bss_bounds\":true"); goto cleanup;
    }
    printf(",\"cached_entry_count\":%lu,\"current_bss\":[", list->dwNumberOfItems);
    for (i = 0; i < list->dwNumberOfItems; ++i) {
        const WLAN_BSS_ENTRY *e = &list->wlanBssEntries[i];
        int ftm = responder(list, e);
        if (ftm == 1) ++responders;
        if (memcmp(e->dot11Bssid, connection->wlanAssociationAttributes.dot11Bssid, 6)) continue;
        printf("%s{\"beacon_timestamp_us\":%llu,\"host_timestamp_100ns\":%llu,\"beacon_interval_tu\":%u,\"frequency_khz\":%lu,\"rssi_dbm\":%ld,\"ftm_responder_advertisement\":%d}",
               matches++ ? "," : "", e->ullTimestamp, e->ullHostTimestamp,
               e->usBeaconPeriod, e->ulChCenterFrequency, e->lRssi, ftm);
    }
    printf("],\"current_bss_matches\":%lu,\"cached_ftm_responder_count\":%lu", matches, responders);
cleanup:
    if (list) WlanFreeMemory(list);
    if (connection) WlanFreeMemory(connection);
    WlanCloseHandle(client, NULL);
    puts(",\"active_scan_requested\":false,\"ftm_requested\":false}");
    return 0;
}
