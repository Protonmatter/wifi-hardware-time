#include "../experiments/qualcomm/ftm_result.h"
#include <stdio.h>

int main(void)
{
    const unsigned char bssid[6] = {2,1,2,3,4,5};
    unsigned char data[104] = {0};
    memcpy(data,bssid,6);
    /* Reproduced live failure: status zero, matching target, no measurements,
       RTT -1. Transport success must not turn this into a successful sample. */
    memset(data+28,0xff,4);
    if (ftm_result_complete(data,sizeof(data),bssid)) return 1;
    data[14]=1;
    if (!ftm_result_complete(data,sizeof(data),bssid)) return 2;
    /* A negative RTT with actual measurements must remain representable. */
    if (ftm_result_complete(data,103,bssid)) return 3;
    data[0]=4;
    if (ftm_result_complete(data,sizeof(data),bssid)) return 4;
    data[0]=2;data[8]=1;
    if (ftm_result_complete(data,sizeof(data),bssid)) return 5;
    if (ftm_result_complete(NULL,104,bssid)) return 6;
    puts("FTM result regression checks passed");
    return 0;
}
