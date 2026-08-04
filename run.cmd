@echo off
REM ===========================================================================
REM  Start VideoScribe.
REM
REM  Double-click this file. It opens the menu, where you choose between a
REM  transcript on its own and a transcript plus a description of the picture.
REM
REM  If nothing happens, run init.cmd first to install what is missing.
REM ===========================================================================

setlocal
cd /d "%~dp0"

REM Prefer the private environment created by init.sh, if one exists.
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
    goto :run
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    goto :run
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py"
    goto :run
)

REM Offer to fix it rather than just reporting it: someone who has never used a
REM terminal has no way to act on "run init.cmd first".
echo.
echo  Python was not found on this computer.
echo  VideoScribe needs it, and the setup can install it for you.
echo.
choice /c YN /n /m "  Run the setup now? [Y,N]: "
if errorlevel 2 goto :nosetup
echo.
call "%~dp0init.cmd"
exit /b %ERRORLEVEL%

:nosetup
echo.
echo  When you are ready, double-click  init.cmd
echo.
pause
exit /b 1

:run
"%PY%" "%~dp0videoscribe.py" %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo  Finished with problems. Read the messages above.
)
pause
exit /b %EXITCODE%
