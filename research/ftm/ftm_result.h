#ifndef WIFI_TIME_FTM_RESULT_H
#define WIFI_TIME_FTM_RESULT_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Pure check for the exact-build 104-byte callback record. Does not establish
 * timestamp accuracy; signed/negative RTT estimates are deliberately retained. */
static int ftm_result_complete(const unsigned char *record, size_t length,
                               const unsigned char expected_bssid[6])
{
    uint32_t status;
    uint16_t measurements;
    if (!record || !expected_bssid || length != 104) return 0;
    status = (uint32_t)record[8] | ((uint32_t)record[9] << 8) |
             ((uint32_t)record[10] << 16) | ((uint32_t)record[11] << 24);
    measurements = (uint16_t)((uint16_t)record[14] | ((uint16_t)record[15] << 8));
    return status == 0 && measurements > 0 && memcmp(record, expected_bssid, 6) == 0;
}
#endif
