#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unlooktool - Utilidad para Xiaomi Mi A1 (tissot) en Windows (fastboot/adb)

Pensada para dispositivos cuyo recovery/bootloader NO ofrece la opcion
"Wipe data / Factory reset". Permite hacer ese borrado y otras operaciones
de mantenimiento (flashear una ROM fastboot, ver estado, etc.) desde el PC.

NOTA sobre el Mi A1: es un ANDROID ONE (no MIUI). El bootloader se desbloquea
directo con 'fastboot flashing unlock' (comando 'unlock'), SIN Mi Unlock ni
espera de 7 dias. Solo hay que activar antes "Desbloqueo de OEM".

Automatiza:
  - Descarga e instalacion de Android platform-tools (adb/fastboot) oficiales.
  - Apertura de las paginas oficiales de drivers USB.
  - Verificacion del modelo (codename) y apertura de la fuente de ROM correcta.
  - Desbloqueo del bootloader (fastboot flashing unlock).
  - Wipe data / factory reset via fastboot.
  - Flasheo de una ROM fastboot ya descargada (ejecuta su flash_all.bat).

REQUISITOS PARA EL WIPE / FLASH:
  - El dispositivo debe ser TUYO.
  - El bootloader debe estar DESBLOQUEADO (comando 'unlock'; el Mi A1 NO usa
    Mi Unlock: se desbloquea con 'fastboot flashing unlock').
  - Las ROMs son ESPECIFICAS de cada modelo: usa siempre la de tu codename.

Uso:
  python unlooktool.py                 # menu interactivo
  python unlooktool.py setup           # descarga platform-tools + abre drivers
  python unlooktool.py drivers         # abre paginas de drivers USB
  python unlooktool.py driver          # descarga el driver USB de Google (fastboot)
  python unlooktool.py devices         # lista dispositivos
  python unlooktool.py info            # datos del dispositivo (codename, etc.)
  python unlooktool.py state           # estado del bootloader (locked/unlocked)
  python unlooktool.py unlock          # desbloquea el bootloader (Mi A1: sin Mi Unlock)
  python unlooktool.py rom             # abre la ROM correcta (tissot)
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
# Perfil del dispositivo objetivo: Xiaomi Mi A1
# --------------------------------------------------------------------------- #
# El Mi A1 es un ANDROID ONE (no MIUI): NO usa Mi Unlock ni espera de 7 dias.
# Se desbloquea directo con 'fastboot flashing unlock' tras activar
# "Desbloqueo de OEM" en Opciones de desarrollador.
DEVICE_NAME = "Xiaomi Mi A1"
DEVICE_CODENAME = "tissot"

