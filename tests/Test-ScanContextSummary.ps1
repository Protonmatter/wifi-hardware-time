#requires -Version 5.1
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$path=Join-Path $PSScriptRoot '../experiments/qualcomm/Export-TsfContext.ps1'
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $path).Path,[ref]$tokens,[ref]$errors)
$function=$ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-ScanContextSummary'},$true)
if($null -eq $function){throw 'Missing scan-summary function'}
Invoke-Expression $function.Extent.Text
$rows=@(
 [pscustomobject]@{ordinal=1;utc='2000-01-01T00:00:00Z';message='wmi cmd endpoint[1]: buf ABCD, cmd WMI_START_SCAN_CMDID (0x3001)'},
 [pscustomobject]@{ordinal=2;utc='2000-01-01T00:00:00Z';message='MP: Sta11NotifyScanentryUpdate ssid=WMI_START_SCAN_CMDID'},
 [pscustomobject]@{ordinal=3;utc='2000-01-01T00:00:00Z';message='MP: StaHandleTaskScanEvent type=STARTED reason=NONE'},
 [pscustomobject]@{ordinal=4;utc='2000-01-01T00:00:00Z';message='MP: Sta11NotifyScanentryUpdate ssid=StaHandleTaskScanEvent type=STARTED'}
)
$result=Get-ScanContextSummary -Rows $rows
if($result.scan_start_commands.Count -ne 1 -or $result.scan_callbacks.Count -ne 1 -or $result.scan_callbacks[0].type -ne 'STARTED'){throw 'Anchored scan classification failed'}
if(($result|ConvertTo-Json -Depth 5) -match 'ABCD|ssid'){throw 'Private log fields escaped summary'}
Write-Output 'Scan context classification passed; no ETL or hardware access.'
