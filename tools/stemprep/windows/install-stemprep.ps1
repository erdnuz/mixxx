# Installs stemprep (spotDL + Demucs + Beat This!) into its own Python
# environment and puts a "Stemprep" shortcut on the Desktop.
#
# Run by double-clicking "Install Stemprep.bat" next to this file.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $here
$appDir = Join-Path $env:LOCALAPPDATA "stemprep"
$venv = Join-Path $appDir "venv"

function Say($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# 1. Python 3.10 - 3.13 ------------------------------------------------------
Say "Looking for Python 3.10-3.13"
$py = $null
foreach ($v in "3.12", "3.11", "3.13", "3.10") {
    try {
        $out = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { $py = @("py", "-$v"); break }
    } catch {}
}
if (-not $py) {
    try {
        $ver = & python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($ver -match '^3\.(1[0-3])$') { $py = @("python") }
    } catch {}
}
if (-not $py) {
    Write-Host "Python 3.12 is needed. Installing it with winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $py = @("py", "-3.12")
}
Write-Host "Using: $($py -join ' ')"

# 2. Virtual environment ----------------------------------------------------
Say "Creating environment in $venv"
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    $pyExe = $py[0]
    $pyArgs = @()
    if ($py.Length -gt 1) { $pyArgs = $py[1..($py.Length - 1)] }
    & $pyExe @pyArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment" }
}
$vpy = Join-Path $venv "Scripts\python.exe"
& $vpy -m pip install --upgrade pip wheel

# 3. PyTorch: CUDA build if there is an NVIDIA GPU, otherwise CPU ----------
$hasNvidia = $false
try { & nvidia-smi *> $null; if ($LASTEXITCODE -eq 0) { $hasNvidia = $true } } catch {}
if ($hasNvidia) {
    Say "NVIDIA GPU found: installing PyTorch with CUDA"
    & $vpy -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126
} else {
    Say "No NVIDIA GPU: installing CPU PyTorch (stems take ~1-3 min per track)"
    & $vpy -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
}
if ($LASTEXITCODE -ne 0) { throw "PyTorch install failed" }

# 4. stemprep and its dependencies (Demucs, Beat This!, spotDL) -------------
Say "Installing stemprep, Demucs, Beat This! and spotDL"
& $vpy -m pip install --upgrade $projectDir
if ($LASTEXITCODE -ne 0) { throw "stemprep install failed" }

# 5. ffmpeg -----------------------------------------------------------------
Say "Checking ffmpeg"
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ff -and -not (Test-Path (Join-Path $HOME ".spotdl\ffmpeg.exe"))) {
    & (Join-Path $venv "Scripts\spotdl.exe") --download-ffmpeg
}

# 6. Download the AI models now so the first run doesn't stall -------------
Say "Downloading the AI models (one time, ~350 MB)"
& $vpy -c "from stemprep.ml import load_models; load_models(True, 'cpu', 'htdemucs'); print('models ready')"

# 7. Desktop shortcut ---------------------------------------------------------
Say "Creating Desktop shortcut"
$launcher = Join-Path $appDir "Stemprep.bat"
Copy-Item (Join-Path $here "Stemprep.bat") $launcher -Force
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop "Stemprep.lnk"))
$lnk.TargetPath = $launcher
$lnk.WorkingDirectory = $appDir
$lnk.Description = "Spotify playlist -> stems + phrases for Mixxx"
$lnk.Save()

Write-Host "`nAll set. Double-click 'Stemprep' on your Desktop and paste a Spotify link." -ForegroundColor Green
Write-Host "Your stems will be in: $HOME\Music\stemprep\Stems" -ForegroundColor Green
