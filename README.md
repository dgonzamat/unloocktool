# unlooktool

Utilidad de línea de comandos **para Windows** que envuelve `fastboot`/`adb`
para el **Xiaomi Mi A1** (codename **`tissot`**). Pensada para teléfonos cuyo
recovery/bootloader **no ofrece la opción "Wipe data / Factory reset"**: permite
hacer ese borrado, desbloquear el bootloader, flashear una ROM fastboot y otras
tareas de mantenimiento desde el PC.

> ℹ️ **El Mi A1 es Android One (no MIUI).** Se desbloquea directo con
> `fastboot flashing unlock` (comando `unlock`) — **sin Mi Unlock ni espera de
> 7 días**. Solo hay que activar antes *Desbloqueo de OEM* en Opciones de
> desarrollador.

> ⚠️ **Solo para tu propio dispositivo.** El *unlock*, el *wipe* y el *flash*
> **borran todos los datos** y son **irreversibles**. Con el bootloader
> bloqueado, `fastboot` no permite formatear ni escribir particiones. Esta
> herramienta **no** intenta sortear bloqueos de cuenta ni protección antirrobo (FRP).

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

### Interfaz gráfica (recomendada)

```bash
python unlooktool_gui.py
```

O en Windows, **doble clic en `unlooktool_gui.bat`**. Es una ventana con botones
para cada acción y un panel de salida. Las acciones destructivas (desbloquear,
wipe, flashear) piden confirmación en un cuadro de diálogo.

### Abrir la GUI automáticamente al conectar el teléfono

```bash
python install_autostart.py install     # arranca con Windows y abre la GUI al conectar
python install_autostart.py uninstall   # lo quita
python install_autostart.py status      # ¿está instalado?
```

Esto registra `unlooktool_watch.py` en la carpeta de Inicio de Windows (sin
permisos de admin). El vigilante sondea el USB y, cuando conectas el Mi A1 (en
modo **adb** con Depuración USB, o **fastboot**), muestra una **notificación de
Windows** y abre la GUI una sola vez. Para probarlo sin reiniciar:
`python unlooktool_watch.py`. Flags: `--interval N`, `--no-launch`, `--no-notify`.

> Nota: si el teléfono está en modo normal **sin** Depuración USB, adb no lo
> detecta (limitación de Android). Actívala en Opciones de desarrollador.

### Menú interactivo (consola)

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
python unlooktool.py unlock          # desbloquea el bootloader (Mi A1: sin Mi Unlock)
python unlooktool.py rom             # abre la ROM fastboot correcta (tissot)
python unlooktool.py reboot bootloader   # entra a modo fastboot
python unlooktool.py wipe            # wipe data / factory reset (pide confirmar)
python unlooktool.py flash <carpeta> # flashea una ROM fastboot extraída
python unlooktool.py reboot          # reinicia el sistema
```

El `wipe` y el `flash` piden escribir `BORRAR` para confirmar. Puedes saltar la
confirmación con `--yes` (con cuidado).

## Flujo completo recomendado (Mi A1)

1. `python unlooktool.py setup` → instala platform-tools y abre los drivers.
2. En el teléfono: **Opciones de desarrollador** → activa **Depuración USB** y
   **Desbloqueo de OEM**.
3. Conecta el teléfono y entra a fastboot: `python unlooktool.py reboot bootloader`
4. `python unlooktool.py state` → mira si está bloqueado/desbloqueado.
   - Si está **bloqueado**: `python unlooktool.py unlock` (confirma en la pantalla
     del teléfono con los botones de volumen/encendido).
5. `python unlooktool.py wipe` → escribe `BORRAR`.
6. (Opcional) Reinstalar sistema:
   - `python unlooktool.py rom` → descarga la ROM **fastboot** de tissot y extráela.
   - `python unlooktool.py flash <carpeta_de_la_rom>`

## Fuentes usadas

- **platform-tools (adb/fastboot):** servidor oficial de Google
  `dl.google.com/android/repository/platform-tools-latest-windows.zip`
- **Drivers USB Xiaomi:** <https://xiaomidriver.com/> ·
  **Google USB Driver:** <https://developer.android.com/studio/run/win-usb>
- **ROM fastboot Mi A1 (tissot):**
  <https://xiaomirom.com/en/rom/mi-a1-tissot-global-fastboot-recovery-rom/> ·
  <https://xmfirmwareupdater.com/?search=tissot>

## Descargo de responsabilidad

Software "tal cual", sin garantías. Modificar/borrar particiones puede dejar el
dispositivo inutilizable y anula la garantía. Úsalo bajo tu propia
responsabilidad y solo en equipos de tu propiedad. Ver [LICENSE](LICENSE).