# --------------------------------------------------------------------------- #
# Fuentes oficiales / confiables (revisadas jul-2026)
# --------------------------------------------------------------------------- #
URL_PLATFORM_TOOLS = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
URL_USB_DRIVER_MI = "https://xiaomidriver.com/"          # driver USB Xiaomi
URL_USB_DRIVER_GOOGLE = "https://developer.android.com/studio/run/win-usb"  # Google USB driver
# Driver USB de Google (incluye 'Android Bootloader Interface' para fastboot)
URL_USB_DRIVER_GOOGLE_ZIP = "https://dl.google.com/android/repository/latest_usb_driver_windows.zip"
DRIVER_DIR = os.path.join(HERE, "usb_driver")
# ROMs fastboot del Mi A1 (tissot). Son especificas del modelo (3-6 GB), no se
# descargan automatico; abrimos la pagina correcta del codename.
URL_ROM_TISSOT = "https://xiaomirom.com/en/rom/mi-a1-tissot-global-fastboot-recovery-rom/"
URL_ROM_XMFU = f"https://xmfirmwareupdater.com/?search={DEVICE_CODENAME}"


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
def _download(url: str, dest: str, timeout: int = 30) -> None:
    """Descarga con barra de progreso y timeout de red (solo stdlib)."""
    import urllib.request

    print(f"[i] Descargando: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "unlooktool"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = resp.read(64 * 1024)  # el timeout aplica a cada read()
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                sys.stdout.write(
                    f"\r    {pct:3d}%  ({done/1048576:6.1f} / {total/1048576:6.1f} MB)"
                )
            else:
                sys.stdout.write(f"\r    {done/1048576:6.1f} MB")
            sys.stdout.flush()
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
    print("[i] Descargando tambien el DRIVER USB (necesario para fastboot)...")
    download_usb_driver()

    adb, fb = _tools()
    print(f"\n    adb:      {adb or 'NO ENCONTRADO'}")
    print(f"    fastboot: {fb or 'NO ENCONTRADO'}")


def open_drivers() -> None:
    """Abre en el navegador las paginas de drivers USB."""
    for url in (URL_USB_DRIVER_MI, URL_USB_DRIVER_GOOGLE):
        print(f"    -> {url}")
        webbrowser.open(url)


def _powershell() -> str:
    exe = shutil.which("powershell") or shutil.which("powershell.exe")
    if exe:
        return exe
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def doctor() -> None:
    """Muestra dispositivos USB con problema de driver y su ID de hardware."""
    print("=" * 60)
    print(" DOCTOR - dispositivos USB sin driver (Codigo 28, etc.)")
    print("=" * 60)
    if os.name != "nt":
        print("[i] Solo Windows.")
        return
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.ConfigManagerErrorCode -ne 0 } | ForEach-Object {"
        " $hw=(Get-PnpDeviceProperty -InstanceId $_.InstanceId "
        "-KeyName 'DEVPKEY_Device_HardwareIds').Data;"
        " Write-Output ('--- ' + $_.FriendlyName);"
        " Write-Output ('    codigo : ' + $_.ConfigManagerErrorCode);"
        " Write-Output ('    hwid   : ' + ($hw -join ' | ')) }"
    )
    try:
        res = subprocess.run([_powershell(), "-NoProfile", "-NonInteractive", "-Command", ps],
                             text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[!] No se pudo consultar: {exc}")
        return
    out = (res.stdout or "").strip()
    if not out:
        print("[OK] No hay dispositivos con problema de driver (o ninguno conectado).")
        print("     Si el telefono esta en fastboot y no aparece, prueba otro cable/puerto.")
        return
    print(out)
    print()
    print("[i] Mira la linea 'hwid':")
    print("    - VID_18D1  -> ID Google (Qualcomm Mi A1 en fastboot; driver de Google)")
    print("    - VID_2717  -> ID Xiaomi (driver de Xiaomi)")
    print("    - VID_0E8D  -> ID MediaTek (NO es un Mi A1 Qualcomm real: es un equipo")
    print("                   MediaTek o un clon. Necesita driver MTK VCOM + SP Flash Tool,")
    print("                   NO fastboot. unlooktool no aplica a estos equipos.)")
    print("    - VID_05C6  -> ID Qualcomm (modo EDL 9008)")
    print("    Pega estas lineas a quien te ayuda para elegir el driver exacto.")


def download_usb_driver(force: bool = False) -> None:
    """Descarga y extrae el driver USB de Google (incluye interfaz fastboot)."""
    print("=" * 60)
    print(" DRIVER USB (Google) - incluye 'Android Bootloader Interface'")
    print("=" * 60)
    inf = os.path.join(DRIVER_DIR, "android_winusb.inf")
    if os.path.isfile(inf) and not force:
        print(f"[OK] Ya esta descargado en: {DRIVER_DIR}")
    else:
        zip_path = os.path.join(HERE, "usb_driver.zip")
        try:
            _download(URL_USB_DRIVER_GOOGLE_ZIP, zip_path)
            print("[i] Extrayendo...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(HERE)  # crea la carpeta usb_driver/
            os.remove(zip_path)
            print(f"[OK] Driver listo en: {DRIVER_DIR}")
        except Exception as exc:  # noqa: BLE001
            print(f"[!] Fallo la descarga: {exc}")
            print(f"    Descarga manual: {URL_USB_DRIVER_GOOGLE}")
            return

    print()
    print("[i] AHORA instala el driver a mano (con el telefono en modo fastboot):")
    print("    1) Pulsa Windows, abre 'Administrador de dispositivos'.")
    print("    2) Busca el dispositivo con triangulo amarillo (Codigo 28 / 'Android').")
    print("    3) Clic derecho -> Actualizar controlador.")
    print("    4) 'Buscar controladores en mi equipo'.")
    print(f"    5) Escribe o pega esta carpeta:  {DRIVER_DIR}")
    print("       marca 'Incluir subcarpetas' y pulsa Siguiente.")
    print("    6) Acepta si Windows avisa que no esta firmado -> Instalar.")
    print("    7) Deberia aparecer 'Android Bootloader Interface'. Listo.")
    print("\n[i] Luego vuelve al menu y prueba la opcion 4 (estado del bootloader).")


# --------------------------------------------------------------------------- #
# Info del dispositivo / ROMs
# --------------------------------------------------------------------------- #
def _fastboot_ready() -> bool:
    """True si hay un dispositivo en modo fastboot (evita que getvar se cuelgue)."""
    fb = _find_tool("fastboot")
    if not fb:
        return False
    try:
        res = subprocess.run([fb, "devices"], text=True, capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        return False
    return bool(res.stdout.strip())


def _getvar(var: str) -> str:
    """Lee una variable de fastboot getvar (fastboot escribe a stderr)."""
    fb = _require(_find_tool("fastboot"), "fastboot")
    # getvar espera indefinidamente si no hay device: comprobamos antes.
    if not _fastboot_ready():
        return ""
    try:
        res = subprocess.run([fb, "getvar", var], text=True, capture_output=True, timeout=15)
    except subprocess.TimeoutExpired:
        return ""
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
    """Abre la fuente de ROM fastboot correcta para el Mi A1 (tissot)."""
    codename = _getvar("product")
    print()
    if codename and codename.lower() != DEVICE_CODENAME:
        print(f"[!] OJO: el dispositivo conectado reporta codename '{codename}',")
        print(f"    pero esta herramienta esta configurada para {DEVICE_NAME} ('{DEVICE_CODENAME}').")
        print(f"    Descarga la ROM de '{codename}', NO la de tissot, o brickeas el equipo.")
        url = f"https://xmfirmwareupdater.com/?search={codename}"
    else:
        print(f"[i] {DEVICE_NAME} (codename: {DEVICE_CODENAME})")
        url = URL_ROM_TISSOT
    print(f"    -> {url}")
    print(f"    -> {URL_ROM_XMFU}")
    webbrowser.open(url)
    webbrowser.open(URL_ROM_XMFU)
    print("\n[i] Descarga la ROM *fastboot* (trae flash_all.bat) y extraela. Luego:")
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
        print(f"    El {DEVICE_NAME} es Android One: NO usa Mi Unlock.")
        print("    1) En el telefono: Ajustes > Sistema > Opciones de desarrollador")
        print("       > activa 'Desbloqueo de OEM'.")
        print("    2) Entra a fastboot y ejecuta:  python unlooktool.py unlock")
    else:
        print("[?] No se pudo determinar el estado. ¿El device esta en modo fastboot?")


def unlock_bootloader(assume_yes: bool = False) -> None:
    """Desbloquea el bootloader del Mi A1 via 'fastboot flashing unlock'."""
    fb = _require(_find_tool("fastboot"), "fastboot")
    print("=" * 60)
    print(f" DESBLOQUEAR BOOTLOADER - {DEVICE_NAME} ({DEVICE_CODENAME})")
    print("=" * 60)
    print("El Mi A1 es Android One: se desbloquea directo, sin Mi Unlock ni")
    print("espera de 7 dias. REQUISITOS:")
    print("  - Activar 'Desbloqueo de OEM' en Opciones de desarrollador.")
    print("  - Esto BORRA TODOS los datos del telefono (es irreversible).\n")

    if not run([fb, "devices"]).stdout.strip():
        print("[!] No hay ningun dispositivo en modo fastboot.")
        print("    Ejecuta primero:  python unlooktool.py reboot bootloader")
        return

    if not assume_yes and not _confirm(">> Confirmar desbloqueo (BORRA el telefono)"):
        print("Cancelado.")
        return

    print("\n[i] Enviando comando de desbloqueo...")
    print("    MIRA LA PANTALLA DEL TELEFONO: usa Volumen +/- para elegir")
    print("    'Unlock the bootloader' y confirma con Power.\n")
    try:
        run([fb, "flashing", "unlock"], check=True, capture=False)
    except subprocess.CalledProcessError:
        print("[i] Probando comando alternativo (oem unlock)...")
        run([fb, "oem", "unlock"], capture=False)
    print("\n[OK] Si confirmaste en el telefono, el bootloader quedara desbloqueado.")
    print("    Verifica con:  python unlooktool.py state")


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
        run([fb, "-w"], check=True, capture=False)
    except subprocess.CalledProcessError:
        print("[i] Intentando metodo alternativo (erase)...")
        run([fb, "erase", "userdata"], capture=False)
        run([fb, "erase", "cache"], capture=False)

    print("\n[2/3] Wipe completado.")
    print("[3/3] Reiniciando...")
    run([fb, "reboot"], capture=False)
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
    subprocess.run([script], cwd=os.path.dirname(script), env=env)
    print("\n[OK] Proceso de flasheo finalizado (revisa la salida arriba).")


def _no_fastboot_device() -> bool:
    """Avisa si no hay dispositivo en fastboot (fastboot reboot se colgaria)."""
    if _fastboot_ready():
        return False
    print("[!] No hay ningun dispositivo en modo fastboot.")
    print("    Conecta el telefono en modo fastboot y reintenta")
    print("    (o si el sistema arranca, activa Depuracion USB).")
    return True


def reboot(target: str = "system") -> None:
    adb, fb = _tools()
    target = (target or "system").lower()
    adb_online = bool(adb) and "\tdevice" in run([adb, "devices"]).stdout if adb else False

    if target in ("system", "reboot", ""):
        if adb_online:
            run([adb, "reboot"], capture=False)
        elif _no_fastboot_device():
            return
        else:
            run([_require(fb, "fastboot"), "reboot"], capture=False)
    elif target in ("bootloader", "fastboot"):
        if adb_online:
            run([adb, "reboot", "bootloader"], capture=False)
        elif _no_fastboot_device():
            return
        else:  # ya esta en fastboot: reinicia de nuevo a bootloader
            run([_require(fb, "fastboot"), "reboot", "bootloader"], capture=False)
    elif target == "recovery":
        if not adb_online:
            print("[!] 'recovery' requiere el telefono encendido con Depuracion USB (adb).")
            return
        run([adb, "reboot", "recovery"], capture=False)
    else:
        print(f"[!] Objetivo desconocido: {target}  (reboot | bootloader | recovery)")


# --------------------------------------------------------------------------- #
# Menu interactivo
# --------------------------------------------------------------------------- #
MENU = """
============================================================
  {app}  -  {device} ({codename}) - Windows
============================================================
  1) Setup: descargar platform-tools + drivers
  2) Listar dispositivos (adb / fastboot)
  3) Ver info del dispositivo (codename, etc.)
  4) Ver estado del bootloader
  5) Desbloquear bootloader (fastboot flashing unlock)
  6) Descargar ROM correcta (tissot)
  7) Reiniciar a modo fastboot (bootloader)
  8) Wipe data / Factory reset
  9) Flashear ROM fastboot (carpeta extraida)
 10) Reiniciar a recovery
 11) Reiniciar el sistema
  0) Salir
------------------------------------------------------------
  adb:      {adb}
  fastboot: {fb}
============================================================
"""


def menu() -> None:
    while True:
        adb, fb = _tools()
        print(MENU.format(app=APP, device=DEVICE_NAME, codename=DEVICE_CODENAME,
                          adb=adb or "NO ENCONTRADO", fb=fb or "NO ENCONTRADO"))
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
                unlock_bootloader()
            elif choice == "6":
                open_rom()
            elif choice == "7":
                reboot("bootloader")
                print("[i] Espera unos segundos a que entre en modo fastboot.")
                time.sleep(2)
            elif choice == "8":
                wipe_data()
            elif choice == "9":
                folder = input("Ruta de la carpeta de la ROM extraida: ").strip().strip('"')
                flash_rom(folder)
            elif choice == "10":
                reboot("recovery")
            elif choice == "11":
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
    elif cmd == "driver":
        download_usb_driver(force="--force" in args)
    elif cmd == "doctor":
        doctor()
    elif cmd == "devices":
        list_devices()
    elif cmd == "info":
        device_info()
    elif cmd == "state":
        bootloader_state()
    elif cmd == "unlock":
        unlock_bootloader(assume_yes=yes)
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
