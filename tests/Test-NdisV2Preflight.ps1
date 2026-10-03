#requires -Version 5.1
$ErrorActionPreference='Stop'
$path=Join-Path $PSScriptRoot '../research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1'
$source=Get-Content -LiteralPath $path -Raw
$begin=$source.IndexOf('$attempted=$true')
$end=$source.IndexOf('finally {',$begin)
if($begin -lt 0 -or $end -lt $begin){throw 'Trace cleanup structure unavailable.'}
if($source.Substring($begin,$end-$begin).Contains('Get-ExactAdapter')){
    throw 'Unbounded in-process adapter query can prevent trace cleanup.'
}
Write-Output 'V2 preflight regression passed: adapter discovery is outside live trace.'
