#!/usr/bin/env python3
"""
unlooktool - Utilidad para Xiaomi (fastboot/adb)

Pensada para dispositivos cuyo recovery/bootloader NO ofrece la opcion
"Wipe data / Factory reset". Permite hacer ese borrado (y otras operaciones
de mantenimiento) desde el PC via fastboot/adb.

REQUISITOS:
  - El dispositivo debe ser tuyo.
  - El bootloader debe estar DESBLOQUEADO (fastboot no permite formatear
    userdata con bootloader bloqueado).
  - Tener 'adb' y 'fastboot' (Android platform-tools) en el PATH o en una
    carpeta 'platform-tools' junto a este script.

Uso:
  python unlooktool.py                 # menu interactivo
  python unlooktool.py devices         # lista dispositivos
  python unlooktool.py state           # estado del bootloader (locked/unlocked)
  python unlooktool.py wipe            # wipe data/factory reset (pide confirmacion)
  python unlooktool.py reboot [target] # reboot | bootloader | recovery | fastboot
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

APP = "unlooktool"
HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- #
# Localizacion de herramientas (adb / fastboot)
# --------------------------------------------------------------------------- #
def _find_tool(name: str) -> str | None:
    """Busca la herramienta en el PATH y en ./platform-tools."""
    exe = name + (".exe" if os.name == "nt" else "")
    found = shutil.which(name) or shutil.which(exe)
    if found:
        return found
    local = os.path.join(HERE, "platform-tools", exe)
    if os.path.isfile(local):
        return local
    return None


ADB = _find_tool("adb")
FASTBOOT = _find_tool("fastboot")


def _require(tool: str | None, name: str) -> str:
    if not tool:
        print(f"[!] No se encontro '{name}'.")
        print("    Instala Android platform-tools y agregalos al PATH, o copia")
        print("    la carpeta 'platform-tools' junto a este script.")
        print("    Descarga: https://developer.android.com/tools/releases/platform-tools")
        sys.exit(2)
    return tool


# --------------------------------------------------------------------------- #
# Ejecucion de comandos
# --------------------------------------------------------------------------- #
def run(cmd: list[str], check: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando y (por defecto) captura la salida."""
    printable = " ".join(cmd)
    print(f"    $ {printable}")
    try:
        return subprocess.run(
            cmd,
            check=check,
            text=True,
            capture_output=capture,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[!] El comando fallo (codigo {exc.returncode}).")
        if exc.stderr:
            print(exc.stderr.strip())
        raise


# --------------------------------------------------------------------------- #
# Operaciones
# --------------------------------------------------------------------------- #
def list_devices() -> None:
    """Muestra dispositivos en modo adb y en modo fastboot."""
    if ADB:
        print("[adb] dispositivos:")
        res = run([ADB, "devices"])
        print(res.stdout.strip() or "(sin salida)")
    else:
        print("[adb] no disponible.")
    print()
    if FASTBOOT:
        print("[fastboot] dispositivos:")
        res = run([FASTBOOT, "devices"])
        out = res.stdout.strip()
        print(out if out else "(ninguno en modo fastboot)")
    else:
        print("[fastboot] no disponible.")


def bootloader_state() -> None:
    """Consulta si el bootloader esta desbloqueado."""
    fb = _require(FASTBOOT, "fastboot")
    print("[i] Consultando estado del bootloader (el dispositivo debe estar en modo fastboot)...")
    res = run([fb, "getvar", "unlocked"])
    # fastboot escribe getvar a stderr
    output = (res.stderr or "") + (res.stdout or "")
    line = next((l for l in output.splitlines() if "unlocked" in l.lower()), "")
    if "yes" in line.lower():
        print("[OK] Bootloader DESBLOQUEADO. Se puede formatear userdata.")
    elif "no" in line.lower():
        print("[X] Bootloader BLOQUEADO. fastboot no permitira borrar userdata.")
        print("    Desbloquea primero con Mi Unlock (proceso oficial de Xiaomi).")
    else:
        print("[?] No se pudo determinar el estado. Salida cruda:")
        print(output.strip() or "(vacia)")


def _confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [escribe BORRAR para confirmar]: ").strip()
    except EOFError:
        return False
    return ans == "BORRAR"


def wipe_data(assume_yes: bool = False) -> None:
    """Wipe data / factory reset via fastboot."""
    fb = _require(FASTBOOT, "fastboot")
    print("=" * 60)
    print(" WIPE DATA / FACTORY RESET")
    print("=" * 60)
    print("Esto BORRA TODOS los datos de usuario del dispositivo.")
    print("El dispositivo debe estar en modo fastboot y con bootloader")
    print("desbloqueado. La operacion es IRREVERSIBLE.")
    print()

    res = run([fb, "devices"])
    if not res.stdout.strip():
        print("[!] No hay ningun dispositivo en modo fastboot.")
        print("    Ejecuta primero:  python unlooktool.py reboot bootloader")
        return

    if not assume_yes and not _confirm(">> Confirmar borrado total"):
        print("Cancelado.")
        return

    print("\n[1/3] Formateando userdata...")
    try:
        run([fb, "-w"], check=True)
    except subprocess.CalledProcessError:
        # Fallback por si -w no aplica en el device
        print("[i] Intentando metodo alternativo (erase)...")
        run([fb, "erase", "userdata"])
        run([fb, "erase", "cache"])

    print("\n[2/3] Wipe completado.")
    print("\n[3/3] Reiniciando el dispositivo...")
    run([fb, "reboot"])
    print("[OK] Listo.")


def reboot(target: str = "system") -> None:
    """Reinicia el dispositivo a distintos modos."""
    target = (target or "system").lower()
    if target in ("system", "reboot", ""):
        # adb primero; si no hay adb, fastboot reboot
        if ADB:
            run([ADB, "reboot"])
        else:
            run([_require(FASTBOOT, "fastboot"), "reboot"])
        return
    if target in ("bootloader", "fastboot"):
        if ADB and run([ADB, "devices"]).stdout.strip().count("\tdevice"):
            run([ADB, "reboot", "bootloader"])
        else:
            run([_require(FASTBOOT, "fastboot"), "reboot", "bootloader"])
        return
    if target == "recovery":
        run([_require(ADB, "adb"), "reboot", "recovery"])
        return
    print(f"[!] Objetivo desconocido: {target}")
    print("    Usa: reboot | bootloader | recovery | fastboot")


# --------------------------------------------------------------------------- #
# Menu interactivo
# --------------------------------------------------------------------------- #
MENU = """
============================================================
  {app}  -  utilidad Xiaomi (fastboot/adb)
============================================================
  1) Listar dispositivos (adb / fastboot)
  2) Ver estado del bootloader
  3) Reiniciar a modo fastboot (bootloader)
  4) Wipe data / Factory reset
  5) Reiniciar a recovery
  6) Reiniciar el sistema
  0) Salir
------------------------------------------------------------
  adb:      {adb}
  fastboot: {fb}
============================================================
"""


def menu() -> None:
    while True:
        print(MENU.format(
            app=APP,
            adb=ADB or "NO ENCONTRADO",
            fb=FASTBOOT or "NO ENCONTRADO",
        ))
        try:
            choice = input("Opcion> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            return
        print()
        if choice == "1":
            list_devices()
        elif choice == "2":
            bootloader_state()
        elif choice == "3":
            reboot("bootloader")
            print("[i] Espera unos segundos a que entre en modo fastboot.")
            time.sleep(2)
        elif choice == "4":
            wipe_data()
        elif choice == "5":
            reboot("recovery")
        elif choice == "6":
            reboot("system")
        elif choice == "0":
            print("Adios.")
            return
        else:
            print("Opcion no valida.")
        input("\n[Enter para continuar]")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    if not argv:
        menu()
        return 0

    cmd = argv[0].lower()
    args = argv[1:]

    if cmd in ("-h", "--help", "help"):
        print(__doc__)
    elif cmd == "devices":
        list_devices()
    elif cmd == "state":
        bootloader_state()
    elif cmd == "wipe":
        wipe_data(assume_yes="--yes" in args or "-y" in args)
    elif cmd == "reboot":
        reboot(args[0] if args else "system")
    else:
        print(f"[!] Comando desconocido: {cmd}")
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        raise SystemExit(130)
