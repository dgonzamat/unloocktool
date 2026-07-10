#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unlooktool_gui - Interfaz grafica (Tkinter) para unlooktool.

Envuelve el CLI (unlooktool.py) en una ventana con botones y un panel de log.
Las acciones que borran datos (unlock / wipe / flash) piden confirmacion en un
cuadro de dialogo y se ejecutan con --yes.

Requiere solo la libreria estandar de Python (tkinter incluido).
Ejecutar:  python unlooktool_gui.py   (o doble clic en unlooktool_gui.bat)
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, "unlooktool.py")
TOOLS_DIR = os.path.join(HERE, "platform-tools")

# Datos del dispositivo (deben coincidir con unlooktool.py)
DEVICE_NAME = "Xiaomi Mi A1"
DEVICE_CODENAME = "tissot"


class UnlooktoolGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.q: queue.Queue[str] = queue.Queue()
        self.running = False
        self.proc: subprocess.Popen | None = None

        root.title(f"unlooktool - {DEVICE_NAME} ({DEVICE_CODENAME})")
        root.geometry("760x560")
        root.minsize(680, 480)

        self._build_header()
        self._build_buttons()
        self._build_log()
        self._build_statusbar()

        self._poll_queue()
        self.refresh_status()

    # ------------------------------------------------------------------ UI
    def _build_header(self) -> None:
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="unlooktool", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(
            top,
            text=f"  {DEVICE_NAME} · codename {DEVICE_CODENAME} · Android One",
            font=("Segoe UI", 10),
            foreground="#666",
        ).pack(side="left")

    def _build_buttons(self) -> None:
        wrap = ttk.Frame(self.root, padding=(12, 4))
        wrap.pack(fill="x")

        # (texto, comando_cli, destructivo?, tooltip)
        rows = [
            [
                ("1. Setup (adb/fastboot + drivers)", "setup", False),
                ("2. Listar dispositivos", "devices", False),
                ("3. Info del dispositivo", "info", False),
            ],
            [
                ("4. Estado del bootloader", "state", False),
                ("5. Desbloquear bootloader", "unlock", True),
                ("6. Descargar ROM (tissot)", "rom", False),
            ],
            [
                ("7. Reboot -> fastboot", "reboot bootloader", False),
                ("8. WIPE DATA / Factory reset", "wipe", True),
                ("9. Flashear ROM fastboot...", "__flash__", True),
            ],
            [
                ("10. Reboot -> recovery", "reboot recovery", False),
                ("11. Reboot -> sistema", "reboot", False),
                ("Limpiar log", "__clear__", False),
            ],
        ]

        style = ttk.Style()
        try:
            style.theme_use("vista" if os.name == "nt" else style.theme_use())
        except tk.TclError:
            pass
        style.configure("Danger.TButton", foreground="#b00020")

        self.buttons: list[ttk.Button] = []
        for row in rows:
            fr = ttk.Frame(wrap)
            fr.pack(fill="x", pady=3)
            for (text, cmd, danger) in row:
                btn = ttk.Button(
                    fr, text=text, width=30,
                    style="Danger.TButton" if danger else "TButton",
                    command=lambda c=cmd, d=danger, t=text: self.on_action(c, d, t),
                )
                btn.pack(side="left", expand=True, fill="x", padx=3)
                if cmd not in ("__clear__",):
                    self.buttons.append(btn)

    def _build_log(self) -> None:
        fr = ttk.Frame(self.root, padding=(12, 6))
        fr.pack(fill="both", expand=True)
        ttk.Label(fr, text="Salida:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(
            fr, wrap="word", height=14, font=("Consolas", 9),
            background="#1e1e1e", foreground="#dcdcdc", insertbackground="#dcdcdc",
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

    def _build_statusbar(self) -> None:
        self.status = tk.StringVar(value="Listo.")
        bar = ttk.Frame(self.root, relief="sunken", padding=(8, 3))
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status, font=("Segoe UI", 9)).pack(side="left")
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=140)
        self.progress.pack(side="right")
        self.cancel_btn = ttk.Button(bar, text="Cancelar", command=self.cancel, state="disabled")
        self.cancel_btn.pack(side="right", padx=(0, 8))

    # -------------------------------------------------------------- helpers
    def _write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _tool_present(self, name: str) -> bool:
        exe = name + (".exe" if os.name == "nt" else "")
        return os.path.isfile(os.path.join(TOOLS_DIR, exe))

    def refresh_status(self) -> None:
        adb = "OK" if self._tool_present("adb") else "falta"
        fb = "OK" if self._tool_present("fastboot") else "falta"
        extra = "" if adb == "OK" else "  (ejecuta Setup)"
        self.status.set(f"adb: {adb}   |   fastboot: {fb}{extra}")

    def _set_running(self, running: bool) -> None:
        self.running = running
        for b in self.buttons:
            b.configure(state="disabled" if running else "normal")
        self.cancel_btn.configure(state="normal" if running else "disabled")
        if running:
            self.progress.start(12)
        else:
            self.progress.stop()
            self.refresh_status()

    def cancel(self) -> None:
        """Termina el proceso en curso (p. ej. si fastboot quedo esperando)."""
        proc = self.proc
        if proc and proc.poll() is None:
            self.q.put("\n[i] Cancelando por peticion del usuario...\n")
            try:
                proc.terminate()
            except Exception as exc:  # noqa: BLE001
                self.q.put(f"[!] No se pudo cancelar: {exc}\n")

    # --------------------------------------------------------------- actions
    def on_action(self, cmd: str, danger: bool, label: str) -> None:
        if self.running:
            return
        if cmd == "__clear__":
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.configure(state="disabled")
            return

        if cmd == "__flash__":
            folder = filedialog.askdirectory(title="Carpeta de la ROM fastboot extraida")
            if not folder:
                return
            if not messagebox.askyesno(
                "Confirmar flasheo",
                "Esto REESCRIBE el firmware y BORRA el telefono.\n\n"
                f"Carpeta:\n{folder}\n\n¿Continuar?",
                icon="warning",
            ):
                return
            self.run_cli(["flash", folder, "--yes"], label)
            return

        if danger:
            msg = {
                "unlock": "Desbloquear el bootloader BORRA todos los datos del "
                          "telefono.\nDeberas confirmar tambien en la pantalla del "
                          "telefono.\n\n¿Continuar?",
                "wipe": "WIPE DATA borra TODOS los datos de usuario.\n"
                        "Es irreversible.\n\n¿Continuar?",
            }.get(cmd, "Esta accion es destructiva. ¿Continuar?")
            if not messagebox.askyesno("Confirmar", msg, icon="warning"):
                return
            self.run_cli(cmd.split() + ["--yes"], label)
            return

        self.run_cli(cmd.split(), label)

    def run_cli(self, args: list[str], label: str) -> None:
        self._set_running(True)
        self._write(f"\n{'='*60}\n>>> {label}\n{'='*60}\n")
        self.status.set(f"Ejecutando: {label} ...")
        t = threading.Thread(target=self._worker, args=(args,), daemon=True)
        t.start()

    def _worker(self, args: list[str]) -> None:
        cmd = [sys.executable, CLI, *args]
        try:
            proc = subprocess.Popen(
                cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, bufsize=1,
            )
            self.proc = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                self.q.put(line)
            proc.wait()
            self.q.put(f"\n[proceso finalizado, codigo {proc.returncode}]\n")
        except Exception as exc:  # noqa: BLE001
            self.q.put(f"\n[!] Error al ejecutar: {exc}\n")
        finally:
            self.proc = None
            self.q.put("__DONE__")

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.q.get_nowait()
                if item == "__DONE__":
                    self._set_running(False)
                    self.status.set("Listo.")
                else:
                    self._write(item)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_queue)


def main() -> int:
    if not os.path.isfile(CLI):
        print(f"[!] No encuentro {CLI}. Coloca unlooktool_gui.py junto a unlooktool.py.")
        return 1
    root = tk.Tk()
    UnlooktoolGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
