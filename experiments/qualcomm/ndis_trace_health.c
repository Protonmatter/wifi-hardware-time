#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <stdio.h>
#include <stddef.h>
#include <string.h>
#include <wchar.h>

/* No payload decoding. Controller modes are restricted to experiment sessions.
 * Validate query before stop; retain BOTH controller reports and closed-file header.
 */
static const GUID ndis={0xcdead503,0x17f5,0x4a3e,{0xb7,0xae,0xdf,0x8c,0xc2,0x90,0x2e,0xb9}};
static const GUID marker={0x209754d0,0x15cd,0x42dd,{0xa9,0xb9,0xd1,0xb3,0x8a,0x60,0x6c,0x08}};
static unsigned long long total,ndis_count,marker_count;
static void print_guid(const GUID *g)
{
    printf("\"%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x\"",g->Data1,g->Data2,g->Data3,
        g->Data4[0],g->Data4[1],g->Data4[2],g->Data4[3],g->Data4[4],g->Data4[5],g->Data4[6],g->Data4[7]);
}
static void WINAPI count_record(PEVENT_RECORD event)
{
    unsigned long long sequence;
    ++total;
    if(memcmp(&event->EventHeader.ProviderId,&ndis,sizeof(GUID))==0)sequence=++ndis_count;
    else if(memcmp(&event->EventHeader.ProviderId,&marker,sizeof(GUID))==0)sequence=++marker_count;
    else return;
    printf("{\"kind\":\"event\",\"provider\":");print_guid(&event->EventHeader.ProviderId);
    printf(",\"id\":%u,\"version\":%u,\"qpc\":\"%lld\",\"pid\":%lu,\"tid\":%lu,\"activity_id\":",
        (unsigned)event->EventHeader.EventDescriptor.Id,(unsigned)event->EventHeader.EventDescriptor.Version,
        event->EventHeader.TimeStamp.QuadPart,event->EventHeader.ProcessId,event->EventHeader.ThreadId);
    print_guid(&event->EventHeader.ActivityId);
    printf(",\"provider_sequence\":%llu}\n",sequence);
}
int wmain(int argc,wchar_t **argv)
{
    ULONG status,closed;
    if(argc==2 && wcscmp(argv[1],L"--help")==0){puts("ndis_trace_health query|stop WifiNdisStatus-NAME | header FILE.etl");return 0;}
    if(argc!=3)return 2;
    if(wcscmp(argv[1],L"query")==0 || wcscmp(argv[1],L"stop")==0){
        struct { EVENT_TRACE_PROPERTIES p; WCHAR name[1024]; WCHAR file[1024]; } buffer={0};
        if(wcsncmp(argv[2],L"WifiNdisStatus-",15)!=0 || wcslen(argv[2])<=15 || wcslen(argv[2])>=1024)return 2;
        buffer.p.Wnode.BufferSize=(ULONG)sizeof(buffer);
        buffer.p.LoggerNameOffset=(ULONG)offsetof(struct { EVENT_TRACE_PROPERTIES p; WCHAR name[1024]; WCHAR file[1024]; },name);
        buffer.p.LogFileNameOffset=(ULONG)offsetof(struct { EVENT_TRACE_PROPERTIES p; WCHAR name[1024]; WCHAR file[1024]; },file);
        status=ControlTraceW(0,argv[2],&buffer.p,wcscmp(argv[1],L"stop")==0?EVENT_TRACE_CONTROL_STOP:EVENT_TRACE_CONTROL_QUERY);
        printf("{\"kind\":\"controller\",\"mode\":\"%ls\",\"status\":%lu",argv[1],status);
        if(!status)printf(",\"events_lost\":%lu,\"log_buffers_lost\":%lu,\"real_time_buffers_lost\":%lu,\"buffers_written\":%lu",buffer.p.EventsLost,buffer.p.LogBuffersLost,buffer.p.RealTimeBuffersLost,buffer.p.BuffersWritten);
        puts("}");return status?1:0;
    }
    if(wcscmp(argv[1],L"header")==0){
        EVENT_TRACE_LOGFILEW log={0}; TRACEHANDLE handle;
        log.LogFileName=argv[2];log.ProcessTraceMode=PROCESS_TRACE_MODE_EVENT_RECORD|PROCESS_TRACE_MODE_RAW_TIMESTAMP;
        log.EventRecordCallback=count_record;
        handle=OpenTraceW(&log);
        if(handle==INVALID_PROCESSTRACE_HANDLE){printf("{\"kind\":\"open_error\",\"status\":%lu}\n",GetLastError());return 1;}
        printf("{\"kind\":\"header\",\"start_time\":\"%lld\",\"end_time\":\"%lld\",\"pointer_size\":%lu,\"clock_type\":%lu,\"perf_frequency_hz\":\"%lld\",\"events_lost\":%lu,\"buffers_lost\":%lu,\"buffers_written\":%lu}\n",
            log.LogfileHeader.StartTime.QuadPart,log.LogfileHeader.EndTime.QuadPart,log.LogfileHeader.PointerSize,
            log.LogfileHeader.ReservedFlags,log.LogfileHeader.PerfFreq.QuadPart,log.LogfileHeader.EventsLost,log.LogfileHeader.BuffersLost,log.LogfileHeader.BuffersWritten);
        status=ProcessTrace(&handle,1,NULL,NULL);closed=CloseTrace(handle);
        printf("{\"kind\":\"summary\",\"process_status\":%lu,\"close_status\":%lu,\"events\":\"%llu\",\"ndis_events\":\"%llu\",\"marker_events\":\"%llu\",\"other_events\":\"%llu\"}\n",status,closed,total,ndis_count,marker_count,total-ndis_count-marker_count);
        return status || closed?1:0;
    }
    return 2;
}
