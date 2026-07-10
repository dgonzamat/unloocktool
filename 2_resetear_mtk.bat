@echo off
REM PASO 2 - Reset de fabrica (borra userdata) via MTKClient.
REM Hazlo SOLO si el PASO 1 mostro la lista de particiones correctamente.
title MTKClient - PASO 2: reset de fabrica (borra datos)
setlocal
cd /d "%~dp0mtkclient"

echo ============================================================
echo  PASO 2 - RESET DE FABRICA (borra 'userdata')
echo ============================================================
echo  Esto BORRA todos los datos del telefono (reset de fabrica).
echo  El telefono debe estar en modo BROM (apagado + Vol Arriba+Abajo
echo  + conectar USB), igual que en el PASO 1.
echo.
set /p ok="Escribe BORRAR y pulsa Enter para continuar: "
if /I not "%ok%"=="BORRAR" (
    echo Cancelado.
    pause
    exit /b
)

echo.
echo Borrando userdata...
python mtk.py e userdata
echo.
echo ------------------------------------------------------------
echo  Si termino sin errores: desconecta, enciende el telefono y
echo  deberia arrancar limpio, sin PIN.
echo  (Si sigue pidiendo PIN, avisa: probamos borrar tambien 'metadata'.)
echo ------------------------------------------------------------
pause
endlocal
