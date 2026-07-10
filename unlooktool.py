#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unlooktool - Utilidad para Xiaomi en Windows (fastboot/adb)

Pensada para dispositivos cuyo recovery/bootloader NO ofrece la opcion
"Wipe data / Factory reset". Permite hacer ese borrado y otras operaciones
de mantenimiento (flashear una ROM fastboot, ver estado, etc.) desde el PC.

Automatiza:
  - Descarga e instalacion de Android platform-tools (adb/fastboot) oficiales.
  - Apertura de las paginas oficiales de drivers USB y Mi Unlock.
  - Autodeteccion del modelo (codename) y apertura de la fuente de ROM correcta.
  - Wipe data / factory reset via fastboot.
  - Flasheo de una ROM fastboot ya descargada (ejecuta su flash_all.bat).

REQUISITOS PARA EL WIPE / FLASH:
  - El dispositivo debe ser TUYO.
  - El bootloader debe estar DESBLOQUEADO (proceso oficial Mi Unlock).
  - Las ROMs son ESPECIFICAS de cada modelo: usa siempre la de tu codename.

Uso:
  python unlooktool.py                 # menu interactivo
  python unlooktool.py setup           # descarga platform-tools + abre drivers/MiUnlock
  python unlooktool.py drivers         # abre paginas de drivers USB
  python unlooktool.py devices         # lista dispositivos
  python unlooktool.py info            # datos del dispositivo (codename, etc.)
  python unlooktool.py state           # estado del bootloader (locked/unlocked)
  python unlooktool.py rom             # detecta codename y abre la ROM correcta
  python unlooktool.py wipe            # wipe data/factory reset (pide confirmacion)
  python unlooktool.py flash <carpeta> # flashea una ROM fastboot extraida
  python unlooktool.py reboot [target] # reboot | bootloader | recovery | fastboot
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
import zipfile

APP = "unlooktool"
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(HERE, "platform-tools")

# --------------------------------------------------------------------------- #
# Fuentes oficiales / confiables (revisadas jul-2026)
# --------------------------------------------------------------------------- #
URL_PLATFORM_TOOLS = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
URL_MI_UNLOCK = "https://en.miui.com/unlock/"            # Mi Unlock oficial (Xiaomi)
URL_USB_DRIVER_MI = "https://xiaomidriver.com/"          # driver USB Xiaomi
URL_USB_DRIVER_GOOGLE = "https://developer.android.com/studio/run/win-usb"  # Google USB driver
# ROMs: fuentes que permiten buscar por codename (NO descargamos automatico:
# son 3-6 GB y especificas del modelo; abrimos la pagina correcta).
URL_ROM_XMFU = "https://xmfirmwareupdater.com/"          # buscar por codename
URL_ROM_XIAOMIROM = "https://xiaomirom.com/en/"          # fastboot/recovery por region


# --------------------------------------------------------------------------- #
# Localizacion de herramientas (adb / fastboot)
# --------------------------------------------------------------------------- #
def _find_tool(name: str) -> str | None:
    """Busca la herramienta en ./platform-tools primero y luego en el PATH."""
    exe = name + (".exe" if os.name == "nt" else "")
    local = os.path.join(TOOLS_DIR, exe)
    if os.path.isfile(local):
        return local
    return shutil.which(name) or shutil.which(exe)


def _tools() -> tuple[str | None, str | None]:
    return _find_tool("adb"), _find_tool("fastboot")


def _require(tool: str | None, name: str) -> str:
    if not tool:
        print(f"[!] No se encontro '{name}'.")
        print("    Ejecuta primero:  python unlooktool.py setup")
        sys.exit(2)
    return tool


