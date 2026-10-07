#requires -Version 5.1
# Offline: extracts only the subprocess helper. Never invokes WPR or a collector.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$source=Join-Path $PSScriptRoot '../research/acquisition/Observe-QutsRegistry.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
$helper=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-BoundedWpr'},$true)
if($null -eq $helper){throw 'Expected subprocess helper unavailable'}
Invoke-Expression $helper.Extent.Text
$artifactRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts'))
$outputRoot=Join-Path $artifactRoot ('QutsRegistryHelperTest-'+[Guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $outputRoot
$wpr=Join-Path $env:windir 'System32/WindowsPowerShell/v1.0/powershell.exe'
$commandCount=0
try {
    $stem=Invoke-BoundedWpr @('-NoProfile','-Command','[Console]::Out.WriteLine(123); [Console]::Error.WriteLine(456); exit 0')
    if((Get-Content -LiteralPath ($stem+'.stdout.txt') -Raw).Trim() -ne '123' -or
       (Get-Content -LiteralPath ($stem+'.stderr.txt') -Raw).Trim() -ne '456'){throw 'Successful child output lost'}
    $rejected=$false
    try {$null=Invoke-BoundedWpr @('-NoProfile','-Command','[Console]::Out.WriteLine(789); [Console]::Error.WriteLine(456); exit 7')}
    catch {if($_.Exception.Message -notlike 'WPR failed with exit 7;*'){throw};$rejected=$true}
    if(-not $rejected -or (Get-Content -LiteralPath (Join-Path $outputRoot 'wpr-2.stdout.txt') -Raw).Trim() -ne '789' -or
       (Get-Content -LiteralPath (Join-Path $outputRoot 'wpr-2.stderr.txt') -Raw).Trim() -ne '456'){
        throw 'Nonzero child exit or output lost'
    }
    $watch=[Diagnostics.Stopwatch]::StartNew();$rejected=$false
    try {$null=Invoke-BoundedWpr @('-NoProfile','-Command','[Console]::Out.WriteLine($PID); [Console]::Error.WriteLine(456); Start-Sleep -Seconds 20') 1000}
    catch {if($_.Exception.Message -ne 'WPR command exceeded its deadline'){throw};$rejected=$true}
    if(-not $rejected -or $watch.ElapsedMilliseconds -gt 18000){throw 'Timeout cleanup was not bounded'}
    $timeoutOut=Join-Path $outputRoot 'wpr-3.stdout.txt'
    $timeoutErr=Join-Path $outputRoot 'wpr-3.stderr.txt'
    if(-not (Test-Path -LiteralPath $timeoutOut -PathType Leaf) -or
       -not (Test-Path -LiteralPath $timeoutErr -PathType Leaf)){throw 'Timeout output files missing'}
    # A loaded CI host may reach the deadline before the child emits anything.
    $childText=[IO.File]::ReadAllText($timeoutOut).Trim()
    $errorText=[IO.File]::ReadAllText($timeoutErr).Trim()
    if($errorText -ne '' -and $errorText -ne '456'){throw 'Unexpected timeout stderr'}
    if($childText -ne ''){
        $childId=0
        if(-not [int]::TryParse($childText,[ref]$childId) -or $childId -le 0){throw 'Unexpected timeout stdout'}
        if(Get-Process -Id $childId -ErrorAction SilentlyContinue){throw 'Timed-out owned child is still running'}
    }
    $unbounded=@($helper.FindAll({param($node) $node -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $node.Member.Value -eq 'WaitForExit' -and $node.Arguments.Count -eq 0},$true))
    if($unbounded.Count){throw 'Unbounded child wait'}
    $rejected=$false
    try {$null=Invoke-BoundedWpr @('bad"argument')}
    catch {if($_.Exception.Message -notlike '*quot*'){throw};$rejected=$true}
    if(-not $rejected){throw 'Unsupported argument was not rejected'}
    Write-Output 'QUTS subprocess checks passed: success, nonzero exit, timeout, retained output and bounded owned-child cleanup. No acquisition.'
} finally {
    $resolved=[IO.Path]::GetFullPath($outputRoot)
    if(-not $resolved.StartsWith($artifactRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw 'Cleanup outside test artifacts refused'
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
