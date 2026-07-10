@echo off
REM PASO 1 - Verificar conexion MediaTek (solo LEE, no borra nada).
REM Con el telefono APAGADO: manten Volumen Arriba + Volumen Abajo y conecta el USB.
title MTKClient - PASO 1: verificar conexion (seguro)
setlocal
cd /d "%~dp0mtkclient"

echo ============================================================
echo  PASO 1 - VERIFICAR CONEXION (no borra nada)
echo ============================================================
echo  1) El telefono debe estar APAGADO.
echo  2) Manten pulsados Volumen ARRIBA + Volumen ABAJO.
echo  3) Conecta el cable USB sin soltar los botones.
echo.
echo  Leyendo la tabla de particiones del telefono...
echo.
python mtk.py printgpt
echo.
echo ------------------------------------------------------------
echo  Si ves una lista de particiones (userdata, cache, etc.) =^> conexion OK.
echo  Si dice "Waiting for PreLoader/BROM" y no avanza =^> falta el driver
echo  UsbDk o no entro en modo BROM (reintenta el paso 2-3).
echo ------------------------------------------------------------
pause
endlocal
