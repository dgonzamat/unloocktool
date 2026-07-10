# unlooktool

Utilidad de línea de comandos **para Windows** que envuelve `fastboot`/`adb`
para dispositivos **Xiaomi**. Pensada para teléfonos cuyo recovery/bootloader
**no ofrece la opción "Wipe data / Factory reset"**: permite hacer ese borrado,
flashear una ROM fastboot y otras tareas de mantenimiento desde el PC.

> ⚠️ **Solo para tu propio dispositivo.** El *wipe* y el *flash* requieren el
> **bootloader desbloqueado** (proceso oficial **Mi Unlock**). Con el bootloader
> bloqueado, `fastboot` no permite formatear ni escribir particiones. El borrado
> es **irreversible**. Esta herramienta **no** intenta sortear bloqueos de
> cuenta Mi ni protección antirrobo (FRP).

## Qué automatiza

- ⬇️ Descarga e instalación de **Android platform-tools** (adb/fastboot) desde el
  servidor **oficial de Google**.
- 🔌 Apertura de las páginas oficiales de **drivers USB** y **Mi Unlock**.
- 🔎 **Autodetección del modelo** (codename) y apertura de la **fuente de ROM
  correcta** — las ROMs son específicas de cada modelo, así que no se descargan
  "genéricas".
- 🧹 **Wipe data / factory reset** vía fastboot.
- 💽 **Flasheo** de una ROM fastboot ya descargada (ejecuta su `flash_all.bat`).

## Requisitos

- **Windows 10/11**
- **Python 3.9+** — <https://www.python.org/downloads/> (marca *Add Python to PATH*)
- **Drivers USB de Xiaomi** (los instala el paso `setup`)

No hay dependencias de terceros: usa solo la librería estándar de Python.

## Instalación

```bash
git clone https://github.com/dgonzamat/unloocktool.git
cd unloocktool
python unlooktool.py setup
```

`setup` descarga `platform-tools` en una carpeta local y abre las páginas de
drivers y Mi Unlock. En Windows también puedes **hacer doble clic en
`unlooktool.bat`** para abrir el menú.

## Uso

### Menú interactivo

```bash
python unlooktool.py
```

### Comandos directos

```bash
python unlooktool.py setup           # descarga platform-tools + abre drivers/MiUnlock
python unlooktool.py drivers         # abre páginas de drivers USB
python unlooktool.py devices         # lista dispositivos (adb y fastboot)
python unlooktool.py info            # datos del dispositivo (codename, etc.)
python unlooktool.py state           # estado del bootloader (locked/unlocked)
python unlooktool.py rom             # detecta codename y abre la ROM correcta
python unlooktool.py reboot bootloader   # entra a modo fastboot
python unlooktool.py wipe            # wipe data / factory reset (pide confirmar)
python unlooktool.py flash <carpeta> # flashea una ROM fastboot extraída
python unlooktool.py reboot          # reinicia el sistema
```

El `wipe` y el `flash` piden escribir `BORRAR` para confirmar. Puedes saltar la
confirmación con `--yes` (con cuidado).

## Flujo completo recomendado

1. `python unlooktool.py setup` → instala platform-tools e instala los drivers.
2. Habilita **Depuración USB** (Opciones de desarrollador) si el sistema arranca.
3. Conecta el teléfono y entra a fastboot: `python unlooktool.py reboot bootloader`
4. `python unlooktool.py state` → confirma **DESBLOQUEADO**.
   - Si está **bloqueado**: desbloquea con **Mi Unlock** (link que abre `setup`).
5. `python unlooktool.py wipe` → escribe `BORRAR`.
6. (Opcional) Reinstalar sistema:
   - `python unlooktool.py rom` → descarga la ROma **fastboot** de tu modelo y extráela.
   - `python unlooktool.py flash <carpeta_de_la_rom>`

## Fuentes usadas

- **platform-tools (adb/fastboot):** servidor oficial de Google
  `dl.google.com/android/repository/platform-tools-latest-windows.zip`
- **Mi Unlock (oficial Xiaomi):** <https://en.miui.com/unlock/>
- **Drivers USB Xiaomi:** <https://xiaomidriver.com/> ·
  **Google USB Driver:** <https://developer.android.com/studio/run/win-usb>
- **ROMs por codename:** <https://xmfirmwareupdater.com/> · <https://xiaomirom.com/en/>

## Descargo de responsabilidad

Software "tal cual", sin garantías. Modificar/borrar particiones puede dejar el
dispositivo inutilizable y anula la garantía. Úsalo bajo tu propia
responsabilidad y solo en equipos de tu propiedad. Ver [LICENSE](LICENSE).
