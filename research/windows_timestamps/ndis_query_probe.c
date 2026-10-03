#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iphlpapi.h>
#include <evntprov.h>
#include <objbase.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* One documented read-only call. No provider installation or device IOCTL.
 * Run only through the bounded, identity-checking experiment wrapper.
 * API errors are observations; setup/clock/marker cleanup errors fail the process.
 */
static const GUID marker_provider = {0x209754d0,0x15cd,0x42dd,{0xa9,0xb9,0xd1,0xb3,0x8a,0x60,0x6c,0x08}};
static void print_guid(const GUID *g)
{
    printf("\"%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x\"",
        g->Data1,g->Data2,g->Data3,g->Data4[0],g->Data4[1],g->Data4[2],g->Data4[3],
        g->Data4[4],g->Data4[5],g->Data4[6],g->Data4[7]);
}
static void print_caps(const INTERFACE_TIMESTAMP_CAPABILITIES *c)
{
    const INTERFACE_HARDWARE_TIMESTAMP_CAPABILITIES *h=&c->HardwareCapabilities;
    printf("\"hardware_clock_frequency_hz\":\"%llu\",\"supports_cross_timestamp\":%u",
        c->HardwareClockFrequencyHz,(unsigned)c->SupportsCrossTimestamp);
    printf(",\"hardware_capabilities\":{\"ptp_ipv4_event_receive\":%u,\"ptp_ipv4_all_receive\":%u,\"ptp_ipv4_event_transmit\":%u,\"ptp_ipv4_all_transmit\":%u,\"ptp_ipv6_event_receive\":%u,\"ptp_ipv6_all_receive\":%u,\"ptp_ipv6_event_transmit\":%u,\"ptp_ipv6_all_transmit\":%u,\"all_receive\":%u,\"all_transmit\":%u,\"tagged_transmit\":%u}",
        (unsigned)h->PtpV2OverUdpIPv4EventMessageReceive,(unsigned)h->PtpV2OverUdpIPv4AllMessageReceive,
        (unsigned)h->PtpV2OverUdpIPv4EventMessageTransmit,(unsigned)h->PtpV2OverUdpIPv4AllMessageTransmit,
        (unsigned)h->PtpV2OverUdpIPv6EventMessageReceive,(unsigned)h->PtpV2OverUdpIPv6AllMessageReceive,
        (unsigned)h->PtpV2OverUdpIPv6EventMessageTransmit,(unsigned)h->PtpV2OverUdpIPv6AllMessageTransmit,
        (unsigned)h->AllReceive,(unsigned)h->AllTransmit,(unsigned)h->TaggedTransmit);
    printf(",\"software_capabilities\":{\"all_receive\":%u,\"all_transmit\":%u,\"tagged_transmit\":%u}",
        (unsigned)c->SoftwareCapabilities.AllReceive,(unsigned)c->SoftwareCapabilities.AllTransmit,
        (unsigned)c->SoftwareCapabilities.TaggedTransmit);
}
int main(int argc,char **argv)
{
    NET_LUID luid={0}; GUID adapter,activity,previous;
    INTERFACE_TIMESTAMP_CAPABILITIES caps={0};
    INTERFACE_HARDWARE_CROSSTIMESTAMP cross={0};
    LARGE_INTEGER frequency,before,after;
    REGHANDLE registration=0; DWORD index,rc,pid,tid; char *end=NULL;
    ULONG marker_begin=ERROR_SUCCESS,marker_end=ERROR_SUCCESS,restore,unregister_status=ERROR_SUCCESS;
    int operation,markers; BOOL before_ok,after_ok;
    if(argc==2 && strcmp(argv[1],"--help")==0){puts("ndis_query_probe IFINDEX supported|active|cross [--markers]");return 0;}
    if((argc!=3 && argc!=4) || argv[1][0]<'1' || argv[1][0]>'9')return 2;
    markers=argc==4;
    if(markers && strcmp(argv[3],"--markers")!=0)return 2;
    operation=strcmp(argv[2],"supported")==0 ? 0 : strcmp(argv[2],"active")==0 ? 1 : strcmp(argv[2],"cross")==0 ? 2 : -1;
    if(operation<0)return 2;
    errno=0;index=strtoul(argv[1],&end,10);
    if(errno || !end || *end || !index || index>0x7fffffff)return 2;
    rc=ConvertInterfaceIndexToLuid(index,&luid);
    if(rc){fprintf(stderr,"Interface LUID lookup failed: %lu\n",rc);return 1;}
    rc=ConvertInterfaceLuidToGuid(&luid,&adapter);
    if(rc){fprintf(stderr,"Interface GUID lookup failed: %lu\n",rc);return 1;}
    if(!QueryPerformanceFrequency(&frequency) || frequency.QuadPart<=0 || FAILED(CoCreateGuid(&activity)))return 1;
    previous=activity;
    rc=EventActivityIdControl(EVENT_ACTIVITY_CTRL_GET_SET_ID,&previous);
    if(rc)return 1;
    if(markers){
        rc=EventRegister(&marker_provider,NULL,NULL,&registration);
        if(rc){EventActivityIdControl(EVENT_ACTIVITY_CTRL_SET_ID,&previous);return 1;}
    }
    pid=GetCurrentProcessId();tid=GetCurrentThreadId();
    if(markers)marker_begin=EventWriteString(registration,4,1,L"query-begin");
    before_ok=QueryPerformanceCounter(&before);
    if(before_ok){
        if(operation==0)rc=GetInterfaceSupportedTimestampCapabilities(&luid,&caps);
        else if(operation==1)rc=GetInterfaceActiveTimestampCapabilities(&luid,&caps);
        else rc=CaptureInterfaceHardwareCrossTimestamp(&luid,&cross);
    } else rc=ERROR_INVALID_DATA;
    after_ok=QueryPerformanceCounter(&after);
    if(markers)marker_end=EventWriteString(registration,4,1,L"query-end");
    restore=EventActivityIdControl(EVENT_ACTIVITY_CTRL_SET_ID,&previous);
    if(markers)unregister_status=EventUnregister(registration);
    if(!before_ok || !after_ok || before.QuadPart<0 || after.QuadPart<before.QuadPart)return 1;
    printf("{\"schema\":\"ndis-query/v1\",\"operation\":\"%s\",\"interface_index\":%lu,\"interface_guid\":",argv[2],index);
    print_guid(&adapter);printf(",\"activity_id\":");print_guid(&activity);
    printf(",\"interface_luid\":\"%llu\",\"oid\":\"0x%08x\"",luid.Value,0x00a00001+(unsigned)operation);
    printf(",\"pid\":%lu,\"tid\":%lu,\"qpc_frequency_hz\":\"%lld\",\"qpc_before\":\"%lld\",\"qpc_after\":\"%lld\",\"return_code\":%lu",
        pid,tid,frequency.QuadPart,before.QuadPart,after.QuadPart,rc);
    if(!rc){
        printf(",\"values\":{");
        if(operation==2)printf("\"system_timestamp_1\":\"%llu\",\"hardware_clock_timestamp\":\"%llu\",\"system_timestamp_2\":\"%llu\"",cross.SystemTimestamp1,cross.HardwareClockTimestamp,cross.SystemTimestamp2);
        else print_caps(&caps);
        printf("}");
    } else printf(",\"values\":null");
    printf(",\"markers_requested\":%s,\"marker_begin_status\":%lu,\"marker_end_status\":%lu,\"activity_restore_status\":%lu,\"unregister_status\":%lu,\"kernel_activity_binding_established\":false}\n",
        markers?"true":"false",marker_begin,marker_end,restore,unregister_status);
    return marker_begin || marker_end || restore || unregister_status ? 1 : 0;
}