# --------------------------------------------------------------------------- #
# Ejecucion de comandos
# --------------------------------------------------------------------------- #
def run(cmd: list[str], check: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    print(f"    $ {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, check=check, text=True, capture_output=capture)
    except subprocess.CalledProcessError as exc:
        print(f"[!] El comando fallo (codigo {exc.returncode}).")
        if capture and exc.stderr:
            print(exc.stderr.strip())
        raise


# --------------------------------------------------------------------------- #
# setup: descarga de platform-tools + drivers
# --------------------------------------------------------------------------- #
def _download(url: str, dest: str) -> None:
    """Descarga con barra de progreso simple (solo stdlib)."""
    import urllib.request

    print(f"[i] Descargando: {url}")

    def _hook(block_num, block_size, total_size):
        if total_size > 0:
            done = min(block_num * block_size, total_size)
            pct = done * 100 // total_size
            mb = done / (1024 * 1024)
            tot = total_size / (1024 * 1024)
            sys.stdout.write(f"\r    {pct:3d}%  ({mb:6.1f} / {tot:6.1f} MB)")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, _hook)
    print()


def setup_tools(force: bool = False) -> None:
    """Descarga y extrae Android platform-tools oficiales de Google."""
    print("=" * 60)
    print(" SETUP - Android platform-tools (adb / fastboot)")
    print("=" * 60)

    if os.path.isfile(os.path.join(TOOLS_DIR, "fastboot.exe")) and not force:
        print(f"[OK] Ya existe platform-tools en: {TOOLS_DIR}")
    else:
        zip_path = os.path.join(HERE, "platform-tools.zip")
        try:
            _download(URL_PLATFORM_TOOLS, zip_path)
            print("[i] Extrayendo...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(HERE)  # el zip ya contiene la carpeta platform-tools/
            os.remove(zip_path)
            print(f"[OK] Instalado en: {TOOLS_DIR}")
        except Exception as exc:  # noqa: BLE001
            print(f"[!] Fallo la descarga automatica: {exc}")
            print(f"    Descarga manual: {URL_PLATFORM_TOOLS}")
            print(f"    y extrae la carpeta 'platform-tools' junto a este script.")
            return

    print()
    print("[i] Ahora necesitas los DRIVERS USB de Xiaomi.")
    print(f"    - Driver Xiaomi:  {URL_USB_DRIVER_MI}")
    print(f"    - Mi Unlock:      {URL_MI_UNLOCK}")
    try:
        ans = input("\n¿Abrir las paginas de drivers y Mi Unlock en el navegador? [s/N]: ").strip().lower()
    except EOFError:
        ans = "n"
    if ans in ("s", "si", "y", "yes"):
        open_drivers()

    adb, fb = _tools()
    print(f"\n    adb:      {adb or 'NO ENCONTRADO'}")
    print(f"    fastboot: {fb or 'NO ENCONTRADO'}")


def open_drivers() -> None:
    """Abre en el navegador las paginas de drivers y Mi Unlock."""
    for url in (URL_USB_DRIVER_MI, URL_USB_DRIVER_GOOGLE, URL_MI_UNLOCK):
        print(f"    -> {url}")
        webbrowser.open(url)


# --------------------------------------------------------------------------- #
# Info del dispositivo / ROMs
# --------------------------------------------------------------------------- #
def _getvar(var: str) -> str:
    """Lee una variable de fastboot getvar (fastboot escribe a stderr)."""
    fb = _require(_find_tool("fastboot"), "fastboot")
    res = run([fb, "getvar", var])
    output = (res.stderr or "") + (res.stdout or "")
    for line in output.splitlines():
        if line.lower().startswith(var.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def device_info() -> dict[str, str]:
    """Datos del dispositivo (requiere modo fastboot)."""
    print("[i] Leyendo datos del dispositivo (modo fastboot)...")
    info = {
        "product (codename)": _getvar("product"),
        "unlocked": _getvar("unlocked"),
        "secure": _getvar("secure"),
        "version-bootloader": _getvar("version-bootloader"),
        "battery-voltage": _getvar("battery-voltage"),
    }
    print()
    for k, v in info.items():
        print(f"    {k:22s}: {v or '(desconocido)'}")
    return info


def open_rom() -> None:
    """Autodetecta el codename y abre la fuente de ROM correcta."""
    codename = _getvar("product")
    print()
    if codename:
        print(f"[i] Codename detectado: {codename}")
        url = f"{URL_ROM_XMFU}?search={codename}"
    else:
        print("[!] No se pudo detectar el codename (¿esta en modo fastboot?).")
        print("    Abriendo el buscador general de ROMs.")
        url = URL_ROM_XMFU
    print(f"    -> {url}")
    print(f"    -> {URL_ROM_XIAOMIROM}")
    webbrowser.open(url)
    webbrowser.open(URL_ROM_XIAOMIROM)
    print("\n[i] Descarga la ROM *fastboot* de TU modelo y extraela. Luego:")
    print("    python unlooktool.py flash <carpeta_de_la_rom>")


# --------------------------------------------------------------------------- #
# Operaciones fastboot/adb
# --------------------------------------------------------------------------- #
def list_devices() -> None:
    adb, fb = _tools()
    if adb:
        print("[adb] dispositivos:")
        print(run([adb, "devices"]).stdout.strip() or "(sin salida)")
    else:
        print("[adb] no disponible. Ejecuta:  python unlooktool.py setup")
    print()
    if fb:
        print("[fastboot] dispositivos:")
        out = run([fb, "devices"]).stdout.strip()
        print(out if out else "(ninguno en modo fastboot)")
    else:
        print("[fastboot] no disponible. Ejecuta:  python unlooktool.py setup")


def bootloader_state() -> None:
    print("[i] Consultando estado del bootloader (modo fastboot)...")
    val = _getvar("unlocked")
    if val.lower() == "yes":
        print("[OK] Bootloader DESBLOQUEADO. Se puede formatear userdata / flashear.")
    elif val.lower() == "no":
        print("[X] Bootloader BLOQUEADO. fastboot no permitira borrar/flashear.")
        print(f"    Desbloquea con Mi Unlock oficial: {URL_MI_UNLOCK}")
    else:
        print("[?] No se pudo determinar el estado. ¿El device esta en modo fastboot?")


def _confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [escribe BORRAR para confirmar]: ").strip() == "BORRAR"
    except EOFError:
        return False


def wipe_data(assume_yes: bool = False) -> None:
    fb = _require(_find_tool("fastboot"), "fastboot")
    print("=" * 60)
    print(" WIPE DATA / FACTORY RESET")
    print("=" * 60)
    print("Esto BORRA TODOS los datos de usuario. Requiere modo fastboot y")
    print("bootloader desbloqueado. La operacion es IRREVERSIBLE.\n")

    if not run([fb, "devices"]).stdout.strip():
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
        print("[i] Intentando metodo alternativo (erase)...")
        run([fb, "erase", "userdata"])
        run([fb, "erase", "cache"])

    print("\n[2/3] Wipe completado.")
    print("[3/3] Reiniciando...")
    run([fb, "reboot"])
    print("[OK] Listo.")


def flash_rom(folder: str, assume_yes: bool = False) -> None:
    """Flashea una ROM fastboot ya descargada y extraida (usa su flash_all.bat)."""
    print("=" * 60)
    print(" FLASH ROM FASTBOOT")
    print("=" * 60)
    if not folder or not os.path.isdir(folder):
        print(f"[!] Carpeta no valida: {folder}")
        print("    Descarga la ROM fastboot de tu modelo, extraela e indica la carpeta.")
        return

    # Las ROMs fastboot de Xiaomi traen scripts en /images o en la raiz.
    candidates = [
        os.path.join(folder, "flash_all.bat"),
        os.path.join(folder, "images", "flash_all.bat"),
    ]
    script = next((c for c in candidates if os.path.isfile(c)), None)
    if not script:
        # buscar recursivo por si la estructura varia
        for root, _dirs, files in os.walk(folder):
            if "flash_all.bat" in files:
                script = os.path.join(root, "flash_all.bat")
                break
    if not script:
        print("[!] No encontre 'flash_all.bat' dentro de la carpeta.")
        print("    Asegurate de haber descargado una ROM *fastboot* (no recovery/OTA).")
        return

    print(f"[i] Script de flasheo: {script}")
    print("    Esto reescribe el firmware del telefono. NO desconectes el cable.")
    print("    El bootloader debe estar desbloqueado y el device en modo fastboot.\n")
    if not assume_yes and not _confirm(">> Confirmar flasheo (BORRA el telefono)"):
        print("Cancelado.")
        return

    # flash_all.bat usa el fastboot que este en el PATH; anteponemos el nuestro.
    env = os.environ.copy()
    env["PATH"] = TOOLS_DIR + os.pathsep + env.get("PATH", "")
    print("[i] Ejecutando flash_all.bat...\n")
    subprocess.run([script], cwd=os.path.dirname(script), env=env, shell=True)
    print("\n[OK] Proceso de flasheo finalizado (revisa la salida arriba).")


def reboot(target: str = "system") -> None:
    adb, fb = _tools()
    target = (target or "system").lower()
    if target in ("system", "reboot", ""):
        if adb:
            run([adb, "reboot"])
        else:
            run([_require(fb, "fastboot"), "reboot"])
    elif target in ("bootloader", "fastboot"):
        if adb and "\tdevice" in run([adb, "devices"]).stdout:
            run([adb, "reboot", "bootloader"])
        else:
            run([_require(fb, "fastboot"), "reboot", "bootloader"])
    elif target == "recovery":
        run([_require(adb, "adb"), "reboot", "recovery"])
    else:
        print(f"[!] Objetivo desconocido: {target}  (reboot | bootloader | recovery)")


# --------------------------------------------------------------------------- #
# Menu interactivo
# --------------------------------------------------------------------------- #
MENU = """
============================================================
  {app}  -  utilidad Xiaomi para Windows (fastboot/adb)
============================================================
  1) Setup: descargar platform-tools + drivers
  2) Listar dispositivos (adb / fastboot)
  3) Ver info del dispositivo (codename, etc.)
  4) Ver estado del bootloader
  5) Descargar ROM correcta (autodetecta modelo)
  6) Reiniciar a modo fastboot (bootloader)
  7) Wipe data / Factory reset
  8) Flashear ROM fastboot (carpeta extraida)
  9) Reiniciar a recovery
 10) Reiniciar el sistema
  0) Salir
------------------------------------------------------------
  adb:      {adb}
  fastboot: {fb}
============================================================
"""


def menu() -> None:
    while True:
        adb, fb = _tools()
        print(MENU.format(app=APP, adb=adb or "NO ENCONTRADO", fb=fb or "NO ENCONTRADO"))
        try:
            choice = input("Opcion> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            return
        print()
        try:
            if choice == "1":
                setup_tools()
            elif choice == "2":
                list_devices()
            elif choice == "3":
                device_info()
            elif choice == "4":
                bootloader_state()
            elif choice == "5":
                open_rom()
            elif choice == "6":
                reboot("bootloader")
                print("[i] Espera unos segundos a que entre en modo fastboot.")
                time.sleep(2)
            elif choice == "7":
                wipe_data()
            elif choice == "8":
                folder = input("Ruta de la carpeta de la ROM extraida: ").strip().strip('"')
                flash_rom(folder)
            elif choice == "9":
                reboot("recovery")
            elif choice == "10":
                reboot("system")
            elif choice == "0":
                print("Adios.")
                return
            else:
                print("Opcion no valida.")
        except SystemExit:
            pass  # _require aborta comandos individuales sin cerrar el menu
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
    yes = "--yes" in args or "-y" in args

    if cmd in ("-h", "--help", "help"):
        print(__doc__)
    elif cmd == "setup":
        setup_tools(force="--force" in args)
    elif cmd == "drivers":
        open_drivers()
    elif cmd == "devices":
        list_devices()
    elif cmd == "info":
        device_info()
    elif cmd == "state":
        bootloader_state()
    elif cmd == "rom":
        open_rom()
    elif cmd == "wipe":
        wipe_data(assume_yes=yes)
    elif cmd == "flash":
        pos = [a for a in args if not a.startswith("-")]
        flash_rom(pos[0] if pos else "", assume_yes=yes)
    elif cmd == "reboot":
        pos = [a for a in args if not a.startswith("-")]
        reboot(pos[0] if pos else "system")
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
