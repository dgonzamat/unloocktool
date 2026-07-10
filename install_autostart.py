#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_autostart - Hace que unlooktool_watch arranque con Windows.

Crea un lanzador en la carpeta de Inicio (Startup) del usuario actual, de modo
que al iniciar sesion en Windows se ejecute el vigilante en segundo plano y la
GUI se abra sola cuando conectes el telefono. No requiere permisos de admin.

Uso:
  python install_autostart.py install     # activa el arranque automatico
  python install_autostart.py uninstall   # lo quita
  python install_autostart.py status      # muestra si esta instalado
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WATCH = os.path.join(HERE, "unlooktool_watch.py")
LAUNCHER_NAME = "unlooktool-watch.bat"


def _startup_dir() -> str:
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def _launcher_path() -> str:
    return os.path.join(_startup_dir(), LAUNCHER_NAME)


def _pythonw() -> str:
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return pyw if os.path.isfile(pyw) else sys.executable


def install() -> int:
    if os.name != "nt":
        print("[!] El arranque automatico por carpeta Startup es solo para Windows.")
        return 2
    startup = _startup_dir()
    if not os.path.isdir(startup):
        print(f"[!] No encontre la carpeta de Inicio: {startup}")
        return 2
    if not os.path.isfile(WATCH):
        print(f"[!] No encuentro {WATCH}")
        return 2

    content = (
        "@echo off\r\n"
        "REM Arranque automatico de unlooktool_watch (generado por install_autostart.py)\r\n"
        f'cd /d "{HERE}"\r\n'
        f'start "" "{_pythonw()}" "{WATCH}"\r\n'
    )
    path = _launcher_path()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("[OK] Arranque automatico INSTALADO.")
    print(f"    Lanzador: {path}")
    print("    Se ejecutara al iniciar sesion en Windows.")
    print("    Para probarlo ahora sin reiniciar:")
    print(f'        python "{WATCH}"')
    return 0


def uninstall() -> int:
    path = _launcher_path()
    if os.path.isfile(path):
        os.remove(path)
        print(f"[OK] Arranque automatico DESINSTALADO ({path}).")
    else:
        print("[i] No estaba instalado (no hay lanzador que quitar).")
    return 0


def status() -> int:
    path = _launcher_path()
    if os.path.isfile(path):
        print(f"[OK] Instalado: {path}")
    else:
        print("[-] No instalado.")
    print(f"    Vigilante: {WATCH}")
    print(f"    Python:    {_pythonw()}")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0].lower() if argv else "status"
    if cmd == "install":
        return install()
    if cmd == "uninstall":
        return uninstall()
    if cmd in ("status", "-h", "--help", "help"):
        if cmd in ("-h", "--help", "help"):
            print(__doc__)
            return 0
        return status()
    print(f"[!] Comando desconocido: {cmd}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
