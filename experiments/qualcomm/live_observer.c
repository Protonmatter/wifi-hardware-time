/* Exact-target passive ETW + WLAN lifecycle observer. No private IOCTLs.
 * Reuse the offline decoder's numeric-only event parser without changing it. */
#define wmain offline_decoder_main
#include "../../tools/decode_tsf_etl.c"
#undef wmain
#include <wlanapi.h>
#include <iphlpapi.h>
#include <stdlib.h>

static CRITICAL_SECTION output_lock;
static GUID selected_guid;
static TRACEHANDLE live_trace;
static volatile LONG process_done;
static ULONG process_result;

static LONGLONG tick(void) { LARGE_INTEGER q; QueryPerformanceCounter(&q); return q.QuadPart; }

static void WINAPI live_event(PEVENT_RECORD event)
{
    EnterCriticalSection(&output_lock);
    on_event(event);
    LeaveCriticalSection(&output_lock);
}

static ULONG WINAPI buffer_callback(PEVENT_TRACE_LOGFILEW logfile)
{
    EnterCriticalSection(&output_lock);
    printf("{\"kind\":\"health\",\"qpc\":%lld,\"events_lost\":%lu}\n",tick(),logfile->EventsLost);
    LeaveCriticalSection(&output_lock);
    return TRUE;
}

static void WINAPI notification(PWLAN_NOTIFICATION_DATA data, PVOID context)
{
    int invalidates=0;
    UNREFERENCED_PARAMETER(context);
    if (memcmp(&data->InterfaceGuid,&selected_guid,sizeof(GUID))) return;
    if (data->NotificationSource==WLAN_NOTIFICATION_SOURCE_MSM) {
        invalidates=data->NotificationCode!=wlan_notification_msm_signal_quality_change;
    } else if(data->NotificationSource==WLAN_NOTIFICATION_SOURCE_ACM) {
        switch(data->NotificationCode) {
        case wlan_notification_acm_connection_start:
        case wlan_notification_acm_connection_complete:
        case wlan_notification_acm_connection_attempt_fail:
        case wlan_notification_acm_interface_arrival:
        case wlan_notification_acm_interface_removal:
        case wlan_notification_acm_disconnecting:
        case wlan_notification_acm_disconnected:
        case wlan_notification_acm_operational_state_change:
            invalidates=1; break;
        default: break;
        }
    }
    EnterCriticalSection(&output_lock);
    printf("{\"kind\":\"lifecycle\",\"qpc\":%lld,\"source\":%lu,\"code\":%lu,\"invalidates\":%s}\n",
        tick(),data->NotificationSource,data->NotificationCode,invalidates?"true":"false");
    LeaveCriticalSection(&output_lock);
}

static DWORD WINAPI process_thread(LPVOID unused)
{
    UNREFERENCED_PARAMETER(unused);
    process_result=ProcessTrace(&live_trace,1,NULL,NULL);
    InterlockedExchange(&process_done,1);
    return 0;
}

