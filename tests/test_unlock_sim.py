#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de simulacion del desbloqueo de bootloader (sin hardware real).

Reemplaza 'fastboot' por un mock que se comporta como un dispositivo Mi A1
conectado en modo fastboot, y ejecuta el flujo REAL de unlooktool.unlock_bootloader
para verificar:
  1) Desbloqueo normal: emite 'fastboot flashing unlock' y el device queda unlocked.
  2) Fallback: si 'flashing unlock' falla, prueba 'oem unlock'.
  3) Sin dispositivo: no emite ningun comando de desbloqueo y avisa.

Ejecutar:  python tests/test_unlock_sim.py
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from contextlib import redirect_stdout

# Permitir importar unlooktool.py (carpeta padre)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unlooktool  # noqa: E402


class FakeDevice:
    """Simula un Mi A1 en modo fastboot respondiendo a los comandos emitidos."""

    def __init__(self, present: bool = True, fail_flashing_unlock: bool = False,
                 fail_wipe: bool = False):
        self.state = {"unlocked": "no", "product": "tissot", "secure": "yes"}
        self.present = present
        self.fail_flashing_unlock = fail_flashing_unlock
        self.fail_wipe = fail_wipe
        self.wiped = False
        self.issued: list[str] = []

    def run(self, cmd, check=False, text=True, capture_output=False, timeout=None, **kw):
        args = list(cmd[1:])  # descarta la ruta del binario 'fastboot'
        self.issued.append(" ".join(args))
        out, err, rc = "", "", 0

        if args == ["devices"]:
            out = "SIM0A1TISSOT\tfastboot\n" if self.present else ""
        elif args[:1] == ["getvar"]:
            var = args[1]
            err = f"{var}: {self.state.get(var, '')}\nfinished. total time: 0.001s\n"
        elif args[:2] == ["flashing", "unlock"]:
            if self.fail_flashing_unlock:
                rc, err = 1, "FAILED (remote: 'unknown command')\n"
            else:
                self.state["unlocked"] = "yes"
                out = "OKAY [  0.030s]\nfinished. total time: 0.031s\n"
        elif args[:2] == ["oem", "unlock"]:
            self.state["unlocked"] = "yes"
            out = "...\nOKAY [  0.025s]\nfinished.\n"
        elif args == ["-w"]:
            if self.fail_wipe:
                rc, err = 1, "FAILED (remote: 'not supported')\n"
            else:
                self.wiped = True
                out = "Erasing 'userdata' OKAY\nErasing 'cache' OKAY\n"
        elif args[:1] == ["erase"]:
            self.wiped = True
            out = f"Erasing '{args[1]}' OKAY [  0.010s]\nfinished.\n"
        elif args[:1] == ["reboot"]:
            out = "rebooting...\nfinished.\n"

        cp = subprocess.CompletedProcess(cmd, rc, out, err)
        if check and rc != 0:
            raise subprocess.CalledProcessError(rc, cmd, out, err)
        return cp


def _install(dev: FakeDevice):
    """Parchea unlooktool para usar el fastboot simulado."""
    unlooktool._find_tool = lambda name: "FASTBOOT" if name == "fastboot" else None
    unlooktool.subprocess.run = dev.run


def _run_capturing(fn) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


PASS, FAIL = "[PASS]", "[FAIL]"
_errors = 0


def check(cond: bool, msg: str) -> None:
    global _errors
    print(f"  {PASS if cond else FAIL} {msg}")
    if not cond:
        _errors += 1


# --------------------------------------------------------------------------- #
def test_unlock_normal():
    print("\n== Escenario 1: desbloqueo normal ==")
    dev = FakeDevice(present=True)
    _install(dev)

    out = _run_capturing(lambda: unlooktool.unlock_bootloader(assume_yes=True))
    print("  --- salida del tool ---")
    for line in out.strip().splitlines():
        print(f"    | {line}")

    check("flashing unlock" in dev.issued, "emitio 'fastboot flashing unlock'")
    check(dev.state["unlocked"] == "yes", "el dispositivo quedo unlocked=yes")
    check("oem unlock" not in dev.issued, "NO uso el fallback (no hizo falta)")

    # Verificar que 'state' ahora reporta DESBLOQUEADO
    out2 = _run_capturing(unlooktool.bootloader_state)
    check("DESBLOQUEADO" in out2, "'state' reporta bootloader DESBLOQUEADO")


def test_unlock_fallback():
    print("\n== Escenario 2: fallback a 'oem unlock' ==")
    dev = FakeDevice(present=True, fail_flashing_unlock=True)
    _install(dev)

    _run_capturing(lambda: unlooktool.unlock_bootloader(assume_yes=True))
    check("flashing unlock" in dev.issued, "intento primero 'flashing unlock'")
    check("oem unlock" in dev.issued, "cayo al fallback 'oem unlock'")
    check(dev.state["unlocked"] == "yes", "el dispositivo quedo unlocked=yes")


def test_unlock_no_device():
    print("\n== Escenario 3: sin dispositivo conectado ==")
    dev = FakeDevice(present=False)
    _install(dev)

    out = _run_capturing(lambda: unlooktool.unlock_bootloader(assume_yes=True))
    check("No hay ningun dispositivo" in out, "avisa que no hay dispositivo")
    check(
        "flashing unlock" not in dev.issued and "oem unlock" not in dev.issued,
        "NO emitio ningun comando de desbloqueo",
    )


