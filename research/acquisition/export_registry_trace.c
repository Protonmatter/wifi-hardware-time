#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <errno.h>

/* Offline ETL reader only. Outputs private raw payloads for selected PIDs.
 * No tracing control, process-memory read, device open or vendor code load.
 * Exit 0: complete export; 1: input/read/bound failure; 2: argument error.
 */
static const GUID registry_guid={0xae53722e,0xc863,0x11d2,{0x86,0x59,0x00,0xc0,0x4f,0xa3,0x21,0xa1}};
static const GUID stack_guid={0xdef2fe46,0x7bd6,0x4b80,{0xbd,0x94,0xf5,0x7f,0xe2,0x0d,0x0c,0xe3}};
static DWORD selected_pids[8];
static int pid_count,failed;
static unsigned long long total,registry_total,stack_total,exported,output_budget;
static LONGLONG first_registry,last_registry;

static int selected(DWORD pid){
    int i;for(i=0;i<pid_count;i++)if(selected_pids[i]==pid)return 1;return 0;
}

static void WINAPI record(PEVENT_RECORD e){
    DWORD pid=e->EventHeader.ProcessId;
    const char *kind;
    unsigned i;
    const unsigned char *bytes=(const unsigned char *)e->UserData;
    ++total;
    if(total>2000000ULL){failed=1;return;}
    if(memcmp(&e->EventHeader.ProviderId,&registry_guid,sizeof(GUID))==0){
        ++registry_total;kind="registry";
        if(!first_registry||e->EventHeader.TimeStamp.QuadPart<first_registry)first_registry=e->EventHeader.TimeStamp.QuadPart;
        if(e->EventHeader.TimeStamp.QuadPart>last_registry)last_registry=e->EventHeader.TimeStamp.QuadPart;
    }else if(memcmp(&e->EventHeader.ProviderId,&stack_guid,sizeof(GUID))==0){
        ++stack_total;kind="stack";
        if(e->UserDataLength<16){failed=1;return;}
        memcpy(&pid,bytes+8,sizeof(pid)); /* StackProcess in StackWalk_Event */
    }else return;
    /* KCB lifecycle is global and required to reject stale/reused key identities. */
    if((!selected(pid)&&!(kind[0]=='r'&&e->EventHeader.EventDescriptor.Opcode>=22&&e->EventHeader.EventDescriptor.Opcode<=25))||failed)return;
    output_budget+=(unsigned long long)e->UserDataLength*2ULL+384ULL;
    if(output_budget>128ULL*1024ULL*1024ULL){failed=1;return;}
    ++exported;
    printf("{\"kind\":\"%s\",\"timestamp\":\"%lld\",\"pid\":%lu,\"tid\":%lu,\"flags\":%u,\"opcode\":%u,\"version\":%u,\"payload\":\"",
        kind,e->EventHeader.TimeStamp.QuadPart,e->EventHeader.ProcessId,e->EventHeader.ThreadId,
        (unsigned)e->EventHeader.Flags,(unsigned)e->EventHeader.EventDescriptor.Opcode,
        (unsigned)e->EventHeader.EventDescriptor.Version);
    for(i=0;i<(unsigned)e->UserDataLength;i++)printf("%02x",bytes[i]);
    puts("\"}");
}

int wmain(int argc,wchar_t **argv){
    WIN32_FILE_ATTRIBUTE_DATA file;
    EVENT_TRACE_LOGFILEW log={0};
    TRACEHANDLE trace;
    ULONG status,closed;
    int i;
    if(argc==2&&wcscmp(argv[1],L"--help")==0){puts("export_registry_trace FILE.etl PID [PID ...] (1-8 PIDs; private JSONL output)");return 0;}
    if(argc<3||argc>10)return 2;
    for(i=2;i<argc;i++){
        wchar_t *end=NULL;
        unsigned long n;
        const wchar_t *digit=argv[i];
        for(;*digit;digit++)if(*digit<L'0'||*digit>L'9')return 2;
        errno=0;n=wcstoul(argv[i],&end,10);
        if(errno||!n||n==0xffffffffUL||!end||*end)return 2;
        selected_pids[pid_count++]=(DWORD)n;
    }
    if(!GetFileAttributesExW(argv[1],GetFileExInfoStandard,&file)||
       (file.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))||
       file.nFileSizeHigh||file.nFileSizeLow>64UL*1024UL*1024UL){
        puts("{\"kind\":\"error\",\"reason\":\"invalid_or_oversized_input\"}");return 1;
    }
    log.LogFileName=argv[1];
    log.ProcessTraceMode=PROCESS_TRACE_MODE_EVENT_RECORD|PROCESS_TRACE_MODE_RAW_TIMESTAMP;
    log.EventRecordCallback=record;
    trace=OpenTraceW(&log);
    if(trace==INVALID_PROCESSTRACE_HANDLE){printf("{\"kind\":\"open_error\",\"status\":%lu}\n",GetLastError());return 1;}
    printf("{\"kind\":\"header\",\"clock_type\":%lu,\"pointer_size\":%lu,\"frequency\":\"%lld\",\"events_lost\":%lu,\"buffers_lost\":%lu,\"buffers_written\":%lu,\"start_filetime\":\"%lld\",\"end_filetime\":\"%lld\",\"boot_filetime\":\"%lld\"}\n",
        log.LogfileHeader.ReservedFlags,log.LogfileHeader.PointerSize,log.LogfileHeader.PerfFreq.QuadPart,
        log.LogfileHeader.EventsLost,log.LogfileHeader.BuffersLost,log.LogfileHeader.BuffersWritten,
        log.LogfileHeader.StartTime.QuadPart,log.LogfileHeader.EndTime.QuadPart,log.LogfileHeader.BootTime.QuadPart);
    status=ProcessTrace(&trace,1,NULL,NULL);closed=CloseTrace(trace);
    printf("{\"kind\":\"summary\",\"process_status\":%lu,\"close_status\":%lu,\"bound_failure\":%s,\"events\":%llu,\"registry_total\":%llu,\"stack_total\":%llu,\"exported\":%llu,\"first_registry\":\"%lld\",\"last_registry\":\"%lld\"}\n",
        status,closed,failed?"true":"false",total,registry_total,stack_total,exported,first_registry,last_registry);
    return status||closed||failed||ferror(stdout)?1:0;
}
