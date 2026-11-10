# run_daily.ps1 - runs the pipeline once and keeps a log (P8).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily.ps1
#
# Meant for the Windows scheduled task that starts the pipeline every weekday at
# 08:00, so it needs no console and no one watching. Everything the pipeline
# prints (output and errors) goes to logs\run_YYYY-MM-DD_HHmm.log. Logs older than
# 30 days are deleted. The script exits with the pipeline's exit code, so Task
# Scheduler shows a failed run as failed.
#
# -Python, -Script and -LogDir exist only so the tests can run a fake pipeline;
# the scheduled task uses the defaults.

param(
    [string]$Python = (Join-Path $PSScriptRoot 'venv\Scripts\python.exe'),
    [string]$Script = 'main.py',
    [string]$LogDir = (Join-Path $PSScriptRoot 'logs')
)

$ErrorActionPreference = 'Stop'

$Root     = $PSScriptRoot
$KeepDays = 30

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("run_{0}.log" -f (Get-Date -Format 'yyyy-MM-dd_HHmm'))

# UTF-8 without a byte-order mark, the same encoding Python writes below
$Utf8 = New-Object System.Text.UTF8Encoding($false)
function Write-Log($text) {
    [System.IO.File]::AppendAllText($Log, "$text`r`n", $Utf8)
}

# Delete old logs so the folder does not grow forever
Get-ChildItem -LiteralPath $LogDir -Filter 'run_*.log' -File |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
    Remove-Item -Force

Write-Log "=== Run started $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Log "ERROR: no Python found at $Python. Create the venv first (see README.md)."
    Write-Log "=== Run finished $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), exit code 1 ==="
    exit 1
}

# Python writes UTF-8 even into a file, so job titles with accents or symbols
# (such as the IND tick) do not crash the run. Unbuffered keeps output and
# errors in the order they happened.
$env:PYTHONUTF8       = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

# cmd does the redirection, so Python's bytes land in the log untouched
# (PowerShell 5 would re-encode them and turn error lines into exceptions).
# The three paths reach cmd through environment variables, not inside the
# command text. If a path with a space is pasted into the text, PowerShell 5
# wraps the whole command in an extra pair of quotes, cmd then splits the paths
# at the space and the run fails before Python starts. The line below has no
# path in it, so it reaches cmd exactly as written and cmd fills in the
# %RD_...% values itself. /s makes cmd drop only the outer pair of quotes and
# keep the ones around each path.
$env:RD_PY     = $Python
$env:RD_SCRIPT = $Script
$env:RD_LOG    = $Log
Push-Location $Root
try {
    cmd /s /c '""%RD_PY%" "%RD_SCRIPT%" >> "%RD_LOG%" 2>&1"'
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

Write-Log "=== Run finished $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), exit code $code ==="
exit $code
