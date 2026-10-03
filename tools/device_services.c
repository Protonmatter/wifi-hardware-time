#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iphlpapi.h>
#include <wlanapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

/* Documented read-only queries. Service GUIDs are contracts, not device IDs. */
int main(int argc, char **argv)
{
    NET_LUID luid = {0};
    GUID guid;
    INTERFACE_HARDWARE_CROSSTIMESTAMP cross = {0};
    WLAN_DEVICE_SERVICE_GUID_LIST *services = NULL;
    HANDLE client = NULL;
    DWORD rc, version, index, i;
    char *end = NULL;
    if (argc != 2 || argv[1][0] < '1' || argv[1][0] > '9') {
        fputs("Usage: device_services.exe INTERFACE_INDEX\n", stderr); return 2;
    }
    errno = 0;
    index = strtoul(argv[1], &end, 10);
    if (errno || !index || index > 0x7fffffff || !end || *end) return 2;
    rc = ConvertInterfaceIndexToLuid(index, &luid);
    if (rc) { fprintf(stderr, "Interface lookup failed: %lu\n", rc); return 1; }
    rc = ConvertInterfaceLuidToGuid(&luid, &guid);
    if (rc) { fprintf(stderr, "Interface GUID lookup failed: %lu\n", rc); return 1; }
    rc = CaptureInterfaceHardwareCrossTimestamp(&luid, &cross);
    printf("{\"cross_timestamp_rc\":%lu", rc);
    if (!rc) printf(",\"qpc_before\":%llu,\"hardware_raw\":%llu,\"qpc_after\":%llu",
        cross.SystemTimestamp1, cross.HardwareClockTimestamp, cross.SystemTimestamp2);
    rc = WlanOpenHandle(2, NULL, &version, &client);
    printf(",\"wlan_open_rc\":%lu", rc);
    if (rc) { puts("}"); return 0; }
    rc = WlanGetSupportedDeviceServices(client, &guid, &services);
    printf(",\"device_services_rc\":%lu", rc);
    if (!rc && services && services->dwNumberOfItems <= 64) {
        printf(",\"service_count\":%lu,\"service_guids\":[", services->dwNumberOfItems);
        for (i = 0; i < services->dwNumberOfItems; ++i) {
            const GUID *g = &services->DeviceService[i];
            printf("%s\"%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x\"",
                i ? "," : "", g->Data1, g->Data2, g->Data3,
                g->Data4[0], g->Data4[1], g->Data4[2], g->Data4[3],
                g->Data4[4], g->Data4[5], g->Data4[6], g->Data4[7]);
        }
        printf("]");
    } else if (!rc) {
        printf(",\"invalid_service_list\":true");
    }
    if (services) WlanFreeMemory(services);
    rc = WlanCloseHandle(client, NULL);
    printf(",\"wlan_close_rc\":%lu,\"service_commands_sent\":0}\n", rc);
    return 0;
}
