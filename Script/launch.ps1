$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = 'vSMR AVISO Converter'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$converterPython = $null
$converterArgs = @()
foreach ($candidateName in @('py.exe', 'python.exe', 'python3.exe')) {
    $candidate = Get-Command $candidateName -ErrorAction SilentlyContinue
    if ($null -eq $candidate) { continue }
    $probeArgs = @()
    if ($candidateName -eq 'py.exe') { $probeArgs += '-3' }
    try {
        & $candidate.Source @probeArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $converterPython = $candidate.Source
            $converterArgs = $probeArgs
            break
        }
    } catch { continue }
}
if ($null -eq $converterPython) {
    Write-Host 'Python 3.10 or later was not found. No conversion was performed.' -ForegroundColor Red
    return
}
Write-Host ''
Write-Host '  AVISO SOURCE' -ForegroundColor Cyan
Write-Host '  [1] Local GNG / Colours.sct (default)'
Write-Host '  [2] Original official GitHub repository'
do {
    $sourceChoice = Read-Host '  Choose 1 or 2 (Enter = local)'
} while ($sourceChoice -notin @('', '1', '2'))
$sourceArgs = @('--local')
if ($sourceChoice -eq '2') { $sourceArgs = @('--github') }
& $converterPython @converterArgs (Join-Path $PSScriptRoot 'aviso_converter.py') @sourceArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Conversion did not complete. See the error above.' -ForegroundColor Red
}
