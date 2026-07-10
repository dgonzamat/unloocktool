#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unlooktool_watch - Vigila el USB y abre la GUI cuando conectas el telefono.

Sondea 'adb devices' / 'fastboot devices' cada pocos segundos. Cuando el
dispositivo pasa de NO conectado a conectado (flanco de subida), lanza
unlooktool_gui.py una sola vez. No vuelve a lanzarla hasta que desconectes y
reconectes.

Detecta el telefono en modo 'adb' (sistema con Depuracion USB) o 'fastboot'.
Nota: en modo normal SIN Depuracion USB, adb no lo ve (limitacion de Android).

Uso:
  python unlooktool_watch.py                # vigila (Ctrl+C para salir)
  python unlooktool_watch.py --interval 3   # intervalo de sondeo en segundos
  python unlooktool_watch.py --once         # abre la GUI si YA hay device y sale
  python unlooktool_watch.py --no-launch    # solo muestra el estado, no abre nada
  python unlooktool_watch.py --no-notify    # no muestra la notificacion de Windows
"""
from __future__ import annotations

import base64
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unlooktool  # noqa: E402  (reutiliza _find_tool y rutas)

HERE = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(HERE, "unlooktool_gui.py")


def device_mode() -> str | None:
    """Devuelve 'adb', 'fastboot' o None segun lo que haya conectado."""
    adb = unlooktool._find_tool("adb")
    fb = unlooktool._find_tool("fastboot")
    if adb:
        try:
            out = subprocess.run([adb, "devices"], text=True, capture_output=True,
                                 timeout=10).stdout
            if any(line.strip().endswith("\tdevice") for line in out.splitlines()):
                return "adb"
        except (subprocess.TimeoutExpired, OSError):
            pass
    if fb:
        try:
            out = subprocess.run([fb, "devices"], text=True, capture_output=True,
                                 timeout=10).stdout
            if out.strip():
                return "fastboot"
        except (subprocess.TimeoutExpired, OSError):
            pass
    return None


def notify(title: str, message: str) -> None:
    """Muestra una notificacion nativa de Windows (globo), sin dependencias."""
    if os.name != "nt":
        return
    t = title.replace("'", "''")
    m = message.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$n = New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon = [System.Drawing.SystemIcons]::Information;"
        f"$n.BalloonTipTitle = '{t}';"
        f"$n.BalloonTipText = '{m}';"
        "$n.Visible = $true;"
        "$n.ShowBalloonTip(5000);"
        "Start-Sleep -Seconds 6;"
        "$n.Dispose()"
    )
    # -EncodedCommand (UTF-16LE base64) evita cualquier problema de comillas.
    b64 = base64.b64encode(ps.encode("utf-16-le")).decode("ascii")
    try:
        subprocess.Popen(
            [_powershell(), "-NoProfile", "-NonInteractive", "-EncodedCommand", b64],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
        )
    except OSError as exc:
        print(f"[i] (no se pudo mostrar la notificacion: {exc})")


def _powershell() -> str:
    """Ruta a powershell.exe (robusta aunque el PATH sea minimo)."""
    import shutil
    found = shutil.which("powershell") or shutil.which("powershell.exe")
    if found:
        return found
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def launch_gui() -> None:
    """Abre la GUI sin ventana de consola (pythonw si existe)."""
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.isfile(pyw) else sys.executable
    print(f"[i] Abriendo la GUI: {exe} {GUI}")
    try:
        subprocess.Popen([exe, GUI], cwd=HERE, close_fds=True)
    except OSError as exc:
        print(f"[!] No se pudo abrir la GUI: {exc}")


def watch(interval: float = 3.0, launch: bool = True, notify_on: bool = True) -> int:
    print("=" * 56)
    print(" unlooktool_watch - vigilando el USB (Ctrl+C para salir)")
    print("=" * 56)
    if not unlooktool._find_tool("adb") and not unlooktool._find_tool("fastboot"):
        print("[!] No hay adb/fastboot. Ejecuta primero:  python unlooktool.py setup")
        return 2

    connected = False  # estado previo
    try:
        while True:
            mode = device_mode()
            now = mode is not None
            if now and not connected:
                print(f"[+] Dispositivo detectado (modo: {mode}).")
                if notify_on:
                    notify(f"{unlooktool.DEVICE_NAME} conectado",
                           f"Modo: {mode}. Abriendo unlooktool...")
                if launch:
                    launch_gui()
            elif not now and connected:
                print("[-] Dispositivo desconectado.")
            connected = now
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[i] Vigilancia detenida.")
        return 0


def main(argv: list[str]) -> int:
    interval = 3.0
    launch = True
    notify_on = True
    once = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--interval" and i + 1 < len(argv):
            try:
                interval = float(argv[i + 1])
            except ValueError:
                print("[!] --interval requiere un numero (segundos).")
                return 1
            i += 2
            continue
        if a == "--no-launch":
            launch = False
        elif a == "--no-notify":
            notify_on = False
        elif a == "--once":
            once = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"[!] Argumento desconocido: {a}")
            print(__doc__)
            return 1
        i += 1

    if once:
        mode = device_mode()
        if mode:
            print(f"[+] Dispositivo presente (modo: {mode}).")
            if notify_on:
                notify(f"{unlooktool.DEVICE_NAME} conectado",
                       f"Modo: {mode}. Abriendo unlooktool...")
            if launch:
                launch_gui()
            return 0
        print("[-] No hay ningun dispositivo conectado.")
        return 1

    return watch(interval=interval, launch=launch, notify_on=notify_on)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
