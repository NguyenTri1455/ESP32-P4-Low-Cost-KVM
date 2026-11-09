@echo off
setlocal enabledelayedexpansion

title ESP32-P4 HDMI KVM Builder

:: Determine if run interactively (no arguments passed)
set "INTERACTIVE=0"
if "%~1"=="" set "INTERACTIVE=1"

:: 1. Check if idf.py is already available in current session PATH
where idf.py >nul 2>nul
if %ERRORLEVEL% equ 0 goto :CHECK_PYTHON_CACHE

:: 2. Prepend Python 3.11 from Espressif tools if available to avoid system python conflicts
if exist "%USERPROFILE%\.espressif\tools\idf-python\3.11.2\python.exe" (
    set "PATH=%USERPROFILE%\.espressif\tools\idf-python\3.11.2;!PATH!"
) else if exist "C:\Espressif\tools\idf-python\3.11.2\python.exe" (
    set "PATH=C:\Espressif\tools\idf-python\3.11.2;!PATH!"
)

if not defined IDF_TOOLS_PATH (
    if exist "%USERPROFILE%\.espressif\esp_idf.json" set "IDF_TOOLS_PATH=%USERPROFILE%\.espressif"
    if exist "C:\Espressif\esp_idf.json" set "IDF_TOOLS_PATH=C:\Espressif"
)

:: 3. Search for ESP-IDF installations
echo [*] idf.py not found in PATH. Searching for local ESP-IDF installations...

set "CANDIDATES=%IDF_PATH% %USERPROFILE%\esp\v5.5.2\esp-idf %USERPROFILE%\esp\v5.4.3\esp-idf C:\esp-idf-v5.5 C:\esp\v5.4.4\esp-idf C:\esp\v6.1\esp-idf C:\Espressif\frameworks\esp-idf-v5.5 C:\Espressif\frameworks\esp-idf-v5.4 C:\Espressif\frameworks\esp-idf-v5.3.2 C:\Espressif\frameworks\esp-idf-v5.3 C:\Espressif\esp-idf C:\esp\esp-idf %USERPROFILE%\esp\v5.4.4\esp-idf %USERPROFILE%\esp\esp-idf"

for %%P in (%CANDIDATES%) do (
    if exist "%%P\export.bat" (
        echo [*] Found ESP-IDF in: %%P
        set "IDF_PATH=%%P"
        call "%%P\export.bat"
        goto :CHECK_AGAIN
    )
)

:CHECK_AGAIN
where idf.py >nul 2>nul
if %ERRORLEVEL% equ 0 goto :CHECK_PYTHON_CACHE

echo [!] ERROR: ESP-IDF export was not successful or tools are not yet installed.
echo If this is a fresh ESP-IDF installation, run:
echo   Build.bat install
echo.
if "%INTERACTIVE%"=="1" pause
exit /b 1

:CHECK_PYTHON_CACHE
if exist "build\CMakeCache.txt" (
    if defined IDF_PYTHON_ENV_PATH (
        findstr /i /c:"%IDF_PYTHON_ENV_PATH%" build\CMakeCache.txt >nul 2>nul
        if errorlevel 1 (
            echo [*] Python interpreter changed to: %IDF_PYTHON_ENV_PATH%
            echo [*] Auto-cleaning build cache to prevent environment mismatch...
            rmdir /s /q build >nul 2>nul
        )
    )
)

:IDF_FOUND
echo [OK] ESP-IDF environment ready.
echo.

:: 4. Parse Arguments
if not "%~1"=="" (
    set "ACTION=%~1"
    set "PORT=%~2"
    set "BAUD=%~3"
    if "!BAUD!"=="" set "BAUD=460800"
    goto :RUN_ACTION
)

:: 5. Interactive Menu
:MENU
cls
echo ==============================================================
echo       ESP32-P4 HDMI-to-Ethernet KVM - Build and Flash Tool
echo ==============================================================
echo.
echo   --- Serial Flashing (USB / COM) ---
echo   [1] Build, Flash and Monitor (All-in-One via USB)
echo   [2] Build Only
echo   [3] Flash Only (USB / COM)
echo   [4] Build and Flash (USB / COM)
echo   [5] Monitor Serial Output Only
echo.
echo   --- Network Flashing (OTA via IP) ---
echo   [6] Build and Flash via Network (OTA)
echo   [7] Flash via Network Only (OTA)
echo.
echo   --- Utilities ---
echo   [8] Menuconfig (Configure Video, Pins, Ethernet)
echo   [9] Clean Build Folder
echo   [10] Full Clean (Clean Build and Cache)
echo   [11] Set Target (esp32p4)
echo   [12] Install ESP-IDF Tools for ESP32-P4
echo   [0] Exit
echo.
set /p "CHOICE=Select an option [0-12] (Default: 6): "
if "%CHOICE%"=="" set "CHOICE=6"

