# unlooktool

Utilidad de línea de comandos para dispositivos **Xiaomi** que envuelve
`fastboot`/`adb`. Pensada para teléfonos cuyo recovery/bootloader **no ofrece
la opción "Wipe data / Factory reset"**: permite hacer ese borrado (y otras
operaciones de mantenimiento) desde el PC.

> ⚠️ **Solo para tu propio dispositivo.** El *wipe* requiere el **bootloader
> desbloqueado** (con el bootloader bloqueado, `fastboot` no permite formatear
> `userdata`). El borrado es **irreversible**.

## Requisitos

- **Python 3.9+**
- **Android platform-tools** (`adb` y `fastboot`) en el `PATH`, o copiados en
  una carpeta `platform-tools/` junto al script.
  Descarga: <https://developer.android.com/tools/releases/platform-tools>
- **Drivers USB** de Xiaomi instalados (Windows).

## Instalación

```bash
git clone https://github.com/<tu-usuario>/unlooktool.git
cd unlooktool
```

No hay dependencias de terceros: usa solo la librería estándar de Python.

## Uso

### Menú interactivo

```bash
python unlooktool.py
```

### Comandos directos

```bash
python unlooktool.py devices        # lista dispositivos (adb y fastboot)
python unlooktool.py state          # estado del bootloader (locked/unlocked)
python unlooktool.py reboot bootloader   # entra a modo fastboot
python unlooktool.py wipe           # wipe data / factory reset (pide confirmar)
python unlooktool.py reboot recovery
python unlooktool.py reboot         # reinicia el sistema
```

El comando `wipe` pide escribir `BORRAR` para confirmar. Puedes saltar la
confirmación con `--yes` (úsalo con cuidado en scripts).

## Flujo típico de "wipe data"

1. Habilita **Depuración USB** en Opciones de desarrollador (si el sistema arranca).
2. Conecta el teléfono por USB.
3. `python unlooktool.py reboot bootloader`
4. `python unlooktool.py state`  → confirma que aparece **DESBLOQUEADO**.
5. `python unlooktool.py wipe`  → escribe `BORRAR` para confirmar.

Si el bootloader está **bloqueado**, primero debes desbloquearlo con el proceso
**oficial de Xiaomi (Mi Unlock)**. Esta herramienta no intenta sortear ningún
bloqueo de cuenta ni protección antirrobo.

## Descargo de responsabilidad

Este software se entrega "tal cual", sin garantías. Modificar/borrar la
partición de datos puede dejar el dispositivo inutilizable si se hace mal y
anula la garantía. Úsalo bajo tu propia responsabilidad y solo en equipos de
tu propiedad. Ver [LICENSE](LICENSE).
