@echo off
setlocal
title FlowCast - Start

:: ===========================================================
:: 0. ASETUKSET (ymparistomuuttujat, valinnainen)
:: ===========================================================
if not defined FLOWCAST_PORT set FLOWCAST_PORT=5010

:: ===========================================================
:: 1. PYTHON-TARKISTUS
:: ===========================================================
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [VIRHE] Python puuttuu tai ei ole PATH:ssa!
    echo Asenna Python 3.12+ osoitteesta https://www.python.org/
    echo Muista ruksata "Add python.exe to PATH" asennuksessa.
    pause
    exit /b
)

:: ===========================================================
:: 2. VIRTUAALIYMPARISTO
:: ===========================================================
if not exist "venv" (
    echo [SETUP] Luodaan Python-ymparisto...
    python -m venv venv
    if errorlevel 1 (
        echo [VIRHE] Virtuaaliympariston luonti epaonnistui!
        pause
        exit /b
    )
)

:: ===========================================================
:: 3. KIRJASTOT
:: ===========================================================
venv\Scripts\python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Asennetaan kirjastot...
    venv\Scripts\python -m pip install --upgrade pip --quiet
    venv\Scripts\pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [VIRHE] Asennus epaonnistui! Tarkista nettiyhteys.
        pause
        exit /b
    )
    echo [OK] Asennus valmis.
)

:: ===========================================================
:: 3.5 FFMPEG-TARKISTUS (videokonversio, valinnainen)
:: ===========================================================
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Asennetaan FFmpeg ^(AVI/WMV/MOV-konversio^)...
    powershell -Command "winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements --silent"
    if errorlevel 1 (
        echo [HUOM] FFmpeg-asennus epaonnistui. AVI/WMV/MOV-videot ohitetaan.
    ) else (
        echo [OK] FFmpeg asennettu. Kaynnista ohjelma uudelleen aktivoidaksesi konversion.
    )
)

:: ===========================================================
:: 4. KAYNNISTYS
:: ===========================================================
:: Kutsutaan PowerShellia tarkistamaan nimenomaan portti 5010
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %FLOWCAST_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>&1

if %errorlevel% equ 1 (
    echo.
    echo [HUOM] Portti %FLOWCAST_PORT% on jo varattu!
    echo        FlowCast on joko jo kaynnissa tai portti on muussa kaytossa.
    echo.
    pause
    exit /b
)

echo.
echo ===================================================
echo   FLOWCAST KAYNNISTYY
echo   Admin:   http://127.0.0.1:%FLOWCAST_PORT%/adminloginhere
echo   Naytto:  http://127.0.0.1:%FLOWCAST_PORT%/display
echo ===================================================
echo.

start http://127.0.0.1:%FLOWCAST_PORT%/adminloginhere
venv\Scripts\python mediaplayer.py

if errorlevel 1 (
    echo.
    echo [CRASH] Ohjelma kaatui odottamattomasti.
    pause
)
