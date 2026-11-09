# ESP32-P4 HDMI-over-Ethernet KVM Build & Flash Automation Script
[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [ValidateSet("all", "build", "flash", "build-flash", "monitor", "menuconfig", "clean", "fullclean", "set-target", "install", "ota", "build-ota")]
    [string]$Action = "all",

    [Parameter(Position = 1)]
    [string]$Port = "",

    [Parameter(Position = 2)]
    [int]$Baud = 460800,

    [string]$Ip = "172.16.1.54",

    [string]$IdfPath = ""
)

# UTF-8 and execution settings to prevent PowerShell native command false positives
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"
if (Get-Variable -Name "PSNativeCommandUseErrorActionPreference" -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Write-Step {
    param([string]$Text)
    Write-Host "`n====> $Text" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host " [OK] $Text" -ForegroundColor Green
}

function Write-WarnMsg {
    param([string]$Text)
    Write-Host " [WARN] $Text" -ForegroundColor Yellow
}

function Write-ErrMsg {
    param([string]$Text)
    Write-Host " [ERROR] $Text" -ForegroundColor Red
}

# 1. Locate ESP-IDF directory
Write-Step "Checking ESP-IDF environment..."

$candidatePaths = @(
    $IdfPath,
    $env:IDF_PATH,
    "$env:USERPROFILE\esp\v5.5.2\esp-idf",
    "$env:USERPROFILE\esp\v5.4.3\esp-idf",
    "C:\esp-idf-v5.5",
    "C:\esp\v5.4.4\esp-idf",
    "C:\esp\v6.1\esp-idf",
    "C:\Espressif\frameworks\esp-idf-v5.5",
    "C:\Espressif\frameworks\esp-idf-v5.4",
    "C:\Espressif\frameworks\esp-idf-v5.3.2",
    "C:\Espressif\frameworks\esp-idf-v5.3.1",
    "C:\Espressif\frameworks\esp-idf-v5.3",
    "C:\Espressif\frameworks\esp-idf-v5.2",
    "C:\Espressif\esp-idf",
    "C:\esp\esp-idf",
    "$env:USERPROFILE\esp\v5.4.4\esp-idf",
    "$env:USERPROFILE\esp\v6.1\esp-idf",
    "$env:USERPROFILE\esp\esp-idf"
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path "$_\export.ps1") }

$selectedIdf = ""
if ($candidatePaths.Count -gt 0) {
    $selectedIdf = $candidatePaths[0]
}

if ([string]::IsNullOrWhiteSpace($selectedIdf)) {
    Write-ErrMsg "Unable to locate ESP-IDF directory."
    Write-Host "  Please pass your ESP-IDF directory: .\build_flash.ps1 -IdfPath 'C:\esp\v5.4.4\esp-idf'" -ForegroundColor Gray
    exit 1
}

$env:IDF_PATH = $selectedIdf

# Pre-configure Python environment and IDF_TOOLS_PATH if available
$pythonCandidates = @(
    "$env:USERPROFILE\.espressif\tools\idf-python\3.11.2",
    "C:\Espressif\tools\idf-python\3.11.2"
)
foreach ($pPath in $pythonCandidates) {
    if (Test-Path "$pPath\python.exe") {
        $env:PATH = "$pPath;$env:PATH"
        break
    }
}
if ([string]::IsNullOrWhiteSpace($env:IDF_TOOLS_PATH)) {
    if (Test-Path "$env:USERPROFILE\.espressif\esp_idf.json") {
        $env:IDF_TOOLS_PATH = "$env:USERPROFILE\.espressif"
    } elseif (Test-Path "C:\Espressif\esp_idf.json") {
        $env:IDF_TOOLS_PATH = "C:\Espressif"
    }
}

# Handle 'install' action (install toolchains and python env)
if ($Action -eq "install") {
    Write-Step "Installing ESP-IDF tools & Python environment for ESP32-P4..."
    & python "$selectedIdf\tools\idf_tools.py" --idf-path "$selectedIdf" install --targets=esp32p4
    & python "$selectedIdf\tools\idf_tools.py" --idf-path "$selectedIdf" install-python-env
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ESP-IDF tools & Python environment installed successfully!"
    } else {
        Write-ErrMsg "Installation failed with exit code $LASTEXITCODE."
    }
    exit $LASTEXITCODE
}

# 2. Check and activate idf.py
$hasIdf = Get-Command "idf.py" -ErrorAction SilentlyContinue

if (-not $hasIdf) {
    Write-Step "Activating ESP-IDF environment from: $selectedIdf"
    try {
        . "$selectedIdf\export.ps1"
        $hasIdf = Get-Command "idf.py" -ErrorAction SilentlyContinue
    } catch {
        Write-WarnMsg "Export warning: $_"
    }

    if (-not $hasIdf) {
        Write-WarnMsg "Python virtual environment or tools might not be set up yet for $selectedIdf."
        Write-Host "  Installing tools automatically now..." -ForegroundColor Yellow
        & python "$selectedIdf\tools\idf_tools.py" --idf-path "$selectedIdf" install --targets=esp32p4
        & python "$selectedIdf\tools\idf_tools.py" --idf-path "$selectedIdf" install-python-env
        . "$selectedIdf\export.ps1"
        $hasIdf = Get-Command "idf.py" -ErrorAction SilentlyContinue
    }
}

