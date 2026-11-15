$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    $candidates = @(
        (Join-Path $AppRoot ".venv\Scripts\python.exe"),
        (Join-Path $AppRoot ".venv\bin\python")
    )
    foreach ($cmdName in @("python3", "python")) {
        $cmd = Get-Command $cmdName -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) {
            $candidates += $cmd.Source
        }
    }
    $pyDirs = Get-ChildItem -Path "C:\Python*", "$env:LOCALAPPDATA\Programs\Python\Python*" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending
    foreach ($dir in $pyDirs) {
        $candidates += (Join-Path $dir.FullName "python.exe")
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            try {
                $null = & $candidate --version 2>$null
                if ($LASTEXITCODE -eq 0) {
                    return $candidate
                }
            } catch {
                continue
            }
        }
    }
    return $null
}

$PythonBin = Find-Python
if (-not $PythonBin) {
    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & py -3 (Join-Path $AppRoot "scripts\run.py") @args
        exit $LASTEXITCODE
    }
    Write-Error "Python 3.12+ was not found. Install Python and rerun .\run.ps1 --setup."
    exit 1
}

& $PythonBin (Join-Path $AppRoot "scripts\run.py") @args
exit $LASTEXITCODE
