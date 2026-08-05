@echo off
REM ===========================================================================
REM  VideoScribe setup for Windows.
REM
REM  Double-click this file. It hands over to scripts\init.ps1, which installs
REM  anything that is missing: Python, ffmpeg, and the Python packages.
REM
REM  This wrapper exists so nobody has to know about PowerShell execution
REM  policies -- -ExecutionPolicy Bypass applies to this one run only and
REM  changes nothing on the machine.
REM ===========================================================================

setlocal
cd /d "%~dp0"

echo.
echo  Starting VideoScribe setup...
echo.

where powershell >nul 2>&1
if errorlevel 1 (
    echo  PowerShell was not found on this computer.
    echo  VideoScribe needs Windows 10 or newer.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\init.ps1" %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo  Setup did not finish cleanly. Read the messages above.
) else (
    echo  Setup finished.
)
echo.
pause
exit /b %EXITCODE%