# Prevent Python virtual environment mismatch (e.g. py3.11 vs py3.12 or v5.4 vs v6.1)
if ((Test-Path "build\CMakeCache.txt") -and (-not [string]::IsNullOrWhiteSpace($env:IDF_PYTHON_ENV_PATH))) {
    $cacheContent = Get-Content "build\CMakeCache.txt" -Raw
    if (-not $cacheContent.Contains($env:IDF_PYTHON_ENV_PATH)) {
        Write-WarnMsg "Active Python environment ($($env:IDF_PYTHON_ENV_PATH)) differs from build cache. Auto-cleaning..."
        Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    }
}

Write-Success "ESP-IDF is ready: $(idf.py --version 2>&1)"

# 3. Port Detection (for flash, build-flash, monitor, and all)
if ($Action -in @("flash", "build-flash", "monitor", "all")) {
    if ([string]::IsNullOrWhiteSpace($Port)) {
        Write-Step "Auto-detecting connected serial COM port..."
        
        $pnpPorts = @()
        try {
            $pnpPorts = Get-PnpDevice -Class Ports -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "OK" }
        } catch {}

        $detectedPort = ""

        # Prioritize CH340, CP210x, or Espressif native JTAG/Serial
        foreach ($dev in $pnpPorts) {
            if ($dev.FriendlyName -match '\((COM\d+)\)') {
                $pName = $Matches[1]
                if ($dev.FriendlyName -match 'CH340|CP210|Espressif|USB Serial') {
                    $detectedPort = $pName
                    Write-Success "Found target board on $pName ($($dev.FriendlyName))"
                    break
                }
            }
        }

        # Fallback to any active COM port
        if ([string]::IsNullOrWhiteSpace($detectedPort)) {
            $rawPorts = [System.IO.Ports.SerialPort]::GetPortNames()
            if ($rawPorts.Count -gt 0) {
                $detectedPort = $rawPorts[0]
                Write-WarnMsg "Defaulting to first detected port: $detectedPort"
            }
        }

        if ([string]::IsNullOrWhiteSpace($detectedPort)) {
            Write-ErrMsg "No serial COM ports found. Please connect the board or specify -Port COMx."
            exit 1
        }

        $Port = $detectedPort
    } else {
        Write-Success "Using specified port: $Port"
    }
}

# 4. Ensure target is set to esp32p4
if (-not (Test-Path "sdkconfig") -or $Action -eq "set-target") {
    Write-Step "Setting target to esp32p4..."
    idf.py set-target esp32p4
    if ($LASTEXITCODE -ne 0) {
        Write-ErrMsg "Failed to set target to esp32p4."
        exit $LASTEXITCODE
    }
}

# 5. Execute selected action
switch ($Action) {
    "clean" {
        Write-Step "Cleaning build artifacts..."
        idf.py clean
    }
    "fullclean" {
        Write-Step "Performing full project clean..."
        idf.py fullclean
        Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    }
    "menuconfig" {
        Write-Step "Launching menuconfig configuration..."
        idf.py menuconfig
    }
    "build" {
        Write-Step "Building firmware for ESP32-P4..."
        idf.py build
    }
    "flash" {
        Write-Step "Flashing firmware to $Port at $Baud baud..."
        Write-Host ">>> NOTE: If connecting loops ('Connecting...'), hold [BOOT], tap [RST], then release [BOOT]! <<<" -ForegroundColor Yellow
        idf.py -p $Port -b $Baud flash
    }
    "build-flash" {
        Write-Step "Building and flashing firmware to $Port at $Baud baud..."
        Write-Host ">>> NOTE: If connecting loops ('Connecting...'), hold [BOOT], tap [RST], then release [BOOT]! <<<" -ForegroundColor Yellow
        idf.py -p $Port -b $Baud flash
    }
    "monitor" {
        Write-Step "Opening serial monitor on $Port..."
        idf.py -p $Port monitor
    }
    "all" {
        Write-Step "Building, flashing to $Port, and starting serial monitor..."
        idf.py -p $Port -b $Baud flash monitor
    }
    "build-ota" {
        Write-Step "Building firmware for OTA update..."
        idf.py build
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Uploading firmware via OTA to http://${Ip}/api/ota ..."
            curl.exe -X POST -H "Content-Type: application/octet-stream" --data-binary "@build\esp32p4_hdmi_kvm.bin" --progress-bar "http://${Ip}/api/ota"
        }
    }
    "ota" {
        Write-Step "Uploading firmware via OTA to http://${Ip}/api/ota ..."
        curl.exe -X POST -H "Content-Type: application/octet-stream" --data-binary "@build\esp32p4_hdmi_kvm.bin" --progress-bar "http://${Ip}/api/ota"
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Success "Action '$Action' completed successfully!"
} else {
    Write-ErrMsg "Action '$Action' failed with exit code $LASTEXITCODE."
    if ($Action -in @("flash", "build-flash", "all")) {
        Write-Host "`n[!] Troubleshooting steps for Guition JC-ESP32P4-M3-DEV:" -ForegroundColor Yellow
        Write-Host "    1. Power Sag: Temporarily disconnect the HDMI capture dongle from the USB-HS (OTG) port while flashing." -ForegroundColor Yellow
        Write-Host "    2. Native USB: Plug a USB-C cable into the board's 'USB / FS' port (direct ESP32-P4 USB-Serial/JTAG)." -ForegroundColor Yellow
        Write-Host "    3. Manual Boot: Hold physical [BOOT] (SW1), tap [RST] (SW2), release [BOOT], then re-run flash." -ForegroundColor Yellow
    }
    exit $LASTEXITCODE
}
