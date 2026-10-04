#requires -Version 7.4
<#
.SYNOPSIS
Previews or records bounded offline Qualcomm package/file inspection.
.DESCRIPTION
Never loads vendor code, changes services or contacts hardware/network endpoints.
Preview creates nothing. Apply creates a new output directory with a receipt.
Matching completed repeats return Unchanged; mismatched/incomplete outputs fail.
Exit 0: preview/success/unchanged. Exit 1: validation or worker failure.
.PARAMETER Operation
Files: bounded PE/file inventory. QikInventory: already decoded QIK blocks.
QccExtract: decode a supported managed QIK container as files. TypeLibrary:
inspect an extracted MSFT type library without COM registration or activation.
.PARAMETER ExpectedSha256
Optional expected SHA-256 for file input; required for QccExtract and TypeLibrary.
.PARAMETER Apply
Create private artifacts. No write occurs without this switch.
.EXAMPLE
./research/adapters/Invoke-QualcommStaticInspection.ps1 -Operation Files -InputPath '<local-directory>' -OutputDirectory './artifacts/vendor-inventory'
.EXAMPLE
./research/adapters/Invoke-QualcommStaticInspection.ps1 -Operation QikInventory -InputPath './artifacts/decoded-blocks' -OutputDirectory './artifacts/qik-inventory' -Apply
.NOTES
Recovery: retain failed outputs for diagnosis, then choose a NEW output directory.
Rollback: remove only the operator-selected output directory after inspecting it.
Use the runbook for acquisition and exact package hashes. Raw artifacts stay private.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][ValidateSet('Files','QikInventory','QccExtract','QpstExtract','MsiTables','TypeLibrary')][string]$Operation,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$InputPath,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$OutputDirectory,
    [ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedSha256,
    [string]$Python = 'python',
    [switch]$Apply
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Get-InputManifest([string]$Path) {
    $item=Get-Item -LiteralPath $Path
    $all=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $Path -Recurse -Force)}else{@($item)}
    if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or @($all | Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Reparse points are not accepted'}
    $files=@($all | Where-Object {-not $_.PSIsContainer} | Sort-Object FullName)
    if($files.Count -gt 4096){throw 'Input exceeds 4096-file limit'}
    $total=0L
    $rows=@(foreach($file in $files){
        $total+=$file.Length
        if($file.Length -gt 536870912 -or $total -gt 2147483648){throw 'Input exceeds byte bounds'}
        [ordered]@{file=if($item.PSIsContainer){[IO.Path]::GetRelativePath($Path,$file.FullName).Replace('\','/')}else{$file.Name};bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    })
    return $rows
}

try {
    $inputFull=(Resolve-Path -LiteralPath $InputPath).ProviderPath
    $inputItem=Get-Item -LiteralPath $inputFull
    $inputAncestor=if($inputItem.PSIsContainer){$inputItem}else{$inputItem.Directory}
    for($ancestor=$inputAncestor;$null -ne $ancestor;$ancestor=$ancestor.Parent){if($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Input may not traverse reparse points'}}
    $outputFull=[IO.Path]::GetFullPath($OutputDirectory)
    $comparison=[StringComparison]::OrdinalIgnoreCase
    if($inputFull.Equals($outputFull,$comparison) -or $outputFull.StartsWith($inputFull.TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar,$comparison) -or $inputFull.StartsWith($outputFull.TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar,$comparison)){throw 'Input and output must be separate, non-nested paths'}
    $parent=Split-Path -Parent $outputFull
    if(-not (Test-Path -LiteralPath $parent -PathType Container)){throw 'Output parent must already exist'}
    for($ancestor=Get-Item -LiteralPath $parent;$null -ne $ancestor;$ancestor=$ancestor.Parent){if($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Output parent may not traverse reparse points'}}
    if($Operation -in @('QccExtract','QpstExtract','MsiTables','TypeLibrary') -and -not $ExpectedSha256){throw 'ExpectedSha256 is required for binary format inspection'}
    if($Operation -in @('QccExtract','QpstExtract','MsiTables','TypeLibrary') -and -not (Test-Path -LiteralPath $inputFull -PathType Leaf)){throw 'This operation requires one file'}
    if($Operation -eq 'QikInventory' -and -not (Test-Path -LiteralPath $inputFull -PathType Container)){throw 'QikInventory requires a directory'}
    $inputs=@(Get-InputManifest $inputFull)
    if($ExpectedSha256 -and ((Test-Path -LiteralPath $inputFull -PathType Container) -or $inputs.Count -ne 1 -or $inputs[0].sha256 -ne $ExpectedSha256.ToLowerInvariant())){throw 'Input does not match the expected file hash'}
    $workers=@($PSCommandPath,(Join-Path $PSScriptRoot 'inspect_qik_inventory.py'))+@(Get-ChildItem (Join-Path $PSScriptRoot 'package_tools') -File | Where-Object {$_.Extension -in '.ps1','.py'} | Select-Object -ExpandProperty FullName)
    $toolHashes=@($workers | Sort-Object | ForEach-Object {[ordered]@{file=[IO.Path]::GetRelativePath($PSScriptRoot,$_).Replace('\','/');sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()}})
    $identity=[ordered]@{schema='wht/offline-inspection-identity-v1';operation=$Operation;inputs=$inputs;tools=$toolHashes}
    $identityJson=$identity | ConvertTo-Json -Depth 8 -Compress
    $receiptPath=Join-Path $outputFull 'receipt.json'
    if(Test-Path -LiteralPath $outputFull){
        if((Get-Item -LiteralPath $outputFull).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked output rejected'}
        if(-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)){throw 'Existing output is incomplete; choose a new directory'}
        $old=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
        if(($old.identity | ConvertTo-Json -Depth 8 -Compress) -ne $identityJson -or $old.status -ne 'Complete'){throw 'Output belongs to different input/tools or is incomplete'}
        $observed=@(Get-InputManifest $outputFull | Where-Object {$_.file -ne 'receipt.json'})
        if(($observed | ConvertTo-Json -Depth 5 -Compress) -ne ($old.outputs | ConvertTo-Json -Depth 5 -Compress)){throw 'Recorded outputs changed; choose a new directory'}
        [ordered]@{Status='Unchanged';Operation=$Operation;OutputDirectory=$outputFull} | ConvertTo-Json -Compress;exit 0
    }
    if(-not $Apply){[ordered]@{Status='WouldInspect';Operation=$Operation;FileCount=$inputs.Count;OutputDirectory=$outputFull} | ConvertTo-Json -Compress;exit 0}
    if(-not $PSCmdlet.ShouldProcess($outputFull,'Create offline inspection artifacts')){[ordered]@{Status='WouldInspect';Operation=$Operation} | ConvertTo-Json -Compress;exit 0}
    [IO.Directory]::CreateDirectory($outputFull) | Out-Null
    try {
        $workerError=Join-Path $outputFull 'worker-stderr.txt'
        $global:LASTEXITCODE=0
        switch($Operation){
            'Files' {$json=& $Python (Join-Path $PSScriptRoot 'package_tools/inspect_files.py') $inputFull 2> $workerError}
            'QikInventory' {$json=& $Python (Join-Path $PSScriptRoot 'inspect_qik_inventory.py') $inputFull 2> $workerError}
            'QccExtract' {$json=& (Join-Path $PSScriptRoot 'package_tools/Expand-QccBlocks.ps1') -Path $inputFull -OutputDirectory (Join-Path $outputFull 'blocks') -Apply 2> $workerError}
            'QpstExtract' {$json=& $Python (Join-Path $PSScriptRoot 'package_tools/expand_qpst.py') $inputFull (Join-Path $outputFull 'members') 2> $workerError}
            'MsiTables' {$json=& (Join-Path $PSScriptRoot 'package_tools/Read-MsiTables.ps1') -Path $inputFull 2> $workerError}
            'TypeLibrary' {$json=& (Join-Path $PSScriptRoot 'package_tools/Read-TypeLibrary.ps1') -Path $inputFull -Pattern '.*' 2> $workerError}
        }
        if($LASTEXITCODE -ne 0){throw "Inspection worker failed with exit code $LASTEXITCODE"}
        $parsed=($json -join "`n") | ConvertFrom-Json
        if($null -eq $parsed){throw 'Inspection worker returned no JSON'}
        [IO.File]::WriteAllText((Join-Path $outputFull 'result.json'),(($parsed | ConvertTo-Json -Depth 50)+"`n"),[Text.UTF8Encoding]::new($false))
        $after=@(Get-InputManifest $inputFull)
        if(($after | ConvertTo-Json -Depth 5 -Compress) -ne ($inputs | ConvertTo-Json -Depth 5 -Compress)){throw 'Input changed during inspection'}
        $outputs=@(Get-InputManifest $outputFull)
        [ordered]@{identity=$identity;status='Complete';outputs=$outputs;scope='offline file inspection only'} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $receiptPath -Encoding utf8NoBOM
        [ordered]@{Status='Complete';Operation=$Operation;OutputDirectory=$outputFull} | ConvertTo-Json -Compress
    }catch{
        [ordered]@{status='Failed';operation=$Operation;message='Inspection incomplete; retain artifacts and review worker errors'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputFull 'failure.json') -Encoding utf8NoBOM
        throw
    }
    exit 0
}catch{Write-Error -ErrorRecord $_;exit 1}
