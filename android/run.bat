@echo off
chcp 65001 >nul
echo ============================================
echo  FlowCast Android — APK Build
echo ============================================
echo.
echo  Vaatimukset:
echo   - Python 3.12+ PATH:ssa
echo   - flet asennettuna (pip install flet)
echo   - Android SDK (tai flutter SDK)
echo.
echo  HUOM: flet build apk vaatii, etta:
echo   1. Flutter on asennettu
echo   2. Android SDK on asennettu (ANDROID_HOME)
echo   3. JDK 17+ on asennettu
echo.
echo  Vaihtoehto 1: Aja suoraan Pythonilla testataksesi
echo    python main.py
echo.
echo  Vaihtoehto 2: Buildaa APK (vaatii Flutter + Android SDK)
echo    flet build apk --org com.flowcast.android
echo.
echo  ============================================

cd /d "%~dp0"

REM Tarkista onko flet asennettu
python -c "import flet" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] flet ei ole asennettu. Asennetaan...
    pip install flet httpx
)

echo.
echo Kaynnistetaan FlowCast Android testitilassa...
echo.
python main.py
pause
