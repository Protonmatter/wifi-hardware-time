#requires -Version 5.1
<#
.SYNOPSIS
Preview or refresh the authored-source reference index.
.DESCRIPTION
Default preview writes nothing. -Apply updates only the two generated index files;
unchanged repeats do not rewrite them. Exit 0 success/preview, 1 failure.
.EXAMPLE
./research/evidence/Update-ResearchKnowledge.ps1 -Apply
.NOTES
Requires Python 3.11+. No vendor files, network calls or devices are accessed.
Rollback: restore only generated docs/knowledge/reference-index.md and research-index.json.
#>
[CmdletBinding(SupportsShouldProcess)]
param([string]$Python='python',[switch]$Apply)
$ErrorActionPreference='Stop'
try {
    $arguments=@((Join-Path $PSScriptRoot 'build_knowledge_index.py'))
    if($Apply -and $PSCmdlet.ShouldProcess('docs/knowledge reference index','Refresh generated files')){$arguments+='--write'}
    & $Python @arguments
    if($LASTEXITCODE -ne 0){throw "Index worker failed: $LASTEXITCODE"}
    exit 0
}catch{Write-Error -ErrorRecord $_;exit 1}