# --------------------------------------------------------------------------- #
def test_wipe_normal():
    print("\n== Escenario 4: wipe data normal ==")
    dev = FakeDevice(present=True)
    _install(dev)

    out = _run_capturing(lambda: unlooktool.wipe_data(assume_yes=True))
    print("  --- salida del tool ---")
    for line in out.strip().splitlines():
        print(f"    | {line}")

    check("-w" in dev.issued, "emitio 'fastboot -w' (formatea userdata)")
    check(dev.wiped, "el dispositivo quedo borrado")
    check("erase userdata" not in dev.issued, "NO uso el fallback (no hizo falta)")
    check("reboot" in dev.issued, "reinicio el dispositivo al terminar")


def test_wipe_fallback():
    print("\n== Escenario 5: wipe con fallback a 'erase' ==")
    dev = FakeDevice(present=True, fail_wipe=True)
    _install(dev)

    _run_capturing(lambda: unlooktool.wipe_data(assume_yes=True))
    check("-w" in dev.issued, "intento primero 'fastboot -w'")
    check("erase userdata" in dev.issued, "cayo al fallback 'erase userdata'")
    check("erase cache" in dev.issued, "y tambien 'erase cache'")
    check("reboot" in dev.issued, "reinicio el dispositivo al terminar")


def test_wipe_no_device():
    print("\n== Escenario 6: wipe sin dispositivo ==")
    dev = FakeDevice(present=False)
    _install(dev)

    out = _run_capturing(lambda: unlooktool.wipe_data(assume_yes=True))
    check("No hay ningun dispositivo" in out, "avisa que no hay dispositivo")
    check("-w" not in dev.issued and not dev.wiped, "NO borro nada")


def test_flash_ok():
    print("\n== Escenario 7: flash de ROM (carpeta con flash_all.bat) ==")
    import tempfile
    import shutil as _sh

    folder = tempfile.mkdtemp(prefix="rom_")
    script = os.path.join(folder, "flash_all.bat")
    with open(script, "w") as fh:
        fh.write("@echo simulacion de flasheo\n")

    calls: list[list[str]] = []

    def recorder(cmd, **kw):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    unlooktool.subprocess.run = recorder
    try:
        out = _run_capturing(lambda: unlooktool.flash_rom(folder, assume_yes=True))
        check(any("flash_all.bat" in " ".join(c) for c in calls),
              "ejecuto el flash_all.bat de la carpeta")
        check("Proceso de flasheo finalizado" in out, "reporto fin del flasheo")
    finally:
        _sh.rmtree(folder, ignore_errors=True)


def test_flash_invalid_folder():
    print("\n== Escenario 8: flash con carpeta inexistente ==")
    calls: list[list[str]] = []
    unlooktool.subprocess.run = lambda cmd, **kw: calls.append(list(cmd))  # type: ignore
    out = _run_capturing(lambda: unlooktool.flash_rom("Z:/no/existe", assume_yes=True))
    check("Carpeta no valida" in out, "avisa que la carpeta no es valida")
    check(not calls, "NO ejecuto ningun script")


def test_flash_missing_script():
    print("\n== Escenario 9: flash sin flash_all.bat en la carpeta ==")
    import tempfile
    import shutil as _sh

    folder = tempfile.mkdtemp(prefix="rom_vacia_")
    calls: list[list[str]] = []
    unlooktool.subprocess.run = lambda cmd, **kw: calls.append(list(cmd))  # type: ignore
    try:
        out = _run_capturing(lambda: unlooktool.flash_rom(folder, assume_yes=True))
        check("No encontre 'flash_all.bat'" in out, "avisa que falta flash_all.bat")
        check(not calls, "NO ejecuto ningun script")
    finally:
        _sh.rmtree(folder, ignore_errors=True)


def test_watch_rising_edge():
    print("\n== Escenario 10: vigilante abre la GUI solo al conectar ==")
    import unlooktool_watch as w

    # Secuencia de estados del USB que simulamos ver en cada sondeo:
    seq = [None, "adb", "adb", None, "fastboot"]
    counters = {"i": 0, "launch": 0}

    def fake_mode():
        i = counters["i"]
        counters["i"] += 1
        return seq[i] if i < len(seq) else None

    def fake_launch():
        counters["launch"] += 1

    def fake_notify(title, message):
        counters["notify"] = counters.get("notify", 0) + 1

    def fake_sleep(_):
        if counters["i"] >= len(seq):
            raise KeyboardInterrupt  # termina el bucle de watch()

    orig = (w.device_mode, w.launch_gui, w.notify, w.time.sleep)
    w.device_mode, w.launch_gui, w.notify, w.time.sleep = (
        fake_mode, fake_launch, fake_notify, fake_sleep)
    try:
        rc = w.watch(interval=0, launch=True, notify_on=True)
    finally:
        w.device_mode, w.launch_gui, w.notify, w.time.sleep = orig

    check(rc == 0, "watch() termino limpio")
    check(counters["launch"] == 2, "abrio la GUI 2 veces (2 conexiones), no en cada sondeo")
    check(counters.get("notify") == 2, "notifico 2 veces (una por conexion)")


def main() -> int:
    print("=" * 60)
    print(" SIMULACION - unlooktool (Mi A1 / tissot)")
    print("=" * 60)
    test_unlock_normal()
    test_unlock_fallback()
    test_unlock_no_device()
    test_wipe_normal()
    test_wipe_fallback()
    test_wipe_no_device()
    test_flash_ok()
    test_flash_invalid_folder()
    test_flash_missing_script()
    test_watch_rising_edge()

    print("\n" + "=" * 60)
    if _errors == 0:
        print(" RESULTADO: TODOS LOS TESTS PASARON ")
    else:
        print(f" RESULTADO: {_errors} COMPROBACION(ES) FALLARON ")
    print("=" * 60)
    return 1 if _errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
