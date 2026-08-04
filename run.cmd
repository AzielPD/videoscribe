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

echo.
echo  Python was not found on this computer.
echo  Run init.cmd first to install it.
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
