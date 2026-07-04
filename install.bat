@echo off
REM Double-click installer for FreeCAD Automatic MCP.
REM Runs install.ps1 with the execution policy bypassed and installs uv if missing.
REM Any arguments passed to this .bat are forwarded to install.ps1.

setlocal
set "SCRIPT_DIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" -InstallUvIfMissing %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Install finished. Open FreeCAD - the MCP bridge auto-starts a few seconds after launch.
) else (
    echo Install failed with exit code %RC%. Review the messages above.
)
echo.
pause
endlocal
