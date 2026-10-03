#requires -Version 5.1
# Pure assertion; no controller, trace, filesystem or adapter operation.
function Assert-NdisV2Health {
    [CmdletBinding()]
    param([object]$Header,[object]$Summary,[object]$Stopped,[long]$EtlBytes)
    foreach($value in @($Header.perf_frequency_hz,$Header.start_time,$Header.end_time)){
        if($value -isnot [string] -or $value -cnotmatch '^[1-9][0-9]{0,18}$' -or [long]$value -le 0){
            throw 'Header clock/finalization value is not a canonical positive integer.'
        }
    }
    if($Header.kind -ne 'header' -or [long]$Header.end_time -lt [long]$Header.start_time -or
       $Header.clock_type -ne 1 -or $Header.pointer_size -ne 8 -or
       $Header.buffers_written -le 0 -or $Stopped.buffers_written -le 0 -or
       $Header.events_lost -ne 0 -or $Header.buffers_lost -ne 0 -or $Summary.kind -ne 'summary' -or
       $Summary.process_status -ne 0 -or $Summary.close_status -ne 0 -or $Stopped.status -ne 0 -or
       $Stopped.events_lost -ne 0 -or $Stopped.log_buffers_lost -ne 0 -or $Stopped.real_time_buffers_lost -ne 0 -or
       $EtlBytes -le 0 -or $EtlBytes -ge 8MB){throw 'Full trace health check failed.'}
}
