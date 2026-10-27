@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo  FlowCast Android — APK Builder
echo ============================================
echo.
echo  Vaatimukset APK-buildaukseen:
echo   1. Python 3.12+ PATHissa
echo   2. flet asennettuna (pip install flet)
echo   3. Flutter SDK asennettuna ja PATHissa
echo   4. Android SDK asennettuna (ANDROID_HOME)
echo   5. JDK 17+ asennettuna
echo.
echo  Jos Flutter/Android SDK puuttuu, APK:ta ei voida buildata.
echo  Voit testata sovellusta ajamalla: python main.py
echo.
echo ============================================
echo.

cd /d "%~dp0"

REM Tarkista flet
python -c "import flet" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] flet ei ole asennettu. Asennetaan...
    pip install flet httpx
    if %ERRORLEVEL% neq 0 (
        echo [X] Asennus epaonnistui
        pause
        exit /b 1
    )
)

REM Tarkista Flutter
where flutter >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Flutteria ei loydy PATHista.
    echo.
    echo  Vaihtoehdot:
    echo   A) Asenna Flutter: https://docs.flutter.dev/get-started/install/windows
    echo   B) Testaa sovellusta desktopilla: python main.py
    echo.
    choice /C AB /N /M "Valitse [A] Lopeta [B] Testaa desktopilla: "
    if !ERRORLEVEL! equ 1 (
        echo.
        echo  Lataa Flutter: https://docs.flutter.dev/get-started/install/windows
        echo  Tai kayta: winget install Google.Flutter
        pause
        exit /b 1
    ) else (
        echo.
        echo Kaynnistetaan desktop-testitilassa...
        python main.py
        pause
        exit /b 0
    )
)

REM Yrita APK build
echo.
echo Rakennetaan APK...
echo.

flet build apk ^
    --org com.flowcast.android ^
    --project "FlowCast Android" ^
    --product "FlowCast" ^
    --description "FlowCast Android - Taildrop File Manager" ^
    --android-permissions "android.permission.INTERNET=true" ^
    --android-permissions "android.permission.ACCESS_NETWORK_STATE=true" ^
    --android-permissions "android.permission.ACCESS_WIFI_STATE=true" ^
    --android-permissions "android.permission.READ_EXTERNAL_STORAGE=true" ^
    --android-permissions "android.permission.WRITE_EXTERNAL_STORAGE=true" ^
    --android-permissions "android.permission.MANAGE_EXTERNAL_STORAGE=true" ^
    --android-permissions "android.permission.READ_MEDIA_IMAGES=true" ^
    --android-permissions "android.permission.READ_MEDIA_VIDEO=true" ^
    --android-permissions "android.permission.READ_MEDIA_AUDIO=true" ^
    --android-features "android.hardware.camera=false" ^
    --android-features "android.hardware.camera.autofocus=false" ^
    --no-android-splash ^
    --no-rich-output ^
    --skip-flutter-doctor

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================
    echo  APK build valmis!
    echo  APK loytyy: build\apk\debug\app-debug.apk
    echo  Siirra APK Taildropilla puhelimeen ja asenna.
    echo ============================================
) else (
    echo.
    echo [X] APK-build epaonnistui.
    echo Tarkista etta Flutter ja Android SDK ovat asennettu oikein.
    echo Voit myos ajaa manuaalisesti:
    echo   flet build apk --org com.flowcast.android
)

pause
