#requires -Version 5.1
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../research/ftm/FtmDeltaLog.ps1')
$valid=ConvertFrom-FtmDeltaLogLine -Text 'prefix handle_merged_event: t3_del 10'
if($valid.field -ne 't3_del' -or $valid.value -ne '10'){throw 'Valid field decode failed.'}
if($null -ne (ConvertFrom-FtmDeltaLogLine -Text 'unrelated provider event')){throw 'Unrelated event accepted.'}
if($null -ne (ConvertFrom-FtmDeltaLogLine -Text 'handle_merged_event: RTT report for MAC <synthetic>')){throw 'Report heading confused with exact lowercase numeric field.'}
$groups=@(
    @('t3_del 10','t4_del BAD','rtt BAD','t3_del BAD','t4_del 15','rtt 5'),
    @('t3_del 10','t4_del 15','rtt 5','t3_del BAD','t4_del BAD','rtt BAD','t3_del 20','t4_del 25','rtt 5'),
    @('t3_del 10','t4_del 15','rtt 5','t3_del BAD'),
    @('t3_del 10 trailing'),
    @('t4_del'),
    @('rtt 1.5')
)
foreach($group in $groups){
    $rejected=$false
    try {foreach($line in $group){$null=ConvertFrom-FtmDeltaLogLine -Text ('handle_merged_event: '+$line)}}
    catch {$rejected=$true}
    if(-not $rejected){throw 'Malformed target log was silently skipped.'}
}
Write-Output 'FTM delta log parser regressions passed.'
