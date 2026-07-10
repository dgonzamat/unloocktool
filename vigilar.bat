@echo off
REM Doble clic para EJECUTAR el vigilante (no abrirlo en el editor).
REM Muestra una consola con el estado del USB y abre la GUI al conectar el telefono.
title unlooktool - vigilante USB
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py unlooktool_watch.py %*
) else (
    python unlooktool_watch.py %*
)

echo.
echo [i] El vigilante se detuvo. Pulsa una tecla para cerrar.
pause >nul
endlocal
