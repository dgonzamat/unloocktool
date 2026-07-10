@echo off
REM Lanzador de doble clic para la interfaz grafica de unlooktool (Windows)
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw unlooktool_gui.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py unlooktool_gui.py
    ) else (
        python unlooktool_gui.py
    )
)
endlocal
