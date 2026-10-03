#requires -Version 5.1
# Pure parser: malformed target messages invalidate extraction instead of being skipped.
function ConvertFrom-FtmDeltaLogLine {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][AllowEmptyString()][string]$Text)
    if($Text -cnotmatch 'handle_merged_event:\s+(?:t3_del|t4_del|rtt)\b'){
        return $null
    }
    if($Text -cnotmatch 'handle_merged_event:\s+(t3_del|t4_del|rtt)\s+(-?\d+)\s*$'){
        throw 'Malformed target delta log.'
    }
    [pscustomobject]@{field=$Matches[1];value=$Matches[2]}
}
