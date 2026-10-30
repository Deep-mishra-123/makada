param(
    [string]$Port,
    [switch]$Flash,
    [switch]$ServoPowerDisconnected
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($Flash -and (-not $ServoPowerDisconnected -or -not $Port)) {
    throw 'Flashing requires -Port COMx -ServoPowerDisconnected after physically unplugging the LiPo.'
}
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 or 3.12 with Add Python to PATH, then retry.' }
}
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $pythonPath tools/setup_robot.py init
if ($LASTEXITCODE -ne 0) { throw 'Local configuration failed.' }
# The hotspot helper invokes python for header generation; use this virtual environment.
$env:PATH = (Join-Path $PSScriptRoot '.venv/Scripts') + ';' + $env:PATH
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/hotspot.ps1
if ($LASTEXITCODE -ne 0) { throw 'Hotspot setup failed. See the manual hotspot instructions in README.md.' }
& $pythonPath -m serial.tools.list_ports
if ($Flash) {
    & $pythonPath -m platformio run -d hexapod -t upload --upload-port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Firmware upload failed.' }
    & $pythonPath tools/setup_robot.py discover --port $Port --servo-power-disconnected
    if ($LASTEXITCODE -ne 0) { throw 'Upload succeeded, but discovery failed. Check the hotspot and retry discovery.' }
}
Write-Host 'Setup complete. Use .venv/Scripts/python.exe for the commands in README.md.'
Write-Host 'The setup script never enables servos or starts a walk.'
