#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iphlpapi.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

/* Independent SDK layout / return-code check. Read-only, no device IOCTLs. */
int main(int argc, char **argv)
{
    NET_LUID luid = {0};
    INTERFACE_TIMESTAMP_CAPABILITIES caps = {0};
    char *end = NULL;
    unsigned long index;
    DWORD result;
    if (argc != 2) return 2;
    index = strtoul(argv[1], &end, 10);
    if (!index || !end || *end) return 2;
    printf("sizeof_caps=%zu hardware_offset=%zu software_offset=%zu\n",
        sizeof(caps), offsetof(INTERFACE_TIMESTAMP_CAPABILITIES, HardwareCapabilities),
        offsetof(INTERFACE_TIMESTAMP_CAPABILITIES, SoftwareCapabilities));
    result = ConvertInterfaceIndexToLuid(index, &luid);
    printf("ConvertInterfaceIndexToLuid=%lu\n", result);
    if (result != NO_ERROR) return 1;
    result = GetInterfaceSupportedTimestampCapabilities(&luid, &caps);
    printf("GetInterfaceSupportedTimestampCapabilities=%lu\n", result);
    ZeroMemory(&caps, sizeof(caps));
    result = GetInterfaceActiveTimestampCapabilities(&luid, &caps);
    printf("GetInterfaceActiveTimestampCapabilities=%lu\n", result);
    return 0;
}
