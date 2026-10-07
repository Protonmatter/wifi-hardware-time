/* Exercise the real exporter output/exit path without opening an ETL.
 * Only the ETW reader operations are replaced; stdio and Windows pipes are real.
 * The Python test owns the working directory and synthetic input file. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <io.h>
#include <fcntl.h>

static TRACEHANDLE trace_output_open(PEVENT_TRACE_LOGFILEW log)
{
    log->LogfileHeader.ReservedFlags = 1;
    log->LogfileHeader.PerfFreq.QuadPart = 10000000;
    return 1;
}

static ULONG trace_output_process(PTRACEHANDLE handles, ULONG count,
    LPFILETIME start, LPFILETIME end)
{
    (void)handles; (void)count; (void)start; (void)end;
    return ERROR_SUCCESS;
}

static ULONG trace_output_close(TRACEHANDLE handle)
{
    (void)handle;
    return ERROR_SUCCESS;
}

#define OpenTraceW trace_output_open
#define ProcessTrace trace_output_process
#define CloseTrace trace_output_close
#define wmain trace_export_main
#if defined(TEST_TSF_EXPORTER)
#include "../research/tsf/export_tsf_trace_bytes.c"
#else
#include "../research/acquisition/export_registry_trace.c"
#endif
#undef wmain

int main(int argc, char **argv)
{
    static char output_buffer[4096];
    wchar_t *arguments[] = {L"exporter", L"synthetic-input.etl", L"1"};
    if (argc != 2 || (strcmp(argv[1], "good") && strcmp(argv[1], "broken"))) return 2;
    if (!strcmp(argv[1], "broken")) {
        HANDLE reader, writer;
        int descriptor;
        if (!CreatePipe(&reader, &writer, NULL, 0)) return 3;
        CloseHandle(reader);
        descriptor = _open_osfhandle((intptr_t)writer, _O_WRONLY | _O_BINARY);
        if (descriptor < 0) { CloseHandle(writer); return 3; }
        if (_dup2(descriptor, _fileno(stdout)) != 0) { _close(descriptor); return 3; }
        if (descriptor != _fileno(stdout)) _close(descriptor);
    }
    /* Keep the small header/summary buffered until the exporter flushes them. */
    if (setvbuf(stdout, output_buffer, _IOFBF, sizeof(output_buffer))) return 3;
#if defined(TEST_TSF_EXPORTER)
    return trace_export_main(2, arguments);
#else
    return trace_export_main(3, arguments);
#endif
}