if "%CHOICE%"=="1" set "ACTION=all"& goto :ASK_PORT
if "%CHOICE%"=="2" set "ACTION=build"& goto :RUN_ACTION
if "%CHOICE%"=="3" set "ACTION=flash"& goto :ASK_PORT
if "%CHOICE%"=="4" set "ACTION=build-flash"& goto :ASK_PORT
if "%CHOICE%"=="5" set "ACTION=monitor"& goto :ASK_PORT
if "%CHOICE%"=="6" set "ACTION=build-ota"& goto :ASK_IP
if "%CHOICE%"=="7" set "ACTION=ota"& goto :ASK_IP
if "%CHOICE%"=="8" set "ACTION=menuconfig"& goto :RUN_ACTION
if "%CHOICE%"=="9" set "ACTION=clean"& goto :RUN_ACTION
if "%CHOICE%"=="10" set "ACTION=fullclean"& goto :RUN_ACTION
if "%CHOICE%"=="11" set "ACTION=set-target"& goto :RUN_ACTION
if "%CHOICE%"=="12" set "ACTION=install"& goto :RUN_ACTION
if "%CHOICE%"=="0" exit /b 0

echo Invalid choice.
pause
goto :MENU

:ASK_PORT
echo.
set /p "PORT=Enter COM Port (e.g. COM39) [Leave blank to auto-detect]: "
set "BAUD=460800"
goto :RUN_ACTION

:ASK_IP
echo.
set /p "TARGET_IP=Enter Device IP Address (Default: 172.16.1.54): "
if "%TARGET_IP%"=="" set "TARGET_IP=172.16.1.54"
goto :RUN_ACTION

:RUN_ACTION
if "%BAUD%"=="" set "BAUD=460800"

:: Handle install
if "%ACTION%"=="install" (
    echo [*] Running ESP-IDF tools installation for esp32p4...
    if exist "%IDF_PATH%\install.bat" (
        call "%IDF_PATH%\install.bat" esp32p4
    ) else (
        python "%IDF_PATH%\tools\idf_tools.py" install --targets=esp32p4
        python "%IDF_PATH%\tools\idf_tools.py" install-python-env
    )
    if "%INTERACTIVE%"=="1" pause
    exit /b %ERRORLEVEL%
)

:: Ensure target is set to esp32p4 if sdkconfig does not exist
if not exist "sdkconfig" (
    echo [*] Setting target to esp32p4...
    call idf.py set-target esp32p4
    if %ERRORLEVEL% neq 0 (
        echo [!] Failed to set target.
        if "%INTERACTIVE%"=="1" pause
        exit /b %ERRORLEVEL%
    )
)

if "%ACTION%"=="set-target" (
    call idf.py set-target esp32p4
    if "%INTERACTIVE%"=="1" pause
    exit /b %ERRORLEVEL%
)

if "%ACTION%"=="clean" (
    call idf.py clean
    if "%INTERACTIVE%"=="1" pause
    exit /b %ERRORLEVEL%
)

if "%ACTION%"=="fullclean" (
    echo [*] Cleaning build and sdkconfig...
    call idf.py fullclean
    if exist "build" rmdir /s /q build
    if "%INTERACTIVE%"=="1" pause
    exit /b %ERRORLEVEL%
)

if "%ACTION%"=="menuconfig" (
    call idf.py menuconfig
    exit /b %ERRORLEVEL%
)

if "%ACTION%"=="build" (
    echo [*] Building project for ESP32-P4...
    call idf.py build
    set "ERR=!ERRORLEVEL!"
    if "!ERR!"=="0" (
        echo.
        echo [OK] Build succeeded! Binaries are in build\ directory.
    ) else (
        echo.
        echo [!] Build failed with error code !ERR!.
    )
    if "%INTERACTIVE%"=="1" pause
    exit /b !ERR!
)

:: OTA Actions
if "%ACTION%"=="build-ota" goto :RUN_BUILD_OTA
if "%ACTION%"=="ota" goto :RUN_OTA

:: For flash, build-flash, monitor, all: resolve COM port if empty
if "%ACTION%"=="flash" goto :RESOLVE_PORT
if "%ACTION%"=="build-flash" goto :RESOLVE_PORT
if "%ACTION%"=="monitor" goto :RESOLVE_PORT
if "%ACTION%"=="all" goto :RESOLVE_PORT

echo Unknown action: %ACTION%
if "%INTERACTIVE%"=="1" pause
exit /b 1

:RUN_BUILD_OTA
echo [*] Building project before OTA upload...
call idf.py build
if not "!ERRORLEVEL!"=="0" (
    echo.
    echo [!] Build failed. Aborting OTA upload.
    if "%INTERACTIVE%"=="1" pause
    exit /b 1
)
goto :RUN_OTA

:RUN_OTA
if not exist "build\esp32p4_hdmi_kvm.bin" (
    echo [*] Firmware binary not found. Building project first...
    call idf.py build
    if not "!ERRORLEVEL!"=="0" (
        echo [!] Build failed. Cannot proceed with OTA.
        if "%INTERACTIVE%"=="1" pause
        exit /b 1
    )
)

