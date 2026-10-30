# Run with Windows PowerShell 5.1: powershell.exe -NoProfile -File tools/hotspot.ps1
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringAccessPointConfiguration,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime] | Out-Null
function Await-Operation($Operation, [Type]$ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait(30000)) { throw 'Hotspot operation timed out' }
    return $task.Result
}
function Await-Action($Action) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
    } | Select-Object -First 1
    $task = $method.Invoke($null, @($Action))
    if (-not $task.Wait(30000)) { throw 'Hotspot configuration timed out' }
    $task.GetAwaiter().GetResult()
}
$root = Split-Path $PSScriptRoot -Parent
$localDir = Join-Path $root '.local'
New-Item -ItemType Directory -Force $localDir | Out-Null
$configPath = Join-Path $localDir 'wifi.json'
if (Test-Path $configPath) {
    $saved = Get-Content $configPath -Raw | ConvertFrom-Json
} else {
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 24
    $rng.GetBytes($bytes)
    $password = ([BitConverter]::ToString($bytes)).Replace('-', '').Substring(0, 20)
    $rng.GetBytes($bytes)
    $saved = [PSCustomObject]@{ssid='CutieCircuits-Bench'; password=$password; token=([BitConverter]::ToString($bytes)).Replace('-', '').ToLower(); host=''}
    $rng.Dispose()
    $saved | ConvertTo-Json | Set-Content $configPath -Encoding UTF8
}
$profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
if (-not $profile) { throw 'No internet connection profile available' }
$manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)
if ($manager.TetheringOperationalState -ne 'On') {
    $config = New-Object Windows.Networking.NetworkOperators.NetworkOperatorTetheringAccessPointConfiguration
    $config.Ssid = $saved.ssid
    $config.Passphrase = $saved.password
    $config.Band = 1 # TwoPointFourGigahertz
    Await-Action ($manager.ConfigureAccessPointAsync($config))
    $result = Await-Operation ($manager.StartTetheringAsync()) ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult])
    if ($result.Status -ne 'Success') { throw "Hotspot failed: $($result.Status) $($result.AdditionalErrorMessage)" }
} else {
    $active = $manager.GetCurrentAccessPointConfiguration()
    if ($active.Ssid -ne $saved.ssid -or $active.Passphrase -ne $saved.password -or [int]$active.Band -ne 1) {
        throw 'An existing hotspot has different settings; stop it before running this setup.'
    }
}
New-Item -ItemType Directory -Force (Join-Path $root 'include') | Out-Null
$setupScript = Join-Path $PSScriptRoot 'setup_robot.py'
python $setupScript header
if ($LASTEXITCODE -ne 0) { throw 'Generating the private firmware header failed.' }
Write-Output "Hotspot: $($saved.ssid); state=$($manager.TetheringOperationalState); uplink=$($profile.ProfileName); band=2.4GHz"
Write-Output 'Credentials saved locally and excluded from git.'
