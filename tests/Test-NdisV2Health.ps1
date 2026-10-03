#requires -Version 5.1
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../experiments/qualcomm/NdisV2Health.ps1')
$header=[pscustomobject]@{kind='header';start_time='100';end_time='200';perf_frequency_hz='10000000';clock_type=1;pointer_size=8;buffers_written=2;events_lost=0;buffers_lost=0}
$summary=[pscustomobject]@{kind='summary';process_status=0;close_status=0}
$stop=[pscustomobject]@{status=0;events_lost=0;log_buffers_lost=0;real_time_buffers_lost=0;buffers_written=2}
Assert-NdisV2Health $header $summary $stop 8192
foreach($bad in @('0','-1','1.5','010',10000000)){
    $header.perf_frequency_hz=$bad;$rejected=$false
    try {Assert-NdisV2Health $header $summary $stop 8192} catch {$rejected=$true}
    if(-not $rejected){throw 'Invalid frequency accepted.'}
}
$header.perf_frequency_hz='10000000'
foreach($field in @('events_lost','log_buffers_lost','real_time_buffers_lost')){
    $stop.$field=1;$rejected=$false
    try {Assert-NdisV2Health $header $summary $stop 8192} catch {$rejected=$true}
    if(-not $rejected){throw 'Controller loss accepted.'}
    $stop.$field=0
}
$header.end_time='0';$rejected=$false
try {Assert-NdisV2Health $header $summary $stop 8192} catch {$rejected=$true}
if(-not $rejected){throw 'Unfinalized trace accepted.'}
Write-Output 'V2 trace health rejection tests passed; no trace or adapter operation.'
