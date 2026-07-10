@echo off
REM Lanzador de doble clic para unlooktool (Windows)
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py unlooktool.py %*
) else (
    python unlooktool.py %*
)

echo.
pause
endlocal
