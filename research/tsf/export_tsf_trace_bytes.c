#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

/* Saved-file ETW UserData export only: no provider/session control or device I/O.
 * Private output may contain diagnostic bytes. Exit 0 complete, 1 failure,
 * 2 invalid arguments. A matching text prefix is selection, not firmware identity.
 */
static const GUID provider = {0xbb6f5b93,0x635c,0x47be,{0x81,0x6f,0xe8,0x95,0xe7,0x70,0x64,0xa8}};
static const char *prefixes[] = {
    "WMI_VDEV_TSF_TSTAMP_ACTION_CMDID:", "OL: receive WMI_VDEV_TSF_REPORT_EVENTID",
    "OL: g_tsf:", "OL: set vdev-"
};
static const char *families[] = {"command","report","soc_timer","delay"};
static unsigned long long total, wlan, emitted, payload_bytes;
static int failed;

static int family(const void *data, size_t size) {
    unsigned i;
    if (!data) return -1;
    for (i=0;i<4;i++) {
        size_t n=strlen(prefixes[i]);
        if (size>=n && memcmp(data,prefixes[i],n)==0) return (int)i;
    }
    return -1;
}

static ULONG WINAPI buffer(PEVENT_TRACE_LOGFILEW log) {
    (void)log;
    return failed ? FALSE : TRUE;
}

static void WINAPI record(PEVENT_RECORD e) {
    int kind;
    unsigned i;
    const unsigned char *data=(const unsigned char *)e->UserData;
    if (failed) return;
    if (++total>2000000ULL) { failed=1; return; }
    if (memcmp(&e->EventHeader.ProviderId,&provider,sizeof(provider))!=0) return;
    ++wlan;
    if (e->EventHeader.EventDescriptor.Id!=1) return;
    if (e->UserDataLength && !data) { failed=1; return; }
    kind=family(data,e->UserDataLength);
    if (kind<0) return;
    if (emitted>=10000 || payload_bytes+e->UserDataLength>4ULL*1024*1024) { failed=1; return; }
    ++emitted;
    payload_bytes+=e->UserDataLength;
    printf("{\"kind\":\"event\",\"ordinal\":%llu,\"family\":\"%s\",\"timestamp\":\"%lld\",\"id\":%u,\"version\":%u,\"opcode\":%u,\"flags\":%u,\"extended_data_count\":%u,\"length\":%u,\"hex\":\"",
        total,families[kind],e->EventHeader.TimeStamp.QuadPart,
        (unsigned)e->EventHeader.EventDescriptor.Id,(unsigned)e->EventHeader.EventDescriptor.Version,
        (unsigned)e->EventHeader.EventDescriptor.Opcode,(unsigned)e->EventHeader.Flags,
        (unsigned)e->ExtendedDataCount,(unsigned)e->UserDataLength);
    for(i=0;i<e->UserDataLength;i++) printf("%02x",data[i]);
    puts("\"}");
    if (ferror(stdout)) failed=1;
}

int wmain(int argc,wchar_t **argv) {
    EVENT_TRACE_LOGFILEW log={0};
    WIN32_FILE_ATTRIBUTE_DATA file;
    TRACEHANDLE trace;
    ULONG status,closed;
    unsigned i;
    if(argc==2 && wcscmp(argv[1],L"--help")==0) {
        puts("export_tsf_trace_bytes SAVED.etl > PRIVATE.jsonl (maximum 64 MiB input)"); return 0;
    }
    if(argc==2 && wcscmp(argv[1],L"--self-test")==0) {
        const char embedded[]="OL: g_tsf:\0\x05\x50\0\0";
        if(family(NULL,8)!=-1 || family("x",1)!=-1 || family(embedded,sizeof(embedded))!=2) return 1;
        for(i=0;i<4;i++) {
            if(family(prefixes[i],strlen(prefixes[i]))!=(int)i ||
               family(prefixes[i],strlen(prefixes[i])-1)!=-1) return 1;
        }
        puts("{\"self_test\":\"pass\",\"device_access\":false}"); return 0;
    }
    if(argc!=2 || argv[1][0]==L'-') return 2;
    if(!GetFileAttributesExW(argv[1],GetFileExInfoStandard,&file) ||
       (file.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)) ||
       file.nFileSizeHigh || !file.nFileSizeLow || file.nFileSizeLow>64UL*1024*1024) {
        fputs("Invalid or oversized saved trace\n",stderr); return 1;
    }
    log.LogFileName=argv[1];
    log.ProcessTraceMode=PROCESS_TRACE_MODE_EVENT_RECORD|PROCESS_TRACE_MODE_RAW_TIMESTAMP;
    log.EventRecordCallback=record;
    log.BufferCallback=buffer;
    trace=OpenTraceW(&log);
    if(trace==INVALID_PROCESSTRACE_HANDLE) { fprintf(stderr,"OpenTrace: %lu\n",GetLastError()); return 1; }
    printf("{\"kind\":\"header\",\"schema\":\"wht/tsf-trace-bytes-v1\",\"provider\":\"bb6f5b93-635c-47be-816f-e895e77064a8\",\"clock_type\":%lu,\"frequency\":\"%lld\",\"events_lost\":%lu,\"buffers_lost\":%lu}\n",
        log.LogfileHeader.ReservedFlags,log.LogfileHeader.PerfFreq.QuadPart,
        log.LogfileHeader.EventsLost,log.LogfileHeader.BuffersLost);
    status=ProcessTrace(&trace,1,NULL,NULL);
    closed=CloseTrace(trace);
    printf("{\"kind\":\"summary\",\"events\":%llu,\"wlan_events\":%llu,\"exported\":%llu,\"payload_bytes\":%llu,\"process_status\":%lu,\"close_status\":%lu,\"bound_failure\":%s}\n",
        total,wlan,emitted,payload_bytes,status,closed,failed?"true":"false");
    return status || closed || failed || ferror(stdout) ? 1 : 0;
}