if "%TARGET_IP%"=="" set "TARGET_IP=%PORT%"
if "%TARGET_IP%"=="" set "TARGET_IP=%~2"
if "%TARGET_IP%"=="" (
    set /p "TARGET_IP=Enter Device IP Address (Default: 172.16.1.54): "
)
if "%TARGET_IP%"=="" set "TARGET_IP=172.16.1.54"

echo.
echo ==============================================================
echo       ESP32-P4 Network OTA Firmware Flasher
echo ==============================================================
echo [*] Target Device IP: %TARGET_IP%
echo [*] Firmware Binary : build\esp32p4_hdmi_kvm.bin
echo [*] Uploading via HTTP POST to http://%TARGET_IP%/api/ota ...
echo.

curl -X POST -H "Content-Type: application/octet-stream" --data-binary "@build\esp32p4_hdmi_kvm.bin" --progress-bar "http://%TARGET_IP%/api/ota"
set "ERR=!ERRORLEVEL!"
echo.
if "!ERR!"=="0" (
    echo.
    echo [OK] OTA Firmware upload completed successfully!
    echo [*] Device is verifying checksum and rebooting into the new firmware.
    echo [*] Web stream and KVM interface will be live at: http://%TARGET_IP%/
) else (
    echo.
    echo [!] OTA Upload failed with error code !ERR!.
    echo [*] Check that the device is online: ping %TARGET_IP%
    echo [*] Check that the URL http://%TARGET_IP%/ is reachable in your browser.
)
if "%INTERACTIVE%"=="1" pause
exit /b !ERR!

:RESOLVE_PORT
if "%PORT%"=="" (
    echo [*] Auto-detecting COM port...
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "$p = (Get-PnpDevice -Class Ports -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -match '\((COM\d+)\)' } | Sort-Object { $_.FriendlyName -match 'CH340|CP210|USB Serial' } -Descending | Select-Object -First 1); if ($p -and $p.FriendlyName -match '\((COM\d+)\)') { $Matches[1] } else { [System.IO.Ports.SerialPort]::GetPortNames() | Select-Object -First 1 }"') do set "PORT=%%i"
)

if "%PORT%"=="" (
    echo [!] No COM port detected. Please specify a COM port, e.g.: Build.bat %ACTION% COM39
    if "%INTERACTIVE%"=="1" pause
    exit /b 1
)

echo [*] Using serial port: %PORT% (Baud: %BAUD%)

if "%ACTION%"=="flash" (
    echo [*] Flashing firmware to %PORT% at %BAUD% baud...
    echo [*] TIP: If connection loops, hold [BOOT], tap [RST], then release [BOOT].
    call idf.py -p %PORT% -b %BAUD% flash
    set "ERR=!ERRORLEVEL!"
    if not "!ERR!"=="0" (
        echo [!] Flashing failed. Common solutions for Guition JC-ESP32P4-M3-DEV:
        echo     1. High Power Draw: Temporarily unplug the HDMI-to-USB capture dongle from OTG during flashing.
        echo     2. Native USB: Connect USB-C to the board native USB/FS port.
        echo     3. Manual Download Mode: Hold [BOOT] SW1, tap [RST] SW2, then release [BOOT].
    )
    if "%INTERACTIVE%"=="1" pause
    exit /b !ERR!
)

if "%ACTION%"=="build-flash" (
    echo [*] Building and flashing firmware to %PORT% at %BAUD% baud...
    echo [*] TIP: If connection loops, hold [BOOT], tap [RST], then release [BOOT].
    call idf.py -p %PORT% -b %BAUD% flash
    set "ERR=!ERRORLEVEL!"
    if not "!ERR!"=="0" (
        echo [!] Flashing failed. Common solutions for Guition JC-ESP32P4-M3-DEV:
        echo     1. High Power Draw: Temporarily unplug the HDMI-to-USB capture dongle from OTG during flashing.
        echo     2. Native USB: Connect USB-C to the board native USB/FS port.
        echo     3. Manual Download Mode: Hold [BOOT] SW1, tap [RST] SW2, then release [BOOT].
    )
    if "%INTERACTIVE%"=="1" pause
    exit /b !ERR!
)

if "%ACTION%"=="monitor" (
    echo [*] Opening serial monitor on %PORT%...
    call idf.py -p %PORT% monitor
    exit /b %ERRORLEVEL%
)

if "%ACTION%"=="all" (
    echo [*] Building, flashing, and opening monitor on %PORT% at %BAUD% baud...
    echo [*] TIP: If connection loops, hold [BOOT], tap [RST], then release [BOOT].
    call idf.py -p %PORT% -b %BAUD% flash monitor
    set "ERR=!ERRORLEVEL!"
    if not "!ERR!"=="0" (
        echo [!] Flashing failed. Common solutions for Guition JC-ESP32P4-M3-DEV:
        echo     1. High Power Draw: Temporarily unplug the HDMI-to-USB capture dongle from OTG during flashing.
        echo     2. Native USB: Connect USB-C to the board native USB/FS port.
        echo     3. Manual Download Mode: Hold [BOOT] SW1, tap [RST] SW2, then release [BOOT].
    )
    if "%INTERACTIVE%"=="1" pause
    exit /b !ERR!
)
