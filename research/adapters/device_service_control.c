/* Exact-build positive control. Use Invoke-DeviceServiceControl.ps1.
 * One service-list query, optionally one fixed test-service GET. No arbitrary
 * GUID/opcode/input, notification registration, cross timestamp or TSF request.
 * --self-test and --help never call the WLAN API. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iphlpapi.h>
#include <wlanapi.h>
#include <objbase.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

static const GUID test_service = {0x24364cfe,0x2ae8,0x4ed5,{0x96,0x43,0xa0,0x61,0xf7,0,0xad,0x5f}};
static int valid_response(DWORD rc,DWORD returned,const unsigned char *bytes,size_t capacity)
{
    static const unsigned char expected[8]={1,2,3,4,5,6,7,8};
    return rc==ERROR_SUCCESS && returned==8 && capacity>=8 && bytes!=NULL && memcmp(bytes,expected,8)==0;
}
static int self_test(void)
{
    unsigned char bytes[8]={1,2,3,4,5,6,7,8};
    if(!valid_response(0,8,bytes,8) || valid_response(5,8,bytes,8) ||
       valid_response(0,7,bytes,8) || valid_response(0,9,bytes,8) ||
       valid_response(0,8,bytes,7) || valid_response(0,8,NULL,8)) return 1;
    bytes[4]^=1;
    if(valid_response(0,8,bytes,8))return 1;
    puts("Fixed-response acceptance and rejection checks passed.");
    return 0;
}
int main(int argc,char **argv)
{
    NET_LUID luid={0}; GUID guid,expected_guid;
    HANDLE client=NULL,token=NULL; TOKEN_ELEVATION elevation={0}; DWORD token_size=0;
    WLAN_DEVICE_SERVICE_GUID_LIST *services=NULL;
    DWORD index,rc,version,i,returned=0,close_rc=0,commands=0; char *end=NULL;
    wchar_t guid_text[40]; unsigned char output[64];
    LARGE_INTEGER before={0},after={0},frequency={0};
    BOOL do_get=FALSE,found=FALSE,valid=FALSE; int result=1;
    if(argc==2 && !strcmp(argv[1],"--self-test"))return self_test();
    if(argc==2 && !strcmp(argv[1],"--help")){
        puts("Use wrapper. --execute INDEX EXPECTED_GUID [--test-get]; --self-test.");return 0;
    }
    if((argc!=4 && argc!=5) || strcmp(argv[1],"--execute") ||
       argv[2][0]<'1' || argv[2][0]>'9' ||
       (argc==5 && strcmp(argv[4],"--test-get")))return 2;
    do_get=(argc==5);
    errno=0;index=strtoul(argv[2],&end,10);
    if(errno || !end || *end || index==0 || index>0x7fffffff)return 2;
    if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,argv[3],-1,guid_text,40) ||
       FAILED(CLSIDFromString(guid_text,&expected_guid)))return 2;
    rc=ConvertInterfaceIndexToLuid(index,&luid);
    if(!rc)rc=ConvertInterfaceLuidToGuid(&luid,&guid);
    if(rc || memcmp(&guid,&expected_guid,sizeof(guid))){
        puts("{\"target_identity_matched\":false,\"service_commands_sent\":0}");return 1;
    }
    if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token))return 1;
    if(!GetTokenInformation(token,TokenElevation,&elevation,sizeof(elevation),&token_size)){
        CloseHandle(token);return 1;
    }
    CloseHandle(token);
    printf("{\"schema\":\"wht/device-service-positive-control-v1\",\"target_identity_matched\":true,\"elevated\":%s",
           elevation.TokenIsElevated?"true":"false");
    rc=WlanOpenHandle(2,NULL,&version,&client);
    printf(",\"wlan_open_rc\":%lu",rc);
    if(rc)goto finish;
    rc=WlanGetSupportedDeviceServices(client,&guid,&services);
    printf(",\"service_list_rc\":%lu",rc);
    /* dwIndex is application-owned, not a validated output from this API. */
    if(rc || !services || services->dwNumberOfItems>64)goto cleanup;
    printf(",\"service_count\":%lu,\"service_guids\":[",services->dwNumberOfItems);
    for(i=0;i<services->dwNumberOfItems;i++){
        const GUID *g=&services->DeviceService[i];
        if(!memcmp(g,&test_service,sizeof(*g)))found=TRUE;
        printf("%s\"%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x\"",
               i?",":"",g->Data1,g->Data2,g->Data3,g->Data4[0],g->Data4[1],g->Data4[2],g->Data4[3],
               g->Data4[4],g->Data4[5],g->Data4[6],g->Data4[7]);
    }
    printf("],\"test_service_advertised\":%s",found?"true":"false");
    if(!do_get){result=0;goto cleanup;}
    if(!found || !QueryPerformanceFrequency(&frequency) || !QueryPerformanceCounter(&before))goto cleanup;
    memset(output,0xa5,sizeof(output));
    commands=1;
    rc=WlanDeviceServiceCommand(client,&guid,(GUID *)&test_service,1,0,NULL,sizeof(output),output,&returned);
    if(!QueryPerformanceCounter(&after))after.QuadPart=0;
    valid=valid_response(rc,returned,output,sizeof(output));
    printf(",\"test_get_attempted\":true,\"test_get_rc\":%lu,\"bytes_returned\":%lu,\"fixed_pattern_matched\":%s",
           rc,returned,valid?"true":"false");
    printf(",\"host_call_qpc_before\":%lld,\"host_call_qpc_after\":%lld,\"qpc_frequency\":%lld",
           before.QuadPart,after.QuadPart,frequency.QuadPart);
    if(!rc && returned<=sizeof(output)){
        printf(",\"returned_hex\":\"");for(i=0;i<returned;i++)printf("%02x",output[i]);printf("\"");
    }
    result=valid?0:1;
cleanup:
    if(services)WlanFreeMemory(services);
    close_rc=WlanCloseHandle(client,NULL);client=NULL;
    printf(",\"wlan_close_rc\":%lu",close_rc);
    if(close_rc)result=1;
finish:
    printf(",\"service_commands_sent\":%lu,\"firmware_timing_event_qualified\":false,\"hardware_qpc_qualified\":false}\n",commands);
    return result;
}