int wmain(int argc,wchar_t **argv)
{
    EVENT_TRACE_LOGFILEW logfile={0};
    NET_LUID luid={0};
    HANDLE wlan=NULL,stop=NULL,thread=NULL;
    DWORD version=0,rc=0,size=0;
    ULONG close_result=0;
    WLAN_CONNECTION_ATTRIBUTES *connection=NULL;
    unsigned char initial_bssid[6]={0};
    int first=1,failed=0;
    LARGE_INTEGER frequency;
    wchar_t *end=NULL;
    unsigned long index;
    if(argc!=4) {fputs("Usage: live_observer SESSION IFINDEX STOP_EVENT\n",stderr);return 2;}
    index=wcstoul(argv[2],&end,10);
    if(!index||!end||*end)return 2;
    InitializeCriticalSection(&output_lock);
    setvbuf(stdout,NULL,_IONBF,0);
    if(ConvertInterfaceIndexToLuid(index,&luid)||ConvertInterfaceLuidToGuid(&luid,&selected_guid))return 1;
    rc=WlanOpenHandle(2,NULL,&version,&wlan);
    if(rc)return 1;
    rc=WlanRegisterNotification(wlan,WLAN_NOTIFICATION_SOURCE_ACM|WLAN_NOTIFICATION_SOURCE_MSM,FALSE,notification,NULL,NULL,NULL);
    if(rc){WlanCloseHandle(wlan,NULL);return 1;}
    stop=OpenEventW(SYNCHRONIZE,FALSE,argv[3]);
    if(!stop){WlanCloseHandle(wlan,NULL);return 1;}
    logfile.LoggerName=argv[1];
    logfile.ProcessTraceMode=PROCESS_TRACE_MODE_REAL_TIME|PROCESS_TRACE_MODE_EVENT_RECORD|PROCESS_TRACE_MODE_RAW_TIMESTAMP;
    logfile.EventRecordCallback=live_event;logfile.BufferCallback=buffer_callback;
    live_trace=OpenTraceW(&logfile);
    if(live_trace==INVALID_PROCESSTRACE_HANDLE){CloseHandle(stop);WlanCloseHandle(wlan,NULL);return 1;}
    thread=CreateThread(NULL,0,process_thread,NULL,0,NULL);
    if(!thread){CloseTrace(live_trace);CloseHandle(stop);WlanCloseHandle(wlan,NULL);return 1;}
    QueryPerformanceFrequency(&frequency);
    EnterCriticalSection(&output_lock);
    printf("{\"kind\":\"ready\",\"qpc\":%lld,\"perf_frequency_hz\":%lld}\n",tick(),frequency.QuadPart);
    LeaveCriticalSection(&output_lock);
    while(WaitForSingleObject(stop,250)==WAIT_TIMEOUT && !InterlockedCompareExchange(&process_done,0,0)) {
        int connected,changed=0;
        rc=WlanQueryInterface(wlan,&selected_guid,wlan_intf_opcode_current_connection,NULL,&size,(PVOID*)&connection,NULL);
        connected=rc==0 && size>=sizeof(*connection) && connection->isState==wlan_interface_state_connected;
        if(connected) {
            if(first)memcpy(initial_bssid,connection->wlanAssociationAttributes.dot11Bssid,6);
            else changed=memcmp(initial_bssid,connection->wlanAssociationAttributes.dot11Bssid,6)!=0;
        }
        EnterCriticalSection(&output_lock);
        /* Local-only association bytes let the controller detect between-run changes. */
        printf("{\"kind\":\"connection\",\"qpc\":%lld,\"connected\":%s,\"changed\":%s,\"query_status\":%lu,\"association\":\"%02x%02x%02x%02x%02x%02x\"}\n",
            tick(),connected?"true":"false",changed?"true":"false",rc,
            initial_bssid[0],initial_bssid[1],initial_bssid[2],initial_bssid[3],initial_bssid[4],initial_bssid[5]);
        LeaveCriticalSection(&output_lock);
        if(connection){WlanFreeMemory(connection);connection=NULL;}
        first=0;
        if(!connected||changed){failed=1;break;}
    }
    close_result=CloseTrace(live_trace);
    if(WaitForSingleObject(thread,5000)!=WAIT_OBJECT_0)failed=1;
    rc=WlanRegisterNotification(wlan,WLAN_NOTIFICATION_SOURCE_NONE,FALSE,NULL,NULL,NULL,NULL);
    if(rc)failed=1;
    if(WlanCloseHandle(wlan,NULL))failed=1;
    CloseHandle(thread);CloseHandle(stop);
    EnterCriticalSection(&output_lock);
    printf("{\"kind\":\"observer_stopped\",\"process_status\":%lu,\"close_status\":%lu,\"failed\":%s,\"qpc\":%lld}\n",
        process_result,close_result,failed?"true":"false",tick());
    LeaveCriticalSection(&output_lock);
    return failed || (process_result!=ERROR_SUCCESS && process_result!=ERROR_CANCELLED) ||
        (close_result!=ERROR_SUCCESS && close_result!=ERROR_CTX_CLOSE_PENDING) ? 1:0;
}
